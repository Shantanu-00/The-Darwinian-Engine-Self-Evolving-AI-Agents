# Requirements Document

## Introduction

This specification defines the migration and modernization of a GCP Vertex AI-based agent system to AWS infrastructure using Bedrock, Lambda, DynamoDB, and EventBridge. The system implements a Darwinian evolution pattern where AI agents self-improve through automated evaluation and mutation cycles. The migration involves transforming the agent from a Cloud Run service using Gemini models to an AWS Lambda function using Claude models via Bedrock, while implementing a complete event-driven architecture for chat handling, genome management, and evolutionary improvement loops.

## Glossary

- **Genome**: A JSON configuration object containing the complete behavioral specification for an AI agent, including model settings, persona, operational guidelines, tools, and evolution rules
- **Proxy Agent**: The primary Lambda function that handles synchronous chat requests from users by fetching the current genome and invoking Bedrock models
- **Chat Transcript**: A conversation history stored in DynamoDB containing user messages and assistant responses
- **Bedrock**: AWS managed service for accessing foundation models including Claude (Anthropic)
- **DynamoDB**: AWS NoSQL database service using single-table design for storing genomes, chats, and evolution data
- **EventBridge**: AWS event bus service for triggering asynchronous workflows
- **Evolution Loop**: A Step Functions state machine that orchestrates genome mutation, evaluation, and deployment
- **Critic Agent**: A Lambda function that evaluates chat responses against quality rubrics and triggers evolution when failures occur
- **API Gateway**: AWS service providing REST API endpoints for chat and feedback operations
- **SK (Sort Key)**: DynamoDB attribute used for versioning, with "CURRENT" indicating the active genome version

## Requirements

### Requirement 1

**User Story:** As a user, I want to send chat messages to an AI agent via a REST API, so that I can receive intelligent responses based on the agent's configured genome.

#### Acceptance Criteria

1. WHEN a user sends a POST request to the /chat endpoint with pk, chat_id, and user_message THEN the Proxy Agent SHALL accept the request and return a 200 status code
2. WHEN the Proxy Agent receives a chat request THEN the Proxy Agent SHALL extract the pk, chat_id, and user_message from the request body
3. WHEN the Proxy Agent processes a request THEN the Proxy Agent SHALL validate that required fields (pk, chat_id, user_message) are present
4. IF required fields (pk or chat_id) are missing THEN the Proxy Agent SHALL fail the request with a descriptive error message
5. WHEN the API Gateway receives a malformed JSON payload THEN the API Gateway SHALL return a 400 error response

### Requirement 2

**User Story:** As the Proxy Agent, I want to resolve the active genome version using a two-step lookup process, so that I can fetch the correct genome configuration dynamically per request.

#### Acceptance Criteria

1. WHEN the Proxy Agent needs genome configuration THEN the Proxy Agent SHALL first query DynamoDB using PK from the request and SK equal to "CURRENT" to retrieve the current pointer
2. WHEN the current pointer is retrieved THEN the Proxy Agent SHALL extract the active_version_sk field containing the version identifier
3. WHEN the Proxy Agent has the active version SK THEN the Proxy Agent SHALL query DynamoDB using PK from the request and the resolved SK to fetch the genome
4. WHEN the genome query succeeds THEN the Proxy Agent SHALL parse the genome JSON structure containing metadata, config, brain, resources, capabilities, and evolution_config sections
5. IF the CURRENT pointer does not exist for the given PK THEN the Proxy Agent SHALL fail the request with an error indicating the agent configuration was not found
6. IF the genome does not exist for the resolved version SK THEN the Proxy Agent SHALL fail the request with an error indicating the genome version was not found
7. WHEN DynamoDB returns a genome THEN the Proxy Agent SHALL validate that the config section contains model_id, temperature, and max_tokens fields
8. IF the genome structure is invalid or missing required fields THEN the Proxy Agent SHALL fail the request with validation details

### Requirement 3

**User Story:** As the Proxy Agent, I want to construct a system prompt from the genome's brain and resources sections, so that the Bedrock model receives appropriate context and instructions.

#### Acceptance Criteria

1. WHEN the Proxy Agent constructs a system prompt THEN the Proxy Agent SHALL include the persona role and tone from the brain section
2. WHEN the Proxy Agent constructs a system prompt THEN the Proxy Agent SHALL include all style_guide items from the brain section
3. WHEN the Proxy Agent constructs a system prompt THEN the Proxy Agent SHALL include all objectives from the brain section
4. WHEN the Proxy Agent constructs a system prompt THEN the Proxy Agent SHALL include all operational_guidelines from the brain section
5. WHEN the Proxy Agent constructs a system prompt THEN the Proxy Agent SHALL include the knowledge_base_text and policy_text from the resources section
6. WHEN the Proxy Agent constructs a system prompt THEN the Proxy Agent SHALL format the prompt as a structured text document with clear sections

### Requirement 4

