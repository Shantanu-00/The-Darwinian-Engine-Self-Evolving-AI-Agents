# Design Document: Lab Genome Editor Improvements

## Overview

The Lab Genome Editor is a Streamlit-based administrative interface for creating and deploying agent genomes in the Darwinian Agent Engine. This design addresses critical alignment issues between The Lab's current implementation and the DynamoDB schema used by the rest of the system, restricts model selection to approved AWS models, and enhances the deployment workflow with clear PK display.

The primary goals are:
1. Ensure schema consistency across all system components
2. Restrict model selection to Meta Llama 70B Instruct and Amazon Nova Premier
3. Provide clear feedback on deployed genome identifiers
4. Enable custom agent naming for better organization

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    The Lab (Streamlit UI)               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Genome Form (7 Sections)                         │  │
│  │  - Identity & Governance                          │  │
│  │  - Config (Model Selection)                       │  │
│  │  - Economics                                      │  │
│  │  - Brain (Persona, Guidelines)                    │  │
│  │  - Resources (Knowledge Base, Policy)             │  │
│  │  - Capabilities (Tools)                           │  │
│  │  - Evolution Config (Critic, Judge)               │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Genome Builder & Validator                       │  │
│  │  - Schema transformation                          │  │
│  │  - Field validation                               │  │
│  │  - PK/SK generation                               │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  DynamoDB Writer                                  │  │
│  │  - Write genome version                           │  │
│  │  - Update CURRENT pointer (if deploying)          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              DynamoDB: DarwinianGenePool                │
│                                                         │
│  PK: AGENT#CarSalesman-auto-01                         │
│  ├─ SK: CURRENT                                        │
│  │  └─ active_version_sk: VERSION#2025-11-27T10:00:00Z│
│  │                                                     │
│  └─ SK: VERSION#2025-11-27T10:00:00Z                  │
│     └─ EntityType: Genome                             │
│        └─ metadata: {...}                             │
│        └─ config: {...}                               │
│        └─ brain: {...}                                │
│        └─ resources: {...}                            │
│        └─ capabilities: {...}                         │
│        └─ evolution_config: {...}                     │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Form Input**: Admin fills out genome configuration across 7 sections
2. **Validation**: System validates required fields, JSON schemas, and model selection
3. **Transformation**: Form data is transformed into the canonical DynamoDB schema
4. **Version Creation**: New genome version is written with generated PK/SK
5. **Deployment (Optional)**: CURRENT pointer is updated to reference the new version
6. **Feedback**: PK and version SK are displayed to the admin

## Components and Interfaces

### 1. Genome Form Component

**Responsibility**: Collect genome configuration from admin users

**Sections**:
- **Section 1 - Identity & Governance**: name, description, creator, agent_identifier
- **Section 2 - Config**: model_id (restricted dropdown), temperature, max_tokens
- **Section 3 - Economics**: token_budget, initial likes/dislikes
- **Section 4 - Brain**: persona (role, tone), style_guide, objectives, operational_guidelines
- **Section 5 - Resources**: knowledge_base_text, policy_text
- **Section 6 - Capabilities**: tools (name, description, input_schema)
- **Section 7 - Evolution Config**: critic_rules, judge_rubric

**Key Changes**:
- Add "Agent Identifier" text input in Section 1
- Replace model dropdown options with only approved AWS models
- Set default model to "us.amazon.nova-premier-v1:0"

### 2. Schema Transformer

**Responsibility**: Convert form data to DynamoDB schema format

**Input**: Raw form data (flat structure with Streamlit widgets)

**Output**: DynamoDB item structure matching seed_final_db.py format

