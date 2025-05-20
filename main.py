import streamlit as st
import google.generativeai as genai
import json
import os
import fitz 
from typing import Set, List, Dict, Any
from dotenv import load_dotenv
from googlesearch import search
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

load_dotenv()
# Configuration
API_KEY = os.environ.get("GEMINI_API_KEY", "your_api_key_here")
genai.configure(api_key=API_KEY)

# Initialize session state variables
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


def initialize_chat():
    """Initialize the Gemini chat model."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    chat = model.start_chat(history=[])
    return chat

def process_message(message: str) -> Set[str]:
    """Process a user message to identify weak topics."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    From the following student message, identify any weak topics or subjects the student might be struggling with.
    Try to think from the students prospective that if he wrote the message then which topic he might be wanting to know more about.
    If there are weak topics, respond with the list of topics separated by a single space (e.g., "calculus thermodynamics optics").
    If no weak topics are found, respond with "none".
    
    Message: "{message}"
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2}
        )
        
        text = response.text.strip().lower()
        if text == "none" or not text:
            return set()
        
        new_topics = set(filter(None, text.split())) # Filter out empty strings
        return new_topics
    
    except Exception as e:
        st.error(f"Error processing message for weak topics: {str(e)}")
        return set()

def get_chatbot_response(message: str) -> str:
    """Get a response from the chatbot based on the user's message."""
    if st.session_state.chat is None:
        st.session_state.chat = initialize_chat()
    
    prompt = f"""
    You are a student support chatbot. The user is preparing for the Joint Entrance Exam (JEE).
    Please provide an appropriate response to their message: "{message}"
    
    Format your response in a clear, helpful manner.
    Keep information short and to the point.
    Highlight important information when needed.
    Keep the overall response brief and easy to read.
    """
    
    try:
        response = st.session_state.chat.send_message(prompt)
        
        new_topics = process_message(message)
        st.session_state.weak_topics.update(new_topics)
        
        return response.text
    except Exception as e:
        st.error(f"Error generating chatbot response: {str(e)}")
        return "Sorry, something went wrong. Please try again later."

