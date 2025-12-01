import json
import os
import boto3
from datetime import datetime
import uuid
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

table_name = os.environ['DYNAMODB_TABLE']
table = dynamodb.Table(table_name)
def sanitize_for_json(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    else:
        return obj

def lambda_handler(event, context):
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        pk = body['pk']
        chat_id = body['chat_id']
        feedback = body['feedback']
        feedback_type = feedback['type']
        feedback_comment = feedback.get('comment', '')
        
        current_response = table.get_item(Key={'PK': pk, 'SK': 'CURRENT'})
        if 'Item' not in current_response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'CURRENT pointer not found'})
            }
        
        active_version_sk = current_response['Item']['active_version_sk']
        
        genome_response = table.get_item(Key={'PK': pk, 'SK': active_version_sk})
        if 'Item' not in genome_response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Genome not found'})
            }
        
        genome = genome_response['Item']
        
        if feedback_type == 'like':
            current_likes = int(genome.get('economics', {}).get('likes', 0))
            table.update_item(
                Key={'PK': pk, 'SK': active_version_sk},
                UpdateExpression='SET economics.likes = :likes',
                ExpressionAttributeValues={':likes': Decimal(current_likes + 1)}
            )
        elif feedback_type == 'dislike':
            current_dislikes = int(genome.get('economics', {}).get('dislikes', 0))
            table.update_item(
                Key={'PK': pk, 'SK': active_version_sk},
                UpdateExpression='SET economics.dislikes = :dislikes',
                ExpressionAttributeValues={':dislikes': Decimal(current_dislikes + 1)}
            )
        
        chat_sk = f"{active_version_sk}#CHAT#{chat_id}"
        chat_response = table.get_item(Key={'PK': pk, 'SK': chat_sk})
        
        if feedback_type == 'dislike':
            chat_transcript = ''
            if 'Item' in chat_response:
                chat_item = chat_response['Item']
                messages = chat_item.get('messages', [])
                for msg in messages:
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    chat_transcript += f"{role}: {content}\n\n"
            
            brain_section = genome.get('brain', {})
            brain_text = json.dumps(sanitize_for_json(brain_section), indent=2)

            
            system_prompt = """You are a senior AI behavior analyst for a multi-tenant AI platform.

You analyze negative user feedback about AI conversations in order to improve long-term agent behavior.

You are given:
- A conversation transcript showing the agent’s actual responses
- The agent’s “brain”, describing its goals, style, constraints, and intended direction
- A user’s explicit feedback comment

Your task is to:
1) Diagnose the precise cause of dissatisfaction using concrete signals from the transcript and the brain (do not rely on generic UX explanations).
2) Decide whether the agent already had enough contextual information to make a strong recommendation.
3) Propose ONE OR TWO specific behavior changes the agent should adopt in similar situations going forward that:
   - Reduce cognitive overload
   - Demonstrate better judgment or decisiveness
   - Align with the agent’s intended long-term behavior as defined in its brain

Important rules:
- Do NOT give vague advice like “be more concise”, “summarize”, or “ask clarifying questions” unless no contextual decision is reasonably possible.
- Do NOT assume or invent any industry, business domain, or user intent that is not evidenced in the transcript or brain.
- Prefer the agent making a context-informed primary recommendation over listing many parallel options, unless the brain explicitly requires exhaustiveness.
- Think in terms of long-term agent evolution, not just this single response.

Output STRICTLY valid JSON, with no extra text, in the following format:

{
  "insight": "<1 clear, specific sentence explaining what went wrong>",
  "recommended_behavior": "<1–2 sentences describing how the agent should behave differently in the future>",
  "improved_response_example": "<2–4 sentences showing how the agent should have responded in this exact situation>"
}
"""
            
            user_prompt = f"""Chat Transcript:
{chat_transcript}

Genome Brain Section:
{brain_text}

User Comment:
{feedback_comment if feedback_comment else 'No comment provided'}

Analyze the dissatisfaction and suggest a fix."""
            
            try:
                # UPDATE: Use Amazon Nova Pro (First-party, RBI safe)
                # Using the Converse API standard
                bedrock_response = bedrock_runtime.converse(
                    modelId='us.amazon.nova-pro-v1:0',
                    messages=[{
                        'role': 'user', 
                        'content': [{'text': user_prompt}]
                    }],
                    system=[{'text': system_prompt}],
                    inferenceConfig={
                        'maxTokens': 1000,
                        'temperature': 0.0
                    }
                )
                
                # Parse Converse API response
                ai_analysis = bedrock_response['output']['message']['content'][0]['text']
                
                if ai_analysis.strip() == 'NOT_POSSIBLE':
                    ai_analysis = 'No actionable fix identified'
                    
            except Exception as e:
                # Log the actual error for debugging if needed
                print(f"Nova generation failed: {str(e)}")
                ai_analysis = 'No actionable fix identified'
              
               
            ticket_id = str(uuid.uuid4())
            ticket_sk = f"{active_version_sk}#TICKET#{ticket_id}"
            
            ticket_item = {
                'PK': pk,
                'SK': ticket_sk,
                'EntityType': 'Ticket',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'type': 'USER',
                'status': 'OPEN',
                'chat_sk': chat_sk,
                'challenger_sk': 'NA',
                'feedback': feedback_comment if feedback_comment else 'User disliked response',
                'ai_analysis': ai_analysis
            }
            
            table.put_item(Item=ticket_item)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Feedback processed successfully'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