**User Story:** As the Proxy Agent, I want to invoke AWS Bedrock with the appropriate Claude model and parameters, so that I can generate intelligent responses to user messages.

#### Acceptance Criteria

1. WHEN the Proxy Agent invokes Bedrock THEN the Proxy Agent SHALL use the model_id specified in the genome config section
2. WHEN the Proxy Agent invokes Bedrock THEN the Proxy Agent SHALL support both anthropic.claude-3-5-sonnet-20240620-v1:0 and anthropic.claude-3-haiku-20240307-v1:0 model identifiers
3. WHEN the Proxy Agent invokes Bedrock THEN the Proxy Agent SHALL set the temperature parameter from the genome config section
4. WHEN the Proxy Agent invokes Bedrock THEN the Proxy Agent SHALL set the max_tokens parameter from the genome config section
5. WHEN the Proxy Agent invokes Bedrock THEN the Proxy Agent SHALL include the constructed system prompt in the request
6. WHEN the Proxy Agent invokes Bedrock THEN the Proxy Agent SHALL include the user message in the request
7. WHEN the Proxy Agent invokes Bedrock with active_tools defined in the genome THEN the Proxy Agent SHALL include the tool definitions in the Bedrock request
8. IF Bedrock returns an error response THEN the Proxy Agent SHALL return a 500 error response with the Bedrock error details

### Requirement 5

**User Story:** As the Proxy Agent, I want to retrieve existing chat history from DynamoDB, so that I can provide conversation context to the Bedrock model.

#### Acceptance Criteria

1. WHEN the Proxy Agent processes a chat request THEN the Proxy Agent SHALL query DynamoDB for existing chat history using PK and SK pattern matching "VERSION#*#CHAT#{chat_id}"
2. WHEN chat history exists THEN the Proxy Agent SHALL extract the transcript array from the stored chat record
3. WHEN the Proxy Agent invokes Bedrock THEN the Proxy Agent SHALL include the historical transcript messages before the current user message
4. WHEN no chat history exists for the chat_id THEN the Proxy Agent SHALL proceed with only the current user message
5. WHEN the Proxy Agent retrieves chat history THEN the Proxy Agent SHALL preserve the order of messages with role and content fields

### Requirement 6

**User Story:** As the Proxy Agent, I want to store chat transcripts in DynamoDB after generating responses, so that conversation history is persisted for future requests and evolution analysis.

#### Acceptance Criteria

1. WHEN the Proxy Agent receives a response from Bedrock THEN the Proxy Agent SHALL append the user message to the transcript array with role "user" and content fields
2. WHEN the Proxy Agent receives a response from Bedrock THEN the Proxy Agent SHALL append the assistant response to the transcript array with role "assistant" and content fields
3. WHEN the Proxy Agent stores a chat transcript THEN the Proxy Agent SHALL use PK from the request and SK formatted as "VERSION#{genome_version}#CHAT#{chat_id}"
4. WHEN the Proxy Agent stores a chat transcript THEN the Proxy Agent SHALL include EntityType field set to "Chat"
5. WHEN the Proxy Agent stores a chat transcript THEN the Proxy Agent SHALL include a timestamp field with ISO 8601 format
6. WHEN a chat record already exists THEN the Proxy Agent SHALL retrieve the existing transcript array and append new messages rather than overwriting
7. WHEN a chat record does not exist THEN the Proxy Agent SHALL create a new chat record with the transcript array containing the current conversation turn
8. IF DynamoDB write fails THEN the Proxy Agent SHALL log the error but still return the response to the user

### Requirement 7

**User Story:** As the Proxy Agent, I want to emit a ChatResponseGenerated event to EventBridge after successfully handling a chat request, so that the Critic Agent can evaluate the response quality asynchronously.

#### Acceptance Criteria

1. WHEN the Proxy Agent successfully generates a response THEN the Proxy Agent SHALL publish an event to the default EventBridge event bus with source "chat.proxy"
2. WHEN the Proxy Agent publishes an event THEN the Proxy Agent SHALL set detail-type to "ChatResponseGenerated"
3. WHEN the Proxy Agent publishes an event THEN the Proxy Agent SHALL include pk and chat_sk fields in the event detail payload
4. WHEN the Proxy Agent formats the chat_sk field THEN the Proxy Agent SHALL use the format "VERSION#{genome_version}#CHAT#{chat_id}"
5. WHEN the Proxy Agent publishes an event THEN the Proxy Agent SHALL NOT wait for evaluation results or downstream processing
6. IF EventBridge publish fails THEN the Proxy Agent SHALL log the error but still return the response to the user

### Requirement 8

**User Story:** As a developer, I want the Proxy Agent Lambda function to have appropriate IAM permissions, so that it can access DynamoDB, Bedrock, and EventBridge services.

#### Acceptance Criteria