**Transformation Rules**:
```python
{
    "PK": "AGENT#{agent_identifier}",
    "SK": "VERSION#{iso8601_timestamp}",
    "EntityType": "Genome",
    "metadata": {
        "name": form.name,
        "description": form.description,
        "creator": form.creator,
        "version_hash": generated_hash,
        "parent_hash": "null" or previous_version_hash,
        "deployment_state": "ACTIVE" if deploying else "DRAFT",
        "mutation_reason": form.mutation_reason or "Initial creation"
    },
    "config": {
        "model_id": form.model_id,
        "temperature": str(form.temperature),
        "max_tokens": int(form.max_tokens)
    },
    "economics": {
        "likes": 0,
        "dislikes": 0,
        "input_token_count": 0,
        "token_budget": int(form.token_budget),
        "estimated_cost_of_calling": calculated_estimate
    },
    "brain": {
        "persona": {
            "role": form.persona_role,
            "tone": form.persona_tone
        },
        "style_guide": parse_lines(form.style_guide_text),
        "objectives": parse_lines(form.objectives_text),
        "operational_guidelines": parse_lines(form.operational_guidelines_text)
    },
    "resources": {
        "knowledge_base_text": form.knowledge_base_text,
        "policy_text": form.policy_text
    },
    "capabilities": {
        "active_tools": form.tools_list,
        "simulation_mocks": {}
    },
    "evolution_config": {
        "critic_rules": parse_lines(form.critic_rules_text),
        "judge_rubric": parse_lines(form.judge_rubric_text)
    }
}
```

### 3. DynamoDB Writer

**Responsibility**: Persist genome data to DynamoDB

**Operations**:

1. **write_genome_version(item)**: Writes a new genome version
   - Input: Transformed genome item
   - Output: Success/failure status
   - Side effects: Creates new item in DynamoDB

2. **update_current_pointer(pk, version_sk)**: Updates the CURRENT pointer
   - Input: Partition key and version sort key
   - Output: Success/failure status
   - Side effects: Creates/updates CURRENT item in DynamoDB

**DynamoDB Table Configuration**:
- Table name: Retrieved from `st.secrets["DYNAMODB_TABLE"]` (should be "DarwinianGenePool")
- Region: Retrieved from `st.secrets["AWS_REGION"]` (default: "us-east-1")

### 4. Validator Component

**Responsibility**: Validate form inputs before submission

**Validation Rules**:
- Required fields: name, description, creator, persona_role, persona_tone, objectives, operational_guidelines, critic_rules, judge_rubric
- Model ID: Must be one of the two approved models
- Temperature: Must be between 0.0 and 1.0
- Max tokens: Must be positive integer
- Token budget: Must be non-negative integer
- Tool schemas: Must be valid JSON if provided
- Agent identifier: Must contain only alphanumeric characters and hyphens (if provided)

## Data Models

### Genome Item (DynamoDB)

```python
{
    "PK": str,                    # Format: "AGENT#{agent_identifier}"
    "SK": str,                    # Format: "VERSION#{ISO8601_timestamp}"
    "EntityType": str,            # Always "Genome"
    "metadata": {
        "name": str,
        "description": str,
        "creator": str,
        "version_hash": str,
        "parent_hash": str,
        "deployment_state": str,  # "ACTIVE" | "DRAFT" | "PENDING_APPROVAL"
        "mutation_reason": str
    },
    "config": {
        "model_id": str,          # "meta.llama3-70b-instruct-v1:0" | "us.amazon.nova-premier-v1:0"
        "temperature": str,       # String representation of float
        "max_tokens": int
    },
    "economics": {
        "likes": int,
        "dislikes": int,
        "input_token_count": int,
        "token_budget": int,
        "estimated_cost_of_calling": str
    },
    "brain": {
        "persona": {
            "role": str,
            "tone": str
        },
        "style_guide": List[str],
        "objectives": List[str],
        "operational_guidelines": List[str]
    },
    "resources": {
        "knowledge_base_text": str,
        "policy_text": str
    },
    "capabilities": {
        "active_tools": List[Tool],
        "simulation_mocks": Dict[str, Any]
    },
    "evolution_config": {
        "critic_rules": List[str],
        "judge_rubric": List[str]
    }
}
```

### Tool Schema

```python
{
    "name": str,
    "description": str,
    "input_schema": {
        "type": "object",
        "properties": Dict[str, Any]
    }
}
```

### CURRENT Pointer Item