def generate_quiz(topic: str, difficulty: str, num_questions: int) -> List[Dict[str, Any]]:
    """Generate a quiz based on the specified topic, difficulty, number of questions, and weak topics."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    weak_topics_str = ", ".join(st.session_state.weak_topics) if st.session_state.weak_topics else "None identified"
    
    prompt = f"""
    Generate a quiz on the topic "{topic}" for a student who is preparing for Joint Entrance Exam (JEE).
    The desired difficulty level is "{difficulty}".
    The quiz should have exactly {num_questions} single choice questions.
    Pick the questions from existing previous year questions (PYQs) available for JEE Exam when possible.
    
    For each question, provide 4 answer choices, the correct answer (as a 0-indexed integer), and a detailed explanation.
    
    
    ❗ Important formatting rules:
    1. Use plain text with Unicode superscripts/subscripts (e.g. n², 2ⁿ, H₂O).  
    2. Do **not** use any HTML tags (`<sup>`, `<sub>`) or LaTeX.  
    
    The explanation should be structured as an object with the following fields:
    "detailed_steps": "Explain the solution in a step-by-step manner, as a JEE teacher would. Break down the problem, mention key formulas or concepts, and guide the student through the solution process. Use markdown for formatting, such as bullet points for steps, bold text for important terms or formulas, and ensure clear separation between steps for readability. Be thorough.",
    "youtube_link": "A relevant YouTube video link explaining the Problem itself. If no video is found, provide null or an empty string."

    Format the response as a JSON array of objects, where each object represents a question and has the following structure:
    {{
      "question": "The question text",
      "answers": ["Answer A", "Answer B", "Answer C", "Answer D"],
      "correctAnswer": 0, // 0-indexed
      "explanation": {{
          "detailed_steps": "Detailed step-by-step explanation using markdown...",
          "youtube_link": "URL or null or empty string"
      }}
    }}
    
    Here are some weak topics the student has mentioned and needs more attention:
    {weak_topics_str}

    Focus more on these weak topics if they are related to {topic}.
    Ensure all questions are appropriate for JEE level and the specified difficulty.
    Return ONLY valid JSON with no additional text or markdown formatting.
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3} 
        )
        
        response_text = response.text
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
            
        json_start = response_text.find("[")
        json_end = response_text.rfind("]") + 1
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            questions = json.loads(json_text)
            return questions
        else:
            st.error(f"Failed to parse quiz data. Raw response: {response_text}")
            return []
            
    except json.JSONDecodeError as je:
        st.error(f"JSON Decode Error while generating quiz: {str(je)}. Raw response: {response_text}")
        return []
    except Exception as e:
        st.error(f"Error generating quiz: {str(e)}. Raw response: {response_text}")
        return []

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file."""
    try:
        text = ""
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

@st.cache_data(ttl=3600) # Cache the search results for an hour to reduce repeated calls
def get_solution_link(jee_question, num_results=10):
    """
    Searches for a textual solution link for a given JEE question on specific educational sites.
    """
    query = f"{jee_question} JEE solution site:byjus.com OR site:unacademy.com OR site:toppr.com OR site:vedantu.com OR site:mathongo.com"
    
    try:
        for url in search(query, num_results=num_results):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                response = requests.get(url, headers=headers, timeout=7) # Increased timeout slightly
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    if any(kw in soup.get_text().lower() for kw in ["solution", "answer", "explanation", "jee"]):
                        return url
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.RequestException as req_e:
                continue
            except Exception as e:
                continue
    except Exception as google_e:
        st.warning(f"Could not perform web search for solution: {google_e}. This might be due to rate limits or network issues with the `googlesearch` library.")

    return None # Return None if no suitable link is found


def analyze_test_results(text):
    """Analyze PDF test results to identify questions, student answers, correct answers, and determine weak topics based on incorrect answers."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are analyzing a student's test results for JEE preparation. The PDF content might contain questions, 
    student's answers, and correct answers. The typical format is:
    
    ->question
    ->answer by student
    ->correct answer
    
    However, the format might vary. Please be flexible in parsing.
    Here is the extracted content from the test result:
    ---
    {text}
    ---
    
    Please analyze and respond with the following JSON structure:
    {{
      "weak_topics": ["topic1 based on incorrect answers", "topic2", ...],
      "analysis": {{
        "total_questions": "number (infer if possible, otherwise state 'not determinable')",
        "correct_answers": "number (infer if possible, otherwise state 'not determinable')",
        "incorrect_answers": "number (infer if possible, otherwise state 'not determinable')",
        "accuracy_percentage": "number (calculate if possible, otherwise 'not determinable')"
      }},
      "question_analysis": [
        {{
          "question": "Question text (or a summary if too long)",
          "student_answer": "Student's answer",
          "correct_answer": "Correct answer",
          "is_correct": boolean,
          "topic": "Related topic (e.g., Kinematics, Thermodynamics, P-block elements)",
          "explanation": "Brief explanation of why the answer is correct/incorrect and what concept the student needs to focus on. If the answer is incorrect, identify the specific sub-topic or concept."
        }}
        // ... more questions
      ],
      "summary": "Brief overall analysis of student performance and recommendations. Highlight areas for improvement and suggest actions."
    }}
    
    Infer the topics from the questions themselves.
    If the number of questions, correct, or incorrect answers cannot be reliably determined from the text, use "not determinable".
    Return ONLY valid JSON with no additional text or markdown formatting.
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2}
        )
        response_text = response.text
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            analysis_result = json.loads(json_text)
            
            if "weak_topics" in analysis_result and isinstance(analysis_result["weak_topics"], list):
                st.session_state.weak_topics.update(topic for topic in analysis_result["weak_topics"] if isinstance(topic, str))
                
            return analysis_result
        else:
            st.error(f"Failed to parse analysis data from LLM. Raw response: {response_text}")
            return None
            
    except json.JSONDecodeError as je:
        st.error(f"JSON Decode Error analyzing test results: {str(je)}. Raw response: {response_text}")
        return None
    except Exception as e:
        st.error(f"Error analyzing test results: {str(e)}. Raw response: {response_text}")
        return None

def display_chat():
    """Display the chat interface."""
    st.subheader("💬 Chat with your Study Buddy")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"]) # Use markdown for chat display too
    
    user_message = st.chat_input("Type your message here (e.g., 'I'm struggling with optics')...")
    
    if user_message:
        st.session_state.chat_history.append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                ai_response = get_chatbot_response(user_message)
                st.markdown(ai_response) # Display AI response using markdown
        
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.rerun() 

def display_quiz_generator():
    """Display the quiz generator interface."""
    st.subheader("📝 Generate a Custom Quiz")
    
    if st.session_state.weak_topics:
        st.info(f"**Identified weak topics to focus on:** {', '.join(st.session_state.weak_topics)}")
    else:
        st.write("No weak topics identified yet. Chat more or upload test results to help us tailor your quiz.")
    
    with st.form("quiz_form"):
        topic = st.text_input("Enter the quiz topic (e.g., 'Thermodynamics', 'Organic Chemistry Nomenclature'):", key="quiz_topic_input")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox(
                "Select difficulty:",
                ("JEE Mains", "JEE Advanced"),
                index=1, 
                key="quiz_difficulty_select"
            )
        with col2:
            num_questions = st.number_input(
                "Number of questions:",
                min_value=1,
                max_value=20, 
                value=1,      
                step=1,
                key="quiz_num_questions_input"
            )
            
        submit_quiz = st.form_submit_button("🚀 Generate Quiz")
        
        if submit_quiz and topic:
            with st.spinner(f"Generating {num_questions} {difficulty} questions on {topic}... This might take a moment."):
                st.session_state.quiz_questions = generate_quiz(topic, difficulty, num_questions)
            
            if st.session_state.quiz_questions:
                st.session_state.showing_quiz = True
                st.session_state.current_question = 0
                st.session_state.score = 0
                st.session_state.answered_questions = {} 
                # Add topic to topics covered
                st.session_state.topics_covered.add(topic)
                # Store the main topic of the quiz
                st.session_state.current_quiz_main_topic = topic
                st.success("Quiz generated successfully! Let's begin.")
                st.rerun()
            else:
                st.error("Could not generate quiz. Please try a different topic or refine your request.")
        elif submit_quiz and not topic:
            st.warning("Please enter a topic for the quiz.")


