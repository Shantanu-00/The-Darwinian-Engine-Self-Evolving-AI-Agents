# Implementation Plan

- [ ] 1. Implement data fetching and filtering module
  - Create function to query DynamoDB for specific lineage PK
  - Filter results to include only VERSION#{timestamp} and VERSION#{timestamp}#CHALLENGER# patterns
  - Exclude items containing #CHAT# or #TICKET#
  - Fetch CURRENT pointer separately to identify active version
  - _Requirements: 1.1, 1.2, 1.3_

- [ ]* 1.1 Write property test for data filtering
  - **Property 1: Data filtering correctness**
  - **Validates: Requirements 1.1, 1.2**

- [ ] 2. Implement version parser to separate versions and challengers
  - Parse SK patterns to identify main versions vs challengers
  - Extract attempt numbers from challenger SKs
  - Group challengers by their parent version timestamp
  - Sort versions chronologically
  - _Requirements: 1.4_

- [ ]* 2.1 Write property test for version classification
  - **Property 3: Version classification**
  - **Validates: Requirements 1.4**

- [ ] 3. Implement tree builder for hierarchical structure
  - Find root node where parent_hash equals "null"
  - Build parent-child relationships using version_hash and parent_hash from metadata
  - Assign sequential labels (V1, V2, V3...) based on tree traversal order
  - Create edge list with mutation_reason labels
  - Attach challengers to their parent versions
  - Handle circular reference detection
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ]* 3.1 Write property test for tree construction
  - **Property 4: Tree construction from parent relationships**
  - **Validates: Requirements 3.1**

- [ ]* 3.2 Write property test for parent-child connections
  - **Property 6: Parent-child connections**
  - **Validates: Requirements 3.4, 3.5, 8.1**

- [ ]* 3.3 Write unit test for root node identification
  - Test that version with parent_hash="null" is identified as root
  - Test that root is labeled "V1"
  - _Requirements: 3.2_

- [ ] 4. Create interactive tree visualization component
  - Build HTML/CSS/JavaScript component using D3.js for tree rendering
  - Implement node rendering for main versions (show label, mutation reason, likes/dislikes)
  - Implement node rendering for challengers (show attempt number, mutation reason, no likes/dislikes)
  - Draw edges with mutation reason labels
  - Implement click handlers to capture selected node SK
  - Add pan and zoom functionality
  - Highlight active version node
  - Integrate with Streamlit using st.components.v1.html()
  - _Requirements: 3.3, 5.1, 5.4, 7.1, 7.2, 7.3, 8.1_

- [ ]* 4.1 Write property test for challenger node structure
  - **Property 9: Challenger node structure**
  - **Validates: Requirements 5.1, 5.4**

- [ ]* 4.2 Write property test for mutation reason truncation
  - **Property 13: Mutation reason text truncation**
  - **Validates: Requirements 8.2**

- [ ] 5. Implement two-panel layout
  - Create left panel (60% width) for tree visualization
  - Create right panel (40% width) for detail display
  - Implement independent scrolling for both panels
  - Add placeholder text for right panel when no selection
  - Use Streamlit columns for layout
  - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [ ]* 5.1 Write unit tests for layout structure
  - Test that layout creates two panels
  - Test placeholder text when no selection
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 6. Implement detail panel for selected version/challenger
  - Display full genome data using st.json() or structured format
  - Show metadata (version_hash, parent_hash, mutation_reason, timestamp)
  - Show all genome sections (config, economics, brain, resources, capabilities, evolution_config)
  - Format economics data prominently (likes, dislikes, costs)
  - Handle both version and challenger selection
  - _Requirements: 4.1, 4.2, 4.4, 5.5_

- [ ]* 6.1 Write property test for selection state management
  - **Property 7: Selection state management**
  - **Validates: Requirements 4.1, 4.4**

- [ ]* 6.2 Write property test for detail panel completeness
  - **Property 8: Detail panel completeness**
  - **Validates: Requirements 4.2**

- [ ]* 6.3 Write property test for challenger selection
  - **Property 10: Challenger selection**
  - **Validates: Requirements 5.5**

- [ ] 7. Implement rollback functionality
  - Add "Rollback to this version" button in detail panel
  - Show button only for non-active versions
  - Implement rollback_version() function to update CURRENT pointer in DynamoDB
  - Update active_version_sk to selected version SK
  - Add timestamp to last_updated field
  - Display success message on successful rollback
  - Handle errors gracefully with error messages
  - Refresh page after successful rollback
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 7.1 Write property test for rollback operation
  - **Property 11: Rollback operation correctness**
  - **Validates: Requirements 6.3**

- [ ]* 7.2 Write property test for rollback error handling
  - **Property 12: Rollback error handling**
  - **Validates: Requirements 6.5**

- [ ]* 7.3 Write unit tests for rollback button visibility
  - Test button shown for non-active versions
  - Test button hidden for active version
  - _Requirements: 6.1, 6.2_

- [ ] 8. Integrate all components in Lineage.py
  - Keep existing dropdown for lineage selection
  - Wire data fetching to selected lineage PK
  - Connect tree builder output to visualization component
  - Connect node selection to detail panel
  - Connect rollback button to rollback handler
  - Add error handling and user feedback messages
  - Test complete workflow end-to-end
  - _Requirements: All_

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