```python
{
    "PK": str,                    # Same as genome PK
    "SK": "CURRENT",              # Literal string
    "active_version_sk": str,     # Points to a genome version SK
    "last_updated": str           # ISO8601 timestamp
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Model validation rejects unapproved models

*For any* model_id string that is not "meta.llama3-70b-instruct-v1:0" or "us.amazon.nova-premier-v1:0", the validation function should return false or raise a validation error.

**Validates: Requirements 1.2**

### Property 2: Genome items follow canonical schema structure

*For any* genome data submitted through the form, the transformed DynamoDB item should have:
- PK in format "AGENT#{agent_identifier}"
- SK in format "VERSION#{ISO8601_timestamp}" matching pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`
- EntityType field equal to "Genome"
- A "metadata" object containing name, description, creator, version_hash, parent_hash, deployment_state, and mutation_reason
- Top-level attributes for config, economics, brain, resources, capabilities, and evolution_config

**Validates: Requirements 2.1, 2.2, 2.3, 2.5**

### Property 3: Deploy action creates both genome and CURRENT pointer

*For any* valid genome data, when the deploy action is triggered, the system should write exactly two items to DynamoDB:
1. A genome version item with SK="VERSION#{timestamp}"
2. A CURRENT pointer item with SK="CURRENT", active_version_sk pointing to the genome version, and matching PK

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 4: Save action creates only genome version

*For any* valid genome data, when the save action (without deploy) is triggered, the system should write exactly one item to DynamoDB with SK matching "VERSION#{timestamp}" pattern, and should NOT create or update any item with SK="CURRENT".

**Validates: Requirements 3.5**

### Property 5: Success message contains formatted identifiers

*For any* successful deployment, the displayed success message should contain both:
- The PK formatted as "AGENT#{agent_identifier}"
- The version SK formatted as "VERSION#{ISO8601_timestamp}"

**Validates: Requirements 3.4, 4.1, 4.2, 4.3**

### Property 6: Agent identifier determines PK format

*For any* provided agent identifier string, the generated PK should be "AGENT#{sanitized_identifier}" where sanitized_identifier contains only alphanumeric characters and hyphens.

**Validates: Requirements 5.2, 5.4**

### Property 7: Empty identifier triggers hash-based PK

*For any* genome with an empty agent identifier field, the system should generate a PK using "AGENT#{hash}" where hash is derived from the genome name.

**Validates: Requirements 5.3**

### Property 8: Required field validation prevents incomplete submissions

*For any* form submission missing one or more required fields (name, description, creator, persona_role, persona_tone, objectives, operational_guidelines, critic_rules, judge_rubric), the validation should fail and prevent the save/deploy action.

**Validates: Requirements 6.1**

### Property 9: Invalid JSON in tool schemas triggers validation error

*For any* tool schema input that is not valid JSON, the validation should detect the error and prevent form submission.

**Validates: Requirements 6.3**

## Error Handling

### Validation Errors

**Field-Level Validation**:
- Display inline error messages for each invalid field
- Prevent form submission until all errors are resolved
- Provide specific guidance (e.g., "Agent identifier can only contain letters, numbers, and hyphens")

**JSON Validation**:
- Catch JSON parsing errors in tool schemas
- Display the specific JSON error message to help debugging
- Highlight the problematic tool input

### DynamoDB Errors

**Connection Failures**:
- Catch boto3 connection exceptions
- Display user-friendly error: "Unable to connect to database. Please check your AWS credentials."
- Log detailed error for debugging

**Write Failures**:
- Catch put_item exceptions
- Display error: "Failed to save genome. Please try again."
- Preserve form data so user doesn't lose work

**Conditional Check Failures**:
- If CURRENT pointer update fails due to concurrent modification
- Retry the update operation once
- If retry fails, display warning but confirm genome version was saved

### Configuration Errors

**Missing Secrets**:
- Check for required secrets (DYNAMODB_TABLE, AWS_REGION) on page load
- Display clear error if secrets are missing
- Provide instructions for configuring secrets.toml

