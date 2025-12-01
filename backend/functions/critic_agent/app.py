import json
import os
import re
import boto3
from datetime import datetime
from decimal import Decimal



dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')
events_client = boto3.client('events')

TABLE_NAME = os.environ['DYNAMODB_TABLE']
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    try:
        payload = event.get('detail', event)
        print(f"Processing payload: {json.dumps(sanitize_for_json(payload))}")

        
        pk = payload['pk']
        chat_sk = payload['chat_sk']
        
        chat_item = fetch_chat(pk, chat_sk)
        genome_sk = derive_genome_sk(chat_sk)
        genome_item = fetch_genome(pk, genome_sk)
        
        critic_result = call_bedrock(chat_item, genome_item)
        print(f"Critic result: {json.dumps(sanitize_for_json(critic_result))}")
        
        update_chat(pk, chat_sk, critic_result)
        
        if critic_result['verdict'] == 'FAIL':
            emit_event(pk, chat_sk, genome_sk, critic_result)
        
        return {
            'statusCode': 200,
            'body': json.dumps(sanitize_for_json(critic_result))

        }
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        raise

def fetch_chat(pk, chat_sk):
    response = table.get_item(Key={'PK': pk, 'SK': chat_sk})
    if 'Item' not in response:
        raise ValueError(f"Chat not found: {pk}/{chat_sk}")
    return sanitize_for_json(response['Item'])


def fetch_genome(pk, genome_sk):
    response = table.get_item(Key={'PK': pk, 'SK': genome_sk})
    if 'Item' not in response:
        raise ValueError(f"Genome not found: {pk}/{genome_sk}")
    return sanitize_for_json(response['Item'])


