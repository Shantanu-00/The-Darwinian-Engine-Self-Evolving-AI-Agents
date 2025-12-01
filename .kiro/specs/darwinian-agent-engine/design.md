# Design Document

## Overview

The Darwinian Agent Engine is a serverless project scaffolding system that generates a complete, production-ready directory structure for an AWS-based evolutionary agent platform. The design focuses on creating a well-organized monorepo with clear separation between infrastructure, backend services, and frontend applications. The system will generate all necessary files with valid placeholder content, ensuring immediate project functionality without syntax errors.

## Architecture

The project follows a monorepo architecture with three main divisions:

1. **Infrastructure Layer**: AWS SAM templates and Step Functions definitions for serverless deployment
2. **Backend Layer**: Six specialized Lambda functions plus a shared utilities layer
3. **Frontend Layer**: Two Streamlit applications (client chat and admin dashboard)

The scaffolding system will create a hierarchical directory structure with proper file organization, ensuring each component has the necessary configuration files and placeholder code.

### Directory Tree Structure

```
darwinian-agent-engine/
├── README.md
├── requirements.txt
├── .gitignore
├── infrastructure/
│   ├── template.yaml
│   └── statemachines/
│       └── evolution_loop.asl.json
├── backend/
│   ├── functions/
│   │   ├── proxy_agent/
│   │   │   ├── app.py
│   │   │   └── requirements.txt
│   │   ├── critic_agent/
│   │   │   ├── app.py
│   │   │   └── requirements.txt
│   │   ├── mutator_agent/
│   │   │   ├── app.py
│   │   │   └── requirements.txt
│   │   ├── judge_agent/
│   │   │   ├── app.py
│   │   │   └── requirements.txt
│   │   ├── supervisor_agent/
│   │   │   ├── app.py
│   │   │   └── requirements.txt
│   │   └── feedback_agent/
│   │       ├── app.py
│   │       └── requirements.txt
│   └── shared/
│       └── python/
│           └── utils.py
├── frontend/
│   ├── client_app/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── .streamlit/
│   │   │   └── secrets.toml
│   │   └── assets/
│   │       └── .gitkeep
│   └── admin_dashboard/
│       ├── Home.py
│       ├── requirements.txt
│       ├── .streamlit/
│       │   └── secrets.toml
│       └── pages/
│           ├── Genome_Editor.py
│           ├── The_Lab.py
│           └── Lineage.py
└── tests/
    ├── unit/
    │   └── .gitkeep
    └── integration/
        └── .gitkeep
```

## Components and Interfaces

### File Generation System

The system consists of a file generation engine that creates directories and files according to the specification. Each component is responsible for generating specific parts of the structure:

**Root Configuration Generator**
- Creates README.md with project documentation
- Generates requirements.txt with development dependencies
- Creates .gitignore with Python and AWS exclusions

**Infrastructure Generator**
- Creates infrastructure/template.yaml with SAM definitions
- Generates infrastructure/statemachines/evolution_loop.asl.json with Step Functions workflow

**Backend Generator**
- Creates six Lambda function directories under backend/functions/
- Generates app.py with lambda_handler signature for each function
- Creates empty requirements.txt for each function
- Generates shared layer structure at backend/shared/python/utils.py

**Frontend Generator**
- Creates client_app with main.py, requirements.txt, secrets.toml, and assets directory
- Creates admin_dashboard with Home.py, requirements.txt, secrets.toml, and three page files

**Testing Generator**
- Creates tests/unit and tests/integration directories with .gitkeep files

### File Templates

Each file type has a specific template:

**Lambda Handler Template (app.py)**
```python
def lambda_handler(event, context):
    pass
```

**Streamlit Client Template (main.py)**
```python
import streamlit as st

st.title("IT Support Agent")
```

**Streamlit Admin Template (Home.py)**
```python
import streamlit as st

st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🧬",
    layout="wide"
)
```

**SAM Template Structure (template.yaml)**
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Darwinian Agent Engine Infrastructure

Resources:
  # Lambda functions and Step Functions will be defined here
```

**Step Functions Definition (evolution_loop.asl.json)**
```json
{
  "Comment": "Evolution Loop State Machine",
  "StartAt": "Placeholder",
  "States": {
    "Placeholder": {
      "Type": "Pass",
      "End": true
    }
  }
}
```

## Data Models

### Directory Structure Model

```python
class DirectoryNode:
    name: str
    type: str  # "file" or "directory"
    content: Optional[str]  # File content if type is "file"
    children: List[DirectoryNode]  # Subdirectories/files if type is "directory"
```

### File Template Model

```python
class FileTemplate:
    path: str
    content: str
    file_type: str  # "python", "yaml", "json", "toml", "markdown", "text"
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Complete directory structure validation