**Invalid Table Name**:
- If table doesn't exist, catch ResourceNotFoundException
- Display error: "Database table '{table_name}' not found. Please verify configuration."

## Testing Strategy

### Unit Testing

We will use **pytest** for unit testing Python functions.

**Test Coverage**:
- Schema transformation logic (form data → DynamoDB item)
- PK/SK generation functions
- Agent identifier sanitization
- Validation functions (required fields, model selection, JSON parsing)
- Timestamp formatting (ISO8601)

**Example Unit Tests**:
```python
def test_sanitize_agent_identifier():
    assert sanitize_identifier("My-Agent_123!") == "My-Agent-123"
    assert sanitize_identifier("Test@#$Agent") == "TestAgent"

def test_generate_pk_with_identifier():
    pk = generate_pk("my-custom-agent", "Test Genome")
    assert pk == "AGENT#my-custom-agent"

def test_generate_pk_without_identifier():
    pk = generate_pk("", "Test Genome")
    assert pk.startswith("AGENT#")
    assert len(pk) > 6  # Has hash component
```

### Property-Based Testing

We will use **Hypothesis** for property-based testing in Python.

**Configuration**: Each property test will run a minimum of 100 iterations to ensure thorough coverage of the input space.

**Test Tagging**: Each property-based test will include a comment explicitly referencing the correctness property using the format: `# Feature: lab-genome-editor-improvements, Property {number}: {property_text}`

**Property Test Coverage**:
- Model validation with random strings
- Schema structure verification with random genome data
- PK/SK format validation across various inputs
- Agent identifier sanitization with random special characters
- Required field validation with various combinations of missing fields

**Example Property Tests**:
```python
from hypothesis import given, strategies as st

# Feature: lab-genome-editor-improvements, Property 1: Model validation rejects unapproved models
@given(st.text())
def test_model_validation_property(model_id):
    approved = ["meta.llama3-70b-instruct-v1:0", "us.amazon.nova-premier-v1:0"]
    result = validate_model_id(model_id)
    if model_id in approved:
        assert result is True
    else:
        assert result is False

# Feature: lab-genome-editor-improvements, Property 2: Genome items follow canonical schema structure
@given(st.builds(GenomeFormData))
def test_schema_structure_property(form_data):
    item = transform_to_dynamodb_item(form_data)
    
    # Verify PK format
    assert item["PK"].startswith("AGENT#")
    
    # Verify SK format (ISO8601)
    assert re.match(r"VERSION#\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", item["SK"])
    
    # Verify EntityType
    assert item["EntityType"] == "Genome"
    
    # Verify metadata structure
    assert "metadata" in item
    required_metadata = ["name", "description", "creator", "version_hash", 
                         "parent_hash", "deployment_state", "mutation_reason"]
    for field in required_metadata:
        assert field in item["metadata"]
    
    # Verify top-level attributes
    top_level = ["config", "economics", "brain", "resources", 
                 "capabilities", "evolution_config"]
    for attr in top_level:
        assert attr in item
```

### Integration Testing

**Scope**: Test the complete flow from form submission to DynamoDB writes

**Test Scenarios**:
1. Create and save a genome (without deploy)
2. Create and deploy a genome (with CURRENT pointer update)
3. Deploy multiple genomes and verify CURRENT pointer updates
4. Test with various agent identifiers (custom, empty, special characters)
5. Test with both approved models

**Mocking Strategy**:
- Mock DynamoDB table for integration tests
- Use moto library for AWS service mocking
- Verify correct put_item calls with expected item structures

### Manual Testing Checklist

1. Form displays with all 7 sections
2. Model dropdown shows only two approved models
3. Default model is Amazon Nova Premier
4. Agent identifier field is present and functional
5. Save button creates genome version only
6. Deploy button creates genome version + CURRENT pointer
7. Success message displays PK and version SK
8. Form resets after successful submission
9. Validation errors display for missing required fields
10. Invalid JSON in tool schemas shows error
11. Special characters in agent identifier are sanitized
12. Empty agent identifier generates hash-based PK
