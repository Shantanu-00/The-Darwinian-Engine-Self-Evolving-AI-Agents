import streamlit as st
import boto3
import json
import hashlib
import re
from datetime import datetime
from decimal import Decimal

st.set_page_config(page_title="The Lab - Darwinian Engine", layout="wide")

st.title("🧬 Darwinian Engine — Admin Console")
st.header("🧪 The Lab")

# Configuration with fallback to DarwinianGenePool
TABLE_NAME = st.secrets.get("DYNAMODB_TABLE", "DarwinianGenePool")
AWS_REGION = st.secrets.get("AWS_REGION", "us-east-1")

# Approved models only
APPROVED_MODELS = [
    "us.amazon.nova-premier-v1:0",
    "meta.llama3-70b-instruct-v1:0"
]

# Initialize DynamoDB
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
except Exception as e:
    st.error(f"❌ Unable to connect to DynamoDB: {str(e)}")
    st.stop()


def sanitize_identifier(identifier):
    """Remove special characters, keeping only alphanumeric and hyphens"""
    if not identifier:
        return ""
    # Replace underscores with hyphens, remove all other special characters
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '', identifier.replace('_', '-'))
    return sanitized


def generate_pk(agent_identifier, genome_name):
    """Generate PK using agent identifier or hash of genome name"""
    if agent_identifier and agent_identifier.strip():
        sanitized = sanitize_identifier(agent_identifier)
        return f"AGENT#{sanitized}"
    else:
        # Fallback to hash-based PK
        name_hash = hashlib.sha256(genome_name.encode()).hexdigest()[:16]
        return f"AGENT#{name_hash}"


def validate_model_id(model_id):
    """Validate that model_id is one of the approved models"""
    return model_id in APPROVED_MODELS


def validate_json_schema(schema_text):
    """Validate that a string is valid JSON"""
    if not schema_text or not schema_text.strip():
        return True, {}
    try:
        parsed = json.loads(schema_text)
        return True, parsed
    except json.JSONDecodeError as e:
        return False, str(e)


def calculate_estimated_cost(model_id, token_budget):
    """Calculate estimated cost based on model and token budget"""
    if model_id == "us.amazon.nova-premier-v1:0":
        cost_per_1k = 0.0025
    elif model_id == "meta.llama3-70b-instruct-v1:0":
        cost_per_1k = 0.00072
    else:
        cost_per_1k = 0.0
    
    estimated_cost = (token_budget / 1000) * cost_per_1k
    return f"${estimated_cost:.6f}"


def transform_to_dynamodb_item(form_data):
    """Transform form data to DynamoDB schema matching seed_final_db.py"""
    pk = form_data["pk"]
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    version_sk = f"VERSION#{timestamp}"
    
    # Generate version hash
    version_hash = hashlib.sha256(f"{pk}{timestamp}".encode()).hexdigest()[:16]
    
    # Calculate estimated cost
    estimated_cost = calculate_estimated_cost(form_data["model_id"], form_data["token_budget"])
    
    item = {
        "PK": pk,
        "SK": version_sk,
        "EntityType": "Genome",
        "metadata": {
            "name": form_data["name"],
            "description": form_data["description"],
            "creator": form_data["creator"],
            "version_hash": f"hash-{version_hash}",
            "parent_hash": "null",
            "deployment_state": "ACTIVE",
            "mutation_reason": "Initial creation"
        },
        "config": {
            "model_id": form_data["model_id"],
            "temperature": str(form_data["temperature"]),
            "max_tokens": int(form_data["max_tokens"])
        },
        "economics": {
            "likes": 0,
            "dislikes": 0,
            "input_token_count": int(form_data["token_budget"]),
            "token_budget": int(form_data["token_budget"]),
            "estimated_cost_of_calling": estimated_cost
        },
        "brain": {
            "persona": {
                "role": form_data["persona_role"],
                "tone": form_data["persona_tone"]
            },
            "style_guide": form_data["style_guide"],
            "objectives": form_data["objectives"],
            "operational_guidelines": form_data["operational_guidelines"]
        },
        "resources": {
            "knowledge_base_text": form_data["knowledge_base_text"],
            "policy_text": form_data["policy_text"]
        },
        "capabilities": {
            "active_tools": form_data["tools"],
            "simulation_mocks": form_data["simulation_mocks"]
        },
        "evolution_config": {
            "critic_rules": form_data["critic_rules"],
            "judge_rubric": form_data["judge_rubric"]
        }
    }
    
    return item, version_sk


def save_genome(item, version_sk):
    """Save genome to DynamoDB and update CURRENT pointer"""
    try:
        # Save genome version
        table.put_item(Item=item)
        
        # Update CURRENT pointer
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        current_item = {
            "PK": item["PK"],
            "SK": "CURRENT",
            "active_version_sk": version_sk,
            "last_updated": timestamp
        }
        table.put_item(Item=current_item)
        
        return True, None
    except Exception as e:
        return False, str(e)


