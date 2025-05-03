# Codebase TODO List

Based on the initial review, here are potential areas for improvement or investigation:

[ ]  **[Code Structure]** Investigate `handle_memories_section` in `app/ui.py`: This function seems defined but unused in `main.py`. Confirm if it's dead code or if the "Available Sessions" feature it contains is intended to be accessible.

[ ] **[Security]** Review API Key Handling: Storing the API key in Streamlit session state (`st.session_state.api_key`) might have security implications depending on deployment. Evaluate if relying solely on `.env` or a more secure secret management approach is better.

[ ] **[Error Handling]** Improve `handle_agent_response` Error Handling: Catch more specific exceptions from the `agno` library if available, instead of relying solely on `except Exception`. Provide more context in error messages.

[ ] **[UI Robustness]** Revisit JavaScript Scroll Hack: The JS snippet for auto-scrolling in `main.py` might be brittle. Explore more robust Streamlit-native ways to achieve this if possible, or test thoroughly across browsers/versions.

[ ] **[Code Clarity]** Analyze `st.rerun()` Usage: Ensure the frequent use of `st.rerun()` is necessary and doesn't introduce unintended side effects or performance issues.

[ ] **[Debugging]** Refine `extract_run_data` in `app/ui.py`: While useful for debugging, the multiple fallback methods (`vars`, `__dict__`, `dir`) could potentially mask errors or be inefficient. Consider relying on a more defined structure or serialization from `agno` if possible.

[ ] **[User Experience]** Automate Memory/History Refresh: Instead of manual "Refresh" buttons, consider automatically updating the memory/history tabs after relevant agent actions.

[ ] **[Best Practices]** Use UUID for Session IDs: Replace the custom timestamp/random number generation for `session_id` in `app/main.py` with standard `uuid.uuid4()` for guaranteed uniqueness.

[ ] **[Code Quality]** Ensure Consistent Type Hinting: Review the codebase for consistent and comprehensive type hinting.

[ ] **[Styling]** Verify CSS Definition: Confirm where the CSS classes for badges (e.g., `blue-badge`) used in `app/ui.py` are defined and ensure they are loaded correctly.


[ ] **[Bug/UX - Investigate]** Tool Badge Not Showing: Despite tools being called and fixes attempted, the tool badge (`:blue-badge[Tools: ...]`) is not appearing in `display_chat_history`. Investigate why `metadata['tool_calls']` remains empty after `handle_agent_response` finishes processing the stream, even when tools are confirmed to run. 