import json
import os
import boto3
import hashlib
import logging
import re
from datetime import datetime
from decimal import Decimal

# --- CONFIGURATION ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'DarwinianGenePool') # Fallback for local testing
table = dynamodb.Table(TABLE_NAME)

MODEL_ID = 'us.meta.llama4-maverick-17b-instruct-v1:0'

# --- HELPER: Handle DynamoDB Decimals ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def sanitize_for_json(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    return obj

def lambda_handler(event, context):
    logger.info(f"Received Event: {json.dumps(event)}")
    
    # 1. UNWRAP INPUT
    data = event.get('detail', event)
    
    # 2. EXTRACT KEYS (Input = lowercase, DB = Uppercase)
    pk_val = data['pk']
    genome_sk_val = data['genome_sk']
    
    # 3. HANDLE CRITIC PAYLOAD
    if 'critic_issue' in data:
        critic_issue = data['critic_issue']
    else:
        critic_issue = {
            'reason': data.get('reason', 'Optimization required'),
            'rule': 'Protocol Violation' 
        }

    retry_count = event.get('retryCount', 0)
    retry_context = event.get('retryContext', {})
    
    # 4. FETCH ORIGINAL GENOME
    original_genome = fetch_genome(pk_val, genome_sk_val)
    
    # 5. GENERATE MUTATIONS (The AI Step - Now Robust)
    mutations = generate_mutations(
        original_genome,
        critic_issue,
        retry_count,
        retry_context
    )
    
    if len(mutations) != 3:
        # Fallback should ensure this doesn't happen, but good safety check
        logger.error(f"Mutation count mismatch: {len(mutations)}")
        mutations = generate_fallback_mutations(original_genome['brain'])
    
    # 6. ASSEMBLE & WRITE CHALLENGERS (The Logic Step)
    challenger_sks = write_complete_challengers(
        original_genome,
        mutations,
        critic_issue,
        retry_count
    )
    
    # 7. RETURN (Fixed for Step Functions)
    # Step Functions cannot handle Python Decimal objects. We must serialize to float/int.
    return json.loads(json.dumps({
        'challenger_sks': challenger_sks
    }, cls=DecimalEncoder))

# --- DATABASE FUNCTIONS ---

def fetch_genome(pk, sk):
    # Strictly use Uppercase keys to match the Table Schema
    response = table.get_item(Key={'PK': pk, 'SK': sk})
    
    if 'Item' not in response:
        # Log the specific keys we failed on for easier debugging
        print(f"❌ DB MISS: Looking for PK={pk}, SK={sk}")
        raise ValueError(f"Genome not found: {pk} / {sk}")
        
    return sanitize_for_json(response['Item'])

def write_complete_challengers(original_genome, mutations, critic_issue, retry_count):
    # Extract timestamp from SK: VERSION#2025... -> 2025...
    # Assuming SK format: VERSION#<TIMESTAMP>
    try:
        parts = original_genome['SK'].split('#')
        original_timestamp = parts[1]
    except:
        # Fallback if SK format is weird
        original_timestamp = datetime.utcnow().isoformat()

    base_attempt = 1 if retry_count == 0 else 4
    challenger_sks = []
    
    for i, mutation_brain in enumerate(mutations):
        attempt_num = base_attempt + i
        challenger_sk = f"VERSION#{original_timestamp}#CHALLENGER#attempt-{attempt_num}"
        
        # BUILD THE FULL GENOME
        challenger_genome = assemble_complete_genome(
            original_genome,
            mutation_brain,
            critic_issue,
            challenger_sk
        )
        
        # Serialize Decimals/Floats for DynamoDB
        item_to_write = json.loads(json.dumps(sanitize_for_json(challenger_genome)), parse_float=Decimal)
        
        table.put_item(Item=item_to_write)
        print(f"✅ Wrote Challenger: {challenger_sk}")
        challenger_sks.append(challenger_sk)
    
    return challenger_sks

# --- ASSEMBLY LOGIC (The "Completion" Step) ---

def assemble_complete_genome(original, mutation_brain, critic_issue, challenger_sk):
    """
    Takes the Original Genome and the AI-generated Brain,
    and merges them into a complete Challenger Genome.
    """
    
    # 1. METADATA UPDATE
    # We copy name/desc but append status
    original_meta = original.get('metadata', {})
    new_metadata = {
        "name": f"{original_meta.get('name', 'Agent')} (Candidate)", # Distinct name
        "description": original_meta.get('description', ''),
        "creator": "Darwinian_Mutator_Agent",
        "version_hash": compute_hash(mutation_brain),
        "parent_hash": original_meta.get('version_hash', 'unknown'),
        "deployment_state": "PENDING_APPROVAL",
        "mutation_reason": critic_issue['reason']
    }

    # 2. CONFIG (Copy Exact)
    config = original.get('config', {})
    
    # 3. RESOURCES & CAPABILITIES & EVOLUTION (Copy Exact)
    resources = original.get('resources', {})
    capabilities = original.get('capabilities', {})
    evolution_config = original.get('evolution_config', {})
    
    # 4. ECONOMICS (Reset & Recalculate)
    original_econ = original.get('economics', {})
    
    # Create the partial object to calculate tokens
    temp_genome_structure = {
        "brain": mutation_brain,
        "resources": resources,
        "capabilities": capabilities
    }
    
    # Construct prompt to count tokens
    full_system_prompt = construct_system_prompt(temp_genome_structure)
    token_count = estimate_token_count(full_system_prompt)
    
    economics = {
        "likes": 0,
        "dislikes": 0,
        "input_token_count": token_count,
        "token_budget": original_econ.get('token_budget', 600),
        "estimated_cost_of_calling": "$0.001" # Placeholder or calc based on tokens
    }

    # 5. FINAL ASSEMBLY
    challenger = {
        "PK": original['PK'],
        "SK": challenger_sk,
        "EntityType": "Challenger",
        "metadata": new_metadata,
        "config": config,
        "economics": economics,
        "brain": mutation_brain, # The new mutated brain
        "resources": resources,
        "capabilities": capabilities,
        "evolution_config": evolution_config
    }
    
    # Note: 'constraints' is intentionally omitted as requested.
    
    return challenger

