"""Page 1: Repository configuration."""

import streamlit as st

from askmyrepo.config import ModelProvider, Settings
from askmyrepo.ui.shared import render_sidebar, render_success, render_error, render_info

render_sidebar()

st.title("1. Repository Configuration")

st.markdown("### Ollama Settings")
col1, col2 = st.columns(2)
with col1:
    chat_url = st.text_input("Chat API URL", value=st.session_state.get("chat_base_url", "http://localhost:11434"))
    chat_model = st.text_input("Chat Model", value=st.session_state.get("chat_model", "qwen3.6"))
with col2:
    embed_url = st.text_input("Embedding API URL", value=st.session_state.get("embedding_base_url", "http://localhost:11434"))
    embed_model = st.text_input("Embedding Model", value=st.session_state.get("embedding_model", "nomic-embed-text"))

st.markdown("---")
st.markdown("### Repository Settings")

col1, col2 = st.columns([3, 1])
with col1:
    repo_source = st.text_input(
        "GitHub URL or local path",
        value=st.session_state.get("repo_source", ""),
        placeholder="https://github.com/username/repo or /path/to/local/repo",
    )
with col2:
    if st.button("Save Config", type="primary"):
        st.session_state.chat_base_url = chat_url
        st.session_state.chat_model = chat_model
        st.session_state.embedding_base_url = embed_url
        st.session_state.embedding_model = embed_model
        st.session_state.repo_source = repo_source
        st.session_state.config_saved = True
        render_success("Configuration saved!")

st.markdown("---")
st.markdown("### Available Tools")
st.info("Once configured, you'll have these agent tools:\n"
        "- `parse_code`: Get AST metadata for files\n"
        "- `read_file`: Read raw file content\n"
        "- `search_codebase`: Vector semantic search\n"
        "- `search_imports`: Find import statements\n"
        "- `find_class_hierarchy`: Class inheritance chain\n"
        "- `list_files`: Browse file structure")
