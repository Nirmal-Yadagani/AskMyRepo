"""Page 3: Chat interface."""

import streamlit as st

from askmyrepo.ui.shared import render_sidebar

render_sidebar()

st.title("3. Chat")

if "repo_path" not in st.session_state or not st.session_state.get("repo_path"):
    st.warning("No repo indexed yet. Go to Config → Indexing first.")
    st.stop()

# Chat message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_usage"):
            with st.expander("Tool calls used"):
                for tc in msg["tool_usage"]:
                    st.code(f"{tc['tool']}: {tc['args']}", language="json")
                    st.caption(tc.get("result_preview", ""))

# Input
if prompt := st.chat_input("Ask a question about the codebase..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Show typing indicator
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            from askmyrepo.agent.agent import AskMeAgent
            from pathlib import Path
            from askmyrepo.config import get_settings

            agent = AskMeAgent(Path(st.session_state.repo_path), get_settings())
            response = agent.ask(prompt)

            st.markdown(response["answer"])
            if response.get("tool_usage"):
                with st.expander(f"Used {len(response['tool_usage'])} tool(s)"):
                    for tc in response["tool_usage"]:
                        st.code(f"{tc['tool']}: {tc['args']}", language="json")
                        st.caption(tc.get("result_preview", "")[:200])

    st.session_state.messages.append({
        "role": "assistant",
        "content": response["answer"],
        "tool_usage": response.get("tool_usage", []),
    })

# Clear button
if st.session_state.messages:
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
