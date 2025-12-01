# Implementation Plan

- [x] 1. Update model selection and configuration


  - Modify the model_id selectbox to display only "meta.llama3-70b-instruct-v1:0" and "us.amazon.nova-premier-v1:0"
  - Set default model to "us.amazon.nova-premier-v1:0"
  - Remove all Anthropic model references
  - _Requirements: 1.1, 1.3_

- [ ]* 1.1 Write property test for model validation
  - **Property 1: Model validation rejects unapproved models**
  - **Validates: Requirements 1.2**


- [ ] 2. Add agent identifier input field
  - Add "Agent Identifier" text input in Section 1 (Identity & Governance)
  - Add helper text explaining the identifier format (alphanumeric and hyphens only)
  - Make the field optional with clear indication that empty will auto-generate

  - _Requirements: 5.1_

- [ ] 3. Implement agent identifier sanitization and PK generation
  - Create `sanitize_identifier()` function to remove special characters, keeping only alphanumeric and hyphens
  - Create `generate_pk()` function that uses agent identifier if provided, otherwise generates hash from genome name
  - Ensure PK format is always "AGENT#{identifier}"
  - _Requirements: 5.2, 5.3, 5.4_

- [ ]* 3.1 Write unit tests for identifier sanitization
  - Test sanitization with various special characters
  - Test empty identifier fallback to hash generation
  - Test PK format consistency
  - _Requirements: 5.2, 5.3, 5.4_

- [ ]* 3.2 Write property test for agent identifier PK generation
  - **Property 6: Agent identifier determines PK format**

  - **Property 7: Empty identifier triggers hash-based PK**
  - **Validates: Requirements 5.2, 5.3, 5.4**

- [ ] 4. Implement schema transformation to match seed_final_db.py format
  - Create `transform_to_dynamodb_item()` function
  - Wrap name, description, creator, version_hash, parent_hash, deployment_state, mutation_reason in "metadata" object
  - Keep config, economics, brain, resources, capabilities, evolution_config as top-level attributes
  - Add "EntityType": "Genome" field
  - Generate version_hash for the genome
  - Use ISO8601 timestamp format for SK: "VERSION#{YYYY-MM-DDTHH:MM:SSZ}"
  - _Requirements: 2.1, 2.2, 2.3, 2.5_


- [ ]* 4.1 Write property test for schema structure
  - **Property 2: Genome items follow canonical schema structure**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.5_

- [x] 5. Update DynamoDB table configuration

  - Verify table name is read from st.secrets["DYNAMODB_TABLE"]
  - Add fallback to "DarwinianGenePool" if not configured
  - Ensure AWS region is properly configured
  - _Requirements: 2.4_

- [ ] 6. Implement save functionality (genome version only)
  - Update save button handler to use new schema transformation
  - Write genome version item to DynamoDB with transformed structure
  - Do NOT update CURRENT pointer when saving
  - Display success message with PK and version SK

  - _Requirements: 3.5_

- [ ]* 6.1 Write property test for save action
  - **Property 4: Save action creates only genome version**
  - **Validates: Requirements 3.5**

- [ ] 7. Implement deploy functionality (genome version + CURRENT pointer)
  - Update deploy button handler to use new schema transformation
  - Write genome version item to DynamoDB
  - Create/update CURRENT pointer item with SK="CURRENT", active_version_sk, and last_updated
  - Ensure CURRENT pointer uses same PK as genome version

  - Set deployment_state to "ACTIVE" in metadata
  - _Requirements: 3.1, 3.2, 3.3_

- [ ]* 7.1 Write property test for deploy action
  - **Property 3: Deploy action creates both genome and CURRENT pointer**
  - **Validates: Requirements 3.1, 3.2, 3.3**

- [ ] 8. Update success message display
  - Format success message to prominently display PK in format "AGENT#{agent_identifier}"
  - Include version SK in format "VERSION#{timestamp}"

  - Use Streamlit success component with clear formatting
  - Ensure message persists until form is reset
  - _Requirements: 3.4, 4.1, 4.2, 4.3_

- [ ]* 8.1 Write property test for success message format
  - **Property 5: Success message contains formatted identifiers**
  - **Validates: Requirements 3.4, 4.1, 4.2, 4.3**

- [ ] 9. Implement form validation
  - Add validation for required fields: name, description, creator, persona_role, persona_tone, objectives, operational_guidelines, critic_rules, judge_rubric
  - Add model_id validation to ensure it's one of the two approved models
  - Add JSON validation for tool schemas
  - Display specific error messages for each validation failure
  - Prevent form submission if validation fails
  - _Requirements: 1.2, 6.1, 6.3_


- [ ]* 9.1 Write property test for required field validation
  - **Property 8: Required field validation prevents incomplete submissions**
  - **Validates: Requirements 6.1**

- [ ]* 9.2 Write property test for JSON validation
  - **Property 9: Invalid JSON in tool schemas triggers validation error**

  - **Validates: Requirements 6.3**

- [ ] 10. Add error handling for DynamoDB operations
  - Wrap DynamoDB put_item calls in try-except blocks
  - Handle connection failures with user-friendly messages

  - Handle write failures while preserving form data
  - Implement retry logic for CURRENT pointer updates
  - Log errors for debugging
  - _Design: Error Handling section_

- [x] 11. Add configuration validation

  - Check for required secrets (DYNAMODB_TABLE, AWS_REGION) on page load
  - Display clear error messages if secrets are missing
  - Handle ResourceNotFoundException for invalid table names
  - _Design: Error Handling section_



- [ ] 12. Update economics section with proper data types
  - Ensure temperature is stored as string representation of float
  - Ensure max_tokens and token_budget are stored as integers
  - Initialize likes, dislikes, and input_token_count to 0
  - Add estimated_cost_of_calling calculation or placeholder
  - _Requirements: 2.2, Design: Data Models_

- [ ] 13. Update capabilities section structure
  - Rename "tools" to "active_tools" in the capabilities object
  - Add empty "simulation_mocks" dictionary to capabilities
  - Ensure tool schema structure matches seed_final_db.py format
  - _Requirements: 2.3, Design: Data Models_

- [ ] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
