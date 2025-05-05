import os
from agno.agent import AgentKnowledge
from agno.vectordb.lancedb import LanceDb
from dotenv import load_dotenv

load_dotenv() # Load OPENAI_API_KEY etc. for the default embedder

# --- Configuration (Match app/models.py) ---
LANCEDB_URI = "tmp/lancedb"
LANCEDB_TABLE_NAME = "agent_knowledge_v1"

# Ensure the LanceDB directory exists
os.makedirs(LANCEDB_URI, exist_ok=True)

print(f"Initializing LanceDB at: {LANCEDB_URI}")
print(f"Using table: {LANCEDB_TABLE_NAME}")

# Initialize LanceDB Vector DB directly
# It will likely use the default OpenAIEmbedder which needs OPENAI_API_KEY
lancedb_vector_db = LanceDb(
    table_name=LANCEDB_TABLE_NAME,
    uri=LANCEDB_URI,
)

# Initialize the base Knowledge Base
knowledge_base = AgentKnowledge(
    vector_db=lancedb_vector_db
)

# --- Prepare Knowledge Texts ---
knowledge_texts = [
    "Agno is a framework for building AI agents.",
    "This Streamlit app allows interacting with an Agno agent.",
    "The agent can use tools like DuckDuckGo for web searches.",
    "The agent can remember facts about users and summarize sessions.",
    "LanceDB is used as the vector database for the knowledge base."
]
print(f"Prepared {len(knowledge_texts)} text snippets to load.")

# --- Load data via AgentKnowledge.load_text --- 
print("Attempting to load data via AgentKnowledge.load_text...")
try:
    # Step 1: Try deleting the existing table first for a clean load
    # We need to access the underlying LanceDB connection/table object if possible
    # This part is speculative based on common patterns
    try:
        print(f"Attempting to delete existing table: {LANCEDB_TABLE_NAME}...")
        # Assuming delete_table exists on the wrapper
        lancedb_vector_db.delete_table()
        print("Existing table deleted (if it existed).")
    except AttributeError:
        print("Warning: 'delete_table' method not found on LanceDb wrapper. Skipping deletion.")
        # Alternative: Manually delete the directory if using file-based storage
        # import shutil
        # table_path = os.path.join(LANCEDB_URI, LANCEDB_TABLE_NAME + ".lance")
        # if os.path.exists(table_path):
        #     print(f"Manually deleting directory: {table_path}")
        #     shutil.rmtree(table_path)
    except Exception as delete_err:
        print(f"Warning: Could not delete table: {delete_err}")

    # Step 2: Load texts one by one using load_text
    # Assuming load_text handles embedding and saving incrementally
    print("Loading text snippets using knowledge_base.load_text()...")
    for text in knowledge_texts:
        knowledge_base.load_text(text)
        print(f"  Loaded: '{text[:50]}...'")

    print("\nKnowledge text loading process completed.")

except Exception as e:
    import traceback
    print(f"\nError during knowledge loading:")
    print(f"  Type: {type(e).__name__}")
    print(f"  Args: {e.args}")
    print(f"  Traceback:")
    traceback.print_exc()
    print("\nPlease ensure LanceDB is installed, accessible, and any required embedder keys (e.g., OPENAI_API_KEY) are set.") 