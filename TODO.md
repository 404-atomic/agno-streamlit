

### Security & Error Handling

- [ ] **Security**: Review API Key Handling - Storing the API key in Streamlit session state (`st.session_state.api_key`) might have security implications. Evaluate if relying solely on `.env` or a more secure secret management approach is better.

- [ ] **Error Handling**: Improve `handle_agent_response` Error Handling - Catch more specific exceptions from the `agno` library instead of relying solely on `except Exception`. Provide more context in error messages.

### UI Improvements

- [ ] **UI Robustness**: Replace JavaScript Scroll Hack - The JS snippet for auto-scrolling in `main.py` might be brittle. As of Streamlit 1.41.0, use Streamlit's built-in container with height parameter for scrollable containers instead.

- [ ] **Debugging**: Refine `extract_run_data` in `app/ui.py` - While useful for debugging, the multiple fallback methods (`vars`, `__dict__`, `dir`) could potentially mask errors or be inefficient. Consider relying on a more defined structure or serialization from `agno` if possible.

- [ ] **User Experience**: Automate Memory/History Refresh - Instead of manual "Refresh" buttons, use Streamlit's fragments (GA as of 1.37.0) to automatically update the memory/history tabs after relevant agent actions.

### Code Quality

- [ ] **Best Practices**: Use UUID for Session IDs - Replace the custom timestamp/random number generation for `session_id` in `app/main.py` with standard `uuid.uuid4()` for guaranteed uniqueness.

- [ ] **Code Quality**: Ensure Consistent Type Hinting - Review the codebase for comprehensive type hinting, adding Context type hints from Streamlit 1.45.0.

- [ ] **Styling**: Verify CSS Definition - Confirm where the CSS classes for badges (e.g., `blue-badge`, `red-badge`) used in `app/ui.py` are defined and ensure they are loaded correctly.

## Enhancement Opportunities

### New Features

- [ ] **Feature**: Add User Information Access - Implement Streamlit's new `st.user` object (GA in 1.45.0) to access user information for personalization.

- [ ] **Feature**: Implement st.dialog for Modal Interactions - Replace custom overlays with Streamlit's dialog component (GA in 1.37.0) for better user experience.

### UX & Performance Improvements

- [ ] **UX Improvement**: Add Chat Streaming Support - Implement `st.write_stream` (introduced in 1.31.0) to handle streaming responses from LLMs for a more dynamic chat experience.

- [ ] **UI Navigation**: Add Custom Navigation - Use `st.navigation` and `st.page_link` (GA in 1.36.0) to create custom navigation interfaces beyond the default sidebar.

- [ ] **Performance**: Implement Fragment-Based Updates - Use `st.fragment` (GA in 1.37.0) to create more interactive UI components that update independently.

### Integration & Interoperability

- [ ] **Integration**: Migrate to Agno Framework - Consider migrating from the legacy Phidata approach to the newer Agno framework for better performance and features.

- [ ] **Interoperability**: Add Context Headers and Cookies - Use `st.context` (expanded in 1.45.0) to access URL, IP address, and cookie information for enhanced functionality.

- [ ] **Code Cleanup**: Refine Debug Logging - Implement structured logging with different verbosity levels that can be toggled through config instead of commenting/uncommenting print statements.