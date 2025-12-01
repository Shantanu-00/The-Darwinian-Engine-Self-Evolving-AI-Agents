import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
# NOTE: Ensure your Lambda Layer uses a recent boto3 version (>=1.34.100) to support 'converse'
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')
events_client = boto3.client('events')

# Environment variables
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'DarwinianGenePool')
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


def exponential_backoff_retry(func, max_retries=3, initial_delay=0.1, max_delay=2.0):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Result of the function call
    
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException', 'Throttling']:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"Throttling error, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)
                else:
                    logger.error(f"Max retries exceeded for throttling error")
                    raise
            else:
                raise
    
    raise last_exception


def sanitize_for_json(obj):
    """
    Recursively convert DynamoDB Decimal objects into JSON-safe types.
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    else:
        return obj


def resolve_active_genome(pk: str) -> Dict[str, Any]:
    """
    Resolve the active genome for an agent lineage using two-step lookup.
    
    Args:
        pk: Agent partition key (e.g., "AGENT#CarSalesman-auto-01")
    
    Returns:
        Genome dictionary containing metadata, config, brain, resources, capabilities, evolution_config
    """
    logger.info(f"Resolving active genome for pk={pk}")
    
    # Step 1: Get CURRENT pointer
    def get_current_pointer():
        response = table.get_item(Key={'PK': pk, 'SK': 'CURRENT'})
        return response
    
    try:
        current_response = exponential_backoff_retry(get_current_pointer)
    except ClientError as e:
        logger.error(f"Failed to get CURRENT pointer for pk={pk}: {e}")
        raise
    
    if 'Item' not in current_response:
        logger.error(f"CURRENT pointer not found for pk={pk}")
        raise ValueError(f"CURRENT pointer not found for pk={pk}")
    
    active_version_sk = current_response['Item'].get('active_version_sk')
    if not active_version_sk:
        logger.error(f"active_version_sk not found in CURRENT pointer for pk={pk}")
        raise ValueError(f"active_version_sk not found in CURRENT pointer for pk={pk}")
    
    logger.info(f"Resolved active version: {active_version_sk}")
    
    # Step 2: Get genome using resolved version SK
    def get_genome():
        response = table.get_item(Key={'PK': pk, 'SK': active_version_sk})
        return response
    
    try:
        genome_response = exponential_backoff_retry(get_genome)
    except ClientError as e:
        logger.error(f"Failed to get genome for pk={pk}, sk={active_version_sk}: {e}")
        raise
    
    if 'Item' not in genome_response:
        logger.error(f"Genome not found for pk={pk}, sk={active_version_sk}")
        raise ValueError(f"Genome not found for pk={pk}, sk={active_version_sk}")
    
    genome = sanitize_for_json(genome_response['Item'])

    # Validate genome structure
    required_sections = ['config', 'brain', 'resources']
    for section in required_sections:
        if section not in genome:
            logger.error(f"Missing required section '{section}' in genome")
            raise ValueError(f"Missing required section '{section}' in genome")
    
    # Validate config section
    config = genome.get('config', {})
    required_config_fields = ['model_id', 'temperature', 'max_tokens']
    for field in required_config_fields:
        if field not in config:
            logger.error(f"Missing required config field '{field}' in genome")
            raise ValueError(f"Missing required config field '{field}' in genome")
    
    logger.info(f"Successfully resolved genome with model_id={config.get('model_id')}")
    return genome


def construct_system_prompt(genome: Dict[str, Any]) -> str:
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
    logger.info(f"Constructed system prompt ({len(system_prompt)} chars)")
    return system_prompt


def get_chat_history(pk: str, version_sk: str, chat_id: str):
    """
    Retrieve existing chat history and critic_verdict from DynamoDB.
    """
    chat_sk = f"{version_sk}#CHAT#{chat_id}"
    logger.info(f"Retrieving chat history for pk={pk}, chat_sk={chat_sk}")
    
    def get_chat():
        response = table.get_item(Key={'PK': pk, 'SK': chat_sk})
        return response
    
    try:
        chat_response = exponential_backoff_retry(get_chat)
    except ClientError as e:
        logger.error(f"Failed to get chat history: {e}")
        return [], None
    
    if 'Item' not in chat_response:
        logger.info(f"No existing chat history found for chat_id={chat_id}")
        return [], None
    
    item = chat_response['Item']
    transcript = item.get('transcript', [])
    critic_verdict = item.get('critic_verdict')
    logger.info(f"Retrieved {len(transcript)} messages from chat history, critic_verdict={critic_verdict}")
    return transcript, critic_verdict


def invoke_bedrock(
    model_id: str,
    system_prompt: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int
) -> str:
    """
    Invoke AWS Bedrock using the unified 'converse' API.
    This supports Amazon Nova, Meta Llama, and Anthropic Claude uniformly.
    
    Args:
        model_id: Bedrock model identifier (e.g., 'amazon.nova-premier-v1:0')
        system_prompt: System instruction text
        messages: List of conversation messages [{'role': 'user', 'content': '...'}, ...]
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        Assistant response text
    """
    logger.info(f"Invoking Bedrock Converse API with model={model_id}, temp={temperature}, max_tokens={max_tokens}")
    
    # 1. Transform simple string messages to Bedrock Converse Block format
    # Input format:  [{'role': 'user', 'content': 'hello'}]
    # Output format: [{'role': 'user', 'content': [{'text': 'hello'}]}]
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })

    # 2. Prepare System Prompt (Must be a list of blocks)
    formatted_system = [{"text": system_prompt}]

    # 3. Prepare Inference Configuration
    inference_config = {
        "temperature": temperature,
        "maxTokens": max_tokens
    }

    def invoke():
        # The 'converse' API abstracts away model-specific JSON bodies (Nova vs Llama vs Claude)
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=formatted_messages,
            system=formatted_system,
            inferenceConfig=inference_config
        )
        return response
    
    try:
        start_time = time.time()
        response = exponential_backoff_retry(invoke, max_retries=3, initial_delay=0.2, max_delay=2.0)
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 4. Extract Output
        # Converse API returns standard structure: output -> message -> content -> text
        output_message = response.get('output', {}).get('message', {})
        content = output_message.get('content', [])
        
        if not content:
            logger.error("No content in Bedrock Converse response")
            raise ValueError("No content in Bedrock Converse response")
            
        assistant_text = content[0].get('text', '')
        
        # Log metadata
        usage = response.get('usage', {})
        input_tokens = usage.get('inputTokens', 0)
        output_tokens = usage.get('outputTokens', 0)
        
        logger.info(f"Bedrock response received: latency={latency_ms}ms, input_tokens={input_tokens}, output_tokens={output_tokens}")
        
        return assistant_text
        
    except ClientError as e:
        logger.error(f"Bedrock invocation failed: {e}")
        raise


def store_chat_transcript(
    pk: str,
    version_sk: str,
    chat_id: str,
    user_message: str,
    assistant_response: str,
    existing_transcript: List[Dict[str, str]],
    critic_verdict: Optional[str] = None
) -> None:
    """
    Append messages to transcript WITHOUT removing critic metadata.
    """
    chat_sk = f"{version_sk}#CHAT#{chat_id}"
    logger.info(f"Updating chat transcript for pk={pk}, chat_sk={chat_sk}")

    # Append new messages
    updated_transcript = existing_transcript.copy()
    updated_transcript.append({"role": "user", "content": user_message})
    updated_transcript.append({"role": "assistant", "content": assistant_response})

    def update_chat():
        table.update_item(
            Key={'PK': pk, 'SK': chat_sk},
            UpdateExpression="""
                SET transcript = :transcript,
                    updated_at = :updated_at
            """,
            ExpressionAttributeValues={
                ':transcript': updated_transcript,
                ':updated_at': datetime.utcnow().isoformat() + 'Z'
            }
        )

    try:
        exponential_backoff_retry(update_chat)
        logger.info("Chat transcript updated successfully (critic fields preserved)")
    except ClientError as e:
        logger.error(f"Failed to update chat transcript: {e}")



def emit_event(pk: str, chat_sk: str) -> None:
    """
    Emit ChatResponseGenerated event to EventBridge.
    """
    logger.info(f"Emitting ChatResponseGenerated event for pk={pk}, chat_sk={chat_sk}")
    
    event_detail = {
        'pk': pk,
        'chat_sk': chat_sk
    }
    
    try:
        events_client.put_events(
            Entries=[
                {
                    'Source': 'chat.proxy',
                    'DetailType': 'ChatResponseGenerated',
                    'Detail': json.dumps(event_detail),
                    'EventBusName': 'default'
                }
            ]
        )
        logger.info("Successfully emitted ChatResponseGenerated event")
    except ClientError as e:
        logger.error(f"Failed to emit event to EventBridge: {e}")
        # Log error but do not raise exception (per requirements)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Proxy Agent.
    """
    request_id = context.aws_request_id if context else 'local'
    logger.info(f"Processing request: request_id={request_id}")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        pk = body.get('pk')
        chat_id = body.get('chat_id')
        user_message = body.get('user_message')
        
        if not pk:
            logger.error("Missing required field: pk")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required field: pk'})
            }
        
        if not chat_id:
            logger.error("Missing required field: chat_id")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required field: chat_id'})
            }
        
        if not user_message:
            logger.error("Missing required field: user_message")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required field: user_message'})
            }
        
        logger.info(f"Request validated: pk={pk}, chat_id={chat_id}")
        
        # Step 1: Resolve active genome
        try:
            genome = resolve_active_genome(pk)
        except ValueError as e:
            logger.error(f"Genome resolution failed: {e}")
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': str(e)})
            }
        
        # Extract version SK from genome
        version_sk = genome.get('SK')
        
        # Step 2: Get chat history and critic verdict
        existing_transcript, critic_verdict = get_chat_history(pk, version_sk, chat_id)
        
        # Step 3: Construct system prompt
        system_prompt = construct_system_prompt(genome)
        
        # Step 4: Prepare messages for Bedrock
        # Note: formatting for 'converse' happens inside invoke_bedrock now
        messages = existing_transcript.copy()
        messages.append({"role": "user", "content": user_message})
        
        # Step 5: Extract model configuration
        config = genome.get('config', {})
        
        # --- MODEL SELECTION WITH FALLBACK ---
        model_id = config.get('model_id')
        
        # Fallback to Claude if Nova Premier not available
        if model_id == 'amazon.nova-premier-v1:0':
            model_id = 'us.amazon.nova-premier-v1:0'
            
        temperature = float(config.get('temperature', 0.7))
        max_tokens = int(config.get('max_tokens', 800))
        
        # Step 6: Invoke Bedrock
        try:
            assistant_response = invoke_bedrock(
                model_id=model_id,
                system_prompt=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except (ClientError, ValueError) as e:
            logger.error(f"Bedrock invocation failed: {e}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Bedrock invocation failed: {str(e)}'})
            }
        
        # Step 7: Store chat transcript
        store_chat_transcript(
            pk=pk,
            version_sk=version_sk,
            chat_id=chat_id,
            user_message=user_message,
            assistant_response=assistant_response,
            existing_transcript=existing_transcript,
            critic_verdict=critic_verdict
        )
        
        # Step 8: Conditionally emit event based on critic_verdict
        chat_sk = f"{version_sk}#CHAT#{chat_id}"
        if critic_verdict is None or critic_verdict == 'PASS':
            emit_event(pk=pk, chat_sk=chat_sk)
        else:
            logger.warning(f"Skipping event emission due to critic_verdict={critic_verdict}")
        
        # Step 9: Return response
        logger.info(f"Request completed successfully: request_id={request_id}")
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            # Sanitize ensures Decimals are converted to int/float for JSON serialization
            'body': json.dumps(sanitize_for_json({'response': assistant_response}))
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }