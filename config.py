import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# YouTube API Configuration
try:
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
except:
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def initialize_session_state():
    """Initialize session state variables."""
    if "chat" not in st.session_state:
        st.session_state.chat = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "weak_topics" not in st.session_state:
        st.session_state.weak_topics = set()
    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = []
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    if "showing_quiz" not in st.session_state:
        st.session_state.showing_quiz = False
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "answered_questions" not in st.session_state:
        st.session_state.answered_questions = {} # Store answers and results
    if "pdf_analysis_result" not in st.session_state:
        st.session_state.pdf_analysis_result = None

    # Gamification additions
    if "total_questions_solved" not in st.session_state:
        st.session_state.total_questions_solved = 0
    if "total_correct_answers" not in st.session_state:
        st.session_state.total_correct_answers = 0
    if "topics_covered" not in st.session_state:
        st.session_state.topics_covered = set()
    if "current_streak" not in st.session_state:
        st.session_state.current_streak = 0
    if "last_quiz_date" not in st.session_state:
        st.session_state.last_quiz_date = None # To track consecutive days
    if "streak_history" not in st.session_state:
        st.session_state.streak_history = {} # {date: True/False if quiz completed on that day}
    if "user_name" not in st.session_state:
        st.session_state.user_name = "" # For personalization

    # New: For topic-specific performance tracking
    if "topic_performance" not in st.session_state:
        st.session_state.topic_performance = {} # {topic: {"total_solved": int, "correct_solved": int}}
    if "current_quiz_main_topic" not in st.session_state: # To store the topic of the currently active quiz
        st.session_state.current_quiz_main_topic = ""

    # New: For bookmarked questions
    if "bookmarked_questions" not in st.session_state:
        st.session_state.bookmarked_questions = [] # Store bookmarked questions