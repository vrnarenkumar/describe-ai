"""
Streamlit Chat UI — Documentation Agent
========================================
A real LLM chat agent (Llama via Groq) greets the user, collects the
GitHub repo URL and target branch through natural conversation, then runs
the LangGraph documentation pipeline.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import logging
import os

import streamlit as st

from agent.chat import (
    DEFAULT_SESSION_STATE,
    STAGE_LABELS,
    S_AWAIT_PR,
    S_CHAT,
    S_CREATING_PR,
    S_DONE,
    S_ERROR,
    S_RUNNING,
    call_llm,
    clean_display_text,
    extract_pipeline_trigger,
    sync_cfg,
)

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Documentation Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.WARNING)


# ── Session-state initialisation ─────────────────────────────────────────────
def _init() -> None:
    for key, value in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init()


# ── Message helpers ───────────────────────────────────────────────────────────
def _bot(text: str) -> None:
    st.session_state.messages.append({"role": "assistant", "content": text})


def _user_msg(text: str) -> None:
    st.session_state.messages.append({"role": "user", "content": text})


# ── Initial greeting (LLM-generated, once per session) ───────────────────────
if not st.session_state["_greeted"] and st.session_state.stage == S_CHAT:
    with st.spinner("Connecting to Docs Agent…"):
        try:
            greeting = call_llm([])
            _bot(clean_display_text(greeting))
        except Exception:
            _bot(
                "👋 **Welcome to the Documentation Agent!**\n\n"
                "I'll clone your GitHub repo, analyse the code with Llama, "
                "write a `README.md`, and open a Pull Request.\n\n"
                "To get started — what's your **GitHub repository URL**?"
            )
    st.session_state["_greeted"] = True


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📚 Docs Agent")
    st.caption("LangGraph · LangChain · Llama via Groq")
    st.divider()

    st.subheader("🤖 Model (Free)")
    provider = st.radio(
        "Provider",
        options=["groq", "ollama"],
        format_func=lambda x: {
            "groq":   "🟢 Groq — free Llama API",
            "ollama": "💻 Ollama — local Llama",
        }[x],
        index=0,
        horizontal=True,
    )
    os.environ["MODEL_PROVIDER"] = provider

    if provider == "groq":
        groq_model = st.selectbox(
            "Llama model",
            [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "llama3-70b-8192",
                "gemma2-9b-it",
            ],
            help="llama-3.1-8b-instant recommended — highest free-tier token limit (30k TPM)",
        )
        os.environ["GROQ_MODEL"] = groq_model
    else:
        oll_url   = st.text_input("Ollama URL",  value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        oll_model = st.text_input("Model name",  value=os.getenv("OLLAMA_MODEL",    "llama3.2"))
        os.environ["OLLAMA_BASE_URL"] = oll_url
        os.environ["OLLAMA_MODEL"]    = oll_model
        st.info("💻 Run `ollama run llama3.2` locally first.")

    st.divider()
    st.info(STAGE_LABELS.get(st.session_state.stage, ""))

    if st.session_state.repo_url:
        st.caption(f"**Repo:** `{st.session_state.repo_url}`")
    if st.session_state.pr_url:
        st.success("PR created!")
        st.markdown(f"[🔗 Open Pull Request]({st.session_state.pr_url})")

    st.divider()
    if st.button(
        "🔄 Start Over",
        use_container_width=True,
        disabled=st.session_state.stage in (S_RUNNING, S_CREATING_PR),
    ):
        st.session_state.clear()
        st.rerun()


# ── Main header ───────────────────────────────────────────────────────────────
st.title("📚 Documentation Agent")
st.caption("Chat → repo analysed by Llama → README generated → PR opened. Powered by LangGraph.")
st.divider()


# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])


# ── README / Analysis panels (shown after pipeline completes) ─────────────────
if st.session_state.stage in (S_AWAIT_PR, S_CREATING_PR, S_DONE):
    if st.session_state.analysis:
        with st.expander("🔍 Codebase Analysis", expanded=False):
            st.markdown(st.session_state.analysis)
    if st.session_state.readme_content:
        with st.expander("📄 Generated README.md", expanded=True):
            tab_preview, tab_raw = st.tabs(["👁 Preview", "📋 Raw Markdown"])
            with tab_preview:
                st.markdown(st.session_state.readme_content)
            with tab_raw:
                st.code(st.session_state.readme_content, language="markdown")
            st.download_button(
                label="⬇️  Download README.md",
                data=st.session_state.readme_content,
                file_name="README.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ── Pipeline execution ────────────────────────────────────────────────────────
if st.session_state.stage == S_RUNNING:
    sync_cfg()
    from agent.nodes import analyze_content, read_repo, write_docs

    _state: dict = {
        "repo_url":      st.session_state.repo_url,
        "target_branch": st.session_state.target_branch,
        "repo_metadata": None,
        "file_tree":     None,
        "file_contents": None,
        "analysis":      None,
        "readme_content": None,
        "pr_url":        None,
        "messages":      [],
        "error":         None,
    }
    _ok = True

    with st.status("🚀 Running documentation pipeline…", expanded=True) as _status:
        st.write("📥 **Step 1 / 3** — Cloning & reading repository…")
        _state.update(read_repo(_state))
        if _state.get("error"):
            _status.update(label="❌ Failed at Step 1", state="error")
            _ok = False
        else:
            st.write(f"✅ Repository cloned — **{len(_state.get('file_contents') or [])} files** read")

        if _ok:
            st.write("🔍 **Step 2 / 3** — Analysing codebase with Llama…")
            _state.update(analyze_content(_state))
            if _state.get("error"):
                _status.update(label="❌ Failed at Step 2", state="error")
                _ok = False
            else:
                st.write("✅ Analysis complete")

        if _ok:
            st.write("✍️  **Step 3 / 3** — Generating README.md…")
            _state.update(write_docs(_state))
            if _state.get("error"):
                _status.update(label="❌ Failed at Step 3", state="error")
                _ok = False
            else:
                st.write(f"✅ README generated — **{len(_state.get('readme_content') or ''):,} chars**")
                _status.update(label="✅ Pipeline complete!", state="complete")

    if _ok:
        _meta = _state["repo_metadata"]
        st.session_state.update(
            {
                "repo_metadata":  _meta,
                "file_tree":      _state.get("file_tree"),
                "file_contents":  _state.get("file_contents"),
                "analysis":       _state.get("analysis"),
                "readme_content": _state.get("readme_content"),
                "stage":          S_AWAIT_PR,
            }
        )
        _bot(
            f"🎉 **Done! Docs generated for `{_meta['owner']}/{_meta['name']}`.**\n\n"
            f"| | |\n|---|---|\n"
            f"| Files analysed | **{len(_state.get('file_contents') or [])}** |\n"
            f"| README length | **{len(_state.get('readme_content') or ''):,} chars** |\n\n"
            "Preview and download the README above.\n\n"
            "**Would you like me to open a Pull Request with this README?**"
        )
    else:
        st.session_state.error = _state.get("error", "Unknown error")
        st.session_state.stage = S_ERROR
        _bot(
            f"❌ **Pipeline failed:**\n\n```\n{st.session_state.error}\n```\n\n"
            "Click **🔄 Start Over** to try again."
        )

    st.rerun()


# ── PR creation ───────────────────────────────────────────────────────────────
if st.session_state.stage == S_CREATING_PR:
    sync_cfg()
    from agent.nodes import create_pr

    _pr: dict = {
        "repo_url":      st.session_state.repo_url,
        "target_branch": st.session_state.target_branch,
        "repo_metadata": st.session_state.repo_metadata,
        "file_tree":     st.session_state.file_tree,
        "file_contents": st.session_state.file_contents,
        "analysis":      st.session_state.analysis,
        "readme_content": st.session_state.readme_content,
        "pr_url":        None,
        "messages":      [],
        "error":         None,
    }

    with st.status("🔀 Opening pull request…", expanded=True) as _prs:
        _pr.update(create_pr(_pr))
        if _pr.get("error"):
            _prs.update(label="❌ PR creation failed", state="error")
            st.session_state.error = _pr["error"]
            st.session_state.stage = S_ERROR
            _bot(f"❌ **PR creation failed:** {_pr['error']}")
        else:
            _prs.update(label="✅ Pull request opened!", state="complete")
            st.session_state.pr_url = _pr["pr_url"]
            st.session_state.stage  = S_DONE
            _bot(
                f"🚀 **Pull request created!**\n\n[🔗 Open Pull Request]({_pr['pr_url']})\n\n"
                "Please review it before merging. Click **🔄 Start Over** for another repo."
            )
    st.rerun()


# ── PR decision buttons ───────────────────────────────────────────────────────
if st.session_state.stage == S_AWAIT_PR:
    st.write("")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("🚀 Yes — create Pull Request", type="primary", use_container_width=True):
            _user_msg("Yes, please create the pull request.")
            st.session_state.stage = S_CREATING_PR
            st.rerun()
    with col_no:
        if st.button("⏭️  No — just download the README", use_container_width=True):
            _user_msg("No thanks, I'll just keep the README.")
            _bot(
                "No problem! Use the **⬇️ Download README.md** button above. "
                "Click **🔄 Start Over** for another repo."
            )
            st.session_state.stage = S_DONE
            st.rerun()


# ── Chat input (active only during S_CHAT) ───────────────────────────────────
if st.session_state.stage == S_CHAT:
    prompt = st.chat_input("Type your message…")
    if prompt:
        _user_msg(prompt.strip())

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                reply = call_llm(st.session_state.messages)

        trigger = extract_pipeline_trigger(reply)
        display = clean_display_text(reply)

        if display:
            _bot(display)

        if trigger:
            st.session_state.repo_url      = trigger.get("repo_url", "").strip()
            st.session_state.target_branch = trigger.get("branch", "").strip()
            branch_display = (
                f"`{st.session_state.target_branch}`"
                if st.session_state.target_branch
                else "the **default branch**"
            )
            _bot(
                f"Got it! Starting the documentation pipeline for "
                f"**`{st.session_state.repo_url}`** targeting {branch_display}…\n\n"
                "_This may take a minute or two._"
            )
            st.session_state.stage = S_RUNNING

        st.rerun()


# ── Terminal footer ───────────────────────────────────────────────────────────
if st.session_state.stage in (S_DONE, S_ERROR):
    st.info("Click **🔄 Start Over** in the sidebar to document another repository.")