1. WHEN the Proxy Agent Lambda is deployed THEN the Lambda execution role SHALL include DynamoDB GetItem permission
2. WHEN the Proxy Agent Lambda is deployed THEN the Lambda execution role SHALL include DynamoDB PutItem permission
3. WHEN the Proxy Agent Lambda is deployed THEN the Lambda execution role SHALL include DynamoDB Query permission
4. WHEN the Proxy Agent Lambda is deployed THEN the Lambda execution role SHALL include DynamoDB UpdateItem permission
5. WHEN the Proxy Agent Lambda is deployed THEN the Lambda execution role SHALL include bedrock:InvokeModel permission for all Claude model resources
6. WHEN the Proxy Agent Lambda is deployed THEN the Lambda execution role SHALL include events:PutEvents permission for the default event bus

### Requirement 9

**User Story:** As a developer, I want the Proxy Agent to handle errors gracefully, so that users receive meaningful error messages and the system remains stable.

#### Acceptance Criteria

1. WHEN an unhandled exception occurs in the Proxy Agent THEN the Proxy Agent SHALL catch the exception and return a 500 error response
2. WHEN the Proxy Agent returns an error response THEN the Proxy Agent SHALL include an error message describing the failure
3. WHEN the Proxy Agent encounters a DynamoDB throttling error THEN the Proxy Agent SHALL implement exponential backoff retry logic with maximum 3 attempts
4. WHEN the Proxy Agent encounters a Bedrock throttling error THEN the Proxy Agent SHALL implement exponential backoff retry logic with maximum 3 attempts
5. WHEN the Proxy Agent logs errors THEN the Proxy Agent SHALL include request_id, PK, chat_id, and error details for debugging

### Requirement 10

**User Story:** As a developer, I want the genome to declare available tools, so that the LLM is aware of capabilities without automatic execution.

#### Acceptance Criteria

1. WHEN the genome contains active_tools in the capabilities section THEN the Proxy Agent SHALL include tool definitions in the system prompt or model configuration
2. WHEN the Proxy Agent constructs the system prompt THEN the Proxy Agent SHALL list active tools with their names, descriptions, and input schemas
3. WHEN the genome declares active_tools THEN the Proxy Agent SHALL NOT automatically execute tool calls
4. WHEN the genome contains simulation_mocks THEN the Proxy Agent SHALL treat them as reference data for future tool execution capabilities
5. WHEN the Proxy Agent processes a genome THEN the Proxy Agent SHALL validate that active_tools follow the expected schema with name, description, and input_schema fields

### Requirement 11

**User Story:** As a system administrator, I want genome records to follow a consistent DynamoDB schema, so that all agents can reliably fetch and parse configuration data.

#### Acceptance Criteria

1. WHEN a genome is stored in DynamoDB THEN the genome SHALL include PK field formatted as "AGENT#{agent_name}"
2. WHEN a genome is stored in DynamoDB THEN the genome SHALL include SK field formatted as "VERSION#{timestamp}" or "CURRENT" for the active version
3. WHEN a genome is stored in DynamoDB THEN the genome SHALL include EntityType field set to "Genome"
4. WHEN a genome is stored in DynamoDB THEN the genome SHALL include metadata section with name, description, creator, version_hash, parent_hash, deployment_state, and mutation_reason fields
5. WHEN a genome is stored in DynamoDB THEN the genome SHALL include config section with model_id, temperature, and max_tokens fields
6. WHEN a genome is stored in DynamoDB THEN the genome SHALL include brain section with persona, style_guide, objectives, and operational_guidelines fields
7. WHEN a genome is stored in DynamoDB THEN the genome SHALL include resources section with knowledge_base_text and policy_text fields
8. WHEN a genome is stored in DynamoDB THEN the genome SHALL include capabilities section with active_tools and simulation_mocks fields
9. WHEN a genome is stored in DynamoDB THEN the genome SHALL include evolution_config section with critic_rules and judge_rubric fields

### Requirement 12

**User Story:** As a developer, I want the Proxy Agent to be deployed as an AWS Lambda function with API Gateway integration, so that it can handle HTTP requests with proper routing and CORS support.

#### Acceptance Criteria

1. WHEN the infrastructure is deployed THEN the API Gateway SHALL expose a /chat endpoint accepting POST requests
2. WHEN the API Gateway receives a request THEN the API Gateway SHALL route the request to the Proxy Agent Lambda function
3. WHEN the API Gateway is configured THEN the API Gateway SHALL enable CORS with allowed origins, methods, and headers
4. WHEN the Proxy Agent Lambda is deployed THEN the Lambda SHALL have a timeout of 30 seconds
5. WHEN the Proxy Agent Lambda is deployed THEN the Lambda SHALL have memory allocation of 1024 MB
6. WHEN the Proxy Agent Lambda is deployed THEN the Lambda SHALL use Python 3.11 or later runtime
7. WHEN the API Gateway returns a response THEN the API Gateway SHALL include appropriate CORS headers in the response