*For any* project initialization, the generated file system should contain all required files and directories at their specified paths, including: README.md, requirements.txt, .gitignore at root; infrastructure/template.yaml and infrastructure/statemachines/evolution_loop.asl.json; all six Lambda function directories with app.py and requirements.txt; backend/shared/python/utils.py; frontend/client_app with main.py, requirements.txt, .streamlit/secrets.toml, and assets/.gitkeep; frontend/admin_dashboard with Home.py, requirements.txt, .streamlit/secrets.toml, and pages containing Genome_Editor.py, The_Lab.py, and Lineage.py; and tests/unit/.gitkeep and tests/integration/.gitkeep.

**Validates: Requirements 1.1, 1.2, 1.3, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 2: File syntax validation by type

*For any* file created by the scaffolding system, the file content should be syntactically valid according to its file type (Python files should parse without syntax errors, JSON files should be valid JSON, YAML files should be valid YAML, TOML files should be valid TOML).

**Validates: Requirements 1.4, 2.5, 8.1, 8.2, 8.3, 8.4, 8.5**

### Property 3: Lambda function directory structure

*For any* Lambda function directory in backend/functions/, the directory should contain both an app.py file with a lambda_handler function that accepts event and context parameters, and an empty requirements.txt file.

**Validates: Requirements 3.3, 3.4, 3.5**

### Property 4: File content validation

*For any* file with specified content requirements (such as Streamlit title in client_app/main.py, page config in admin_dashboard/Home.py, placeholder comments in utils.py, API_URL in client secrets, ADMIN_PASSWORD in admin secrets), the file should contain the expected content patterns.

**Validates: Requirements 2.4, 4.3, 5.2, 5.4, 6.2, 6.4**

## Error Handling

The scaffolding system should handle the following error conditions:

1. **File System Errors**: If directories cannot be created due to permissions or disk space, the system should report clear error messages indicating which path failed and why.

2. **Invalid Path Errors**: If attempting to create files in non-existent parent directories, the system should create parent directories first or report the missing prerequisite.

3. **File Overwrite Protection**: If files already exist at target paths, the system should either skip creation, prompt for confirmation, or report conflicts without data loss.

4. **Syntax Validation Errors**: If generated content fails syntax validation, the system should report which file and what validation failed.

## Testing Strategy

### Unit Testing

Unit tests will verify individual file generation functions:

- Test that each file template generates valid content
- Test that directory creation functions handle nested paths correctly
- Test that syntax validators correctly identify valid and invalid content
- Test that file content contains expected patterns (e.g., lambda_handler signature, Streamlit imports)

### Property-Based Testing

Property-based testing will be implemented using **Hypothesis** for Python. Each property test will run a minimum of 100 iterations.

**Property Test 1: Complete Structure Validation**
- Generate the complete project structure
- Verify all required paths exist
- Verify no unexpected files are created
- **Feature: darwinian-agent-engine, Property 1: Complete directory structure validation**

**Property Test 2: Syntax Validation**
- For each file type (Python, JSON, YAML, TOML), generate file content
- Parse the content using appropriate parsers (ast.parse for Python, json.loads, yaml.safe_load, toml.loads)
- Verify no syntax errors occur
- **Feature: darwinian-agent-engine, Property 2: File syntax validation by type**

**Property Test 3: Function Directory Structure**
- For each of the six Lambda function directories, verify structure
- Check app.py exists and contains lambda_handler with correct signature
- Check requirements.txt exists
- **Feature: darwinian-agent-engine, Property 3: Lambda function directory structure**

**Property Test 4: Content Pattern Validation**
- For files with specific content requirements, verify patterns exist
- Check Streamlit imports and function calls
- Check placeholder comments and configuration keys
- **Feature: darwinian-agent-engine, Property 4: File content validation**

### Integration Testing

Integration tests will verify the complete scaffolding process:

- Run the full scaffolding system in a temporary directory
- Verify the complete structure is created correctly
- Verify all files can be parsed/imported without errors
- Test that the generated SAM template can be validated by AWS SAM CLI
- Test that Streamlit applications can be started without import errors

## Implementation Notes

### File Generation Order

Files should be generated in the following order to ensure parent directories exist:

1. Root configuration files
2. Infrastructure directory and files
3. Backend functions directories and files
4. Backend shared layer
5. Frontend client_app directory and files
6. Frontend admin_dashboard directory and files
7. Testing directories

### Technology Stack

- **Language**: Python 3.9+
- **File System Operations**: pathlib for cross-platform path handling
- **Syntax Validation**: ast (Python), json (JSON), PyYAML (YAML), toml (TOML)
- **Testing**: pytest for unit tests, Hypothesis for property-based testing
- **AWS Tools**: AWS SAM CLI for template validation (optional)

### Validation Tools

Each file type will use appropriate validation:
- Python: `ast.parse()`
- JSON: `json.loads()`
- YAML: `yaml.safe_load()`
- TOML: `toml.loads()`
