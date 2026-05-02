"""Shared layout helpers for the Streamlit app."""

import streamlit as st


def render_sidebar() -> None:
    """Render the left sidebar with repo info and navigation."""
    with st.sidebar:
        st.title("AskMe")
        st.markdown("Agentic RAG for GitHub repos")
        st.divider()

        if "repo_path" in st.session_state:
            st.success(f"Repo: {st.session_state.repo_path}")
        else:
            st.warning("No repo loaded. Go to Config page first.")
        st.divider()

        st.markdown("### Navigation")
        st.page_link("askme/ui/pages/1_repo_config.py", label="1. Config")
        st.page_link("askme/ui/pages/2_indexing.py", label="2. Indexing")
        st.page_link("askme/ui/pages/3_chat.py", label="3. Chat")
        st.divider()
        st.caption("Powered by Ollama + tree-sitter")


def render_error(message: str) -> None:
    st.error(message)


def render_success(message: str) -> None:
    st.success(message)


def render_info(message: str) -> None:
    st.info(message)


def render_progress_bar(label: str, progress: float, total: int) -> None:
    """Render a progress bar for the indexing pipeline."""
    percent = progress / total if total > 0 else 0
    st.progress(percent, text=f"{label}: {progress}/{total}")
