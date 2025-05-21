import streamlit as st
from config import initialize_session_state, YOUTUBE_API_KEY, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION
from chat_module import display_chat
from quiz_module import display_quiz_generator, display_quiz
from pdf_analyzer_module import display_pdf_analyzer
from profile_module import display_profile
import os
from googleapiclient.discovery import build

def main():
    """Main application function."""
    st.set_page_config(page_title="JEE Study Buddy", layout="wide")
    st.title("🚀 JEE Study Buddy")
    
    # Initialize YouTube API client
    if "youtube_client" not in st.session_state:
        st.session_state.youtube_client = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)

    initialize_session_state()

    # Personalization prompt if name is not set
    if not st.session_state.user_name:
        st.info("Welcome to your JEE Study Buddy! What should I call you?")
        user_input_name = st.text_input("Your Name:", key="initial_name_input")
        if st.button("Start My Journey"):
            if user_input_name:
                st.session_state.user_name = user_input_name
                st.success(f"Great, {user_input_name}! Let's get started.")
                st.rerun()
            else:
                st.warning("Please enter your name to begin.")
        st.stop() # Stop execution until name is set

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Chat", "Quiz Generator", "Test Results Analyzer", "Profile"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 Identified Weak Topics")
    if st.session_state.weak_topics:
        for topic in sorted(list(st.session_state.weak_topics)): 
            st.sidebar.write(f"- {topic}")
    else:
        st.sidebar.write("No weak topics identified yet. Chat with the buddy or analyze a test!")
    
    if st.sidebar.button("Clear Identified Weak Topics", key="clear_weak_topics"):
        st.session_state.weak_topics = set()
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("⚠️ Clear All App Data & Restart", key="clear_all_data"):
        keys_to_clear = list(st.session_state.keys())
        for key in keys_to_clear:
            del st.session_state[key]
        # Re-initialize all session state variables
        initialize_session_state()
        st.session_state.user_name = "" # Clear user name too
        st.success("All application data cleared! Restarting...")
        st.rerun()

    if page == "Chat":
        display_chat()
    elif page == "Quiz Generator":
        if st.session_state.showing_quiz:
            display_quiz()
        else:
            display_quiz_generator()
    elif page == "Test Results Analyzer":
        display_pdf_analyzer()
    elif page == "Profile":
        display_profile()

if __name__ == "__main__":
    main()