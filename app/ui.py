import streamlit as st
from agno.agent import Agent, RunResponse, Message
from .prompts import SEQUENTIAL_PROMPTS, EXAMPLE_DESCRIPTIONS, EXAMPLE_INSTRUCTIONS
import json # For pretty printing debug info
from agno.memory.v2.memory import Memory # Import Memory for type hint
from agno.storage.sqlite import SqliteStorage # Import Storage
from agno.vectordb.lancedb import LanceDb # Import LanceDb for type hint
import re # Import regex module
import os # Import os module
import lancedb # Import base lancedb library
import traceback # For error reporting

# --- Constants ---
# The list is now defined in app/prompts.py
# SEQUENTIAL_PROMPTS = [
#     "Step 1: Tell me a short story about a brave knight.",
#     "Step 2: Now, describe the dragon the knight faced.",
#     "Step 3: Finally, how did the story end?"
# ]

def display_chat_history():
    """Displays the chat messages from session state, including metadata tags as badges."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Add badge styles
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message["content"]
            if message["role"] == "assistant":
                # Check for image URLs in the content
                image_urls = re.findall(r'!\[.*?\]\((.*?)\.(png|jpg|jpeg|gif|bmp|svg)\)', content, re.IGNORECASE)
                
                if image_urls:
                    text_parts = re.split(r'!\[.*?\]\(.*?\.(?:png|jpg|jpeg|gif|bmp|svg)\)', content, flags=re.IGNORECASE)
                    url_index = 0
                    for i, part in enumerate(text_parts):
                        if part: # Display text part if it exists
                            st.markdown(part)
                        if i < len(image_urls):
                            full_url = f"{image_urls[url_index][0]}.{image_urls[url_index][1]}"
                            st.image(full_url, width=500) # Display image with width constraint
                            url_index += 1
                else:
                    st.markdown(content) # Display as markdown if no image found
            else:
                st.markdown(content) # Display user message as markdown
            
            # Display metadata as badges if it exists for assistant
            if message["role"] == "assistant" and "metadata" in message:
                metadata = message["metadata"]
                badge_md_parts = [] # List to hold markdown badge strings

                # Model Badge
                model_id = metadata.get('model_id')
                if model_id:
                    badge_md_parts.append(f":gray-badge[{model_id}]")

                # Feature Badges
                if metadata.get("user_memory"):
                    badge_md_parts.append(":violet-badge[User Memory]")
                if metadata.get("session_summary"):
                    badge_md_parts.append(":violet-badge[Session Summary]")
                if metadata.get("load_history"):
                    badge_md_parts.append(":violet-badge[Chat History]")

                # Tool Badges
                if "tool_calls" in metadata and metadata["tool_calls"]:
                    tool_names = [tool.get('function', {}).get('name', 'Unknown') for tool in metadata["tool_calls"]]
                    if tool_names:
                         # Deduplicate tool names before displaying them
                         unique_tool_names = list(set(tool_names))
                         badge_md_parts.append(f":red-badge[{', '.join(unique_tool_names)}]") # Changed color for tools

                if badge_md_parts:
                    st.markdown(" " + " ".join(badge_md_parts)) # Join with spaces

def handle_agent_response(agent: Agent, prompt: str, user_id: str, session_id: str):
    """Gets streamed response, adds final message with metadata."""
    full_response_content = ""
    internal_error_message = None
    
    # Always get the latest session_id and user_id from session state
    # This ensures we use the most current values even if they were changed
    current_user_id = st.session_state.get("user_id", user_id)
    current_session_id = st.session_state.get("session_id", session_id)
    
    metadata = { 
        "model_id": getattr(agent.model, 'id', 'N/A'),
        "user_memory": getattr(agent, 'enable_user_memories', False),
        "session_summary": getattr(agent, 'enable_session_summaries', False),
        "load_history": getattr(agent, 'add_history_to_messages', False),
        "tool_calls": [], # Will be populated with tool call data if tools are used
    }

    # --- Stream Processing --- 
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking... ▌")
        try:
            response_stream = agent.run(
                prompt,
                user_id=current_user_id if current_user_id else None,
                session_id=current_session_id if current_session_id else None,
                stream=True
            )

            # --- Add check for None stream ---
            if response_stream is None:
                internal_error_message = "Agent run returned None, cannot process stream."
                st.error(internal_error_message)
                message_placeholder.error(internal_error_message)
                metadata["error"] = True
                full_response_content = internal_error_message
            else:
                # --- Original stream processing loop ---
                has_captured_all_tool_calls = False  # Flag to track if we've already captured all tools
                
                # Storage for saving complete response (will be used to extract tools at the end)
                complete_response = None
                
                for chunk in response_stream:
                    # Save the complete response once available (last chunk should have everything)
                    if hasattr(chunk, '__dict__') and 'content' in chunk.__dict__:
                        complete_response = chunk

                    # Handle different types of chunks
                    if chunk is None:
                        # Skip None chunks
                        continue
                    # Check for the specific error structure within the stream
                    elif isinstance(chunk, dict) and "ERROR" in chunk and isinstance(chunk["ERROR"], dict):
                        internal_error_message = chunk["ERROR"].get("message", "Unknown internal error")
                        st.error(f"Internal Agno Error: {internal_error_message}")
                        message_placeholder.error(f"Error during stream: {internal_error_message}")
                        metadata["error"] = True
                        full_response_content = f"Internal Error: {internal_error_message}"
                        break
                    elif hasattr(chunk, 'content') and chunk.content:
                        # Handle RunResponse objects or any object with a content attribute
                        full_response_content += chunk.content
                        message_placeholder.markdown(full_response_content + " ▌")

                        # --- Capture tool calls --- 
                        # Check if nested in messages
                        if hasattr(chunk, 'messages') and chunk.messages is not None:
                            for msg in chunk.messages:
                                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                    metadata["tool_calls"].extend(msg.tool_calls)
                        # Check if directly on chunk object
                        elif hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                            metadata["tool_calls"].extend(chunk.tool_calls)
                        # Check if tools field exists (Agno's actual field name for tool calls)
                        elif hasattr(chunk, 'tools') and chunk.tools:
                            # Convert tools to the expected tool_calls format (function.name)
                            for tool in chunk.tools:
                                if isinstance(tool, dict) and 'tool_name' in tool:
                                    metadata["tool_calls"].append({"function": {"name": tool['tool_name']}})
                                elif hasattr(tool, 'tool_name'):
                                    metadata["tool_calls"].append({"function": {"name": tool.tool_name}})
                        # Try to access tool_calls through a run property if it exists
                        elif hasattr(chunk, 'run') and hasattr(chunk.run, 'tool_calls') and chunk.run.tool_calls:
                            metadata["tool_calls"].extend(chunk.run.tool_calls)

                    elif isinstance(chunk, dict) and 'content' in chunk:
                        # Handle dictionary chunks with content
                        full_response_content += chunk['content']
                        message_placeholder.markdown(full_response_content + " ▌")

                        # --- Capture tool calls --- 
                        # Check if nested in messages
                        if 'messages' in chunk and chunk['messages'] is not None:
                            for msg in chunk['messages']:
                                if 'tool_calls' in msg and msg['tool_calls']:
                                    metadata["tool_calls"].extend(msg['tool_calls'])
                        # Check if directly in chunk dict
                        elif 'tool_calls' in chunk and chunk['tool_calls']:
                            metadata["tool_calls"].extend(chunk['tool_calls'])
                        # Check if tools field exists (Agno's actual field name for tool calls)
                        elif 'tools' in chunk and chunk['tools']:
                            # Convert tools to the expected tool_calls format (function.name)
                            for tool in chunk['tools']:
                                if isinstance(tool, dict) and 'tool_name' in tool:
                                    metadata["tool_calls"].append({"function": {"name": tool['tool_name']}})
                        # Try run property if present
                        elif 'run' in chunk and 'tool_calls' in chunk['run'] and chunk['run']['tool_calls']:
                            metadata["tool_calls"].extend(chunk['run']['tool_calls'])

                    elif isinstance(chunk, str):
                        # Handle plain string chunks
                        full_response_content += chunk
                        message_placeholder.markdown(full_response_content + " ▌")

                # Try to find tool calls from the complete response (which might have all tools)
                if complete_response and not metadata["tool_calls"]:
                    try:
                        if hasattr(complete_response, 'run') and hasattr(complete_response.run, 'tool_calls') and complete_response.run.tool_calls:
                            metadata["tool_calls"] = complete_response.run.tool_calls
                        # Check for tools field in complete response
                        elif hasattr(complete_response, 'tools') and complete_response.tools:
                            for tool in complete_response.tools:
                                if isinstance(tool, dict) and 'tool_name' in tool:
                                    metadata["tool_calls"].append({"function": {"name": tool['tool_name']}})
                                elif hasattr(tool, 'tool_name'):
                                    metadata["tool_calls"].append({"function": {"name": tool.tool_name}})
                    except Exception as e:
                        pass
                
                # If still no tool calls found but we know Agno uses them, try parsing from full_response_content
                if not metadata["tool_calls"] and "tool:" in full_response_content.lower():
                    try:
                        # This is a simple regex-based fallback to extract tool names
                        import re
                        # Find patterns like "Tool: tool_name" or similar in the response
                        tool_matches = re.findall(r"tool:\s*(\w+)", full_response_content, re.IGNORECASE)
                        if tool_matches:
                            # Create simplified tool_call objects with just the function name
                            for tool_name in tool_matches:
                                metadata["tool_calls"].append({"function": {"name": tool_name}})
                    except Exception:
                        pass

                if not internal_error_message:
                    message_placeholder.markdown(full_response_content)


        except Exception as e:
            # Log the full traceback for better debugging
            import traceback
            tb_str = traceback.format_exc()
            internal_error_message = f"An error occurred: {e}\\nTraceback:\\n{tb_str}"
            st.error(internal_error_message)
            full_response_content = f"An error occurred: {e}" # Keep user-facing error simpler
            message_placeholder.error(full_response_content)
            metadata["error"] = True
            
    # --- Update Session State --- 
    # Only log minimal debugging info if needed
    # print(f"DEBUG: Found {len(metadata.get('tool_calls', []))} tool calls")
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
         st.session_state.messages.append({
             "role": "assistant", "content": full_response_content,"metadata": metadata })
    elif st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
         st.session_state.messages[-1]["content"] = full_response_content
         st.session_state.messages[-1]["metadata"] = metadata
    else:
         st.session_state.messages.append({"role": "assistant", "content": full_response_content, "metadata": metadata})

def extract_run_data(run_info):
    """Helper function to extract data from various response object types."""
    data = {}
    
    # Get type information
    data['_type'] = type(run_info).__name__
    
    # Handle different types
    if run_info is None:
        return {'_type': 'None', 'error': 'Response was None'}
    
    elif isinstance(run_info, dict):
        # Just return the dictionary directly
        data.update(run_info)
        return data
        
    else:
        # Try multiple approaches to extract data
        
        # 1. Try direct attribute access for common fields
        for attr in ['user_id', 'session_id', 'input', 'content', 'metrics', 'messages', 
                     'tool_calls', 'error', 'thinking', 'run_id', 'input_tokens', 
                     'output_tokens', 'total_tokens', 'provider', 'agent_id']:
            if hasattr(run_info, attr):
                data[attr] = getattr(run_info, attr)
        
        # 2. Try to convert the whole object to a dict
        try:
            obj_dict = vars(run_info)
            for k, v in obj_dict.items():
                if k not in data:  # Don't overwrite already captured attributes
                    data[k] = v
        except:
            pass
            
        # 3. Try to access __dict__ directly
        try:
            if hasattr(run_info, '__dict__'):
                for k, v in run_info.__dict__.items():
                    if k not in data:  # Don't overwrite already captured attributes
                        data[k] = v
        except:
            pass
            
        # 4. Try dir() to get all attributes including inherited ones
        try:
            for attr in dir(run_info):
                # Skip private/special attributes and methods
                if not attr.startswith('_') and attr not in data:
                    try:
                        value = getattr(run_info, attr)
                        # Skip methods and functions
                        if not callable(value):
                            data[attr] = value
                    except:
                        pass
        except:
            pass
            
        return data

def display_debugging_info():
    """Displays details from the logged RunResponse or error dictionary."""
    st.header("Agent Run Logs")
    if "debug_runs" not in st.session_state:
        st.session_state.debug_runs = []
    if not st.session_state.debug_runs:
        st.info("No agent runs recorded yet.")
        return
    
    # Debug information about the contents of debug_runs
    st.write(f"Number of debug entries: {len(st.session_state.debug_runs)}")
    
    for i, run_info in enumerate(reversed(st.session_state.debug_runs)):
        run_num = len(st.session_state.debug_runs) - i
        expander_title = f"Run {run_num}"
        
        # Use our helper function to extract data
        run_data = extract_run_data(run_info)
        run_info_type = run_data.get('_type', 'Unknown')
        
        # Create the expander title with useful info
        if 'user_id' in run_data and run_data['user_id']:
            expander_title += f" - User: {run_data['user_id']}"
        if 'session_id' in run_data and run_data['session_id']:
            expander_title += f" - Session: {run_data['session_id']}"
        if 'error' in run_data and run_data['error']:
            expander_title += " - ERROR"
            
        # Display the run info in an expander
        with st.expander(f"{expander_title} ({run_info_type})", expanded=True):
            # Show object type and basic info
            st.markdown(f"**Response Type:** {run_info_type}")
            
            # Show prompt/input if available
            if 'input' in run_data:
                st.markdown("**Input Prompt:**")
                st.text(run_data['input'])
            
            # Show response content if available
            if 'content' in run_data and run_data['content']:
                st.markdown("**Response Content:**")
                st.markdown(run_data['content'])
                
            # Show error if present
            if 'error' in run_data and run_data['error']:
                st.markdown("**Error:**")
                st.error(run_data['error'])
                
            # Show complete JSON view of all data
            with st.expander("Complete Debug Data", expanded=True):
                try:
                    # First try with the original data
                    st.json(run_data)
                except:
                    # If serialization fails, convert everything to strings
                    safe_data = {}
                    for k, v in run_data.items():
                        try:
                            # Try to make it JSON-serializable
                            import json
                            json.dumps({k: v})
                            safe_data[k] = v
                        except:
                            # Fall back to string representation
                            safe_data[k] = str(v)
                    st.json(safe_data)
            
            # Show specific sections in their own expandable areas
            if 'messages' in run_data and run_data['messages']:
                with st.expander("Messages to Model", expanded=False):
                    try:
                        st.json(run_data['messages'])
                    except:
                        st.text(str(run_data['messages']))
            
            if 'tool_calls' in run_data and run_data['tool_calls']:
                with st.expander("Tool Calls", expanded=True):
                    try:
                        st.json(run_data['tool_calls'])
                    except:
                        st.text(str(run_data['tool_calls']))
            
            if 'metrics' in run_data and run_data['metrics']:
                with st.expander("Metrics", expanded=False):
                    try:
                        st.json(run_data['metrics'])
                    except:
                        st.text(str(run_data['metrics']))
                        
            # Show thinking/internal processing if available
            if 'thinking' in run_data and run_data['thinking']:
                with st.expander("Agent Thinking", expanded=False):
                    st.markdown(run_data['thinking'])

def display_chunk_info():
    """Displays summary information about response chunks."""
    st.header("Chunk Information")
    
    if "debug_all_chunks" not in st.session_state:
        st.session_state.debug_all_chunks = []
        
    if not st.session_state.debug_all_chunks:
        st.info("No chunk information recorded yet.")
        return
        
    st.write(f"Number of recorded chunk sets: {len(st.session_state.debug_all_chunks)}")
    
    for i, chunk_info in enumerate(reversed(st.session_state.debug_all_chunks)):
        run_num = len(st.session_state.debug_all_chunks) - i
        with st.expander(f"Run {run_num} Chunk Info", expanded=True):
            st.markdown(f"**User ID:** {chunk_info.get('user_id', 'N/A')}")
            st.markdown(f"**Session ID:** {chunk_info.get('session_id', 'N/A')}")
            st.markdown(f"**Prompt:** {chunk_info.get('prompt', 'N/A')}")
            st.markdown(f"**Number of Chunks:** {chunk_info.get('num_chunks', 0)}")
            st.markdown(f"**Last Chunk Type:** {chunk_info.get('last_chunk_type', 'Unknown')}")

def display_user_memories(memory: Memory):
    """Fetches and displays user memories from the Memory object."""
    st.header("User Memories")
    user_id = st.session_state.get("user_id", None)

    if not user_id:
        st.info("Please enter a User ID in the sidebar to view memories.",)
        return

    # Add user ID display with refresh button only (clear removed temporarily)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"Showing memories for User ID: `{user_id}`")
    with col2:
        if st.button("🔄 Refresh", key="refresh_user_memories"):
            st.rerun()
    
    try:
        with st.spinner("Fetching memories..."):
            user_memories = memory.get_user_memories(user_id=user_id)
        
        if user_memories:
            # Display memories in a more user-friendly format if possible
            for i, mem in enumerate(user_memories):
                with st.expander(f"Memory {i+1}", expanded=False):
                    # Handle string representation of UserMemory objects
                    if isinstance(mem, str) and "UserMemory" in mem:
                        # Extract just the memory content from the string representation
                        try:
                            memory_content = mem.split('memory="', 1)[1].split('",', 1)[0]
                            st.markdown(f"**Content:** {memory_content}")
                        except (IndexError, AttributeError):
                            st.text(mem)  # Fall back to displaying the raw string
                    # Handle dictionary format
                    elif isinstance(mem, dict):
                        if "ERROR" in mem:
                            st.error(f"Error retrieving memory: {mem['ERROR'].get('message', 'Unknown error')}")
                        else:
                            content = mem.get('content', mem.get('memory', 'N/A'))
                            score = mem.get('score', 'N/A')
                            created_at = mem.get('created_at', 'N/A')
                            
                            st.markdown(f"**Content:** {content}")
                            st.markdown(f"**Score:** {score}")
                            st.markdown(f"**Created:** {created_at}")
                    else:
                        # Try to extract memory content for any object
                        memory_content = getattr(mem, 'memory', str(mem))
                        st.markdown(f"**Content:** {memory_content}")
            
            # Also show as raw format for debugging
            with st.expander("Raw Memory Data", expanded=False):
                st.text(str(user_memories))
        else:
            st.info("No memories found for this User ID. Chat with the agent with User Memory enabled to create memories.")
    except Exception as e:
        st.error(f"Could not retrieve memories: {e}")

def display_session_storage(agent: Agent):
    """Fetches and displays chat history via the Agent object in a simple format."""
    st.header("Session Chat History")
    user_id = st.session_state.get("user_id", None)
    session_id = st.session_state.get("session_id", None)

    if not session_id:
        st.info("The Session ID will be automatically generated once you provide a User ID.")
        return

    # Add session ID display with refresh button only (clear removed temporarily)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"Showing history for Session ID: `{session_id}`")
    with col2:
        if st.button("🔄 Refresh", key="refresh_session_history"):
            st.rerun()

    try:
        with st.spinner("Fetching history from agent..."):
            # Explicitly pass the session_id to ensure it's using the correct one
            stored_history = agent.get_messages_for_session(session_id=session_id)

        if stored_history:
            st.caption("Note: This shows history loaded by the agent based on the current Session ID.")
            
            # Show session information if available
            if hasattr(agent, 'get_session_info'):
                try:
                    session_info = agent.get_session_info(session_id=session_id)
                    with st.expander("Session Information", expanded=False):
                        st.json(session_info)
                except:
                    pass
            
            # Display history messages
            for msg in stored_history:
                 try:
                     # Check if it's a Message object or dict
                     if isinstance(msg, Message):
                         role = msg.role
                         content = msg.content
                     else:
                         role = msg.get("role", "unknown")
                         content = msg.get("content", "")
                     
                     # Simple markdown display for role
                     st.markdown(f"**{role.capitalize()}:**")
                     # Use st.code for the content block - Handles formatting better
                     st.code(content, language=None) # language=None prevents syntax highlighting
                     st.divider()
                 except Exception as display_err:
                     st.error(f"Error displaying message: {display_err}")
                     st.json(msg) # Fallback display
        else:
            st.info("No history loaded by the agent for this Session ID. Interact with the agent using this Session ID first.")
            
            # Add debugging information
            st.expander("Debug Info", expanded=False).write(f"""
            - Current User ID: {user_id}
            - Current Session ID: {session_id}
            - History Loading Enabled: {getattr(agent, 'add_history_to_messages', False)}
            - Number of History Runs: {getattr(agent, 'num_history_runs', 'N/A')}
            """)
    except Exception as e:
        st.error(f"Could not retrieve history via agent: {e}")

def display_session_summary(agent: Agent, memory: Memory):
    """Fetches and displays the session summary, includes trigger button."""
    st.header("Session Summary")
    user_id = st.session_state.get("user_id", None)
    session_id = st.session_state.get("session_id", None)

    if not user_id or not session_id:
        if not user_id:
            st.info("First enter a User ID in the sidebar.")
        elif not session_id:
            st.info("A Session ID will be automatically generated once you provide a User ID.")
        return

    # Add user/session ID display with refresh button only (clear removed temporarily)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"User: `{user_id}`, Session: `{session_id}`")
    with col2:
        if st.button("🔄 Refresh", key="refresh_session_summary"):
            st.rerun()
    
    # Check if the capability is enabled via the agent's settings
    summary_capability_enabled = getattr(agent, 'enable_session_summaries', False)

    if not summary_capability_enabled:
        st.info("Session summary capability is disabled. Enable it in the sidebar under 'Session & Memory Features'.", icon="ℹ️")
        return

    # Button to trigger summary creation/update
    if st.button("Generate/Update Session Summary", type="primary"):
        try:
            with st.spinner("Generating summary..."):
                # Create session summary using memory
                memory.create_session_summary(user_id=user_id, session_id=session_id)
            st.success("Summary generation triggered.")
            # Rerun to refresh the display below
            st.rerun()
        except Exception as e:
            st.error(f"Could not generate summary: {e}")

    # Display existing summary (if any)
    try:
        with st.spinner("Fetching summary..."):
            session_summary_obj = memory.get_session_summary(user_id=user_id, session_id=session_id)

        if session_summary_obj and hasattr(session_summary_obj, 'summary') and session_summary_obj.summary:
            st.markdown("**Current Summary:**")
            st.markdown(session_summary_obj.summary)
            
            # Display summary metadata if available
            if hasattr(session_summary_obj, 'created_at') or hasattr(session_summary_obj, 'updated_at'):
                with st.expander("Summary Metadata", expanded=False):
                    created_at = getattr(session_summary_obj, 'created_at', 'N/A')
                    updated_at = getattr(session_summary_obj, 'updated_at', 'N/A')
                    st.markdown(f"**Created:** {created_at}")
                    st.markdown(f"**Last Updated:** {updated_at}")
        else:
            st.info("No session summary found. Use the 'Generate Summary' button above to create one.")
            st.caption("Note: You need to have some chat history in this session before generating a summary.")
    except Exception as e:
        st.error(f"Could not retrieve session summary: {e}")

def handle_chat_interaction(agent: Agent):
    """Handles the user input and triggers agent response on rerun."""
    # Show the header with status indicator if agent has custom settings
    if st.session_state.get("agent_description") or st.session_state.get("agent_instructions"):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Chat with Customized Agent")
        with col2:
            st.markdown("<div style='text-align: right; margin-top: 10px;'><span style='background-color: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;'>Custom Settings Active</span></div>", unsafe_allow_html=True)
        
        with st.expander("Current Agent Configuration", expanded=False):
            if st.session_state.get("agent_description"):
                st.markdown("#### Description")
                st.markdown(f"*{st.session_state.get('agent_description')}*")
            
            if st.session_state.get("agent_instructions"):
                st.markdown("#### Instructions")
                for i, instruction in enumerate(st.session_state.get("agent_instructions", [])):
                    st.markdown(f"{i+1}. {instruction}")
    else:
        st.caption("Agent is using default settings. Go to the Prompts tab to customize.")
    
    # Initialize session state variables if they don't exist
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Ensure metadata exists even if no agent response yet
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant" and "metadata" not in st.session_state.messages[-1]:
        st.session_state.messages[-1]["metadata"] = {}

    # Get current user_id and session_id
    user_id = st.session_state.get("user_id", "")
    session_id = st.session_state.get("session_id", "")

    # Display chat history first
    display_chat_history()

    # --- Agent Response Trigger --- 
    # Check if the last message is from the user and trigger response
    # Also check if the assistant hasn't already responded to this user message
    # (by checking if the last message is still user) 
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_user_prompt = st.session_state.messages[-1]["content"]
        # Generate and append the agent's response with metadata
        handle_agent_response(agent, last_user_prompt, user_id, session_id)
        # Rerun *after* handling response to ensure metadata display updates
        st.rerun() 

    # --- User Input --- 
    if prompt := st.chat_input("Enter your message..."):
        # Append user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Immediately rerun to show the user message
        st.rerun()
    # The agent response will be triggered in the *next* script run after this rerun

def display_sequential_prompts(agent: Agent):
    """Display sequential prompts that only appear after the previous one is clicked."""
    st.subheader("Sequential Prompts")
    
    # Initialize session state for tracking which steps have been completed
    if "completed_steps" not in st.session_state:
        st.session_state.completed_steps = []
        
    # Display each prompt as a button depending on completion status
    for i, prompt in enumerate(SEQUENTIAL_PROMPTS):
        step_num = i + 1
        step_id = f"step_{step_num}"
        
        # Only show this step if it's the first step or previous steps are completed
        if i == 0 or f"step_{step_num-1}" in st.session_state.completed_steps:
            # Extract the prompt text without the "Step X:" prefix
            prompt_text = prompt.split(":", 1)[1].strip() if ":" in prompt else prompt
            
            if st.button(f"Step {step_num}: {prompt_text}", key=f"seq_prompt_{step_num}"):
                # Mark this step as completed
                if step_id not in st.session_state.completed_steps:
                    st.session_state.completed_steps.append(step_id)
                
                # Add the prompt to messages
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Trigger agent response
                handle_agent_response(
                    agent, 
                    prompt, 
                    st.session_state.get("user_id", ""), 
                    st.session_state.get("session_id", "")
                )
                st.rerun()

def display_agent_settings():
    """Display minimal settings for agent description and instructions."""
    
    # Initialize session state for agent settings
    if "agent_description" not in st.session_state:
        st.session_state.agent_description = ""
    
    if "agent_instructions" not in st.session_state:
        st.session_state.agent_instructions = []
    
    # Add a template selector
    st.subheader("Templates")
    template_cols = st.columns(3)
    
    with template_cols[0]:
        if st.button("Explainer Template"):
            st.session_state.agent_description = EXAMPLE_DESCRIPTIONS[0]
            st.session_state.agent_instructions = EXAMPLE_INSTRUCTIONS.copy()
            st.rerun()
    
    with template_cols[1]:
        if st.button("Storyteller Template"):
            st.session_state.agent_description = EXAMPLE_DESCRIPTIONS[1]
            st.session_state.agent_instructions = [
                "Create engaging and vivid stories",
                "Develop interesting characters with depth",
                "Build immersive settings that enhance the narrative"
            ]
            st.rerun()
    
    with template_cols[2]:
        if st.button("Technical Expert"):
            st.session_state.agent_description = EXAMPLE_DESCRIPTIONS[2]
            st.session_state.agent_instructions = [
                "Provide accurate technical information",
                "Explain concepts with appropriate detail",
                "Reference reliable sources when necessary"
            ]
            st.rerun()
    
    st.divider()
    
    # Description input
    description_input = st.text_area(
        "Description", 
        value=st.session_state.agent_description,
        key="agent_description_input",
        placeholder="E.g., You are a helpful assistant that specializes in storytelling",
        help="A description that guides the overall behavior of the agent"
    )
    
    # Instructions input (one per line)
    instructions_input = st.text_area(
        "Instructions (one per line)", 
        value="\n".join(st.session_state.agent_instructions),
        key="agent_instructions_input",
        placeholder="Be concise and clear\nUse descriptive language\nKeep your stories family-friendly",
        help="A list of precise, task-specific instructions (enter one per line)"
    )
    
    # Convert instructions from text to list for preview
    instructions_list = [
        line.strip() for line in instructions_input.split("\n") 
        if line.strip()  # Skip empty lines
    ]
    
    # Button to save settings
    if st.button("Apply Settings", type="primary"):
        # Update session state
        st.session_state.agent_description = st.session_state.agent_description_input
        
        # Convert instructions from text to list
        instructions_text = st.session_state.agent_instructions_input
        st.session_state.agent_instructions = [
            line.strip() for line in instructions_text.split("\n") 
            if line.strip()  # Skip empty lines
        ]
        
        st.success("Agent settings updated! The agent will be reinitialized with these settings.")
        # Force a rerun to reinitialize the agent with the new settings
        st.rerun()

def handle_prompts_section(agent: Agent):
    """Handles the prompts tab with sequential prompts and agent settings."""
    # Create tabs within the prompts section
    prompt_tab1, prompt_tab2 = st.tabs(["Quick Sequential Prompts", "Agent Settings"])
    
    # Tab 1: Sequential Prompts
    with prompt_tab1:
        display_sequential_prompts(agent)
    
    # Tab 2: Agent Settings
    with prompt_tab2:
        display_agent_settings()

def display_available_sessions(agent: Agent):
    """Displays and allows selection of available sessions for the current user."""
    st.header("Available Sessions")
    user_id = st.session_state.get("user_id", None)

    if not user_id:
        st.warning("Please enter a User ID in the sidebar to view available sessions.", icon="👤")
        return

    st.write(f"Available sessions for User ID: `{user_id}`")
    
    try:
        # Fetch available sessions if the function is available
        available_sessions = []
        if hasattr(agent.storage, 'get_sessions_for_user'):
            available_sessions = agent.storage.get_sessions_for_user(user_id=user_id)
        elif hasattr(agent.storage, 'get_all_sessions'):
            # If user-specific function is not available, get all sessions and filter
            all_sessions = agent.storage.get_all_sessions()
            # This filtering depends on how sessions are stored; this is just an example
            available_sessions = [s for s in all_sessions if getattr(s, 'user_id', '') == user_id]
        
        if available_sessions:
            st.success(f"Found {len(available_sessions)} sessions for this user.")
            
            # Display sessions in a table or list
            for i, session in enumerate(available_sessions):
                session_id = getattr(session, 'session_id', session.get('session_id', f'Session {i+1}'))
                created_at = getattr(session, 'created_at', session.get('created_at', 'Unknown'))
                
                with st.expander(f"Session: {session_id}", expanded=False):
                    st.markdown(f"**Created At:** {created_at}")
                    
                    # Add a button to select this session
                    if st.button("Select This Session", key=f"select_session_{i}"):
                        st.session_state.session_id = session_id
                        st.success(f"Selected session: {session_id}")
                        st.rerun()
                    
                    # Show full session data if available
                    if isinstance(session, dict):
                        with st.expander("Session Details", expanded=False):
                            st.json(session)
        else:
            st.info("No sessions found for this user. Start a chat with the agent to create a session.")
    except Exception as e:
        st.error(f"Could not retrieve available sessions: {e}")

def handle_memories_section(agent: Agent, memory: Memory):
    """Handles the entire memories tab with subtabs for different memory types."""
    memories_tab1, memories_tab2, memories_tab3, memories_tab4 = st.tabs([

        "Session Storage",
        "Session Summaries",
        "Available Sessions"
    ])
    
    with memories_tab1:
        display_user_memories(memory)
    
    with memories_tab2:
        display_session_storage(agent)
    
    with memories_tab3:
        display_session_summary(agent, memory)
        
    with memories_tab4:
        display_available_sessions(agent)

def display_knowledge_base(lancedb_uri: str):
    """Connects to LanceDB URI, lists all tables, and displays their content."""
    st.header("Knowledge Base Content (LanceDB)")

    if not lancedb_uri:
        st.error("LanceDB URI not provided.")
        return

    if not os.path.exists(lancedb_uri):
        st.warning(f"LanceDB directory not found at: `{lancedb_uri}`")
        st.info("Please ensure the directory exists. Run `load_knowledge.py` if needed.")
        return

    try:
        db = lancedb.connect(lancedb_uri)
        table_names = db.table_names()

        if not table_names:
            st.info(f"No tables found in LanceDB directory: `{lancedb_uri}`")
            return

        st.success(f"Found {len(table_names)} table(s) in `{lancedb_uri}`")

        for table_name in table_names:
            with st.expander(f"Table: `{table_name}`", expanded=True):
                try:
                    with st.spinner(f"Fetching data from table: {table_name}..."):
                        table = db.open_table(table_name)
                        df = table.to_pandas()
                    
                    if not df.empty:
                        st.dataframe(df)
                        # Optionally show raw text in expanders
                        if 'text' in df.columns:
                            with st.expander("View Text Snippets", expanded=False):
                                for index, row in df.iterrows():
                                    st.text(f"Entry {index}:")
                                    st.code(row['text'], language=None)
                                    st.divider()
                    else:
                        st.info(f"Table '{table_name}' exists but appears to be empty.")

                except Exception as table_err:
                    st.error(f"Failed to read or display data from table '{table_name}': {table_err}")
                    st.code(traceback.format_exc())

    except Exception as e:
        st.error(f"Failed to connect to or list tables from LanceDB at '{lancedb_uri}': {e}")
        st.code(traceback.format_exc())

def display_todo_list():
    """Displays the TODO.md file as a formatted Streamlit component."""
    st.header("Project TODO List")
    
    try:
        # Read TODO.md file
        import os
        todo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "TODO.md")
        
        if os.path.exists(todo_path):
            with open(todo_path, "r") as f:
                todo_content = f.read()
                
            # Display the todo content
            st.markdown(todo_content)
            
            # Add a refresh button
            if st.button("🔄 Refresh TODO List"):
                st.rerun()
        else:
            st.error(f"TODO.md file not found at {todo_path}")
    except Exception as e:
        st.error(f"Error reading TODO.md: {e}")