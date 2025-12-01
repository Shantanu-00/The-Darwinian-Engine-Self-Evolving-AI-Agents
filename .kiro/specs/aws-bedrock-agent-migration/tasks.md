# Implementation Plan

- [ ] 1. Set up Proxy Agent Lambda project structure
  - Create `backend/functions/proxy_agent/` directory
  - Create `app.py` with lambda_handler entry point
  - Create `requirements.txt` with boto3 dependency
  - _Requirements: 12.6_

- [ ] 2. Implement genome resolution logic
  - [ ] 2.1 Implement `resolve_active_genome(pk)` function
    - Query DynamoDB for CURRENT pointer (SK="CURRENT")
    - Extract `active_version_sk` from response
    - Query DynamoDB for genome using resolved SK
    - Parse and return genome JSON
    - Raise exception if CURRENT pointer or genome not found
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6_

  - [ ]* 2.2 Write property test for genome resolution consistency
    - **Property 1: Genome Resolution Consistency**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [ ]* 2.3 Write unit tests for genome resolution
    - Test successful CURRENT pointer lookup
    - Test missing CURRENT pointer
    - Test missing genome version
    - Test malformed genome JSON
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6_

- [ ] 3. Implement system prompt construction
  - [ ] 3.1 Implement `construct_system_prompt(genome)` function
    - Extract brain section (persona, style_guide, objectives, operational_guidelines)
    - Extract resources section (knowledge_base_text, policy_text)
    - Extract capabilities section (active_tools)
    - Format as structured text prompt with clear sections
    - Return complete system instruction string
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 3.2 Write property test for system prompt completeness
    - **Property 2: System Prompt Completeness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

  - [ ]* 3.3 Write unit tests for system prompt construction
    - Test complete genome with all brain/resources fields
    - Test genome with empty style_guide
    - Test genome with missing resources section
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 4. Implement chat history retrieval
  - [ ] 4.1 Implement `get_chat_history(pk, version_sk, chat_id)` function
    - Construct chat SK: `{version_sk}#CHAT#{chat_id}`
    - Query DynamoDB for existing chat record
    - Extract transcript array if exists
    - Return transcript array or empty list
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

  - [ ]* 4.2 Write property test for chat history retrieval idempotence
    - **Property 7: Chat History Retrieval Idempotence**
    - **Validates: Requirements 5.1, 5.2, 5.5**

  - [ ]* 4.3 Write unit tests for chat history retrieval
    - Test existing chat with multiple messages
    - Test non-existent chat
    - Test chat with single message
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

- [ ] 5. Implement Bedrock model invocation
  - [ ] 5.1 Implement `invoke_bedrock(model_id, system_prompt, messages, temperature, max_tokens)` function
    - Create boto3 bedrock-runtime client
    - Format request according to Anthropic Messages API
    - Include system prompt in request
    - Include conversation history in messages array
    - Set temperature and max_tokens from parameters
    - Parse response and extract assistant text
    - Implement exponential backoff retry for throttling errors
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 9.4_

  - [ ]* 5.2 Write property test for Bedrock model configuration fidelity
    - **Property 4: Bedrock Model Configuration Fidelity**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [ ]* 5.3 Write unit tests for Bedrock invocation
    - Test request formatting with system prompt and messages
    - Test response parsing
    - Test error handling for throttling
    - Test retry logic with exponential backoff
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 9.4_

- [ ] 6. Implement chat transcript storage
  - [ ] 6.1 Implement `store_chat_transcript(pk, version_sk, chat_id, transcript)` function
    - Construct chat SK: `{version_sk}#CHAT#{chat_id}`
    - Query DynamoDB for existing chat record
    - If exists, retrieve existing transcript array
    - Append new user message with role and content
    - Append new assistant message with role and content
    - Write updated chat record with EntityType, timestamp, and transcript
    - Implement exponential backoff retry for throttling errors
    - Log error if write fails but do not raise exception
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 9.3_

  - [ ]* 6.2 Write property test for chat transcript append-only
    - **Property 3: Chat Transcript Append-Only**
    - **Validates: Requirements 6.6**

  - [ ]* 6.3 Write unit tests for chat transcript storage
    - Test appending to existing chat
    - Test creating new chat
    - Test preserving message order
    - Test error handling for DynamoDB failures
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

