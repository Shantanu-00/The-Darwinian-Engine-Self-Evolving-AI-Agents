# Design Document

## Overview

This design document outlines the technical approach for improving the Lineage visualization page in the Darwinian Engine Admin Dashboard. The solution will replace the current linear list view with an interactive hierarchical tree graph, implement efficient data fetching to exclude unnecessary items, and provide a two-panel layout for better user experience.

The implementation will use Streamlit as the base framework with custom HTML/CSS/JavaScript components for the interactive tree visualization, leveraging D3.js or a similar graph library for rendering the hierarchical structure.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Lineage.py (Streamlit)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────────┐    │
│  │  Data Layer      │         │  Presentation Layer  │    │
│  │                  │         │                      │    │
│  │ - DynamoDB Query │────────▶│ - Tree Builder       │    │
│  │ - Data Filter    │         │ - Layout Manager     │    │
│  │ - Version Parser │         │ - Interactive Graph  │    │
│  └──────────────────┘         └──────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
   ┌──────────┐                      ┌────────────────┐
   │ DynamoDB │                      │ Browser (D3.js)│
   └──────────┘                      └────────────────┘
```

### Component Breakdown

1. **Data Fetching Module**: Queries DynamoDB and filters results
2. **Version Parser**: Separates main versions from challengers
3. **Tree Builder**: Constructs hierarchical structure from parent_hash relationships
4. **Graph Renderer**: Generates interactive visualization using D3.js or similar
5. **Detail Panel**: Displays selected version/challenger genome data
6. **Rollback Handler**: Updates CURRENT pointer in DynamoDB

## Components and Interfaces

### 1. Data Fetching Module

**Purpose**: Query DynamoDB efficiently and filter out unwanted items

**Interface**:
```python
def fetch_lineage_data(table, pk: str) -> dict:
    """
    Fetch all versions and challengers for a given lineage PK.
    
    Args:
        table: DynamoDB table resource
        pk: Primary key (e.g., "AGENT#CarSalesman-auto-01")
    
    Returns:
        {
            'versions': [list of main version items],
            'challengers': [list of challenger items],
            'current_version_sk': str
        }
    """
```

**Implementation Details**:
- Use `query()` with KeyConditionExpression on PK
- Filter SK to match patterns: `VERSION#{timestamp}` or `VERSION#{timestamp}#CHALLENGER#attempt-{n}`
- Exclude items containing `#CHAT#` or `#TICKET#`
- Fetch CURRENT item separately to identify active version

### 2. Version Parser

**Purpose**: Separate and categorize fetched items

**Interface**:
```python
def parse_versions(items: list) -> tuple:
    """
    Parse items into main versions and challengers.
    
    Args:
        items: List of DynamoDB items
    
    Returns:
        (main_versions: list, challengers_by_parent: dict)
    """
```

**Implementation Details**:
- Main versions: SK matches `VERSION#{timestamp}` exactly
- Challengers: SK matches `VERSION#{timestamp}#CHALLENGER#attempt-{n}`
- Group challengers by their parent version timestamp
- Sort main versions by timestamp

### 3. Tree Builder

**Purpose**: Construct hierarchical tree structure from flat version list

**Interface**:
```python
def build_tree(versions: list) -> dict:
    """
    Build tree structure from versions using parent_hash.
    
    Args:
        versions: List of version items with metadata.parent_hash
    
    Returns:
        Tree structure with nodes and edges
    """
```

**Implementation Details**:
- Find root node (parent_hash == "null")
- Build parent-child relationships using version_hash and parent_hash
- Assign sequential labels (V1, V2, V3...) based on tree traversal order
- Include mutation_reason for edge labels
- Attach challengers to their parent versions

### 4. Graph Renderer Component

**Purpose**: Render interactive tree visualization

**Technology**: Streamlit + HTML/CSS/JavaScript with D3.js

**Interface**:
```python
def render_tree_graph(tree_data: dict, active_version_sk: str) -> None:
    """
    Render interactive tree graph using Streamlit components.
    
    Args:
        tree_data: Tree structure with nodes and edges
        active_version_sk: Currently active version SK
    """
```

**Implementation Details**:
- Use `st.components.v1.html()` to embed custom HTML/JS
- D3.js for tree layout and rendering
- Node representation:
  - Main versions: Card with label (V1, V2...), mutation reason, likes/dislikes
  - Challengers: Smaller card with attempt number and mutation reason
- Edge representation: Lines with mutation reason labels
- Interactive features:
  - Click to select node
  - Highlight active version
  - Pan and zoom support
- Return selected node SK via Streamlit session state

### 5. Detail Panel

**Purpose**: Display full genome data for selected version/challenger

**Interface**:
```python
def render_detail_panel(selected_item: dict, is_active: bool) -> None:
    """
    Render detail panel with genome data and rollback button.
    
    Args:
        selected_item: Full genome/challenger item from DynamoDB
        is_active: Whether this is the currently active version
    """
```

**Implementation Details**:
- Display all genome sections: metadata, config, economics, brain, resources, capabilities, evolution_config
- Use `st.json()` for structured data display
- Show rollback button only if not active version
- Format economics data prominently (likes, dislikes, costs)