# Session state
if "show_form" not in st.session_state:
    st.session_state.show_form = False
if "deployment_success" not in st.session_state:
    st.session_state.deployment_success = None

# Show deployment success message if exists
if st.session_state.deployment_success:
    st.success(f"✅ **Genome deployed successfully!**")
    st.info(f"**PK (Agent Identifier):** `{st.session_state.deployment_success['pk']}`\n\n**Version:** `{st.session_state.deployment_success['version_sk']}`")
    st.markdown("---")
    if st.button("✨ Clear Message"):
        st.session_state.deployment_success = None
        st.rerun()

if st.button("➕ Write New Genome"):
    st.session_state.show_form = True
    st.session_state.deployment_success = None  # Clear any previous success message

if st.session_state.show_form:
    with st.form("genome_form"):
        st.subheader("SECTION 1 — Governance & Identity")
        name = st.text_input("Name*", key="name")
        description = st.text_area("Description*", key="description")
        creator = st.text_input("Creator*", key="creator")
        agent_identifier = st.text_input(
            "Agent Identifier (optional)", 
            key="agent_identifier",
            help="Custom identifier for this agent. Leave empty to auto-generate. Only alphanumeric characters and hyphens allowed."
        )
        
        st.divider()
        st.subheader("SECTION 2 — Config")
        model_id = st.selectbox(
            "Model ID*", 
            APPROVED_MODELS,
            index=0,  # Default to Amazon Nova Premier
            key="model_id"
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1, key="temperature")
        max_tokens = st.slider("Max Tokens", 100, 4096, 800, 100, key="max_tokens")
        
        st.divider()
        st.subheader("SECTION 3 — Economics")
        token_budget = st.number_input("Token Budget (Input Tokens)*", min_value=0, value=600, key="token_budget")
        
        # Calculate estimated costs for both models
        amazon_cost = (token_budget / 1000) * 0.0025
        llama_cost = (token_budget / 1000) * 0.00072
        
        st.markdown("---")
        st.markdown("### 💰 Estimated Cost Breakdown")
        st.markdown(f"""
        **Amazon Nova Premier:**
        - Rate: $0.0025 per 1,000 input tokens
        - Calculation: ({token_budget:,} tokens ÷ 1,000) × $0.0025
        - **Total Cost: ${amazon_cost:.6f}**
        
        **Meta Llama 70B Instruct:**
        - Rate: $0.00072 per 1,000 input tokens
        - Calculation: ({token_budget:,} tokens ÷ 1,000) × $0.00072
        - **Total Cost: ${llama_cost:.6f}**
        """)
        st.markdown("---")
        
        st.divider()
        st.subheader("SECTION 4 — Brain")
        persona_role = st.text_input("Persona Role*", key="persona_role")
        persona_tone = st.text_input("Persona Tone*", key="persona_tone")
        style_guide_text = st.text_area("Style Guide (one per line)", key="style_guide")
        objectives_text = st.text_area("Objectives (one per line)*", key="objectives")
        operational_guidelines_text = st.text_area("Operational Guidelines (one per line)*", key="operational_guidelines")
        
        st.divider()
        st.subheader("SECTION 5 — Resources")
        knowledge_base_text = st.text_area("Knowledge Base Text", height=200, key="knowledge_base")
        policy_text = st.text_area("Policy Text", height=200, key="policy")
        
        st.divider()
        st.subheader("SECTION 6 — Capabilities")
        
        # Initialize session state for tools if not exists
        if "num_tools" not in st.session_state:
            st.session_state.num_tools = 1
        
        num_tools = st.number_input("Number of tools", min_value=0, max_value=10, value=st.session_state.num_tools, key="num_tools_input")
        st.session_state.num_tools = int(num_tools)
        
        tools_list = []
        simulation_mocks = {}
        tool_validation_errors = []
        
        if num_tools > 0:
            for i in range(int(num_tools)):
                st.markdown(f"### 🔧 Tool {i+1}")
                tool_name = st.text_input(f"Tool Name", key=f"tool_name_{i}", placeholder="e.g., check_inventory")
                tool_desc = st.text_input(f"Tool Description", key=f"tool_desc_{i}", placeholder="e.g., Check product inventory levels")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Actual Tool Schema (JSON)**")
                    tool_schema = st.text_area(
                        f"Tool Schema", 
                        key=f"tool_schema_{i}", 
                        height=150,
                        placeholder='{"type": "object", "properties": {"model": {"type": "string"}}}',
                        label_visibility="collapsed"
                    )
                with col2:
                    st.markdown("**Shadow Tool Mock (JSON)**")
                    shadow_schema = st.text_area(
                        f"Shadow Mock", 
                        key=f"shadow_schema_{i}", 
                        height=150,
                        placeholder='{"status": "success", "data": {...}}',
                        label_visibility="collapsed"
                    )
                
                # Process tool if name is provided
                if tool_name and tool_name.strip():
                    # Validate actual tool JSON schema
                    if tool_schema and tool_schema.strip():
                        is_valid, result = validate_json_schema(tool_schema)
                        if not is_valid:
                            tool_validation_errors.append(f"Tool {i+1} ({tool_name}) has invalid actual tool JSON schema: {result}")
                        else:
                            tool_obj = {
                                "name": tool_name,
                                "description": tool_desc if tool_desc else "",
                                "input_schema": result if result else {}
                            }
                            tools_list.append(tool_obj)
                    else:
                        # Empty schema is allowed
                        tool_obj = {
                            "name": tool_name,
                            "description": tool_desc if tool_desc else "",
                            "input_schema": {}
                        }
                        tools_list.append(tool_obj)
                    
                    # Validate shadow tool mock JSON
                    if shadow_schema and shadow_schema.strip():
                        is_valid_shadow, result_shadow = validate_json_schema(shadow_schema)
                        if not is_valid_shadow:
                            tool_validation_errors.append(f"Tool {i+1} ({tool_name}) has invalid shadow mock JSON: {result_shadow}")
                        else:
                            simulation_mocks[tool_name] = result_shadow
                
                st.markdown("---")
        else:
            st.info("💡 Set number of tools to 1 or more to add tool configurations")
        
        st.divider()
        st.subheader("SECTION 7 — Evolution Config")
        critic_rules_text = st.text_area("Critic Rules (one per line)*", key="critic_rules")
        judge_rubric_text = st.text_area("Judge Rubric (one per line)*", key="judge_rubric")
        
        deploy_btn = st.form_submit_button("🚀 Deploy Genome", use_container_width=True)
        
        if deploy_btn:
            # Validation
            validation_errors = []
            
            # Required fields
            if not name:
                validation_errors.append("Name is required")
            if not description:
                validation_errors.append("Description is required")
            if not creator:
                validation_errors.append("Creator is required")
            if not persona_role:
                validation_errors.append("Persona Role is required")
            if not persona_tone:
                validation_errors.append("Persona Tone is required")
            if not objectives_text or not objectives_text.strip():
                validation_errors.append("Objectives are required")
            if not operational_guidelines_text or not operational_guidelines_text.strip():
                validation_errors.append("Operational Guidelines are required")
            if not critic_rules_text or not critic_rules_text.strip():
                validation_errors.append("Critic Rules are required")
            if not judge_rubric_text or not judge_rubric_text.strip():
                validation_errors.append("Judge Rubric is required")
            
            # Model validation
            if not validate_model_id(model_id):
                validation_errors.append(f"Invalid model selected. Must be one of: {', '.join(APPROVED_MODELS)}")
            
            # Tool validation errors
            validation_errors.extend(tool_validation_errors)
            
            if validation_errors:
                st.error("❌ Please fix the following errors:")
                for error in validation_errors:
                    st.error(f"  • {error}")
            else:
                # Generate PK
                pk = generate_pk(agent_identifier, name)
                
                # Prepare form data
                form_data = {
                    "pk": pk,
                    "name": name,
                    "description": description,
                    "creator": creator,
                    "model_id": model_id,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "token_budget": token_budget,
                    "persona_role": persona_role,
                    "persona_tone": persona_tone,
                    "style_guide": [s.strip() for s in style_guide_text.split('\n') if s.strip()],
                    "objectives": [o.strip() for o in objectives_text.split('\n') if o.strip()],
                    "operational_guidelines": [g.strip() for g in operational_guidelines_text.split('\n') if g.strip()],
                    "knowledge_base_text": knowledge_base_text,
                    "policy_text": policy_text,
                    "tools": tools_list,
                    "simulation_mocks": simulation_mocks,
                    "critic_rules": [r.strip() for r in critic_rules_text.split('\n') if r.strip()],
                    "judge_rubric": [j.strip() for j in judge_rubric_text.split('\n') if j.strip()]
                }
                
                # Transform to DynamoDB schema
                item, version_sk = transform_to_dynamodb_item(form_data)
                
                # Save to DynamoDB
                success, error = save_genome(item, version_sk)
                
                if success:
                    # Store success info in session state
                    st.session_state.deployment_success = {
                        "pk": pk,
                        "version_sk": version_sk
                    }
                    st.session_state.show_form = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to deploy genome: {error}")
                    st.warning("Your form data has been preserved. Please try again.")
