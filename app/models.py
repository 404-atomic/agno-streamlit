import streamlit as st
from agno.agent import Agent
# Import specific model classes
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.models.anthropic import Claude
# Memory imports
import os
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.sqlite import SqliteStorage # Import Storage
from typing import Tuple, Optional # Import Optional
from agno.tools.duckduckgo import DuckDuckGoTools # <<< Added Import

# --- Knowledge Imports ---
from agno.agent import AgentKnowledge
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType

# Import the unified key getter
# from app.config import get_api_key_for_provider

# --- Constants ---
DB_DIR = "tmp"
DB_FILE = os.path.join(DB_DIR, "agent_memory.db")
MEMORY_TABLE_NAME = "user_memories_v2"
STORAGE_TABLE_NAME = "agent_sessions_v2" # New constant for storage table

# --- Knowledge Base Setup ---
LANCEDB_URI = "tmp/lancedb" # Store LanceDB data locally within the project
# Default table, not used by the agent in this configuration
# DEFAULT_KNOWLEDGE_TABLE_NAME = "agent_knowledge_v1"
RECIPES_TABLE_NAME = "recipes" # Table name from test.py

# Initialize LanceDB Vector DB specifically for the recipes table
# This is the vector_db the agent will use for knowledge search
recipes_vector_db = LanceDb(
    table_name=RECIPES_TABLE_NAME,
    uri=LANCEDB_URI,
    # search_type=SearchType.keyword # Optional: Can specify search type
)

# Initialize the Knowledge Base using the recipes vector_db
# This knowledge object will be passed to the agent
recipes_knowledge = AgentKnowledge(
    vector_db=recipes_vector_db
)
# --- End Knowledge Base Setup ---

# --- Model ID Mappings ---
# Maps provider key (lowercase) to a list of available model IDs
AVAILABLE_MODELS = {
    "openai": [
        "gpt-4o-mini-2024-07-18",
        "gpt-4.1-nano-2025-04-14",
        "gpt-4.1-2025-04-14",
        "gpt-4o", # Keep previous default as an option
    ],
    "google": [
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro-latest", # Keep previous default
        "gemini-1.5-flash-latest",
    ],
    "anthropic": [
        "claude-3-7-sonnet-20250219",
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-latest", # Keep previous default
    ]
}

# Helper to get provider key from display name
def get_provider_key(provider_display_name: str) -> str:
    name_lower = provider_display_name.lower()
    if "openai" in name_lower:
        return "openai"
    elif "google" in name_lower or "gemini" in name_lower:
        return "google"
    elif "anthropic" in name_lower or "claude" in name_lower:
        return "anthropic"
    return "openai" # Default fallback

@st.cache_resource
def initialize_agent(
    provider_name: str,
    model_id: str,
    api_key: str,
    use_user_memory: bool,
    use_session_summary: bool,
    load_chat_history: bool,
    description: str = None,
    instructions: list = None
) -> Tuple[Agent, Memory, SqliteStorage, LanceDb, str]:
    """Initializes agent based on selected settings, using provided API key."""

    provider_key = get_provider_key(provider_name)

    # --- Initialize Model Instance (using passed api_key) --- 
    model_instance = None
    if provider_key == "openai":
        model_instance = OpenAIChat(id=model_id, api_key=api_key)
    elif provider_key == "google":
        model_instance = Gemini(id=model_id, api_key=api_key)
    elif provider_key == "anthropic":
        model_instance = Claude(id=model_id, api_key=api_key)
    else:
        st.error(f"Unsupported provider: {provider_name}")
        st.stop()

    # --- Initialize Memory & Storage --- 
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Use a smaller/faster model for memory tasks as recommended in docs
    if provider_key == "openai":
         memory_model = OpenAIChat(id="gpt-4o-mini-2024-07-18", api_key=api_key) 
    elif provider_key == "google":
         memory_model = Gemini(id="gemini-1.5-flash-latest", api_key=api_key) 
    elif provider_key == "anthropic":
         memory_model = Claude(id="claude-3-5-haiku-20241022", api_key=api_key)
    else: # Fallback
        memory_model = OpenAIChat(id="gpt-4o-mini-2024-07-18", api_key=api_key)
    
    # Initialize memory database for user memories and session summaries
    memory_db = SqliteMemoryDb(table_name=MEMORY_TABLE_NAME, db_file=DB_FILE)
    memory = Memory(model=memory_model, db=memory_db)
    
    # Initialize storage for chat history
    storage = SqliteStorage(table_name=STORAGE_TABLE_NAME, db_file=DB_FILE)

    # Construct info message based on toggles
    active_features = []
    if use_user_memory: active_features.append("UserMem")
    if use_session_summary: active_features.append("Summary")
    if load_chat_history: active_features.append("History")
    feature_str = " | Feat: " + ", ".join(active_features) if active_features else ""
    
    # Simplified info message
    st.sidebar.caption(f"Agent: {provider_name}/{model_id}{feature_str}") 

    # --- Initialize Agent --- 
    agent = Agent(
        model=model_instance,
        memory=memory,
        storage=storage,
        
        # Memory features as per docs recommendation
        enable_user_memories=use_user_memory,      # Run MemoryManager after each response
        enable_agentic_memory=use_user_memory,     # Give agent tool to manage user memories
        enable_session_summaries=use_session_summary,
        
        # Chat history features as per docs recommendation
        add_history_to_messages=load_chat_history, # Add chat history to messages
        num_history_runs=5,                        # Number of runs to include in history
        read_chat_history=load_chat_history,       # Enable chat history tool
        read_tool_call_history=load_chat_history,  # Enable tool call history tool
        
        # Other settings
        markdown=True,
        debug_mode=False,
        description=description,
        instructions=instructions,
        knowledge=recipes_knowledge,      # <<< Use the recipes knowledge base
        # search_knowledge=True, # This is True by default when knowledge is provided
        tools=[DuckDuckGoTools()],
        show_tool_calls=True,
    )
    # Return the LanceDB URI and the vector_db used by the agent
    return agent, memory, storage, recipes_vector_db, LANCEDB_URI 