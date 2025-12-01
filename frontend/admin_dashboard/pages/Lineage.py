import streamlit as st
import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime

# library for interactive graph
from streamlit_agraph import agraph, Node, Edge, Config

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Version Control - Darwinian Engine", layout="wide")

st.markdown("""
<style>
    /* Main Page Layout - Fix the header and make columns scrollable */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Make the columns scroll independently */
    div[data-testid="column"] {
        height: 85vh;
        overflow-y: auto;
        padding-right: 15px;
        background-color: #ffffff;
        border-right: 1px solid #f0f2f6;
    }

    /* Styling for the Right Panel Cards */
    .info-section {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .section-header {
        font-size: 0.9rem;
        font-weight: 700;
        color: #555;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    
    .genome-text {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 0.85rem;
        color: #333;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 4px;
        margin-bottom: 5px;
    }
    
    .guideline-item {
        font-size: 0.9rem;
        padding: 4px 0;
        border-bottom: 1px dashed #eee;
    }

    /* Header Styling */
    h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        color: #111;
        margin-bottom: 0px;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1; 
    }
    ::-webkit-scrollbar-thumb {
        background: #c1c1c1; 
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8; 
    }
</style>
""", unsafe_allow_html=True)

st.title("🧬 Darwinian Engine — Admin Console")

# -----------------------------------------------------------------------------
# 2. BACKEND & DATA LOGIC
# -----------------------------------------------------------------------------

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=st.secrets.get("AWS_REGION", "us-east-1"))
table = dynamodb.Table(st.secrets.get("DYNAMODB_TABLE", "DarwinianGenePool"))

# Initialize session state
if "selected_lineage_pk" not in st.session_state:
    st.session_state.selected_lineage_pk = None
if "selected_node_sk" not in st.session_state:
    st.session_state.selected_node_sk = None

def decimal_to_native(obj):
    """Recursively convert DynamoDB Decimals into int/float."""
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    else:
        return obj

def fetch_lineage_data(table, pk):
    """Fetch all versions and challengers for a given lineage PK."""
    try:
        response = table.query(
            KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('VERSION#')
        )
        items = response.get('Items', [])
        
        # Filter out CHAT and TICKET items to only get Genomes
        filtered_items = [
            item for item in items 
            if '#CHAT#' not in item['SK'] and '#TICKET#' not in item['SK']
        ]
        
        # Get current active version pointer
        try:
            current_response = table.get_item(Key={'PK': pk, 'SK': 'CURRENT'})
            current_version_sk = current_response.get('Item', {}).get('active_version_sk', '')
        except:
            current_version_sk = ''
        
        return {
            'items': filtered_items,
            'current_version_sk': current_version_sk
        }
    except Exception as e:
        st.error(f"Failed to load lineage data: {str(e)}")
        return {'items': [], 'current_version_sk': ''}

def parse_versions(items):
    """Separate main versions from challengers and sort them."""
    main_versions = []
    challengers = []
    
    for item in items:
        sk = item['SK']
        if '#CHALLENGER#' in sk:
            parts = sk.split('#CHALLENGER#')
            if len(parts) == 2:
                attempt = parts[1]
                item['attempt_number'] = attempt
                item['parent_version_sk'] = parts[0]
            challengers.append(item)
        else:
            main_versions.append(item)
    
    # Sort main versions by timestamp (SK)
    main_versions.sort(key=lambda x: x['SK'])
    
    # Group challengers by parent version
    challengers_by_parent = {}
    for challenger in challengers:
        parent_sk = challenger.get('parent_version_sk', '')
        if parent_sk not in challengers_by_parent:
            challengers_by_parent[parent_sk] = []
        challengers_by_parent[parent_sk].append(challenger)
    
    return main_versions, challengers_by_parent

def rollback_version(table, pk, target_sk):
    """
    Update the 'CURRENT' pointer in DynamoDB to point to the target_sk.
    This effectively rolls back (or promotes) the selected version.
    """
    try:
        current_item = {
            "PK": pk,
            "SK": "CURRENT",
            "active_version_sk": target_sk,
            "last_updated": datetime.utcnow().isoformat()
        }
        table.put_item(Item=current_item)
        return True, "Successfully updated active version pointer."
    except Exception as e:
        return False, f"Update failed: {str(e)}"

# -----------------------------------------------------------------------------
# 3. GRAPH DATA PREPARATION
# -----------------------------------------------------------------------------

def build_agraph_data(main_versions, challengers_by_parent, active_version_sk):
    nodes = []
    edges = []
    data_lookup = {}
    
    def add_node(item, node_type, label, parent_id=None):
        sk = item['SK']
        data_lookup[sk] = item
        
        if node_type == 'version':
            if sk == active_version_sk:
                color = "#28a745"  # Green for Active
                size = 35
                shape = "dot"
                border_width = 3
            else:
                color = "#007bff"  # Blue for History
                size = 25
                shape = "dot"
                border_width = 1
        else:
            color = "#fd7e14"  # Orange for Challenger
            size = 20
            shape = "diamond"
            border_width = 1

        nodes.append(Node(
            id=sk,
            label=label,
            size=size,
            shape=shape,
            color=color,
            borderWidth=border_width,
            borderWidthSelected=3,
            title=f"{label}: {item.get('metadata', {}).get('mutation_reason', '')}"
        ))
        
        if parent_id:
            edges.append(Edge(
                source=parent_id,
                target=sk,
                color="#adb5bd",
                type="STRAIGHT" if node_type == "challenger" else "CURVE_SMOOTH"
            ))

    # Build Spine
    previous_version_sk = None
    for idx, ver in enumerate(main_versions):
        current_sk = ver['SK']
        add_node(ver, 'version', f"V{idx + 1}", previous_version_sk)
        previous_version_sk = current_sk
        
        if current_sk in challengers_by_parent:
            for c_idx, chal in enumerate(challengers_by_parent[current_sk]):
                add_node(chal, 'challenger', f"C-{c_idx+1}", current_sk)
                
    return nodes, edges, data_lookup

