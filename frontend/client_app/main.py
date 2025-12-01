import streamlit as st
import requests
import uuid
import time

# -----------------------------------------------------------------------------
# 1. CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Grand Azure Hotel & Resort", 
    layout="wide", 
    page_icon="🏨",
    initial_sidebar_state="collapsed"
)

# Load secrets safely
try:
    API_BASE_URL = st.secrets["api"]["BASE_URL"]
    API_KEY = st.secrets["api"]["X_API_KEY"]
    AGENT_PK = st.secrets["api"]["AGENT_PK"]
except FileNotFoundError:
    st.error("Secrets not found. Please create .streamlit/secrets.toml")
    st.stop()
except KeyError:
    st.error("Missing configuration in secrets.toml")
    st.stop()

# Session State Init
if "chat_id" not in st.session_state:
    st.session_state.chat_id = f"session-{uuid.uuid4().hex[:8]}"
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------------------------------------------------
# 2. STYLING (Single Page Demo Optimized)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* 1. Reset & Single Page Layout */
    .stApp {
        background-color: #f8f9fa;
        overflow: hidden; /* Try to suppress main page scroll */
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    header, footer { visibility: hidden; }
    
    /* 2. Left Panel Content */
    .hotel-header {
        font-family: 'Garamond', serif;
        font-size: 2.5rem;
        color: #1a2a3a;
        margin-bottom: 0rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .hotel-subheader {
        font-family: 'Helvetica Neue', sans-serif;
        color: #8a6d3b;
        font-size: 1rem;
        margin-bottom: 1rem;
        letter-spacing: 0.5px;
    }
    
    /* Compact Service Cards */
    .service-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        height: 100%;
        text-align: center;
    }
    .card-title {
        color: #1a2a3a;
        font-weight: bold;
        font-size: 1rem;
        margin-bottom: 5px;
    }
    .card-price {
        color: #8a6d3b;
        font-size: 0.9rem;
    }

    /* 3. Right Panel (Chat) */
    .chat-header-text {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 1.2rem;
        font-weight: 700;
        color: #333;
        border-bottom: 2px solid #8a6d3b;
        padding-bottom: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Feedback Section Styling */
    .feedback-container {
        padding: 10px;
        background-color: #f1f3f4;
        border-radius: 8px;
        margin-top: 5px;
        margin-bottom: 5px;
        border: 1px solid #e0e0e0;
    }
    .feedback-text {
        font-size: 0.85rem;
        color: #555;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. LAYOUT SETUP
# -----------------------------------------------------------------------------

col_content, col_chat = st.columns([0.60, 0.40], gap="large")

# =============================================================================
# LEFT PANEL: VISUALS (Fixed Content)
# =============================================================================
with col_content:
    st.markdown('<div class="hotel-header">Grand Azure Resort</div>', unsafe_allow_html=True)
    st.markdown('<div class="hotel-subheader">Sanctuary by the Sea</div>', unsafe_allow_html=True)

    # Main Hero Image (Reduced vertical space for single page feel)
    st.image("https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80", use_container_width=True)

    st.markdown("#### Exclusive Offers")
    
    # Compact Cards
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="service-card">
            <div class="card-title">🌊 Royal Ocean Suite</div>
            <div class="card-price">From $850 / night</div>
            <small>Includes Butler Service</small>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        st.markdown("""
        <div class="service-card">
            <div class="card-title">💆 Azure Spa Package</div>
            <div class="card-price">$200 Credit Included</div>
            <small>With 3+ Night Stay</small>
        </div>
        """, unsafe_allow_html=True)
        
    st.info("💡 **Concierge Tip:** Ask the bot about late-night dining or room upgrades!")

# =============================================================================
# RIGHT PANEL: CHAT CONSOLE
# =============================================================================
with col_chat:
    st.markdown('<div class="chat-header-text">💬 Concierge Desk</div>', unsafe_allow_html=True)
    
    # FIXED HEIGHT CONTAINER -> This enables scrolling ONLY within chat, not the page
    # Decreased height slightly to make room for fixed feedback area
    chat_container = st.container(height=600)
    
    # 1. MESSAGES AREA (Scrollable)
    with chat_container:
        if not st.session_state.messages:
             with st.chat_message("assistant"):
                st.write("Welcome to Grand Azure. I am your personal concierge. How may I assist you?")
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    
    # 2. FEEDBACK AREA (Fixed Position - Does NOT Scroll)
    # Only show if there are messages and the last one is from the assistant
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        last_msg_idx = len(st.session_state.messages) - 1
        
        # Check if feedback already given for this specific interaction
        if not st.session_state.get(f"feedback_done_{last_msg_idx}", False):
            
            # Container to visually separate feedback controls
            with st.container():
                cols = st.columns([0.7, 0.15, 0.15])
                with cols[0]:
                    st.caption("Was this helpful?")
                
                with cols[1]:
                    if st.button("👍", key="fb_up", help="Helpful"):
                        try:
                            requests.post(
                                f"{API_BASE_URL}/feedback",
                                headers={"x-api-key": API_KEY},
                                json={
                                    "pk": AGENT_PK,
                                    "chat_id": st.session_state.chat_id,
                                    "feedback": {"type": "like", "comment": ""}
                                }
                            )
                            st.toast("Thanks for the feedback!", icon="⭐")
                            st.session_state[f"feedback_done_{last_msg_idx}"] = True
                            st.rerun()
                        except: pass
                
                with cols[2]:
                    if st.button("👎", key="fb_down", help="Not Helpful"):
                        st.session_state["show_comment_box"] = True
                        st.rerun()
            
            # Negative Feedback Comment Form (Expands when Dislike clicked)
            if st.session_state.get("show_comment_box", False):
                with st.form(key="feedback_form"):
                    comment = st.text_input("How can we improve?", placeholder="e.g. Information was incorrect...")
                    
                    c1, c2 = st.columns([1,1])
                    if c1.form_submit_button("Submit"):
                        try:
                            requests.post(
                                f"{API_BASE_URL}/feedback",
                                headers={"x-api-key": API_KEY},
                                json={
                                    "pk": AGENT_PK,
                                    "chat_id": st.session_state.chat_id,
                                    "feedback": {"type": "dislike", "comment": comment}
                                }
                            )
                            st.toast("Feedback received.", icon="📨")
                            st.session_state[f"feedback_done_{last_msg_idx}"] = True
                            st.session_state["show_comment_box"] = False
                            st.rerun()
                        except: pass
                    
                    if c2.form_submit_button("Cancel"):
                        st.session_state["show_comment_box"] = False
                        st.rerun()

    # 3. CHAT INPUT (Pinned to bottom)
    if prompt := st.chat_input("Type your request here..."):
        # Clear any open feedback forms from previous turn
        st.session_state["show_comment_box"] = False
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.markdown("Thinking...")
                
                try:
                    payload = {
                        "pk": AGENT_PK,
                        "chat_id": st.session_state.chat_id,
                        "user_message": prompt
                    }
                    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}

                    response = requests.post(f"{API_BASE_URL}/chat", json=payload, headers=headers)

                    if response.status_code == 200:
                        data = response.json()
                        bot_reply = data.get("response", "No response.")
                        placeholder.markdown(bot_reply)
                        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    else:
                        err = f"Error {response.status_code}"
                        placeholder.error(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
                    
                    st.rerun() 
                except Exception as e:
                    placeholder.error(f"Connection Error: {e}")