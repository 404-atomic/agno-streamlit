import streamlit as st
import streamlit.components.v1 as components
from app.models import initialize_agent, AVAILABLE_MODELS, get_provider_key
from app.ui import (
    handle_chat_interaction, 
    display_user_memories, 
    display_session_storage, 
    display_session_summary,
    handle_prompts_section
)
# Import the optional key getter
from app.config import get_optional_key_from_env

# --- Page Configuration ---
st.set_page_config(
    page_title="Agno Chat",
    page_icon="🤖",
    layout="wide" # Use wide layout for better tab/sidebar spacing
)

st.title("Agno Chat Agent")

# --- Sidebar for Settings ---
with st.sidebar:
    st.header("Agent Settings")

    # --- Determine initial provider key --- 
    # Need this before initializing API key state
    initial_provider = st.session_state.get('selected_provider', "OpenAI")
    initial_provider_key = get_provider_key(initial_provider)
    
    # --- Initialize session state with potential .env prefill --- 
    st.session_state.setdefault('selected_provider', initial_provider)
    st.session_state.setdefault('selected_model_id', AVAILABLE_MODELS[initial_provider_key][0])
    st.session_state.setdefault('user_id', "")
    st.session_state.setdefault('session_id', "default_session_001")
    # Try pre-filling API key from .env for the initial provider
    st.session_state.setdefault('api_key', get_optional_key_from_env(initial_provider_key) or "") 
    st.session_state.setdefault('use_user_memory', True)
    st.session_state.setdefault('use_session_summary', True)
    st.session_state.setdefault('load_chat_history', True)

    st.subheader("Credentials & Model")
    
    # --- Provider Selection --- 
    provider_display_names = {
        "openai": "OpenAI",
        "google": "Google/Gemini",
        "anthropic": "Anthropic/Claude"
    }
    selected_provider_display = st.selectbox(
        "Provider:",
        options=list(provider_display_names.values()),
        key="provider_select",
        index=list(provider_display_names.values()).index(provider_display_names[get_provider_key(st.session_state.selected_provider)])
    )
    new_selected_provider_key = next((key for key, value in provider_display_names.items() if value == selected_provider_display), "openai")
    current_provider_key_in_state = get_provider_key(st.session_state.selected_provider)
    
    provider_changed = new_selected_provider_key != current_provider_key_in_state
    
    # Update state and potentially API key if provider actually changed
    if provider_changed:
        st.session_state.selected_provider = provider_display_names[new_selected_provider_key]
        st.session_state.selected_model_id = AVAILABLE_MODELS[new_selected_provider_key][0]
        # Attempt to load new key from .env when provider changes
        env_key = get_optional_key_from_env(new_selected_provider_key)
        st.session_state.api_key = env_key if env_key else "" # Reset or fill from env
        st.rerun()
    else:
        st.session_state.selected_provider = selected_provider_display 

    # --- API Key Input (shows pre-filled value if loaded) --- 
    st.session_state.api_key = st.text_input(
        "API Key:", 
        type="password", 
        value=st.session_state.api_key, # Value comes from session state
        key="api_key_input",
        help="Enter the API key for the selected provider (auto-filled if in .env)."
    )

    # --- Model Selection (Dynamic) --- 
    current_provider_key = get_provider_key(st.session_state.selected_provider)
    available_models_for_provider = AVAILABLE_MODELS[current_provider_key]
    current_model_index = 0
    if st.session_state.selected_model_id in available_models_for_provider:
        current_model_index = available_models_for_provider.index(st.session_state.selected_model_id)
    else:
        st.session_state.selected_model_id = available_models_for_provider[0]
    st.session_state.selected_model_id = st.selectbox(
        "Model ID:",
        options=available_models_for_provider,
        key="model_select",
        index=current_model_index
    )
    
    st.divider()
    st.subheader("Session & Memory Features")
    
    # --- User ID Input --- 
    previous_user_id = st.session_state.get("user_id", "")
    st.session_state.user_id = st.text_input(
        "User ID:", value=st.session_state.user_id, key="user_id_input",
        help="Identifier for user-specific memories."
    )
    
    # Check if user_id changed, and if so, update session_id with a pattern
    if st.session_state.user_id and st.session_state.user_id != previous_user_id:
        import random
        import time
        # Generate a new session ID when user ID changes
        unique_id = f"{int(time.time() * 1000) % 10000:04d}{random.randint(1000, 9999)}"
        st.session_state.session_id = f"default_session_{st.session_state.user_id}_{unique_id}"
    
    # --- Session ID Input ---
    # Only enable session ID input if user_id is provided
    if st.session_state.user_id:
        st.session_state.session_id = st.text_input(
            "Session ID:", value=st.session_state.session_id, key="session_id_input",
            help="Identifier for chat history and summaries."
        )
    else:
        # Display disabled session ID input 
        st.text_input(
            "Session ID:", value="Please enter User ID first", key="disabled_session_id_input",
            help="Identifier for chat history and summaries.",
            disabled=True
        )
        # Reset session ID when no user ID is present
        st.session_state.session_id = ""
    
    # --- Memory Toggles --- 
    # Chat history toggle - Only enable if session_id is provided
    load_history_disabled = not bool(st.session_state.session_id)
    st.session_state.load_chat_history = st.toggle(
        "Load History", 
        value=st.session_state.load_chat_history if not load_history_disabled else False, 
        key="toggle_history",
        help="Load stored chat history for the session.",
        disabled=load_history_disabled
    )
    if load_history_disabled:
        st.session_state.load_chat_history = False
    
    # User memory toggle - Only enable if user_id is provided
    user_memory_disabled = not bool(st.session_state.user_id)
    st.session_state.use_user_memory = st.toggle(
        "User Memory", 
        value=st.session_state.use_user_memory if not user_memory_disabled else False, 
        key="toggle_user_mem",
        help="Allow agent to save/load facts about the user.",
        disabled=user_memory_disabled
    )
    if user_memory_disabled:
        st.session_state.use_user_memory = False
    
    # Session summary toggle - Only enable if both user_id and session_id are provided
    summary_disabled = not (bool(st.session_state.user_id) and bool(st.session_state.session_id))
    st.session_state.use_session_summary = st.toggle(
        "Session Summary", 
        value=st.session_state.use_session_summary if not summary_disabled else False, 
        key="toggle_summary",
        help="Enable summary generation capability.",
        disabled=summary_disabled
    )
    if summary_disabled:
        st.session_state.use_session_summary = False
        
    # Add an info box explaining the dependencies
    if not st.session_state.user_id or not st.session_state.session_id:
        st.info("""
        **Note:** Memory features require identifiers:
        - User Memory requires a User ID
        - Chat History requires a Session ID
        - Session Summary requires both User ID and Session ID
        """)
        
    st.divider()
    st.caption("Agent will re-initialize if settings change.")
    
    # Create better display for current selections
    st.markdown("### Current Configuration")
    
    # Provider and model with visual highlight
    st.markdown(f"**Provider:** {st.session_state.selected_provider}")
    st.markdown(f"**Model ID:** {st.session_state.selected_model_id}")
    
    # User ID and Session ID with visual indicators
    user_id_status = "🟢" if st.session_state.user_id else "🔴"
    session_id_status = "🟢" if st.session_state.session_id else "🔴"
    st.markdown(f"**User ID:** {user_id_status} {st.session_state.user_id if st.session_state.user_id else 'Not Set'}")
    st.markdown(f"**Session ID:** {session_id_status} {st.session_state.session_id if st.session_state.session_id else 'Not Set'}")
    
    # Active features section
    st.markdown("**Active Features:**")
    features_active = False
    
    # Display feature status with colored indicators
    if st.session_state.load_chat_history:
        st.markdown("- 🟢 Chat History")
        features_active = True
    else:
        st.markdown("- 🔴 Chat History (disabled)")
        
    if st.session_state.use_user_memory:
        st.markdown("- 🟢 User Memory")
        features_active = True
    else:
        st.markdown("- 🔴 User Memory (disabled)")
        
    if st.session_state.use_session_summary:
        st.markdown("- 🟢 Session Summary")
        features_active = True
    else:
        st.markdown("- 🔴 Session Summary (disabled)")
        
    # Show message if no features are active
    if not features_active:
        st.warning("No memory features are currently active.", icon="⚠️")
    
    # Add a Clear Session button at the bottom
    st.divider()
    if st.button("🧹 Clear Session", key="clear_session", help="Clear all session data including chat history"):
        # Reset conversation
        if "messages" in st.session_state:
            st.session_state.messages = []
        
        # Reset sequential prompts progress
        if "completed_steps" in st.session_state:
            st.session_state.completed_steps = []
            
        # Show success message
        st.success("Session cleared successfully!")
        st.rerun()

