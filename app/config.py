import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables on import (if .env file exists)
load_dotenv()

def get_key_from_env_var(env_var_name: str) -> str | None:
    """Attempts to read a specific environment variable."""
    return os.getenv(env_var_name)

def get_optional_key_from_env(provider_key: str) -> str | None:
    """Attempts to get API key from environment based on provider key."""
    env_var_map = {
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY"
    }
    env_var_name = env_var_map.get(provider_key)
    if env_var_name:
        return get_key_from_env_var(env_var_name)
    return None

# Removed previous key-getting functions that stopped execution

# Keeping file in case other shared config is needed later

# No configuration needed from this file currently. 