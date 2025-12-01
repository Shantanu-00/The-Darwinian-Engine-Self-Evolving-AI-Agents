# Requirements Document

## Introduction

This document specifies the requirements for improving the Lineage visualization page in the Darwinian Engine Admin Dashboard. The current implementation fetches unnecessary data and displays versions in a simple linear list. The improved version will provide an efficient data-fetching strategy, a hierarchical tree visualization with interactive cards, and a two-panel layout for better user experience.

## Glossary

- **Lineage System**: The version control system that tracks the evolution of agent genomes through parent-child relationships
- **Version Node**: A specific version of an agent genome identified by a version hash
- **Parent Hash**: A reference to the previous version from which a version was derived
- **Challenger**: Alternative genome variations (3-6 per version) that competed during the evolution process
- **Genome**: The configuration and parameters that define an agent's behavior
- **Rollback**: The action of reverting the active version to a previous version in the lineage
- **DynamoDB**: The AWS database service storing all lineage and version data
- **Tree Visualization**: A hierarchical graph display showing parent-child relationships between versions

## Requirements

### Requirement 1

**User Story:** As an admin user, I want the system to fetch only relevant version data from DynamoDB, so that the page loads quickly without unnecessary data transfer.

#### Acceptance Criteria

1. WHEN the lineage page loads THEN the Lineage System SHALL query only items where SK matches pattern "VERSION#{timestamp}" or "VERSION#{timestamp}#CHALLENGER#attempt-{n}"
2. WHEN querying DynamoDB THEN the Lineage System SHALL exclude items with SK containing "#CHAT#" or "#TICKET#"
3. WHEN fetching version data THEN the Lineage System SHALL retrieve the complete genome object including metadata, config, economics, brain, resources, capabilities, and evolution_config
4. WHEN the query completes THEN the Lineage System SHALL separate main versions from challengers based on SK pattern

### Requirement 2

**User Story:** As an admin user, I want to see a two-panel layout with the lineage tree on the left and details on the right, so that I can navigate the version history efficiently.

#### Acceptance Criteria

1. WHEN the lineage page renders THEN the Lineage System SHALL display a left panel occupying 60% of the viewport width
2. WHEN the lineage page renders THEN the Lineage System SHALL display a right panel occupying 40% of the viewport width
3. WHEN no version is selected THEN the Lineage System SHALL show placeholder text in the right panel
4. WHEN the viewport is resized THEN the Lineage System SHALL maintain the panel proportions responsively
5. WHILE viewing the page THEN the Lineage System SHALL allow independent scrolling of left and right panels

### Requirement 3

**User Story:** As an admin user, I want to see versions displayed as a hierarchical tree graph, so that I can understand the evolution path and branching structure.

#### Acceptance Criteria

1. WHEN versions are loaded THEN the Lineage System SHALL construct a tree structure based on parent_hash relationships from metadata
2. WHEN a version has parent_hash as "null" THEN the Lineage System SHALL position it as the root node labeled "V1"
3. WHEN displaying the tree THEN the Lineage System SHALL render each main version as a card showing dynamic label (V1, V2, V3...), mutation reason, and like/dislike counts from economics
4. WHEN multiple versions share the same parent THEN the Lineage System SHALL display them as connected child nodes in sequence
5. WHEN rendering connections THEN the Lineage System SHALL draw lines with mutation reason labels between parent and child nodes

### Requirement 4

**User Story:** As an admin user, I want to click on a version card in the tree to view its full details, so that I can inspect specific version information without cluttering the tree view.

#### Acceptance Criteria

1. WHEN a user clicks on a version card THEN the Lineage System SHALL display the full version details in the right panel
2. WHEN displaying version details THEN the Lineage System SHALL show the version hash, parent hash, mutation reason, creation timestamp, and genome configuration
3. WHEN displaying version details THEN the Lineage System SHALL highlight the selected card in the tree view
4. WHEN a different version card is clicked THEN the Lineage System SHALL update the right panel with the new version's details
5. WHEN version details are displayed THEN the Lineage System SHALL show a "Rollback to this version" button below the details

### Requirement 5

**User Story:** As an admin user, I want to see challengers associated with each version in a compact format, so that I can understand the competition without overwhelming the visualization.

#### Acceptance Criteria

1. WHEN a version has associated challengers THEN the Lineage System SHALL display them as small compact nodes showing mutation reason and attempt number
2. WHEN displaying challengers in the tree THEN the Lineage System SHALL render them in a space-efficient layout connected to their parent version
3. WHEN a version has 0, 3, or 6 challengers THEN the Lineage System SHALL arrange them without overlapping the main version nodes
4. WHEN displaying challengers THEN the Lineage System SHALL NOT show like/dislike counts or include them in V1/V2 naming
5. WHEN a user clicks on a challenger THEN the Lineage System SHALL display the challenger genome details in the right panel

### Requirement 6

**User Story:** As an admin user, I want to rollback to a previous version, so that I can restore the agent to a known good state.

#### Acceptance Criteria

1. WHEN viewing a non-active version's details THEN the Lineage System SHALL display a "Rollback to this version" button at the bottom of the right panel
2. WHEN viewing the currently active version THEN the Lineage System SHALL not display the rollback button
3. WHEN a user clicks the rollback button THEN the Lineage System SHALL update the item with PK={selected_lineage} and SK="CURRENT" setting active_version_sk to the selected version's SK
4. WHEN a rollback completes successfully THEN the Lineage System SHALL display a success message and refresh the tree view
5. WHEN a rollback fails THEN the Lineage System SHALL display an error message without modifying the current state

### Requirement 7

**User Story:** As an admin user, I want the lineage visualization to use modern interactive components, so that the interface feels responsive and professional.

#### Acceptance Criteria

1. WHEN rendering the tree visualization THEN the Lineage System SHALL use a React-based graph library or equivalent interactive visualization library
2. WHEN the tree is displayed THEN the Lineage System SHALL support pan and zoom interactions for navigating large lineages
3. WHEN hovering over version cards THEN the Lineage System SHALL provide visual feedback (e.g., highlight, shadow)
4. WHEN the tree layout is calculated THEN the Lineage System SHALL prevent node overlap and maintain readable spacing
5. WHEN displaying the tree THEN the Lineage System SHALL use the entire available viewport space efficiently

### Requirement 8

**User Story:** As an admin user, I want to see the mutation reason connecting parent and child versions, so that I understand why each evolution occurred.

#### Acceptance Criteria

1. WHEN displaying a connection between parent and child versions THEN the Lineage System SHALL show the mutation reason as a label on or near the connecting line
2. WHEN the mutation reason text is long THEN the Lineage System SHALL truncate it and show the full text on hover
3. WHEN rendering mutation reasons THEN the Lineage System SHALL format them in a readable, non-overlapping manner
4. WHEN a version has no mutation reason THEN the Lineage System SHALL display "Initial version" or "No reason provided"