### 6. Rollback Handler

**Purpose**: Update CURRENT pointer to selected version

**Interface**:
```python
def rollback_version(table, pk: str, target_sk: str) -> bool:
    """
    Rollback to a specific version by updating CURRENT pointer.
    
    Args:
        table: DynamoDB table resource
        pk: Primary key
        target_sk: Target version SK to rollback to
    
    Returns:
        Success status
    """
```

**Implementation Details**:
- Update item with PK={pk}, SK="CURRENT"
- Set active_version_sk to target_sk
- Update last_updated timestamp
- Handle errors gracefully

## Data Models

### Version Node (Main Version)
```python
{
    'sk': 'VERSION#2025-11-27T10:00:00Z',
    'label': 'V1',  # Generated dynamically
    'metadata': {
        'version_hash': 'hash-v1-000',
        'parent_hash': 'null',
        'mutation_reason': 'Initial Deployment',
        'name': 'Car Auto Concierge - V1.0',
        ...
    },
    'economics': {
        'likes': 10,
        'dislikes': 2,
        ...
    },
    'challengers': [...]  # List of associated challengers
}
```

### Challenger Node
```python
{
    'sk': 'VERSION#2025-11-27T10:00:00Z#CHALLENGER#attempt-1',
    'label': 'Attempt 1',  # Generated from SK
    'parent_version_sk': 'VERSION#2025-11-27T10:00:00Z',
    'metadata': {
        'version_hash': 'hash-v1-challenger-01',
        'parent_hash': 'hash-v1-000',
        'mutation_reason': 'Critic detected discount violation',
        ...
    }
    # No economics displayed for challengers
}
```

