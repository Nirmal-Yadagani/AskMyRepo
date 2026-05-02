"""Page 2: Indexing dashboard."""

import streamlit as st

from askmyrepo.ui.shared import render_sidebar, render_success, render_error, render_info

render_sidebar()

st.title("2. Indexing")

st.markdown("Clone and index a repository for querying.")

if not st.session_state.get("repo_source"):
    render_error("No repository configured. Go to Config page first.")
    st.stop()

source = st.session_state.repo_source

if "indexing_status" not in st.session_state:
    st.session_state.indexing_status = "idle"

col1, col2 = st.columns(2)
with col1:
    if st.button("Start Indexing", type="primary", use_container_width=True):
        st.session_state.indexing_status = "running"
        st.session_state.indexing_progress = 0
        st.session_state.indexing_total = 6
        st.session_state.indexing_message = ""

if st.session_state.indexing_status == "running":
    st.info("Indexing in progress... This may take a few minutes for large repos.")

    # Show progress bars for each phase
    phases = [
        ("Cloning", "repo_cloner"),
        ("Parsing", "tree_sitter_parser"),
        ("Chunking", "chunker"),
        ("Embedding", "ollama_embedder"),
        ("Storing", "chroma_store"),
        ("Complete", ""),
    ]

    current_phase = 0
    for i, (label, _) in enumerate(phases):
        if i < current_phase:
            st.success(f"✓ {label}")
        elif i == current_phase:
            st.info(f"→ {label}...")
        else:
            st.caption(f"○ {label}")

    # Actually run the indexer
    from askmyrepo.indexing.indexer import Indexer
    from askmyrepo.config import get_settings

    try:
        indexer = Indexer()
        result = indexer.index(source)

        st.session_state.indexing_status = result.status.value
        st.session_state.indexing_result = result

        if result.status.value == "complete":
            render_success(f"Indexed {result.total_chunks} chunks!")
        else:
            render_error(f"Indexing failed: {result.error_message}")
    except Exception as e:
        st.error(f"Indexing error: {e}")
        st.session_state.indexing_status = "failed"

elif st.session_state.indexing_status == "complete":
    result = st.session_state.get("indexing_result")
    if result:
        st.success(f"Indexed {result.total_chunks} chunks from {result.total_files} files ({result.total_nodes} AST nodes)")
        st.markdown(f"- **Files:** {result.total_files}")
        st.markdown(f"- **AST Nodes:** {result.total_nodes}")
        st.markdown(f"- **Chunks:** {result.total_chunks}")
        st.markdown(f"- **Status:** Complete")
    st.info("You can now ask questions about this repo in the Chat page.")

else:
    render_info("Enter a repo URL in Config and click 'Start Indexing' to begin.")