# -----------------------------------------------------------------------------
# 4. MAIN APP LAYOUT
# -----------------------------------------------------------------------------

# Sidebar Selection
response = table.scan()
scan_items = response.get('Items', [])
# Extract unique PKs that start with AGENT#
pks = sorted(list(set([item['PK'] for item in scan_items if item.get('PK', '').startswith('AGENT#')])))

with st.sidebar:
    st.header("Configuration")
    selected_pk = st.selectbox("Select Agent Lineage", pks, key="lineage_selector")
    st.info("Select an agent lineage to view its evolution tree.")

if selected_pk:
    lineage_data = fetch_lineage_data(table, selected_pk)
    main_versions, challengers_by_parent = parse_versions(lineage_data['items'])
    active_version_sk = lineage_data['current_version_sk']

    if main_versions:
        nodes, edges, data_lookup = build_agraph_data(main_versions, challengers_by_parent, active_version_sk)
        
        col_tree, col_details = st.columns([0.65, 0.35], gap="medium")
        
        # --- LEFT PANEL: TREE ---
        with col_tree:
            st.subheader("Evolution Tree", anchor=False)
            config = Config(
                width="100%",
                height=700,
                directed=True,
                physics=False,
                hierarchical={
                    "enabled": True,
                    "levelSeparation": 120,
                    "nodeSpacing": 100,
                    "treeSpacing": 100,
                    "direction": "UD", 
                    "sortMethod": "directed"
                },
                nodeHighlightBehavior=True,
                highlightColor="#F7A7A6",
            )
            clicked_node_id = agraph(nodes=nodes, edges=edges, config=config)
            if clicked_node_id:
                st.session_state.selected_node_sk = clicked_node_id
        
        # --- RIGHT PANEL: GENOME DETAILS ---
        with col_details:
            st.subheader("Genome Inspector", anchor=False)
            
            if st.session_state.selected_node_sk and st.session_state.selected_node_sk in data_lookup:
                raw_data = data_lookup[st.session_state.selected_node_sk]
                genome = decimal_to_native(raw_data)
                
                meta = genome.get('metadata', {})
                eco = genome.get('economics', {})
                brain = genome.get('brain', {})
                config_data = genome.get('config', {})
                evo = genome.get('evolution_config', {})
                
                # 1. Status Header
                is_active = (st.session_state.selected_node_sk == active_version_sk)
                if is_active:
                    st.success(f"✅ ACTIVE: {meta.get('name', 'Unknown')}")
                else:
                    st.info(f"📜 {meta.get('deployment_state', 'HISTORICAL')}: {meta.get('name', 'Unknown')}")

                # 2. Key Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("Likes", eco.get('likes', 0))
                c2.metric("Dislikes", eco.get('dislikes', 0))
                c3.metric("Cost", eco.get('estimated_cost_of_calling', '$0'))
                
                st.divider()

                # 3. Brain / Personality (Parsed)
                with st.container():
                    st.markdown('<div class="section-header">🧠 Brain & Personality</div>', unsafe_allow_html=True)
                    persona = brain.get('persona', {})
                    st.markdown(f"**Role:** {persona.get('role', 'N/A')}")
                    st.markdown(f"**Tone:** {persona.get('tone', 'N/A')}")
                    
                    if 'operational_guidelines' in brain:
                        st.markdown("**Operational Guidelines:**")
                        for idx, rule in enumerate(brain['operational_guidelines']):
                            st.markdown(f"<div class='guideline-item'>{rule}</div>", unsafe_allow_html=True)

                # 4. LLM Configuration (Parsed)
                with st.container():
                    st.markdown('<br><div class="section-header">⚙️ LLM Configuration</div>', unsafe_allow_html=True)
                    c_col1, c_col2 = st.columns(2)
                    c_col1.markdown(f"**Model:** `{config_data.get('model_id', 'N/A')}`")
                    c_col1.markdown(f"**Temp:** `{config_data.get('temperature', 'N/A')}`")
                    c_col2.markdown(f"**Tokens:** `{config_data.get('max_tokens', 'N/A')}`")

                # 5. Evolution / Critic (Parsed)
                if evo:
                    with st.container():
                        st.markdown('<br><div class="section-header">⚖️ Critic Rules</div>', unsafe_allow_html=True)
                        for rule in evo.get('critic_rules', []):
                            st.markdown(f"- {rule}")

                # 6. Raw Data Fallback
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("🧬 View Raw JSON Genome"):
                    st.json(genome)

                # 7. Action Button (Rollback/Promote)
                st.divider()
                if not is_active:
                    btn_label = "🚀 Promote to Active" if '#CHALLENGER#' in st.session_state.selected_node_sk else "🔄 Rollback to this Version"
                    if st.button(btn_label, type="primary", use_container_width=True):
                        success, msg = rollback_version(table, selected_pk, st.session_state.selected_node_sk)
                        if success:
                            st.toast("Success! Updating pointer...", icon="✅")
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.button("✅ Currently Active", disabled=True, use_container_width=True)

            else:
                st.info("👈 Select a node to inspect its genome.")
                st.caption("Clicking a node will reveal its DNA, personality, and configuration.")
                
    else:
        st.warning("No versions found for this agent.")
else:
    st.info("Please select an Agent Lineage from the sidebar.")