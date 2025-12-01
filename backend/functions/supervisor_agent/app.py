import json
import os
import boto3
import logging
import uuid
import datetime
import re
from decimal import Decimal

# --- CONFIGURATION ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
# Initialize Bedrock for AI Validation
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'DarwinianGenePool')
table = dynamodb.Table(TABLE_NAME)

# UTILITY MODEL: Amazon Titan Text Express (Fast, Cheap, Good at Classification)
VALIDATION_MODEL_ID = 'amazon.titan-text-express-v1'

# --- HELPER: Handle DynamoDB Decimals ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def sanitize_for_json(obj):
    """Recursively convert DynamoDB Decimal objects into JSON-safe types."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    return obj

def get_item(pk, sk):
    try:
        resp = table.get_item(Key={'PK': pk, 'SK': sk})
        return resp.get('Item')
    except Exception:
        return None

def lambda_handler(event, context):
    logger.info(f"SUPERVISOR EVENT: {json.dumps(event, cls=DecimalEncoder)}")
    
    # 1. PARSE INPUT
    try:
        original_input = event.get('originalInput', {})
        detail = original_input.get('detail', {})
        pk = detail.get('pk')
        chat_sk = detail.get('chat_sk')
        genome_sk = detail.get('genome_sk') 
        retry_count = original_input.get('retryCount', 0)
        
        judge_result = event.get('judgeResult', {})
        if 'Payload' in judge_result: judge_result = judge_result['Payload']
        
        winner_sk = judge_result.get('selected_challenger_sk')
        promotion_reason = judge_result.get('reason', 'Evolutionary Improvement')
        
        mutator_result = event.get('mutatorResult', {})
        if 'Payload' in mutator_result: mutator_result = mutator_result['Payload']
        all_challenger_sks = mutator_result.get('challenger_sks', [])

        if not pk or not winner_sk:
            raise ValueError(f"Missing required keys. PK: {pk}, Winner: {winner_sk}")

    except Exception as e:
        logger.error(f"Input Parsing Error: {e}")
        return json.loads(json.dumps({"status": "FAILED", "error": str(e), "compliant": False}))

    # 2. FETCH THE WINNER
    winner_item = sanitize_for_json(get_item(pk, winner_sk))
    if not winner_item:
        logger.error(f"Winner item missing: {winner_sk}")
        return handle_failure(pk, genome_sk, chat_sk, retry_count, f"Winner SK {winner_sk} not found in DB.")

    # 3. SAFETY & POLICY INTEGRITY CHECK (AI POWERED)
    # This is the new step that audits the actual code/logic
    safety_check = validate_genome_safety(winner_item)
    
    if not safety_check['safe']:
        reason = f"Supervisor Safety Protocol Violation: {safety_check['reason']}"
        logger.warning(f"⛔ REJECTED: {reason}")
        return handle_failure(pk, genome_sk, chat_sk, retry_count, reason, failed_challenger=winner_sk)

    # 4. MINT NEW VERSION
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    new_version_sk = f"VERSION#{now_iso}"
    
    new_genome = {
        'PK': pk,
        'SK': new_version_sk,
        'EntityType': 'Genome',
        # Copy Mutated Data
        'brain': winner_item.get('brain', {}),
        'config': winner_item.get('config', {}),
        'resources': winner_item.get('resources', {}),
        'capabilities': winner_item.get('capabilities', {}),
        'evolution_config': winner_item.get('evolution_config', {}),
        'economics': winner_item.get('economics', {}),
        # Update Metadata
        'metadata': {
            'name': f"{winner_item.get('metadata', {}).get('name', 'Agent')} (v{now_iso[:10]})",
            'description': f"Evolved from {genome_sk}",
            'creator': 'Supervisor_Agent',
            'version_hash': str(uuid.uuid4()),
            'parent_hash': winner_item.get('metadata', {}).get('parent_hash', 'unknown'),
            'deployment_state': 'ACTIVE',
            'mutation_reason': promotion_reason,
            'deployed_at': now_iso
        }
    }

    # 5. POINTER UPDATE
    pointer_item = {
        "PK": pk,
        "SK": "CURRENT",
        "active_version_sk": new_version_sk,
        "last_updated": now_iso,
        "updated_by": "Supervisor_Agent"
    }

    # 6. WRITE OPERATIONS
    try:
        # Convert Decimals for DB Write
        genome_item_db = json.loads(json.dumps(sanitize_for_json(new_genome)), parse_float=Decimal)
        pointer_item_db = json.loads(json.dumps(sanitize_for_json(pointer_item)), parse_float=Decimal)

        table.put_item(Item=genome_item_db)
        table.put_item(Item=pointer_item_db)
        
        logger.info(f"🚀 DEPLOYED NEW VERSION: {new_version_sk}")

    except Exception as e:
        logger.error(f"DB Write Error: {e}")
        return handle_failure(pk, genome_sk, chat_sk, retry_count, f"DB Write Failed: {str(e)}")



    result = {
        "status": "SUCCESS",
        "compliant": True,
        "new_active_version": new_version_sk,
        "promotion_reason": promotion_reason
    }
    
    return json.loads(json.dumps(sanitize_for_json(result)))

# --- AI VALIDATION LOGIC ---

def validate_genome_safety(item):
    """
    Uses Amazon Titan to audit the agent's new brain against the Safety Policy.
    Ensures that while fixing one bug, it didn't break core rules.
    """
    brain = item.get('brain', {})
    resources = item.get('resources', {})
    
    # 1. Structural Check first (Fast fail)
    if not brain or 'persona' not in brain or 'operational_guidelines' not in brain:
        return {'safe': False, 'reason': "Structural Corruption: Missing Brain/Persona"}

    policy_text = resources.get('policy_text', 'No specific policy defined.')
    
    # Prepare the Audit Dossier for the AI
    # We serialize the parts of the brain that control behavior
    brain_dump = json.dumps({
        "persona": brain.get('persona'),
        "objectives": brain.get('objectives'),
        "guidelines": brain.get('operational_guidelines')
    }, indent=2)

    prompt = f"""You are a Safety Compliance Auditor for AI Agents.