def display_quiz():
    """Display the quiz interface."""
    if not st.session_state.quiz_questions:
        st.warning("No quiz questions available. Please generate a quiz first.")
        if st.button("⬅️ Back to Quiz Generator"):
            st.session_state.showing_quiz = False
            st.rerun()
        return

    questions = st.session_state.quiz_questions
    current_q_idx = st.session_state.current_question

    if current_q_idx >= len(questions):
        st.balloons()
        st.success(f"🎉 Quiz Completed! Your score: {st.session_state.score}/{len(questions)} 🎉")
        
        # Update streak history for today
        today = datetime.now().date()
        st.session_state.streak_history[today.isoformat()] = True

        # Calculate streak
        if st.session_state.last_quiz_date:
            # Check if today is the day after the last quiz date
            if today == st.session_state.last_quiz_date + timedelta(days=1):
                st.session_state.current_streak += 1
            # Check if it's the same day (don't break streak if multiple quizzes today)
            elif today == st.session_state.last_quiz_date:
                pass # Streak remains the same, already logged for today
            else:
                st.session_state.current_streak = 1 # Reset if not consecutive
        else:
            st.session_state.current_streak = 1 # First quiz completed

        st.session_state.last_quiz_date = today

        st.write("### Review Your Answers:")
        for i, q_data in enumerate(questions):
            user_answer_idx = st.session_state.answered_questions.get(i, {}).get("selected_idx")
            is_correct = st.session_state.answered_questions.get(i, {}).get("is_correct", False)
            
            st.markdown(f"--- \n**Question {i+1}:**")
            st.markdown(q_data['question']) # Display question using markdown
            if user_answer_idx is not None:
                st.write(f"Your answer: {q_data['answers'][user_answer_idx]} ({'Correct' if is_correct else 'Incorrect'})")
            else:
                st.write("You did not answer this question.")
            st.write(f"Correct answer: {q_data['answers'][q_data['correctAnswer']]}")

            # ✅ This is where get_solution_link is always called for textual solutions
            with st.spinner("Searching for solution..."):
                txt_link = get_solution_link(q_data['question'])

            with st.expander("View Detailed Explanation"):
                explanation_obj = q_data.get("explanation", {})
                if isinstance(explanation_obj, dict):
                    detailed_steps = explanation_obj.get('detailed_steps', 'Not provided.')
                    st.markdown(f"**Teacher's Explanation:**\n{detailed_steps}") # Use markdown for steps

                    yt_link = explanation_obj.get("youtube_link")
                    if yt_link and yt_link.strip().lower() not in ["", "null"]:
                        st.markdown(f"[📺 Watch on YouTube]({yt_link})")
                    else:
                        st.info("No YouTube video link provided by the AI.")
                    
                    if txt_link:
                        st.markdown(f"[📖 View Textual Solution]({txt_link})")
                    else:
                        st.info("Could not find a textual solution link online for this question.")
                else: 
                    st.markdown(f"**Explanation:**\n{explanation_obj}")


        if st.button("Start New Quiz", key="new_quiz_button"):
            st.session_state.showing_quiz = False
            st.session_state.quiz_questions = []
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.session_state.answered_questions = {}
            st.rerun()
        return

    question = questions[current_q_idx]
    
    st.subheader(f"Question {current_q_idx + 1} of {len(questions)}")
    st.markdown(f"**{question['question']}**") # Display question using markdown

    if current_q_idx in st.session_state.answered_questions:
        answer_info = st.session_state.answered_questions[current_q_idx]
        
        st.radio(
            "Your answer was:",
            question["answers"],
            index=answer_info["selected_idx"],
            disabled=True, 
            key=f"q_{current_q_idx}_answered"
        )

        if answer_info["is_correct"]:
            st.success("You answered: Correct! 🎉")
        else:
            st.error(f"You answered: Incorrect. Correct answer: {question['answers'][question['correctAnswer']]}")
        
        # ✅ This is where get_solution_link is always called for textual solutions
        with st.spinner("Searching for textual solution..."):
            txt_link = get_solution_link(question['question'])

        explanation_obj = question.get("explanation", {})
        if isinstance(explanation_obj, dict):
            detailed_steps = explanation_obj.get('detailed_steps', 'Not provided.')
            # Using st.info for the main explanation block can give it a distinct look
            st.info(f"**Teacher's Explanation:**\n{detailed_steps}") # Keep st.info for main block, markdown renders inside

            yt_link = explanation_obj.get("youtube_link")
            if yt_link and yt_link.strip().lower() not in ["", "null"]:
                st.markdown(f"[📺 Watch on YouTube]({yt_link})")
            else:
                st.info("No YouTube video link provided by the AI.")
            
            if txt_link:
                st.markdown(f"[📖 View Textual Solution]({txt_link})")
            else:
                st.info("Could not find a textual solution link online for this question.")

        else: 
             st.info(f"**Explanation:**\n{explanation_obj}")
        
        if st.button("Next Question", key=f"next_q_{current_q_idx}"):
            st.session_state.current_question += 1
            st.rerun()
    else:
        options = question["answers"]
        selected_option = st.radio(
            "Select your answer:",
            options,
            key=f"q_{current_q_idx}_options"
        )

        if st.button("Submit Answer", key=f"submit_q_{current_q_idx}"):
            selected_idx = options.index(selected_option)
            is_correct = (selected_idx == question["correctAnswer"])
            
            st.session_state.answered_questions[current_q_idx] = {
                "selected_idx": selected_idx,
                "is_correct": is_correct
            }

            st.session_state.total_questions_solved += 1
            if is_correct:
                st.session_state.score += 1
                st.session_state.total_correct_answers += 1

            # Update topic-specific performance from quiz
            quiz_main_topic = st.session_state.get("current_quiz_main_topic", "General") 
            if quiz_main_topic not in st.session_state.topic_performance:
                st.session_state.topic_performance[quiz_main_topic] = {"total_solved": 0, "correct_solved": 0}
            
            st.session_state.topic_performance[quiz_main_topic]["total_solved"] += 1
            if is_correct:
                st.session_state.topic_performance[quiz_main_topic]["correct_solved"] += 1

            st.rerun() 