# --- Pre-computation Checks --- 
# Check if API key is provided before initializing agent
if not st.session_state.api_key:
    st.sidebar.error("Please enter your API key in the sidebar.")
    st.info("Enter your API Key in the sidebar to begin.")
    st.stop() # Halt execution until API key is provided

# --- Initialize Agent, Memory, and Storage ---
# Pass the API key and toggle states
agent, memory, storage = initialize_agent(
    provider_name=st.session_state.selected_provider,
    model_id=st.session_state.selected_model_id,
    api_key=st.session_state.api_key,
    load_chat_history=st.session_state.load_chat_history,
    use_user_memory=st.session_state.use_user_memory,
    use_session_summary=st.session_state.use_session_summary,
    description=st.session_state.get("agent_description", ""),
    instructions=st.session_state.get("agent_instructions", [])
)

# --- Create Main Tabs ---
tab_chat, tab_prompts, tab_memories = st.tabs(["Chat UI", "Prompts", "Memories"])

# --- Tab 1: Chat UI ---
with tab_chat:
    st.header("Conversation")
    handle_chat_interaction(agent)

# --- Tab 2: Prompts ---
with tab_prompts:
    handle_prompts_section(agent)

# --- Tab 3: Memories (with Sub-Tabs) ---
with tab_memories:
    sub_tab_user, sub_tab_storage, sub_tab_summary = st.tabs([
        "User Memories",
        "Session Storage",
        "Session Summaries"
    ])

    with sub_tab_user:
        display_user_memories(memory)

    with sub_tab_storage:
        display_session_storage(agent)

    with sub_tab_summary:
        # Pass both agent and memory for capability check and triggering
        display_session_summary(agent, memory)

# --- JavaScript Scroll Hack --- 
# This script attempts to scroll to the bottom after the page rerenders.
# It might need adjustments depending on browser behavior and Streamlit versions.
scroll_script = """
<script>
    window.scrollTo(0, document.body.scrollHeight);
</script>
"""
components.html(scroll_script, height=0, width=0) 