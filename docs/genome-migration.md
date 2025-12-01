# Darwinian Agent Genome Migration Guide
## GCP → AWS Architecture Modernization

---

## Table of Contents

1. [Overview](#overview)
2. [New Genome Structure](#new-genome-structure)
3. [Section-by-Section Breakdown](#section-by-section-breakdown)
4. [Migration Mapping](#migration-mapping)
5. [Implementation Guide](#implementation-guide)

---

## Overview

This document outlines the migration path from the legacy GCP-based genome schema to the modernized AWS DynamoDB-optimized structure. The new schema introduces better organization, evolution tracking, and cost management while maintaining backward compatibility in core concepts.

**Migration Goals:**
- Optimize for AWS DynamoDB storage and querying
- Enhance evolution tracking and lineage management
- Introduce cost and performance metrics
- Simplify schema structure while adding capabilities
- Enable tool-based agent interactions

---

## New Genome Structure

The modernized genome consists of 7 core sections, each serving a distinct purpose:

```json
{
  // --- DYNAMODB KEYS ---
  "PK": "AGENT#CarSalesman-auto-01",
  "SK": "VERSION#2025-11-27T11:30:00Z",

  // --- SECTION 1: GOVERNANCE & IDENTITY ---
  "metadata": {
    "name": "Car Auto Concierge - V2.1",
    "description": "Optimized lead capture logic with consolidated guidelines.",
    "creator": "Darwinian_Evolution_Engine",
    "version_hash": "f7a8b9c0...",
    "parent_hash": "e4d909c2...",
    "deployment_state": "ACTIVE",
    "mutation_reason": "Refactoring: Critic detected 15% drop in sentiment. V2.1 adds 'Expedited Protocol' for VIPs."
  },

  // --- SECTION 2: CONFIG ---
  "config": {
    "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "temperature": 0.2,
    "max_tokens": 800
  },

  // --- SECTION 3: ECONOMICS ---
  "economics": {
    "likes": 2,
    "dislikes": 4,
    "input_token_count": 420,
    "token_budget": 600,
    "estimated_cost_of_calling": "$0.001"
  },

  // --- SECTION 4: THE BRAIN ---
  "brain": {
    "persona": {
      "role": "Senior Sales Concierge",
      "tone": "High-Energy, Consultative"
    },
    "style_guide": [
      "Use Markdown.",
      "Be definitive."
    ],
    "objectives": [
      "Prioritize capturing Email/Phone."
    ],
    "operational_guidelines": [
      "PROTOCOL 1: If inventory is 0, offer Pre-Order immediately.",
      "PROTOCOL 2: If user is 'Ian', expedite request.",
      "PROTOCOL 3: Always quote MSRP."
    ]
  },

  // --- SECTION 5: RESOURCES (Text Box) ---
  "resources": {
    "knowledge_base_text": "INVENTORY: Model X (0 Stock). Model Y (5 Stock).",
    "policy_text": "LEGAL: Deposits 100% refundable."
  },

  // --- SECTION 6: CAPABILITIES ---
  "capabilities": {
    "active_tools": [
      { 
        "name": "check_incoming", 
        "description": "Check inventory status for incoming vehicles", 
        "input_schema": {
          "type": "object",
          "properties": {
            "model": { "type": "string" }
          }
        }
      },
      { 
        "name": "capture_lead", 
        "description": "Capture customer contact information", 
        "input_schema": {
          "type": "object",
          "properties": {
            "email": { "type": "string" },
            "phone": { "type": "string" }
          }
        }
      }
    ],
    "simulation_mocks": {
      "check_incoming": { 
        "status": "success", 
        "arrival": "Tue" 
      },
      "capture_lead": { 
        "status": "success" 
      }
    }
  },

  // --- SECTION 7: EVOLUTION CONFIG ---
  "evolution_config": {
    "critic_rules": [
      "FAIL if the user expresses frustration.",
      "FAIL if the conversation ends without a lead capture.",
      "FAIL if the agent apologizes more than once."
    ],
    "judge_rubric": [
      "Did the agent offer the 'Incoming' Model X?",
      "Did the agent capture the email?"
    ]
  }
}
```

---

## Section-by-Section Breakdown

### DynamoDB Keys

**Purpose:** Enable efficient querying and version management in DynamoDB.

| Field | Format | Description |
|-------|--------|-------------|
| `PK` | `AGENT#{agent-id}` | Partition key - groups all versions of an agent |
| `SK` | `VERSION#{ISO-8601-timestamp}` | Sort key - orders versions chronologically |

**Example:**
```json
"PK": "AGENT#CarSalesman-auto-01",
"SK": "VERSION#2025-11-27T11:30:00Z"
```

**Query Patterns:**
- Get all versions of an agent: Query by PK
- Get latest version: Query by PK, sort by SK descending, limit 1
- Get version history: Query by PK, sort by SK

---

### Section 1: Governance & Identity (metadata)

**Purpose:** Track who created the agent, why it exists, and its evolutionary lineage.

#### Identity Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Human-readable agent name | "Car Auto Concierge - V2.1" |
| `description` | string | What this version does | "Optimized lead capture logic..." |
| `creator` | enum | Who created this version | "Darwinian_Evolution_Engine" or "Human_Admin" |

#### Technical Lineage

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `version_hash` | string | SHA-256 hash of genome content | "f7a8b9c0..." |
| `parent_hash` | string/null | Hash of parent genome (null for v1) | "e4d909c2..." |
| `deployment_state` | enum | Current deployment status | "ACTIVE", "DRAFT", "ARCHIVED", "FAILED" |

#### The Story

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `mutation_reason` | string | Why this mutation was created | "Critic detected 15% drop in sentiment..." |

**Why This Matters:**
- Enables full traceability of agent evolution
- Supports rollback to previous versions
- Documents the "why" behind each change
- Distinguishes human-created vs. auto-evolved agents

---

### Section 2: Config

**Purpose:** Define the AI model and generation parameters.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `model_id` | string | AWS Bedrock model identifier | "anthropic.claude-3-5-sonnet-20240620-v1:0" |
| `temperature` | float (0-1) | Randomness in responses | 0.2 (more deterministic) |
| `max_tokens` | integer | Maximum response length | 800 |

**Migration Note:** 
- Old: `config.modelName` (GCP Gemini format)
- New: `config.model_id` (AWS Bedrock format)
- Removed: `generationConfig` nesting - now flattened
- Removed: `topK` parameter (not used by Claude models)

---

### Section 3: Economics

**Purpose:** Track performance metrics and cost efficiency.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `likes` | integer | Positive feedback count | 2 |
| `dislikes` | integer | Negative feedback count | 4 |
| `input_token_count` | integer | Estimated tokens per invocation | 420 |
| `token_budget` | integer | Maximum allowed tokens | 600 |
| `estimated_cost_of_calling` | string | Cost per invocation | "$0.001" |

**Why This Matters:**
- Enables cost-based evolution decisions
- Tracks user satisfaction (likes/dislikes ratio)
- Monitors token efficiency
- Supports budget constraints

**Calculation Example:**
```
Success Rate = likes / (likes + dislikes) = 2 / 6 = 33%
Token Efficiency = input_token_count / token_budget = 420 / 600 = 70%
```

---

### Section 4: The Brain

**Purpose:** Define the agent's personality, behavior, and operational protocols.

#### Persona

Defines the agent's identity and communication style.

```json
"persona": {
  "role": "Senior Sales Concierge",
  "tone": "High-Energy, Consultative"
}
```

#### Style Guide

Array of formatting and communication rules.

```json
"style_guide": [
  "Use Markdown.",
  "Be definitive."
]
```

#### Objectives

Array of primary goals the agent should achieve.

```json
"objectives": [
  "Prioritize capturing Email/Phone."
]
```

#### Operational Guidelines

Array of specific protocols and decision rules.

```json
"operational_guidelines": [
  "PROTOCOL 1: If inventory is 0, offer Pre-Order immediately.",
  "PROTOCOL 2: If user is 'Ian', expedite request.",
  "PROTOCOL 3: Always quote MSRP."
]
```

**Migration Note:**
- Old: `context` (nested objects with `goal`, `beliefs`, `rules`)
- New: `brain` (simplified arrays)
- Removed: `systemPromptTemplate` (built dynamically from brain structure)

---

### Section 5: Resources

**Purpose:** Provide static knowledge and reference information.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `knowledge_base_text` | string | Domain-specific information | "INVENTORY: Model X (0 Stock)..." |
| `policy_text` | string | Rules, regulations, legal info | "LEGAL: Deposits 100% refundable." |

**Why This Matters:**
- Separates static knowledge from dynamic behavior
- Easier to update without changing agent logic
- Supports RAG (Retrieval Augmented Generation) patterns
- Can be expanded with additional text fields as needed

---

### Section 6: Capabilities

**Purpose:** Define tools the agent can use and their test mocks.

#### Active Tools

Array of tool definitions following AWS Bedrock tool schema.

```json
"active_tools": [
  { 
    "name": "check_incoming",
    "description": "Check inventory status for incoming vehicles",
    "input_schema": {
      "type": "object",
      "properties": {
        "model": { "type": "string" }
      }
    }
  }
]
```

#### Simulation Mocks

Mock responses for testing without external dependencies.

```json
"simulation_mocks": {
  "check_incoming": { 
    "status": "success", 
    "arrival": "Tue" 
  }
}
```

**Why This Matters:**
- Enables function calling / tool use
- Supports testing in isolation
- Documents available capabilities
- Facilitates capability-based evolution

---

### Section 7: Evolution Config

**Purpose:** Define rules for automated evaluation and evolution.

#### Critic Rules

Array of failure conditions that trigger mutations.

```json
"critic_rules": [
  "FAIL if the user expresses frustration.",
  "FAIL if the conversation ends without a lead capture.",
  "FAIL if the agent apologizes more than once."
]
```

#### Judge Rubric

Array of evaluation questions for scoring agent performance.

```json
"judge_rubric": [
  "Did the agent offer the 'Incoming' Model X?",
  "Did the agent capture the email?"
]
```

**Why This Matters:**
- Automates quality control
- Defines clear success criteria
- Enables data-driven evolution
- Supports A/B testing and optimization

---

## Migration Mapping

### Complete Field Mapping Table

| Old Schema (GCP) | New Schema (AWS) | Change Type | Notes |
|------------------|------------------|-------------|-------|
| `metadata.genomeId` | `PK` | **Restructured** | Now `AGENT#{id}` format for DynamoDB |
| `metadata.createdAt` | `SK` | **Restructured** | Now `VERSION#{timestamp}` format |
| `metadata.creatorId` | `metadata.creator` | **Simplified** | Enum: "Human_Admin" or "Darwinian_Evolution_Engine" |
| `metadata.status` | `metadata.deployment_state` | **Renamed** | Values: DRAFT, ACTIVE, ARCHIVED, FAILED |
| `metadata.visibility` | **Removed** | **Removed** | Not needed in new architecture |
| `metadata.updatedAt` | **Removed** | **Removed** | Tracked via SK (version timestamp) |
| `metadata.deploymentUrl` | **Removed** | **Removed** | Managed by infrastructure |
| `lineage.version` | `metadata.version_hash` | **Enhanced** | Integer → SHA-256 hash |
| `lineage.parentGenomeId` | `metadata.parent_hash` | **Renamed** | Tracks parent version hash |
| `lineage.latest` | **Removed** | **Removed** | Determined by DynamoDB query |
| `lineage.automutate` | **Removed** | **Removed** | Handled by evolution engine |
| `manifest.name` | `metadata.name` | **Consolidated** | Merged into metadata |
| `manifest.purpose` | `metadata.description` | **Consolidated** | Merged into metadata |
| N/A | `metadata.mutation_reason` | **New** | Documents why mutation occurred |
| `fitness.avgRating` | `economics.likes` / `economics.dislikes` | **Split** | Separate positive/negative metrics |
| `fitness.feedbackCount` | **Removed** | **Removed** | Calculated: likes + dislikes |
| `fitness.mutateOn` | **Removed** | **Removed** | Handled by evolution engine |
| `config.serviceType` | **Removed** | **Removed** | Implicit from model_id |
| `config.modelName` | `config.model_id` | **Renamed** | GCP format → AWS Bedrock format |
| `config.generationConfig.temperature` | `config.temperature` | **Flattened** | Removed nesting |
| `config.generationConfig.maxOutputTokens` | `config.max_tokens` | **Flattened** | Removed nesting |
| `config.generationConfig.topK` | **Removed** | **Removed** | Not used by Claude models |
| N/A | `economics.input_token_count` | **New** | Track token usage |
| N/A | `economics.token_budget` | **New** | Budget management |
| N/A | `economics.estimated_cost_of_calling` | **New** | Cost tracking |
| `context` | `brain` | **Renamed** | Better semantic meaning |
| `context.persona` | `brain.persona` | **Unchanged** | Same structure |
| `context.objectives.goal` | `brain.objectives` | **Simplified** | Object → Array |
| `context.objectives.beliefs` | `brain.operational_guidelines` | **Merged** | Combined with guardrails |
| `context.guardrails.rules` | `brain.operational_guidelines` | **Merged** | Combined with beliefs |
| N/A | `brain.style_guide` | **New** | Formatting instructions |
| `systemPromptTemplate` | **Removed** | **Removed** | Built dynamically from brain |
| N/A | `resources` | **New** | Knowledge base section |
| N/A | `capabilities` | **New** | Tool definitions |
| N/A | `evolution_config` | **New** | Evolution rules |

---

## Implementation Guide

### Step 1: Prepare Old Schema Data

Extract data from your GCP genome:

```javascript
// Old GCP Genome
const oldGenome = {
  metadata: {
    genomeId: "sarcastic-summarizer-v1",
    creatorId: "user-abc-123-xyz",
    status: "active",
    createdAt: "2025-11-08T12:00:00Z"
  },
  manifest: {
    name: "Sarcastic Summarizer",
    purpose: "Make boring text fun"
  },
  config: {
    modelName: "gemini-2.5-flash-preview-09-2025",
    generationConfig: {
      temperature: 0.7,
      maxOutputTokens: 512
    }
  },
  context: {
    persona: {
      role: "expert summarizer",
      tone: "sarcastic and witty"
    },
    objectives: {
      goal: "create funny summaries",
      beliefs: ["stay factual", "be playful"]
    },
    guardrails: {
      rules: ["no profanity", "no harmful content"]
    }
  }
};
```

### Step 2: Transform to New Schema

```javascript
// New AWS Genome
const newGenome = {
  // DynamoDB Keys
  PK: `AGENT#${oldGenome.metadata.genomeId}`,
  SK: `VERSION#${oldGenome.metadata.createdAt}`,
  
  // Metadata (consolidated)
  metadata: {
    name: oldGenome.manifest.name,
    description: oldGenome.manifest.purpose,
    creator: oldGenome.metadata.creatorId.startsWith('user-') 
      ? "Human_Admin" 
      : "Darwinian_Evolution_Engine",
    version_hash: generateHash(oldGenome),
    parent_hash: null, // First version
    deployment_state: oldGenome.metadata.status.toUpperCase(),
    mutation_reason: "Initial migration from GCP"
  },
  
  // Config (flattened)
  config: {
    model_id: "anthropic.claude-3-5-sonnet-20240620-v1:0", // Update to AWS model
    temperature: oldGenome.config.generationConfig.temperature,
    max_tokens: oldGenome.config.generationConfig.maxOutputTokens
  },
  
  // Economics (new)
  economics: {
    likes: 0,
    dislikes: 0,
    input_token_count: estimateTokens(oldGenome),
    token_budget: oldGenome.config.generationConfig.maxOutputTokens,
    estimated_cost_of_calling: "$0.001"
  },
  
  // Brain (restructured)
  brain: {
    persona: oldGenome.context.persona,
    style_guide: ["Use clear formatting"],
    objectives: [
      oldGenome.context.objectives.goal,
      ...oldGenome.context.objectives.beliefs
    ],
    operational_guidelines: [
      ...oldGenome.context.guardrails.rules.map((rule, i) => 
        `PROTOCOL ${i+1}: ${rule}`
      )
    ]
  },
  
  // Resources (new)
  resources: {
    knowledge_base_text: "",
    policy_text: ""
  },
  
  // Capabilities (new)
  capabilities: {
    active_tools: [],
    simulation_mocks: {}
  },
  
  // Evolution Config (new)
  evolution_config: {
    critic_rules: [
      "FAIL if user expresses dissatisfaction"
    ],
    judge_rubric: [
      "Did the agent complete the task?",
      "Was the response appropriate?"
    ]
  }
};
```

### Step 3: Validation Checklist

Before deploying migrated genomes:

- [ ] PK follows format: `AGENT#{agent-id}`
- [ ] SK follows format: `VERSION#{ISO-8601-timestamp}`
- [ ] `metadata.creator` is either "Human_Admin" or "Darwinian_Evolution_Engine"
- [ ] `metadata.deployment_state` is one of: DRAFT, ACTIVE, ARCHIVED, FAILED
- [ ] `config.model_id` uses AWS Bedrock format
- [ ] `config.temperature` is between 0 and 1
- [ ] `config.max_tokens` is a positive integer
- [ ] `economics` fields are populated with initial values
- [ ] `brain.objectives` is an array (not object)
- [ ] `brain.operational_guidelines` is an array (not object)
- [ ] `resources` section exists (can be empty)
- [ ] `capabilities` section exists (can be empty)
- [ ] `evolution_config` has at least one critic rule and judge rubric item

### Step 4: Deploy to DynamoDB

```python
import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('AgentGenomes')

# Put item
table.put_item(Item=newGenome)

# Query latest version
response = table.query(
    KeyConditionExpression='PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'AGENT#CarSalesman-auto-01'
    },
    ScanIndexForward=False,  # Sort descending
    Limit=1
)

latest_version = response['Items'][0]
```

---

## Summary

The new genome schema provides:

✅ **Better Organization** - Clear separation of concerns across 7 sections  
✅ **Evolution Tracking** - Complete lineage with version hashing  
✅ **Cost Management** - Token and cost tracking built-in  
✅ **DynamoDB Optimized** - Efficient querying with PK/SK structure  
✅ **Tool Support** - Native capability definitions  
✅ **Simplified Structure** - Flattened configs, array-based objectives  
✅ **Automated Evolution** - Critic rules and judge rubrics for quality control

The migration consolidates redundant fields, adds essential tracking capabilities, and positions the system for scalable evolution on AWS infrastructure.