def display_pdf_analyzer():
    """Display the PDF test results analyzer interface."""
    st.subheader("📄 Analyze Test Results from PDF")
    
    uploaded_file = st.file_uploader("Upload your test result (PDF format expected by the prompt)", type=["pdf"])
    
    if uploaded_file:
        if st.button("Analyze Test Results", key="analyze_pdf_button"):
            with st.spinner("Extracting text and analyzing test results... This may take some time."):
                extracted_text = extract_text_from_pdf(uploaded_file)
                if not extracted_text:
                    st.error("Could not extract text from the PDF. Please ensure it's a text-based PDF and not an image.")
                else:
                    analysis_result = analyze_test_results(extracted_text)
                    if analysis_result:
                        st.session_state.pdf_analysis_result = analysis_result
                        
                        # Update gamification data from PDF analysis
                        if analysis_result.get("analysis", {}).get("total_questions") != "not determinable":
                            st.session_state.total_questions_solved += analysis_result["analysis"]["total_questions"]
                        if analysis_result.get("analysis", {}).get("correct_answers") != "not determinable":
                            st.session_state.total_correct_answers += analysis_result["analysis"]["correct_answers"]
                        
                        # Update topic-specific performance from PDF analysis
                        question_analysis_list = analysis_result.get("question_analysis", [])
                        for q_analysis in question_analysis_list:
                            topic = q_analysis.get("topic")
                            is_correct = q_analysis.get("is_correct")

                            if topic and isinstance(topic, str): 
                                if topic not in st.session_state.topic_performance:
                                    st.session_state.topic_performance[topic] = {"total_solved": 0, "correct_solved": 0}
                                
                                st.session_state.topic_performance[topic]["total_solved"] += 1
                                if is_correct:
                                    st.session_state.topic_performance[topic]["correct_solved"] += 1

                        if analysis_result.get("weak_topics"):
                            st.session_state.topics_covered.update(analysis_result["weak_topics"])


                        st.success("Analysis completed successfully!")
                        st.rerun() 
                    else:
                        st.error("Failed to analyze the test results. The content might not be in the expected format, or an API error occurred.")
    
    if st.session_state.pdf_analysis_result:
        result = st.session_state.pdf_analysis_result
        
        st.markdown("### 📊 Test Analysis Summary")
        analysis_stats = result.get("analysis", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Questions", analysis_stats.get("total_questions", "N/A"))
        with col2:
            st.metric("Correct Answers", analysis_stats.get("correct_answers", "N/A"))
        with col3:
            st.metric("Incorrect Answers", analysis_stats.get("incorrect_answers", "N/A"))
        with col4:
            accuracy = analysis_stats.get('accuracy_percentage', "N/A")
            st.metric("Accuracy", f"{accuracy}%" if isinstance(accuracy, (int, float)) else "N/A")
            
        st.markdown("### 🔍 Identified Weak Topics (from PDF)")
        weak_topics_from_pdf = result.get("weak_topics", [])
        if weak_topics_from_pdf:
            for topic in weak_topics_from_pdf:
                st.write(f"- {topic}")
        else:
            st.write("No specific weak topics identified from this PDF, or unable to determine.")
            
        st.markdown("### 📝 Performance Summary & Recommendations")
        st.markdown(result.get("summary", "No summary provided.")) # Use markdown
            
        with st.expander("Detailed Question Analysis (from PDF)"):
            question_analysis_list = result.get("question_analysis", [])
            if question_analysis_list:
                for i, q_analysis in enumerate(question_analysis_list):
                    status = "✅ Correct" if q_analysis.get("is_correct") else "❌ Incorrect"
                    st.markdown(f"**Question {i+1}**: {status}")
                    st.markdown(f"**Q**: {q_analysis.get('question', 'N/A')}") # Use markdown
                    st.markdown(f"**Your Answer**: {q_analysis.get('student_answer', 'N/A')}") # Use markdown
                    st.markdown(f"**Correct Answer**: {q_analysis.get('correct_answer', 'N/A')}")# Use markdown
                    st.markdown(f"**Topic**: {q_analysis.get('topic', 'N/A')}")# Use markdown
                    st.markdown(f"**Explanation/Focus Area**: {q_analysis.get('explanation', 'N/A')}")# Use markdown
                    st.markdown("---")
            else:
                st.write("No detailed question analysis available or could not be parsed.")

def display_profile():
    """Display the user profile with gamification stats."""
    st.subheader("👤 Your Study Profile")

    # Personalization greeting
    if st.session_state.user_name:
        st.write(f"### Hello, {st.session_state.user_name}! 👋")
    else:
        st.write("### Welcome to your Study Profile! 👋")
        with st.form("name_form"):
            user_input_name = st.text_input("What's your name?", key="name_input")
            if st.form_submit_button("Set Name"):
                if user_input_name:
                    st.session_state.user_name = user_input_name
                    st.success(f"Name set to {user_input_name}!")
                    st.rerun()
                else:
                    st.warning("Please enter a name.")
        st.markdown("---") # Add a separator if the name input is shown

    total_q_solved = st.session_state.total_questions_solved
    total_corr_ans = st.session_state.total_correct_answers
    accuracy = (total_corr_ans / total_q_solved * 100) if total_q_solved > 0 else 0

    st.markdown("---")
    st.markdown("### 📈 Overall Performance")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Questions Solved", total_q_solved)
    with col2:
        st.metric("Accuracy", f"{accuracy:.2f}%")
    with col3:
        st.metric("Current Streak", f"{st.session_state.current_streak} days 🔥")

    st.markdown("---")
    st.markdown("### 📚 Topics Covered and Performance")
    if st.session_state.topics_covered:
        # Get a sorted list of topics to display consistently
        topics_list = sorted(list(st.session_state.topics_covered))
        
        # Start a container for the tags to allow for horizontal wrapping
        st.markdown('<div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
        
        for topic in topics_list:
            performance = st.session_state.topic_performance.get(topic, {"total_solved": 0, "correct_solved": 0})
            total = performance["total_solved"]
            correct = performance["correct_solved"]
            
            percentage = (correct / total * 100) if total > 0 else 0

            color = "var(--text-color)" # Default for no questions solved, adapting to theme
            if total > 0:
                if percentage >= 75: # Green for great accuracy
                    color = "green"
                elif percentage >= 50: # Orange for medium accuracy (better visibility)
                    color = "orange" 
                else: # Red for bad accuracy
                    color = "red"
            
            # HTML for the compact tag
            tag_html = f"""
            <div style="
                background-color: var(--secondary-background-color); /* Matches Streamlit's secondary background */
                border-radius: 20px; /* Rounded corners like a button/tag */
                padding: 8px 15px; /* Padding inside the tag */
                display: flex;
                align-items: center; /* Vertically center content */
                font-size: 0.9em;
                color: var(--text-color);
                box-shadow: 1px 1px 3px rgba(0,0,0,0.2); /* Subtle shadow */
                min-width: 120px; /* Ensure a minimum width */
                justify-content: center; /* Center content horizontally if min-width is larger */
                margin-right: 10px; /* Spacing between tags */
                margin-bottom: 10px; /* Spacing for wrapping */
            ">
                <div style="
                    width: 12px; 
                    height: 12px; 
                    border-radius: 50%; 
                    background-color: {color}; 
                    display: inline-block; 
                    vertical-align: middle;
                    margin-right: 8px; /* Space between circle and text */
                "></div>
                <strong>{topic}</strong>: {percentage:.1f}%
            </div>
            """
            st.markdown(tag_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True) # Close the container div

    else:
        st.write("Start solving quizzes or analyzing tests to see topics you've covered!")


    st.markdown("---")
    st.markdown("### 🔥 Quiz Streak Chart")
    st.write("🟢: Quiz completed | ⚪: No quiz")
    
    # Generate data for the streak chart (similar to GitHub's contribution graph)
    today = datetime.now().date()
    
    # Get dates for the last 365 days (a year's worth, similar to GitHub)
    num_days = 90 # Or 90 for a quarter, etc.
    dates_to_display = []
    for i in range(num_days):
        dates_to_display.append(today - timedelta(days=num_days - 1 - i))

    # Determine the number of columns (weeks) for the chart
    # A standard GitHub chart has 7 rows (days of the week)
    
    # We need to arrange `num_days` into a grid.
    # Start with the day of the week for the first date to align columns.
    first_date_in_chart = dates_to_display[0]
    first_day_of_week = first_date_in_chart.weekday() # Monday is 0, Sunday is 6

    # Prepare the grid. 7 rows for days of the week.
    # Fill in leading empty cells if the first day isn't a Monday in the chart's first column.
    chart_grid = [[] for _ in range(7)] # 7 lists for 7 days of the week (rows)

    # Add placeholders for days before the first day of the week for the first date
    for i in range(7):
        if i < first_day_of_week:
            chart_grid[i].append(" ") # Empty cell for alignment
        else:
            break # Stop filling placeholders once we hit the starting day

    for date in dates_to_display:
        day_of_week = date.weekday() # 0=Monday, 6=Sunday
        date_str = date.isoformat()
        
        symbol = "🟢" if st.session_state.streak_history.get(date_str, False) else "⚪"
        chart_grid[day_of_week].append(symbol)

    # Pad the last week's rows if they don't end on a Sunday
    max_len = max(len(row) for row in chart_grid)
    for i in range(7):
        while len(chart_grid[i]) < max_len:
            chart_grid[i].append(" ") # Pad with spaces

    # Render the chart using columns for weeks
    st.markdown("---")
    st.markdown("#### Contributions in last year")
    
    # Create a single row for the weekday labels
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Calculate number of weeks (columns)
    num_weeks = max_len
    
    # Create columns to simulate the GitHub graph
    # Add an extra column at the beginning for weekday labels
    cols = st.columns([0.5] + [1] * num_weeks) 
    
    with cols[0]: # First column for weekday labels
        st.markdown("<br>", unsafe_allow_html=True) # Spacer
        for label in weekday_labels:
            st.markdown(f"<div style='height: 40px; display: flex; align-items: center;'>{label}</div>", unsafe_allow_html=True)


    for week_idx in range(num_weeks):
        with cols[week_idx + 1]: # Shift by 1 because the first column is for labels
            # Optional: Add month label for first day of month in this column
            # This is complex to do accurately for all weeks and months
            # For simplicity, we'll omit explicit month labels for now.
            st.write(" ") # Placeholder for alignment or month

            for day_idx in range(7):
                if week_idx < len(chart_grid[day_idx]): # Ensure index is valid
                    st.markdown(f"<div style='font-size: 1.5em; text-align: center; margin: 0px;'>{chart_grid[day_idx][week_idx]}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='font-size: 1.5em; text-align: center; margin: 0px;'> </div>", unsafe_allow_html=True)

    st.markdown("---")
    st.write(f"Your longest streak: **{st.session_state.current_streak} days** (Note: this is the *current* streak, not the historical longest)")


def main():
    """Main application function."""
    st.set_page_config(page_title="JEE Study Buddy", layout="wide")
    st.title("🚀 JEE Study Buddy")
    
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
        # Re-initialize essential keys if needed, or let them be created on demand
        st.session_state.chat = None
        st.session_state.chat_history = []
        st.session_state.weak_topics = set()
        st.session_state.quiz_questions = []
        st.session_state.current_question = 0
        st.session_state.showing_quiz = False
        st.session_state.score = 0
        st.session_state.answered_questions = {}
        st.session_state.pdf_analysis_result = None
        # Reset gamification specific keys
        st.session_state.total_questions_solved = 0
        st.session_state.total_correct_answers = 0
        st.session_state.topics_covered = set()
        st.session_state.current_streak = 0
        st.session_state.last_quiz_date = None
        st.session_state.streak_history = {}
        st.session_state.user_name = "" # Clear user name too
        st.session_state.topic_performance = {} # Clear topic performance too
        st.session_state.current_quiz_main_topic = "" # Clear current quiz topic
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