# --- TOKEN & PROMPT UTILS ---

def construct_system_prompt(genome):
    """
    Construct a system prompt from the genome's brain and resources sections.
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
    
    # Construct prompt
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

def estimate_token_count(text):
    """
    Estimates token count. 
    In production, use tiktoken. Here we use a standard approximation (Char / 4).
    """
    if not text:
        return 0
    return int(len(text) / 4)

def compute_hash(data):
    content = json.dumps(sanitize_for_json(data), sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]

# --- AI GENERATION ---

def generate_mutations(original_genome, critic_issue, retry_count, retry_context):
    brain = original_genome['brain']
    
    # Llama 4 Maverick System Prompt
    system_prompt_text = """You are a prompt-engineering MUTATOR agent.
Your role:
- Generate alternative prompt variants to fix identified issues.
- OPTIMIZE: Ensure the new prompts are concise and token-efficient without losing meaning.
- You ONLY propose mutations to the 'brain' section.

Output requirements:
- Return ONLY valid JSON.
- No markdown, no explanations.
- Exactly 3 mutation candidates.
- Structure: {"mutations": [ {mutation1}, {mutation2}, {mutation3} ]}"""

    # Using DecimalEncoder to prevent crashes when dumping brain
    brain_json = json.dumps(sanitize_for_json(brain), indent=2)
    
    user_prompt_text = f"""Generate 3 mutations of the following agent brain to fix this issue.

CRITIC ISSUE:
Rule: {critic_issue['rule']}
Reason: {critic_issue['reason']}

ORIGINAL BRAIN:
{brain_json}

Ensure the output is valid JSON matching the structure requested."""

    # Retry Logic: If retrying, lower temp to be more compliant/strict
    temperature = 0.4 if retry_count > 0 else 0.8  # Maverick likes higher temp for creativity
    
    try:
        # 1. ATTEMPT AI GENERATION WITH CONVERSE API
        messages = [{
            "role": "user",
            "content": [{"text": user_prompt_text}]
        }]
        
        system_prompts = [{"text": system_prompt_text}]
        
        inference_config = {
            "temperature": temperature,
            "maxTokens": 4096
        }

        bedrock_response = bedrock.converse(
            modelId=MODEL_ID,
            messages=messages,
            system=system_prompts,
            inferenceConfig=inference_config
        )
        
        # Parse Response from Converse API structure
        output_message = bedrock_response['output']['message']
        content = output_message['content'][0]['text']
        
        # 2. ATTEMPT ROBUST PARSING (Regex extraction)
        try:
            return extract_json_safely(content)
        except Exception as parse_error:
            logger.error(f"JSON Parsing failed: {parse_error}. Content: {content}")
            raise parse_error
            
    except Exception as e:
        logger.error(f"Bedrock/Parsing Error: {e}")
        logger.warning("⚠️ Triggering Fallback Mutation to save the Demo!")
        # 3. GOLDEN PARACHUTE FALLBACK
        return generate_fallback_mutations(brain)
def extract_json_safely(text):
    """
    Uses Regex to find the first JSON object or array, ignoring conversational filler.
    """
    text = text.strip()
    # Regex to find content between the first { and the last } 
    # OR first [ and last ] (in case it returns a list)
    json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    
    if json_match:
        clean_json = json_match.group(0)
        parsed = json.loads(clean_json)
        # Handle case where LLM wraps it in a root key "mutations" vs just a list
        if isinstance(parsed, dict) and 'mutations' in parsed:
            return parsed['mutations']
        elif isinstance(parsed, list):
            return parsed
            
    raise ValueError("No valid JSON found in response")

def generate_fallback_mutations(original_brain):
    """
    Returns 3 'safe' mutations based on the original brain.
    This ensures the array always has 3 items.
    """
    # Deep copy using load/dump to handle potential decimals or deep structures
    safe_brain = json.loads(json.dumps(original_brain, cls=DecimalEncoder)) 
    
    mutations = []
    
    # Mutation 1: Stricter Tone
    m1 = json.loads(json.dumps(safe_brain))
    m1['persona']['tone'] = f"{m1['persona'].get('tone', 'Professional')} (Stricter)"
    m1['operational_guidelines'].append("Strictly adhere to the provided policy.")
    mutations.append(m1)
    
    # Mutation 2: Empathetic Tone
    m2 = json.loads(json.dumps(safe_brain))
    m2['persona']['tone'] = f"{m2['persona'].get('tone', 'Professional')} (Empathetic)"
    m2['operational_guidelines'].append("Ensure the user feels heard and understood.")
    mutations.append(m2)
    
    # Mutation 3: Concise
    m3 = json.loads(json.dumps(safe_brain))
    m3['persona']['tone'] = f"{m3['persona'].get('tone', 'Professional')} (Concise)"
    m3['style_guide'].append("Keep responses under 2 sentences when possible.")
    mutations.append(m3)
        
    return mutations