### Tree Structure
```python
{
    'nodes': [
        {
            'id': 'VERSION#2025-11-27T10:00:00Z',
            'type': 'version',  # or 'challenger'
            'label': 'V1',
            'mutation_reason': 'Initial Deployment',
            'likes': 10,
            'dislikes': 2,
            'is_active': True,
            'data': {...}  # Full genome data
        },
        ...
    ],
    'edges': [
        {
            'source': 'VERSION#2025-11-27T10:00:00Z',
            'target': 'VERSION#2025-11-28T15:30:00Z',
            'label': 'Fixed discount policy'
        },
        ...
    ]
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After reviewing all testable properties from the prework, I've identified the following consolidations:

- Properties 1.1 and 1.2 can be combined into a single comprehensive filtering property
- Properties 4.1 and 4.4 both test selection state management and can be combined
- Properties 4.2 and 4.5 both test detail panel content and can be combined
- Properties 5.1 and 5.4 both test challenger node structure and can be combined
- Properties 3.5 and 8.1 both test edge labels and can be combined

### Correctness Properties

Property 1: Data filtering correctness
*For any* set of DynamoDB items, the filtering function should return only items where SK matches "VERSION#{timestamp}" or "VERSION#{timestamp}#CHALLENGER#attempt-{n}" and exclude any items containing "#CHAT#" or "#TICKET#"
**Validates: Requirements 1.1, 1.2**

Property 2: Complete genome structure
*For any* fetched version or challenger item, it should contain all required fields: metadata, config, economics, brain, resources, capabilities, and evolution_config
**Validates: Requirements 1.3**

Property 3: Version classification
*For any* list of filtered items, the parser should correctly separate items into main versions (SK matches "VERSION#{timestamp}" exactly) and challengers (SK contains "#CHALLENGER#")
**Validates: Requirements 1.4**

Property 4: Tree construction from parent relationships
*For any* set of versions with parent_hash relationships, the tree builder should construct a valid hierarchical structure where each node (except root) has exactly one parent matching its parent_hash
**Validates: Requirements 3.1**

Property 5: Sequential version labeling
*For any* tree of versions, traversing from root to leaves should assign sequential labels V1, V2, V3... in chronological order based on timestamps
**Validates: Requirements 3.3**

Property 6: Parent-child connections
*For any* version with a parent_hash that matches another version's version_hash, the tree should contain an edge from parent to child with the child's mutation_reason as the label
**Validates: Requirements 3.4, 3.5, 8.1**

Property 7: Selection state management
*For any* version or challenger node, when selected, the system state should update to store that node's SK and full data for display in the detail panel
**Validates: Requirements 4.1, 4.4**

Property 8: Detail panel completeness
*For any* selected version or challenger, the detail panel data should include version_hash, parent_hash, mutation_reason, timestamp, and all genome sections
**Validates: Requirements 4.2**

Property 9: Challenger node structure
*For any* challenger node, it should display mutation_reason and attempt_number extracted from SK, and should NOT include likes, dislikes, or V# labels
**Validates: Requirements 5.1, 5.4**

Property 10: Challenger selection
*For any* challenger node, when selected, the system should display its full genome data in the detail panel just like main versions
**Validates: Requirements 5.5**

Property 11: Rollback operation correctness
*For any* non-active version SK, executing rollback should update the DynamoDB item with SK="CURRENT" to set active_version_sk equal to the target version SK
**Validates: Requirements 6.3**

Property 12: Rollback error handling
*For any* rollback operation that fails, the system state should remain unchanged and no database modifications should occur
**Validates: Requirements 6.5**

Property 13: Mutation reason text truncation
*For any* mutation reason longer than 50 characters, the displayed label should be truncated to 50 characters with "..." appended
**Validates: Requirements 8.2**

## Error Handling

### DynamoDB Query Errors
- **Scenario**: DynamoDB query fails due to network issues or permissions
- **Handling**: Display error message to user, log error details, maintain current UI state
- **User Feedback**: "Failed to load lineage data. Please try again."

### Invalid Data Structure
- **Scenario**: Fetched items missing required fields (metadata, parent_hash, etc.)
- **Handling**: Skip malformed items, log warnings, display valid items only
- **User Feedback**: Warning banner if some items were skipped

### Circular Parent References
- **Scenario**: parent_hash relationships form a cycle
- **Handling**: Detect cycles during tree construction, break cycle at oldest node, log error
- **User Feedback**: Warning message about data inconsistency

### Rollback Failures
- **Scenario**: DynamoDB update fails during rollback
- **Handling**: Catch exception, display error message, do not update UI state
- **User Feedback**: "Rollback failed: [error message]. Please try again."

### Missing CURRENT Pointer
- **Scenario**: No item with SK="CURRENT" exists for selected lineage
- **Handling**: Assume no active version, allow rollback to any version
- **User Feedback**: Info message "No active version set"

### Empty Lineage
- **Scenario**: No versions found for selected lineage
- **Handling**: Display empty state message
- **User Feedback**: "No versions found for this lineage"

## Testing Strategy

### Unit Testing

Unit tests will cover core logic functions:

1. **Data Filtering Tests**
   - Test filtering with various SK patterns
   - Test exclusion of CHAT and TICKET items
   - Test handling of edge cases (empty results, malformed SKs)

2. **Version Parser Tests**
   - Test separation of versions and challengers
   - Test extraction of attempt numbers from challenger SKs
   - Test handling of unexpected SK formats

3. **Tree Builder Tests**
   - Test tree construction with linear lineage (no branches)
   - Test tree construction with multiple children per parent
   - Test root node identification (parent_hash = "null")
   - Test cycle detection
   - Test sequential labeling (V1, V2, V3...)

4. **Rollback Logic Tests**
   - Test DynamoDB update parameters
   - Test error handling
   - Test state preservation on failure

### Property-Based Testing

Property-based tests will verify universal properties using a Python PBT library (Hypothesis):

1. **Property 1: Data Filtering Correctness**
   - Generate random lists of items with various SK patterns
   - Verify filtered results contain only valid patterns
   - Verify no CHAT or TICKET items in results

2. **Property 3: Version Classification**
   - Generate random mixed lists of versions and challengers
   - Verify classification is correct for all items

3. **Property 4: Tree Construction**
   - Generate random valid parent-child relationships
   - Verify resulting tree has correct structure
   - Verify all nodes (except root) have exactly one parent

4. **Property 6: Parent-Child Connections**
   - Generate random version sets with parent_hash relationships
   - Verify all edges connect correct parent-child pairs
   - Verify edge labels match mutation reasons

5. **Property 11: Rollback Operation**
   - Generate random version SKs
   - Verify rollback updates correct DynamoDB item
   - Verify active_version_sk is set correctly

### Integration Testing

Integration tests will verify end-to-end workflows:

1. **Full Lineage Load Test**
   - Mock DynamoDB with sample data
   - Verify complete flow from query to tree rendering
   - Verify correct data displayed in UI

2. **Version Selection Test**
   - Simulate clicking on version nodes
   - Verify detail panel updates correctly
   - Verify rollback button visibility

3. **Rollback Workflow Test**
   - Simulate rollback operation
   - Verify DynamoDB update called correctly
   - Verify UI refresh after successful rollback

### Manual Testing

Manual testing will cover UI/UX aspects:

1. **Visual Layout**
   - Verify two-panel layout proportions
   - Verify tree graph renders cleanly
   - Verify node spacing and readability

2. **Interactivity**
   - Test pan and zoom functionality
   - Test node selection and highlighting
   - Test hover effects

3. **Responsiveness**
   - Test on different screen sizes
   - Verify panel scrolling works independently

## Implementation Notes

### Technology Stack
- **Backend**: Python 3.x with boto3 for DynamoDB
- **Frontend Framework**: Streamlit
- **Visualization**: D3.js embedded via `st.components.v1.html()`
- **Alternative**: Consider using `streamlit-agraph` or `streamlit-d3graph` if available

### Performance Considerations
- Limit initial query to 100 most recent versions
- Implement pagination for large lineages
- Cache tree structure in session state to avoid rebuilding on every interaction
- Use DynamoDB query (not scan) for efficiency

### Accessibility
- Ensure keyboard navigation support for tree nodes
- Provide text alternatives for visual elements
- Maintain sufficient color contrast for readability

### Future Enhancements
- Search/filter functionality for large lineages
- Export tree visualization as image
- Compare two versions side-by-side
- Batch rollback to multiple agents
- Timeline view showing evolution over time
