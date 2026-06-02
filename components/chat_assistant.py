import streamlit as st
from services.groq_chain import build_chat_chain


def chat_assistant(user_profile: dict, current_recipes: list[dict]):
    st.markdown("---")
    st.subheader("🤖 Chat Assistant")
    st.caption("Ask me anything about nutrition, cooking, or your meal plan!")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_fn = build_chat_chain(user_profile, current_recipes)

    chat_container = st.container(height=400)
    with chat_container:
        if not st.session_state.chat_history:
            with st.chat_message("assistant"):
                st.write(
                    f"Hi! I'm your nutrition assistant. I know your goal is to "
                    f"**{user_profile.get('goal', 'eat well')}**. "
                    "Ask me about any recipe in your plan, substitutions, nutrition, or meal ideas!"
                )
        for turn in st.session_state.chat_history:
            with st.chat_message(turn["role"]):
                st.write(turn["content"])

    user_input = st.chat_input("Ask about nutrition, recipes, substitutions…")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("Thinking…"):
            reply = chat_fn(st.session_state.chat_history[:-1], user_input)

        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("Clear chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()
