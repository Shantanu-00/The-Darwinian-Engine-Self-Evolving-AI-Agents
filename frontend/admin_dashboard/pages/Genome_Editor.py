import streamlit as st
import boto3
import json
import uuid
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Mutation Studio - Darwinian Engine", layout="wide")

st.markdown("""
<style>
    /* Main Layout */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Scrollable Columns */
    div[data-testid="column"] {
        height: 85vh;
        overflow-y: auto;
        padding-right: 15px;
        border-right: 1px solid #f0f2f6;
    }
    
    /* Ticket Card Styling */
    .ticket-card {
        background-color: #fff;
        border: 1px solid #e0e0e0;
        border-left: 4px solid #ff4b4b; /* Red accent for issues */
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: transform 0.1s;
    }
    .ticket-card:hover {
        border-color: #ff4b4b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .ticket-header { font-weight: 700; font-size: 0.9rem; color: #333; }
    .ticket-meta { font-size: 0.75rem; color: #666; margin-bottom: 8px; }
    .ticket-body { font-size: 0.9rem; color: #444; background: #f9f9f9; padding: 8px; border-radius: 4px; }
    
    /* Editor Section Styling */
    .editor-section {
        background-color: #ffffff;
        padding: 20px;
        border: 1px solid #eee;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    h1 { font-family: 'Helvetica Neue', sans-serif; font-weight: 700; color: #111; }
    h3 { font-size: 1.1rem; font-weight: 600; color: #444; margin-top: 0; padding-bottom: 10px; border-bottom: 1px solid #eee; }
    
    /* Selected Ticket Banner */
    .selected-ticket-banner {
        background-color: #e6f3ff;
        border: 1px solid #b6d4fe;
        color: #084298;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 15px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧬 Darwinian Engine — Admin Console")

# -----------------------------------------------------------------------------
# 2. BACKEND CONNECTION
# -----------------------------------------------------------------------------
dynamodb = boto3.resource('dynamodb', region_name=st.secrets.get("AWS_REGION", "us-east-1"))
table = dynamodb.Table(st.secrets.get("DYNAMODB_TABLE", "DarwinianGenePool"))

# Session State Initialization
if "selected_pk" not in st.session_state:
    st.session_state.selected_pk = None
if "selected_ticket" not in st.session_state:
    st.session_state.selected_ticket = None

# Utilities
def decimal_to_native(obj):
    if isinstance(obj, list): return [decimal_to_native(i) for i in obj]
    elif isinstance(obj, dict): return {k: decimal_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal): return int(obj) if obj % 1 == 0 else float(obj)
    return obj

# -----------------------------------------------------------------------------
# 3. SIDEBAR - AGENT SELECTION
# -----------------------------------------------------------------------------
try:
    response = table.scan()
    items = response.get('Items', [])
    pks = sorted(list(set([item['PK'] for item in items if item.get('PK', '').startswith('AGENT#')])))
except Exception as e:
    st.sidebar.error(f"DB Error: {e}")
    pks = []

with st.sidebar:
    st.header("Mutation Studio")
    selected_pk = st.selectbox("Select Agent Lineage", pks, index=0 if pks else None)
    
    # Update session state only if changed
    if selected_pk != st.session_state.selected_pk:
        st.session_state.selected_pk = selected_pk
        st.session_state.selected_ticket = None # Reset ticket selection on agent change

    if st.session_state.selected_pk:
        st.success(f"Editing: {st.session_state.selected_pk.split('#')[-1]}")
    else:
        st.info("Please select an agent to begin.")

# -----------------------------------------------------------------------------
# 4. MAIN LAYOUT
# -----------------------------------------------------------------------------
if st.session_state.selected_pk:
    col_left, col_right = st.columns([0.35, 0.65], gap="large")

    # === LEFT PANEL: OPEN TICKETS ===
    with col_left:
        st.subheader("🎫 Open Tickets")
        
        # Robust Ticket Fetching: Fetch all items for PK and filter in memory
        # This handles tickets regardless of SK prefix (TICKET# or VERSION#...#TICKET#)
        try:
            lineage_response = table.query(KeyConditionExpression=Key('PK').eq(st.session_state.selected_pk))
            all_items = lineage_response.get('Items', [])
            
            # Filter for tickets that are OPEN
            tickets = [
                item for item in all_items 
                if (item.get('EntityType') == 'Ticket' or '#TICKET#' in item.get('SK', '')) 
                and item.get('status') == 'OPEN'
            ]
            
            if tickets:
                st.caption(f"Found {len(tickets)} open issues needing resolution.")
                for t in tickets:
                    # Determine styling based on selection
                    is_selected = st.session_state.selected_ticket and st.session_state.selected_ticket['SK'] == t['SK']
                    card_style = "border: 2px solid #007bff; background-color: #f0f7ff;" if is_selected else ""
                    
                    # Render Ticket Card
                    with st.container():
                        st.markdown(f"""
                        <div class="ticket-card" style="{card_style}">
                            <div class="ticket-header">Issue: {t.get('SK', '').split('#')[-1]}</div>
                            <div class="ticket-meta">📅 {t.get('timestamp', 'Unknown')}</div>
                            <div class="ticket-body">
                                <b>Analysis:</b> {t.get('ai_analysis', 'No analysis provided.')}<br><br>
                                <i>Feedback: "{t.get('feedback', '')}"</i>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Selection Button
                        btn_label = "✅ Solving this" if is_selected else "Select to Fix"
                        if st.button(btn_label, key=f"btn_{t['SK']}", type="primary" if is_selected else "secondary", use_container_width=True):
                            st.session_state.selected_ticket = t
                            st.rerun()
            else:
                st.success("🎉 No open tickets! System is stable.")
                st.caption("You can still perform manual mutations on the right.")
                
        except Exception as e:
            st.error(f"Error fetching tickets: {e}")

    # === RIGHT PANEL: GENOME EDITOR ===
    with col_right:
        st.subheader("🧬 Genome Editor")

        # 1. Fetch Current Active Genome
        try:
            current_ptr = table.get_item(Key={'PK': st.session_state.selected_pk, 'SK': 'CURRENT'})
            active_sk = current_ptr.get('Item', {}).get('active_version_sk')
            
            if not active_sk:
                st.warning("⚠️ No active version pointer found (SK='CURRENT'). Please seed the database.")
                st.stop()
                
            active_version_resp = table.get_item(Key={'PK': st.session_state.selected_pk, 'SK': active_sk})
            active_genome = active_version_resp.get('Item')
            
            if not active_genome:
                st.error(f"Pointer found but version data missing for SK: {active_sk}")
                st.stop()
                
            # Convert Decimals for form handling
            genome = decimal_to_native(active_genome)
            
        except Exception as e:
            st.error(f"Failed to load genome: {e}")
            st.stop()

        # 2. Context Banner
        if st.session_state.selected_ticket:
            st.markdown(f"""
            <div class="selected-ticket-banner">
                <b>🎯 Fixing Ticket:</b> {st.session_state.selected_ticket['SK'].split('#')[-1]}<br>
                Use the editor below to address the feedback. Deploying will automatically close this ticket.
            </div>
            """, unsafe_allow_html=True)

        # 3. The Form
        with st.form("genome_editor_form", border=False):
            
            # --- GOVERNANCE ---
            with st.container():
                st.markdown("### 1. Identity & Governance")
                meta = genome.get('metadata', {})
                col1, col2 = st.columns(2)
                new_name = col1.text_input("Agent Name", value=meta.get('name', ''))
                new_creator = col2.text_input("Creator/Mutator", value=st.session_state.get('user', 'Human_Admin'))
                new_desc = st.text_area("Description", value=meta.get('description', ''))

            st.divider()

            # --- LLM CONFIG ---
            with st.container():
                st.markdown("### 2. LLM Configuration")
                conf = genome.get('config', {})
                c1, c2, c3 = st.columns(3)
                
                model_options = [
                    "us.amazon.nova-premier-v1:0",
                    "anthropic.claude-3-5-sonnet-20240620-v1:0",
                    "anthropic.claude-3-haiku-20240307-v1:0"
                ]
                curr_model = conf.get('model_id', model_options[0])
                index_model = model_options.index(curr_model) if curr_model in model_options else 0
                
                new_model = c1.selectbox("Model ID", model_options, index=index_model)
                new_temp = c2.slider("Temperature", 0.0, 1.0, float(conf.get('temperature', 0.7)))
                new_tokens = c3.number_input("Max Tokens", 100, 8192, int(conf.get('max_tokens', 1000)))

            st.divider()

            # --- BRAIN ---
            with st.container():
                st.markdown("### 3. Brain & Personality")
                brain = genome.get('brain', {})
                persona = brain.get('persona', {})
                
                b1, b2 = st.columns(2)
                new_role = b1.text_input("Role", value=persona.get('role', ''))
                new_tone = b2.text_input("Tone", value=persona.get('tone', ''))
                
                st.caption("Operational Guidelines (One per line)")
                current_guidelines = "\n".join(brain.get('operational_guidelines', []))
                new_guidelines = st.text_area("Guidelines", value=current_guidelines, height=150)
                
                st.caption("Objectives")
                current_objs = "\n".join(brain.get('objectives', []))
                new_objs = st.text_area("Objectives", value=current_objs, height=100)

            st.divider()

            # --- CRITIC ---
            with st.container():
                st.markdown("### 4. Evolution Logic (Critic)")
                evo = genome.get('evolution_config', {})
                current_rules = "\n".join(evo.get('critic_rules', []))
                new_rules = st.text_area("Critic Failure Rules", value=current_rules, height=100)

            st.divider()
            
            # --- DEPLOYMENT SECTION ---
            st.markdown("### 🚀 Deployment Control")
            mutation_reason = st.text_input("Mutation Reason (Required)", placeholder="e.g., Fixed pricing hallucination reported in Ticket #123")
            
            d_col1, d_col2 = st.columns([1, 1])
            save_draft = d_col1.form_submit_button("💾 Save as Draft (Challenger)")
            deploy_live = d_col2.form_submit_button("🚀 Deploy to Production", type="primary")

            # --- FORM SUBMISSION LOGIC ---
            if save_draft or deploy_live:
                if not mutation_reason:
                    st.error("❌ You must provide a Mutation Reason.")
                else:
                    # 1. Prepare New Version Metadata
                    now_iso = datetime.utcnow().isoformat()
                    # Simple version increment logic for demo
                    try:
                        old_v_num = int(active_sk.split('VERSION#')[-1].split('#')[0].replace('v', '')) # extracts number if format matches
                    except:
                        old_v_num = int(datetime.now().timestamp()) # Fallback
                        
                    version_num = old_v_num + 1
                    
                    # Generate new SK
                    if deploy_live:
                        new_sk = f"VERSION#v{version_num}#{now_iso}"
                        dep_state = "ACTIVE"
                    else:
                        new_sk = f"VERSION#v{version_num}#{now_iso}#CHALLENGER#manual"
                        dep_state = "DRAFT"

                    # 2. Construct New Genome Object
                    new_genome = {
                        "PK": st.session_state.selected_pk,
                        "SK": new_sk,
                        "EntityType": "Genome",
                        "created_at": now_iso,
                        
                        "metadata": {
                            "name": new_name,
                            "description": new_desc,
                            "creator": new_creator,
                            "version_hash": f"hash-v{version_num}-{uuid.uuid4().hex[:6]}",
                            "parent_hash": meta.get('version_hash', 'null'), # POINTER TO PARENT
                            "deployment_state": dep_state,
                            "mutation_reason": mutation_reason
                        },
                        "config": {
                            "model_id": new_model,
                            "temperature": Decimal(str(new_temp)),
                            "max_tokens": int(new_tokens)
                        },
                        "brain": {
                            "persona": { "role": new_role, "tone": new_tone },
                            "operational_guidelines": [x.strip() for x in new_guidelines.split('\n') if x.strip()],
                            "objectives": [x.strip() for x in new_objs.split('\n') if x.strip()],
                            "style_guide": brain.get('style_guide', []) # Preserve existing
                        },
                        "evolution_config": {
                            "critic_rules": [x.strip() for x in new_rules.split('\n') if x.strip()],
                            "judge_rubric": evo.get('judge_rubric', []) # Preserve existing
                        },
                        "economics": genome.get('economics', {}), # Preserve
                        "resources": genome.get('resources', {}), # Preserve
                        "capabilities": genome.get('capabilities', {}) # Preserve
                    }

                    # 3. Write to DynamoDB
                    table.put_item(Item=new_genome)
                    st.success(f"✅ Genome Saved: {new_sk}")

                    # 4. If Deploying: Update Pointer and Close Ticket
                    if deploy_live:
                        # Update CURRENT pointer
                        pointer_item = {
                            "PK": st.session_state.selected_pk,
                            "SK": "CURRENT",
                            "active_version_sk": new_sk,
                            "last_updated": now_iso
                        }
                        table.put_item(Item=pointer_item)
                        st.toast("Updated 'CURRENT' pointer!", icon="🚀")

                        # Close Ticket if selected
                        if st.session_state.selected_ticket:
                            ticket_update = st.session_state.selected_ticket
                            ticket_update['status'] = 'CLOSED'
                            ticket_update['resolution_version_sk'] = new_sk
                            ticket_update['closed_at'] = now_iso
                            table.put_item(Item=ticket_update)
                            st.toast(f"Closed Ticket {ticket_update['SK']}", icon="🎫")
                            st.session_state.selected_ticket = None # Clear selection

                        st.balloons()
                        import time
                        time.sleep(2)
                        st.rerun()

else:
    # Empty State (No Agent Selected)
    st.markdown("""
    <div style='text-align: center; padding: 50px; color: #666;'>
        <h3>👋 Welcome to Mutation Studio</h3>
        <p>Select an Agent Lineage from the sidebar to view open tickets and edit genomes.</p>
    </div>
    """, unsafe_allow_html=True)