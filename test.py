import streamlit as st
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools

# Initialize agent
agent = Agent(tools=[DuckDuckGoTools()], show_tool_calls=True, markdown=True, stream=True)

# App title
st.title("France News Agent 🗞️")

# User input
query = st.text_input("Ask me something about France:", value="Whats happening in France?")

if st.button("Ask"):
    with st.status("Running agent...", expanded=True) as status:
        # Stream the agent response
        message_placeholder = st.empty()
        full_response = ""
        last_response = None

        for chunk in agent.run(query):
            if hasattr(chunk, "content") and chunk.content:
                full_response += chunk.content
                message_placeholder.markdown(full_response)
            last_response = chunk  # Keep the last chunk for metadata

        status.update(label="Tool calls complete", state="running")

        # Extract tool calls from last_response
        tool_calls = []
        if last_response and hasattr(last_response, "messages"):
            for msg in last_response.messages:
                if msg.role == "assistant" and msg.tool_calls:
                    tool_calls.extend(msg.tool_calls)

        if tool_calls:
            st.subheader("🔧 Tool Calls")
            for tool_call in tool_calls:
                tool_name = tool_call.get('function', {}).get('name', 'Unknown Tool')
                args = tool_call.get('function', {}).get('arguments', '{}')
                st.markdown(f"- **{tool_name}** → `{args}`")
        else:
            st.markdown("_No tool calls found._")

        status.update(label="Response ready!", state="complete")

    # Final response summary
    st.subheader("💬 Final Agent Response")
    st.markdown(full_response)
