import json
import os
import boto3
import logging
import uuid
import re
import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal
from botocore.exceptions import ClientError

# --- CONFIGURATION ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
# region_name='us-east-1' is REQUIRED for Cross-Region Inference Profiles (us.amazon...)
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'DarwinianGenePool')
table = dynamodb.Table(TABLE_NAME)

# JUDGE MODEL: The "Brain" that evaluates the results.
# We use Nova Premier for the highest reasoning capability.
JUDGE_MODEL_ID = 'us.amazon.nova-premier-v1:0'

# --- HELPER: Handle DynamoDB Decimals ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def sanitize_for_json(obj):
    """
    Recursively convert DynamoDB Decimal objects into JSON-safe types.
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    return obj

def get_item(pk, sk):
    """
    Helper to fetch a single item from DynamoDB.
    """
    try:
        resp = table.get_item(Key={'PK': pk, 'SK': sk})
        return resp.get('Item')
    except Exception as e:
        logger.error(f"DB Read Error {pk}/{sk}: {e}")
        return None

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"JUDGE EVENT: {json.dumps(event, cls=DecimalEncoder)}")

    # 1. PARSE INPUT (From Step Function Payload)
    try:
        # Step Function passes { "mutatorResult": ..., "originalInput": ... }
        mutator_payload = event.get('mutatorResult', {})
        original_input = event.get('originalInput', {})
        
        # Handle cases where mutatorResult might be nested inside 'Payload' 
        if 'Payload' in mutator_payload:
            mutator_payload = mutator_payload['Payload']
            
        challenger_sks = mutator_payload.get('challenger_sks', [])
        
        # Extract Details
        detail = original_input.get('detail', {})
        pk = detail.get('pk')
        genome_sk = detail.get('genome_sk')
        chat_sk = detail.get('chat_sk', f"{genome_sk}#CHAT#abc-123")
        
        # Extract Retry Count (Vital for Logic)
        retry_count = original_input.get('retryCount', 0)

    except Exception as e:
        logger.error(f"Input Parsing Error: {e}")
        raise ValueError(f"Structure Mismatch: {str(e)}")

    # 2. FETCH DATA FROM DYNAMODB
    original_genome = sanitize_for_json(get_item(pk, genome_sk))
    original_chat = sanitize_for_json(get_item(pk, chat_sk))
    
    if not original_genome or not original_chat:
        raise ValueError(f"Missing Data. PK: {pk}")

    # 3. PREPARE EVALUATION CONTEXT
    transcript = original_chat.get('transcript', [])
    failure_index = int(original_chat.get('failure_turn_index', len(transcript) - 1))
    
    # We slice the transcript up to the failure point so the simulator acts from there
    truncated_transcript = transcript[:failure_index]
    
    original_bad_response = transcript[failure_index]['content']
    critic_reason = original_chat.get('critic_reason', 'Unknown failure')

    # 4. RUN CHALLENGERS (Dynamic Simulation)
    candidate_responses = []
    
    for sk in challenger_sks:
        challenger_genome = sanitize_for_json(get_item(pk, sk))
        if not challenger_genome: 
            continue

        # We construct a composite genome:
        # - New Brain (Mutation)
        # - New Config (Model settings)
        # - Old Resources/Capabilities (Unless mutated, usually static)
        composite_genome = {
            'brain': challenger_genome.get('brain', {}),
            'config': challenger_genome.get('config', original_genome.get('config', {})),
            'resources': original_genome.get('resources', {}),
            'capabilities': original_genome.get('capabilities', {})
        }
        
        try:
            # DYNAMIC SIMULATION: Runs on the model the GENOME asks for (Environment Parity)
            new_response = invoke_agent_simulation(composite_genome, truncated_transcript)
            candidate_responses.append({
                'challenger_sk': sk,
                'response': new_response
            })
        except Exception as e:
            logger.error(f"Failed to sim challenger {sk}: {e}")

    # 5. STAGE 1: COMPARATOR (Uses JUDGE_MODEL_ID - Nova Premier)
    # Compares the new responses against the original bad response
    winner = run_comparator_stage(
        critic_reason, 
        original_bad_response, 
        candidate_responses, 
        truncated_transcript
    )

    # 6. LOGIC BRANCHING (Retry vs Ticket vs Success)
    
    # CASE A: No Comparator Winner
    if not winner:
        logger.info("Comparator found no improvement.")
        result = handle_failure(pk, genome_sk, chat_sk, retry_count, reason="No challenger improved on the failure.")
        return json.loads(json.dumps(result, cls=DecimalEncoder))

    # CASE B: Candidate Improved, check Compliance (Uses JUDGE_MODEL_ID - Nova Premier)
    compliance_result = run_compliance_stage(
        winner['response'],
        original_genome,
        truncated_transcript
    )

    if compliance_result['passed']:
        # CASE C: SUCCESS
        logger.info("JUDGE SUCCESS: Challenger selected.")
        result = {
            "improved": True,
            "selected_challenger_sk": winner['challenger_sk'],
            "improved_response": winner['response'],
            "reason": compliance_result['reason'],
            "retryCount": retry_count
        }
        return json.loads(json.dumps(result, cls=DecimalEncoder))
    else:
        # CASE D: Compliance Failed
        reason = f"Improved logic but failed Compliance: {compliance_result['reason']}"
        result = handle_failure(pk, genome_sk, chat_sk, retry_count, reason=reason, failed_challenger=winner['challenger_sk'])
        return json.loads(json.dumps(result, cls=DecimalEncoder))


# --- FAILURE HANDLER (TICKET LOGIC) ---

def handle_failure(pk, genome_sk, chat_sk, retry_count, reason, failed_challenger=None):
    """
    Decides whether to trigger a retry loop (via Step Functions) 
    or create a Failure Ticket in DynamoDB.
    """
    
    # Logic: If we haven't maxed retries (e.g., retry_count < 1), just return False.
    # The Step Function "Choice" state will see "improved": False and route to Mutator.
    if retry_count < 1:
        logger.info(f"Attempt {retry_count} failed. Signaling Step Function to Retry.")
        return {
            "improved": False,
            "reason": reason,
            "retryCount": retry_count
        }
    
    # Logic: If we ARE at max retries, create the ticket.
    else:
        logger.warning(f"Final Attempt {retry_count} failed. Creating TICKET.")
        
        ticket_id = f"xyz-{uuid.uuid4().hex[:6]}" # Placeholder style
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        
        # Parse Version from Genome SK to maintain hierarchy
        version_prefix = genome_sk 
        ticket_sk = f"{version_prefix}#TICKET#{ticket_id}"
        
        ticket_item = {
            "PK": pk,
            "SK": ticket_sk,
            "EntityType": "Ticket",
            "timestamp": timestamp,
            "type": "SYSTEM",
            "status": "OPEN",
            "chat_sk": chat_sk,
            "challenger_sk": failed_challenger if failed_challenger else "NONE_SELECTED",
            "feedback": "Automated Alert: Judge marked evolution as FAIL after retries.",
            "ai_analysis": reason
        }
        
        try:
            # Serialize Decimals for DynamoDB Write
            item_db = json.loads(json.dumps(ticket_item), parse_float=Decimal)
            table.put_item(Item=item_db)
            logger.info(f"✅ Ticket created: {ticket_sk}")
        except Exception as e:
            logger.error(f"Failed to write ticket: {e}")
            
        return {
            "improved": False,
            "reason": f"Final Failure. Ticket Created: {ticket_id}",
            "ticket_sk": ticket_sk,
            "retryCount": retry_count
        }


# --- EVALUATION LOGIC ---

def run_comparator_stage(issue: str, bad_resp: str, candidates: List[Dict], history: List[Dict]) -> Optional[Dict]:
    if not candidates:
        return None
        
    last_user_msg = history[-1]['content'] if history else "Start"
    
    candidate_list_json = json.dumps(
        sanitize_for_json([{'id': i, 'text': c['response']} for i, c in enumerate(candidates)]), 
        indent=2
    )

    prompt = f"""You are a QA Comparator.
