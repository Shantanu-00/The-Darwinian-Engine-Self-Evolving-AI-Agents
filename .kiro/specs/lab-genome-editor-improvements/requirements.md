# Requirements Document

## Introduction

This document specifies the requirements for improving The Lab genome editor interface to align with the DynamoDB schema used by the Darwinian Agent Engine, restrict model selection to specific AWS models, and enable genome loading and editing capabilities.

## Glossary

- **Genome**: A complete configuration object that defines an agent's behavior, including persona, operational guidelines, tools, and evolution rules
- **The Lab**: The Streamlit-based admin interface for creating and editing agent genomes
- **CURRENT Pointer**: A DynamoDB item with SK="CURRENT" that points to the active version of a genome via the `active_version_sk` attribute
- **Version SK**: A sort key in the format "VERSION#{ISO8601_timestamp}" that uniquely identifies a genome version
- **Lineage Key**: The partition key (PK) in the format "AGENT#{agent_identifier}" that groups all versions of an agent
- **DynamoDB Table**: The single-table design database named "DarwinianGenePool" that stores all genome data
- **EntityType**: A discriminator attribute that identifies the type of item (e.g., "Genome", "Chat", "Challenger", "Ticket")

## Requirements

### Requirement 1

**User Story:** As an admin, I want to create new genomes using only approved AWS models, so that I maintain consistency with our infrastructure and avoid using Anthropic models.

#### Acceptance Criteria

1. WHEN the admin selects a model from the dropdown THEN the system SHALL display only "meta.llama3-70b-instruct-v1:0" and "us.amazon.nova-premier-v1:0" as options
2. WHEN the admin attempts to save a genome THEN the system SHALL validate that the selected model_id matches one of the two approved models
3. WHEN the form is initialized THEN the system SHALL set "us.amazon.nova-premier-v1:0" as the default model selection

### Requirement 2

**User Story:** As an admin, I want The Lab to use the same DynamoDB schema as the seed script, so that all components of the system can read and write genome data consistently.

#### Acceptance Criteria

1. WHEN saving a genome THEN the system SHALL structure the item with PK in format "AGENT#{agent_identifier}", SK in format "VERSION#{ISO8601_timestamp}", and EntityType="Genome"
2. WHEN saving a genome THEN the system SHALL wrap name, description, creator, version_hash, parent_hash, deployment_state, and mutation_reason in a "metadata" object
3. WHEN saving a genome THEN the system SHALL store config, economics, brain, resources, capabilities, and evolution_config as top-level attributes within the genome item
4. WHEN saving a genome THEN the system SHALL use the table name "DarwinianGenePool" from secrets configuration
5. WHEN generating a version SK THEN the system SHALL use ISO8601 format timestamps (YYYY-MM-DDTHH:MM:SSZ) instead of custom version strings

### Requirement 3

**User Story:** As an admin, I want to deploy a genome and update the CURRENT pointer, so that the proxy agent uses the latest approved version.

#### Acceptance Criteria

1. WHEN the admin clicks "Deploy" THEN the system SHALL save the genome version item to DynamoDB
2. WHEN the genome version is saved successfully THEN the system SHALL create or update an item with SK="CURRENT" containing the active_version_sk pointing to the new version
3. WHEN updating the CURRENT pointer THEN the system SHALL use the same PK as the genome version and set last_updated to the current ISO8601 timestamp
4. WHEN the deployment completes THEN the system SHALL display the PK prominently in the success message
5. WHEN the admin clicks "Save" without deploying THEN the system SHALL save the genome version but NOT update the CURRENT pointer

### Requirement 4

**User Story:** As an admin, I want to see the deployed genome's PK displayed in The Lab after deployment, so that I can easily reference and share the agent identifier.

#### Acceptance Criteria

1. WHEN a genome is successfully deployed THEN the system SHALL display the PK in a prominent success message
2. WHEN displaying the PK THEN the system SHALL format it as "AGENT#{agent_identifier}" for clarity
3. WHEN the deployment message is shown THEN the system SHALL include both the PK and the version SK for complete reference
4. WHEN multiple genomes are deployed in a session THEN the system SHALL display each deployment's PK separately
5. WHEN the form is reset after deployment THEN the system SHALL maintain the success message with the PK visible until the next action

### Requirement 5

**User Story:** As an admin, I want to specify a custom agent identifier when creating a genome, so that I can organize agents by meaningful names rather than auto-generated hashes.

#### Acceptance Criteria

1. WHEN creating a new genome THEN the system SHALL provide an input field for "Agent Identifier" in the Identity section
2. WHEN the admin provides an agent identifier THEN the system SHALL use it to construct the PK as "AGENT#{agent_identifier}"
3. WHEN the agent identifier field is empty THEN the system SHALL generate a PK using a hash of the genome name
4. WHEN the agent identifier contains special characters THEN the system SHALL sanitize it to use only alphanumeric characters and hyphens
5. WHEN loading an existing genome THEN the system SHALL display the agent identifier extracted from the PK

### Requirement 6

**User Story:** As an admin, I want the genome editor to validate required fields before saving, so that I don't create incomplete or invalid genome configurations.

#### Acceptance Criteria

1. WHEN the admin attempts to save without filling required fields THEN the system SHALL prevent submission and display specific error messages for each missing field
2. WHEN all required fields are filled THEN the system SHALL enable the Save and Deploy buttons
3. WHEN the admin enters invalid JSON in tool schemas THEN the system SHALL display a validation error before attempting to save
4. WHEN numeric fields receive non-numeric input THEN the system SHALL display appropriate validation errors
5. WHEN the form is successfully submitted THEN the system SHALL clear all fields and reset the form state