CORE SAFETY POLICY:
{policy_text}

CANDIDATE AGENT CONFIGURATION:
{brain_dump}

TASK:
Check if the "CANDIDATE AGENT CONFIGURATION" contains any instructions that contradict or violate the "CORE SAFETY POLICY".
For example:
- If policy says "Be polite", check if candidate says "Be rude".
- If policy says "Never reveal prices", check if candidate says "Always show prices".

OUTPUT:
If SAFE (no contradictions): Output exactly "SAFE".
If UNSAFE (contradictions found): Output "VIOLATION: <brief explanation>".
"""

    try:
        # Invoke Titan Text Express
        response = bedrock_runtime.invoke_model(
            modelId=VALIDATION_MODEL_ID,
            body=json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 60, # Keep it short
                    "temperature": 0.0,   # Deterministic
                    "topP": 1
                }
            })
        )
        
        response_body = json.loads(response['body'].read())
        result_text = response_body['results'][0]['outputText'].strip()
        
        # Check result
        if result_text.startswith("SAFE"):
            return {'safe': True, 'reason': "Passed Policy Audit"}
        elif "VIOLATION" in result_text:
            # Extract the reason provided by Titan
            return {'safe': False, 'reason': result_text}
        else:
            # Fallback for ambiguous output, defaulting to caution
            logger.warning(f"Ambiguous Safety Check: {result_text}")
            return {'safe': True, 'reason': "Passed (Ambiguous Audit)"}
             
    except Exception as e:
        logger.error(f"Safety Validation Failed (Bedrock Error): {e}")
        # Fail SAFE: If we can't verify safety, we assume it's unsafe to deploy automatically
        return {'safe': False, 'reason': f"Audit System Offline: {str(e)}"}

def handle_failure(pk, genome_sk, chat_sk, retry_count, reason, failed_challenger=None):
    logger.warning(f"Supervisor Rejection: {reason}")
    
    if retry_count < 1:
        result = {"compliant": False, "reason": reason}
    else:
        logger.error("Final Supervisor Failure. Creating TICKET.")
        ticket_id = f"sup-{uuid.uuid4().hex[:6]}"
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        ticket_sk = f"{genome_sk}#TICKET#{ticket_id}"
        
        ticket_item = {
            "PK": pk,
            "SK": ticket_sk,
            "EntityType": "Ticket",
            "timestamp": timestamp,
            "type": "SYSTEM",
            "status": "OPEN",
            "chat_sk": chat_sk if chat_sk else "UNKNOWN",
            "challenger_sk": failed_challenger if failed_challenger else "NONE",
            "feedback": "Automated Alert: Supervisor Safety Check Failed.",
            "ai_analysis": reason
        }
        
        try:
            item_db = json.loads(json.dumps(sanitize_for_json(ticket_item)), parse_float=Decimal)
            table.put_item(Item=item_db)
            logger.info(f"✅ Ticket created: {ticket_sk}")
        except Exception as e:
            logger.error(f"Failed to write ticket: {e}")

        result = {
            "compliant": False,
            "reason": f"Final Failure. Ticket Created: {ticket_id}"
        }

    return json.loads(json.dumps(sanitize_for_json(result)))