CRITIC ISSUE: {issue}
USER INPUT: "{last_user_msg}"
ORIGINAL FAIL: "{bad_resp}"

CANDIDATES:
{candidate_list_json}

TASK: Return JSON {{ "winner_id": int or -1, "reason": "string" }}. 
Select the candidate that BEST resolves the Critic Issue. If none, return -1."""

    try:
        # NOTE: Always uses JUDGE_MODEL_ID (Nova Premier)
        res = invoke_judge_model(prompt)
        w_id = res.get('winner_id')
        if w_id is not None and w_id != -1 and 0 <= w_id < len(candidates):
            return candidates[w_id]
        return None
    except Exception:
        return None

def run_compliance_stage(response_text: str, genome: Dict, history: List[Dict]) -> Dict:
    resources = genome.get('resources', {})
    rubric = genome.get('evolution_config', {}).get('judge_rubric', [])
    
    prompt = f"""STRICT COMPLIANCE CHECK.
Context: {resources.get('knowledge_base_text', '')}
Policy: {resources.get('policy_text', '')}
Rubric: {json.dumps(sanitize_for_json(rubric))}

Candidate: "{response_text}"

Check: 1. No Hallucinations? 2. Follows Policy? 3. Passes Rubric?
Output JSON: {{ "passed": boolean, "reason": "concise string" }}"""

    try:
        # NOTE: Always uses JUDGE_MODEL_ID (Nova Premier)
        return invoke_judge_model(prompt)
    except Exception as e:
        return {"passed": False, "reason": f"Judge Error: {e}"}


# --- SIMULATION & BEDROCK CALLS ---

def invoke_agent_simulation(genome: Dict, transcript: List[Dict]) -> str:
    """
    Simulates the agent using the SPECIFIC model defined in the genome config.
    This ensures Environment Parity.
    """
    # 1. Determine Model ID from Genome
    config = genome.get('config', {})
    # Fallback to Nova Micro if genome is broken, but try to use config first
    target_model_id = config.get('model_id', 'us.amazon.nova-micro-v1:0') 
    
    # Auto-fix for Cross-Region Inference (Crucial for Hackathon stability)
    # If using Nova or Llama without 'us.' prefix, add it.
    if (target_model_id.startswith('amazon.nova') and not target_model_id.startswith('us.')):
        target_model_id = "us." + target_model_id
        
    logger.info(f"Simulating chat using genome model: {target_model_id}")

    # 2. Build System Prompt
    system_prompt_text = construct_system_prompt(genome)
    
    # 3. Format Messages for Converse API (List of Blocks)
    formatted_messages = []
    for msg in transcript:
        formatted_messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })
    
    # 4. Invoke the Target Model
    try:
        response = bedrock_runtime.converse(
            modelId=target_model_id,
            messages=formatted_messages,
            system=[{"text": system_prompt_text}],
            inferenceConfig={
                "maxTokens": 800,
                "temperature": 0.0  # Zero temp for consistent testing
            }
        )
        return response['output']['message']['content'][0]['text']
        
    except ClientError as e:
        logger.error(f"Simulation failed on model {target_model_id}: {e}")
        # If simulation fails, we re-raise so the Lambda fails gracefully
        raise

def invoke_judge_model(prompt: str) -> Dict:
    """
    Invokes the high-intelligence Judge Model (Nova Premier).
    """
    messages = [{
        "role": "user", 
        "content": [{"text": prompt}]
    }]
    
    try:
        response = bedrock_runtime.converse(
            modelId=JUDGE_MODEL_ID, # Uses the global constant (Nova Premier)
            messages=messages,
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.0
            }
        )
        
        text = response['output']['message']['content'][0]['text']
        text = text.strip()
        
        # --- ROBUST REGEX PARSING ---
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            # Last ditch effort
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1:
                return json.loads(text[start:end])
            return {}
            
    except Exception as e:
        logger.error(f"Judge invocation failed: {e}")
        return {}

def construct_system_prompt(genome: Dict[str, Any]) -> str:
    """
    Reconstructs the full System Prompt based on the Genome.
    Required for accurate Simulation.
    """
    brain = genome.get('brain', {})
    resources = genome.get('resources', {})
    capabilities = genome.get('capabilities', {})
    
    # Extract brain components
    persona = brain.get('persona', {})
    role = persona.get('role', 'AI Assistant')
    tone = persona.get('tone', 'Professional')
    style_guide = brain.get('style_guide', [])
    objectives = brain.get('objectives', [])
    operational_guidelines = brain.get('operational_guidelines', [])
    
    # Extract resources
    knowledge_base_text = resources.get('knowledge_base_text', '')
    policy_text = resources.get('policy_text', '')
    
    # Extract tools
    active_tools = capabilities.get('active_tools', [])
    
    # Construct prompt parts
    prompt_parts = []
    
    # Persona
    prompt_parts.append(f"You are a {role} with a {tone} tone.")
    prompt_parts.append("")
    
    # Style guide
    if style_guide:
        prompt_parts.append("STYLE GUIDE:")
        for item in style_guide:
            prompt_parts.append(f"- {item}")
        prompt_parts.append("")
    
    # Objectives
    if objectives:
        prompt_parts.append("OBJECTIVES:")
        for item in objectives:
            prompt_parts.append(f"- {item}")
        prompt_parts.append("")
    
    # Operational guidelines
    if operational_guidelines:
        prompt_parts.append("OPERATIONAL GUIDELINES:")
        for i, guideline in enumerate(operational_guidelines, 1):
            prompt_parts.append(f"{guideline}")
        prompt_parts.append("")
    
    # Knowledge base
    if knowledge_base_text:
        prompt_parts.append("KNOWLEDGE BASE:")
        prompt_parts.append(knowledge_base_text)
        prompt_parts.append("")
    
    # Policy constraints
    if policy_text:
        prompt_parts.append("POLICY CONSTRAINTS:")
        prompt_parts.append(policy_text)
        prompt_parts.append("")
    
    # Available tools
    if active_tools:
        prompt_parts.append("AVAILABLE TOOLS:")
        for tool in active_tools:
            tool_name = tool.get('name', 'unknown')
            tool_desc = tool.get('description', 'No description')
            prompt_parts.append(f"- {tool_name}: {tool_desc}")
        prompt_parts.append("")
    
    system_prompt = "\n".join(prompt_parts)
    return system_prompt