- [ ] 7. Implement EventBridge event emission
  - [ ] 7.1 Implement `emit_event(pk, chat_sk)` function
    - Create boto3 events client
    - Construct event with source "chat.proxy"
    - Set detail-type to "ChatResponseGenerated"
    - Include pk and chat_sk in event detail
    - Publish to default event bus
    - Log error if publish fails but do not raise exception
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 7.2 Write property test for event emission non-blocking
    - **Property 5: Event Emission Non-Blocking**
    - **Validates: Requirements 7.6**

  - [ ]* 7.3 Write unit tests for event emission
    - Test successful event publish
    - Test failed event publish (should not raise exception)
    - Test event payload structure
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ] 8. Implement request validation and Lambda handler
  - [ ] 8.1 Implement input validation logic
    - Parse API Gateway event body JSON
    - Validate presence of pk, chat_id, and user_message fields
    - Return 400 error if required fields missing
    - _Requirements: 1.2, 1.3, 1.4_

  - [ ]* 8.2 Write property test for required field validation
    - **Property 6: Required Field Validation**
    - **Validates: Requirements 1.4**

  - [ ]* 8.3 Write unit tests for input validation
    - Test missing pk field
    - Test missing chat_id field
    - Test missing user_message field
    - Test malformed JSON body
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

  - [ ] 8.4 Implement complete `lambda_handler` orchestration
    - Parse and validate input
    - Call `resolve_active_genome(pk)`
    - Extract version_sk from genome SK
    - Call `get_chat_history(pk, version_sk, chat_id)`
    - Call `construct_system_prompt(genome)`
    - Append user message to history
    - Extract model_id, temperature, max_tokens from genome config
    - Call `invoke_bedrock` with all parameters
    - Append assistant response to history
    - Call `store_chat_transcript` with updated history
    - Construct chat_sk for event
    - Call `emit_event(pk, chat_sk)`
    - Return 200 response with assistant message
    - Implement error handling for all steps
    - Return appropriate error codes (400, 404, 500)
    - _Requirements: 1.1, 1.2, 9.1, 9.2, 9.5_

  - [ ]* 8.5 Write unit tests for lambda_handler orchestration
    - Test happy path with all steps succeeding
    - Test genome not found error
    - Test Bedrock invocation error
    - Test DynamoDB write error (should still return response)
    - Test EventBridge publish error (should still return response)
    - _Requirements: 1.1, 9.1, 9.2, 9.5_

- [ ] 9. Implement error handling and logging
  - [ ] 9.1 Add CloudWatch logging throughout all functions
    - Log genome resolution steps with request_id, pk
    - Log Bedrock request/response metadata (token counts, latency)
    - Log EventBridge publish attempts
    - Log all errors with full context
    - Use INFO level for normal operations, ERROR for failures
    - _Requirements: 9.5_

  - [ ] 9.2 Implement exponential backoff retry logic
    - Create reusable retry decorator or utility function
    - Apply to DynamoDB operations (max 3 retries, 100ms-1000ms delay)
    - Apply to Bedrock operations (max 3 retries, 200ms-2000ms delay)
    - _Requirements: 9.3, 9.4_

  - [ ]* 9.3 Write unit tests for retry logic
    - Test successful retry after transient failure
    - Test max retries exceeded
    - Test exponential backoff timing
    - _Requirements: 9.3, 9.4_

- [ ] 10. Update SAM template for Proxy Agent deployment
  - [ ] 10.1 Add Proxy Agent Lambda function resource to template.yaml
    - Set CodeUri to `../backend/functions/proxy_agent/`
    - Set Handler to `app.lambda_handler`
    - Set Runtime to `python3.11`
    - Set Timeout to 30 seconds
    - Set MemorySize to 1024 MB
    - Add DYNAMODB_TABLE environment variable
    - _Requirements: 12.4, 12.5, 12.6_

  - [ ] 10.2 Add IAM policies to Proxy Agent Lambda
    - Add DynamoDBCrudPolicy for table access
    - Add bedrock:InvokeModel permission for all Claude models
    - Add events:PutEvents permission for default event bus
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ] 10.3 Add API Gateway event trigger
    - Configure POST /chat endpoint
    - Set RestApiId reference to ChatApi
    - Enable Lambda proxy integration
    - _Requirements: 12.1, 12.2_

  - [ ] 10.4 Configure CORS settings on API Gateway
    - Set AllowOrigin to '*'
    - Set AllowMethods to 'POST, OPTIONS'
    - Set AllowHeaders to include Content-Type and Authorization
    - _Requirements: 12.3, 12.7_

- [ ] 11. Create sample genome seed data
  - [ ] 11.1 Create seed script for DynamoDB
    - Write Python script to create CURRENT pointer
    - Write Python script to create sample genome with all required sections
    - Use CarSalesman example from design document
    - Include metadata, config, brain, resources, capabilities, evolution_config
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_

  - [ ] 11.2 Execute seed script to populate DynamoDB
    - Run script against deployed DynamoDB table
    - Verify CURRENT pointer exists
    - Verify genome record exists
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Deploy and test Proxy Agent end-to-end
  - [ ] 13.1 Deploy infrastructure using SAM
    - Run `sam build`
    - Run `sam deploy --guided`
    - Capture API Gateway endpoint URL
    - _Requirements: 12.1, 12.2_

  - [ ] 13.2 Test /chat endpoint with sample request
    - Send POST request with pk, chat_id, user_message
    - Verify 200 response with assistant message
    - Verify chat record created in DynamoDB
    - Verify EventBridge event emitted
    - _Requirements: 1.1, 6.7, 7.1_

  - [ ] 13.3 Test error scenarios
    - Test missing pk field (expect 400)
    - Test invalid pk (expect 404 or 500)
    - Test malformed JSON (expect 400)
    - _Requirements: 1.4, 1.5, 2.5_

  - [ ] 13.4 Verify CloudWatch logs and metrics
    - Check Lambda invocation logs
    - Verify genome resolution logged
    - Verify Bedrock invocation logged
    - Verify EventBridge publish logged
    - _Requirements: 9.5_