def sanitize_for_json(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    else:
        return obj

def derive_genome_sk(chat_sk):
    if '#CHAT#' not in chat_sk:
        raise ValueError(f"Invalid chat_sk format: {chat_sk}")
    return chat_sk.split('#CHAT#')[0]

  # Add this to your imports

def call_bedrock(chat_item, genome_item):
    transcript = chat_item.get('transcript', [])
    brain = genome_item.get('brain', {})
    resources = genome_item.get('resources', {})
    evolution_config = genome_item.get('evolution_config', {})
    
    persona = brain.get('persona', {})
    objectives = brain.get('objectives', [])
    operational_guidelines = brain.get('operational_guidelines', [])
    knowledge_base = resources.get('knowledge_base_text', '')
    policy_text = resources.get('policy_text', '')
    critic_rules = evolution_config.get('critic_rules', [])
    
    if not critic_rules:
        raise ValueError("No critic_rules found in genome evolution_config")
    
    # 1. Prepare prompts
    # We switch to a generic "Chain of Thought" system prompt
    system_prompt_text = build_system_prompt()
    
    # Your existing build_user_prompt handles the dynamic domain content perfectly
    user_prompt_text = build_user_prompt(transcript, persona, objectives, operational_guidelines, 
                                         knowledge_base, policy_text, critic_rules)
    
    # 2. Format for Bedrock Converse API (Nova Pro)
    messages = [{
        "role": "user",
        "content": [{"text": user_prompt_text}]
    }]
    
    system_prompts = [{"text": system_prompt_text}]
    
    inference_config = {
        "temperature": 0.0,
        "maxTokens": 2000 # Increased to allow for reasoning text before JSON
    }

    try:
        # 3. Invoke Amazon Nova Pro (General Purpose Intelligence)
        response = bedrock.converse(
            modelId='us.amazon.nova-pro-v1:0',
            messages=messages,
            system=system_prompts,
            inferenceConfig=inference_config
        )
        
        # 4. Parse Response
        output_message = response['output']['message']
        content_text = output_message['content'][0]['text']
        
        # 5. Robust Extraction: Find JSON strictly within markdown or brackets
        # This handles cases where the model "thinks" out loud before outputting JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', content_text, re.DOTALL)
        
        if json_match:
            clean_json = json_match.group(1)
        else:
            # Fallback: Find the outer-most curly braces
            start_index = content_text.find('{')
            end_index = content_text.rfind('}')
            if start_index != -1 and end_index != -1:
                clean_json = content_text[start_index : end_index + 1]
            else:
                # If no JSON found, log the raw text for debugging
                print(f"FAILED PARSE. Raw Output: {content_text}")
                raise ValueError("No JSON object found in LLM response")
        
        result = json.loads(clean_json)
        
    except Exception as e:
        print(f"Bedrock invocation or parsing failed: {str(e)}")
        raise ValueError(f"Bedrock error: {str(e)}")
    
    if 'verdict' not in result or result['verdict'] not in ['PASS', 'FAIL']:
        raise ValueError(f"Invalid verdict in result: {result}")
    
    return result

def build_system_prompt():
    return """You are a strict Quality Assurance Auditor for AI agent conversations.

Your task is to evaluate the assistant's responses strictly against the provided "CRITIC RULES".

Use this Step-by-Step Reasoning Process:
1.  **Analyze User Intent:** What was the user trying to achieve or ask?
2.  **Audit Assistant Response:** Did the assistant answer correctly based on the Knowledge Base?
3.  **Check Critic Rules:** Go through the provided 'CRITIC RULES' list one by one.
    - If the assistant violated ANY rule, the verdict is FAIL.
    - If the assistant missed a required action stated in the rules (e.g., "FAIL if X is not mentioned"), the verdict is FAIL.
4.  **Final Verdict:** Determine PASS or FAIL.

**OUTPUT FORMAT:**
After your internal reasoning, you must output a single valid JSON block:

```json
{
  "audit_metadata": {
    "auditor": "CriticAgent-NovaPro",
    "timestamp": "ISO8601 timestamp"
  },
  "verdict": "PASS" or "FAIL",
  "failure_detail": {
    "turn_index": <integer or null>,
    "violation_category": "The exact text of the violated rule",
    "reasoning": "A concise explanation of why it failed"
  }
}
"""
def build_user_prompt(transcript, persona, objectives, operational_guidelines, 
                      knowledge_base, policy_text, critic_rules):
    
    transcript_text = format_transcript_with_turns(transcript)
    
    genome_dna = f"""<genome_dna>
PERSONA:
Role: {persona.get('role', 'N/A')}
Tone: {persona.get('tone', 'N/A')}

OBJECTIVES:
{format_list(objectives)}

OPERATIONAL GUIDELINES:
{format_list(operational_guidelines)}

KNOWLEDGE BASE:
{knowledge_base}
</genome_dna>"""
    
    policy_section = f"""<policy>
{policy_text}
</policy>"""
    
    transcript_section = f"""<transcript>
{transcript_text}
</transcript>"""
    
    critic_rules_text = format_list(critic_rules)
    
    prompt = f"""Audit the following conversation transcript against the critic rules.

{genome_dna}

{policy_section}

CRITIC RULES (FAIL if ANY of these are violated):
{critic_rules_text}

{transcript_section}

Evaluate each assistant response in the transcript. If ANY critic rule is violated, return FAIL with the exact turn_index where it occurred. If NO rules are violated, return PASS.

Current timestamp: {datetime.utcnow().isoformat()}Z

Output only valid JSON."""
    
    return prompt

def format_transcript_with_turns(transcript):
    lines = []
    for idx, msg in enumerate(transcript):
        role = msg.get('role', 'unknown').capitalize()
        content = msg.get('content', '')
        lines.append(f"[{idx}] {role}: {content}")
    return '\n'.join(lines)

def format_list(items):
    if not items:
        return "None"
    if isinstance(items, list):
        return '\n'.join(f"- {item}" for item in items)
    return str(items)

def update_chat(pk, chat_sk, critic_result):
    verdict = critic_result['verdict']
    failure_detail = critic_result.get('failure_detail', {})
    
    update_expr = "SET critic_verdict = :verdict, critic_reason = :reason, failure_turn_index = :turn_idx, updated_at = :updated"
    expr_values = {
        ':verdict': verdict,
        ':reason': failure_detail.get('reasoning') if verdict == 'FAIL' else None,
        ':turn_idx': failure_detail.get('turn_index') if verdict == 'FAIL' else None,
        ':updated': datetime.utcnow().isoformat()
    }
    
    table.update_item(
        Key={'PK': pk, 'SK': chat_sk},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values
    )
    print(f"Updated chat {pk}/{chat_sk} with verdict: {verdict}")

def emit_event(pk, chat_sk, genome_sk, critic_result):
    failure_detail = critic_result.get('failure_detail', {})
    reason = failure_detail.get('reasoning', 'Critic rule violation detected')
    
    event_detail = {
        'pk': pk,
        'chat_sk': chat_sk,
        'genome_sk': genome_sk,
        'reason': reason
    }
    
    events_client.put_events(
        Entries=[
            {
                'Source': 'ai.critic',
                'DetailType': 'EvaluationPassed',
                'Detail': json.dumps(event_detail)
            }
        ]
    )
    print(f"Emitted EvaluationPassed event for {pk}/{chat_sk}")
