import streamlit as st
import google.generativeai as genai
import json
import os
import fitz  # PyMuPDF
from typing import Set, List, Dict, Any
from dotenv import load_dotenv

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
    st.session_state.answered_questions = set()
if "pdf_analysis_result" not in st.session_state:
    st.session_state.pdf_analysis_result = None

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
    If there are weak topics, respond with the list of topics separated by a single space.
    If no weak topics are found, respond with "none".
    
    Message: "{message}"
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2}
        )
        
        text = response.text.strip().lower()
        if text == "none":
            return set()
        
        new_topics = set(text.split())
        return new_topics
    
    except Exception as e:
        st.error(f"Error processing message: {str(e)}")
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

def generate_quiz(topic: str) -> List[Dict[str, Any]]:
    """Generate a quiz based on the specified topic and weak topics."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    weak_topics = ", ".join(st.session_state.weak_topics) if st.session_state.weak_topics else "None identified"
    
    prompt = f"""
    Generate a quiz on the topic "{topic}" for a student who is preparing for Joint Entrance Exam (JEE).
    Pick the questions from existing previous year questions (PYQs) available for JEE Exam when possible.
    
    Create 10 single choice questions. For each question, provide 4 answer choices, the correct answer, and a brief explanation.
    
    Format the response as a JSON array of objects, where each object represents a question and has the following structure:
    {{
      "question": "The question text",
      "answers": ["Answer A", "Answer B", "Answer C", "Answer D"],
      "correctAnswer": 0,
      "explanation": "Brief explanation of the correct answer"
    }}
    
    Here are some weak topics the student has mentioned and needs more attention:
    {weak_topics}

    Focus more on these weak topics if they are related to {topic}.
    Ensure all questions are appropriate for JEE level.
    Return ONLY valid JSON with no additional text.
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2}
        )
        
        response_text = response.text
        
        json_start = response_text.find("[")
        json_end = response_text.rfind("]") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            questions = json.loads(json_text)
            return questions
        else:
            st.error("Failed to parse quiz data")
            return []
            
    except Exception as e:
        st.error(f"Error generating quiz: {str(e)}")
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

def analyze_test_results(text):
    """Analyze PDF test results to identify questions, student answers, correct answers, and determine weak topics based on incorrect answers."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are analyzing a student's test results for JEE preparation. The PDF contains questions, 
    student's answers, and correct answers in the following format:
    
    ->question
    ->answer by student
    ->correct answer
    
    Here is the extracted content from the test result:
    {text}
    
    Please analyze and respond with the following JSON structure:
    {{
      "weak_topics": ["topic1", "topic2", ...],
      "analysis": {{
        "total_questions": number,
        "correct_answers": number,
        "incorrect_answers": number,
        "accuracy_percentage": number
      }},
      "question_analysis": [
        {{
          "question": "Question text",
          "student_answer": "Student's answer",
          "correct_answer": "Correct answer",
          "is_correct": boolean,
          "topic": "Related topic",
          "explanation": "Brief explanation of why the answer is correct/incorrect and what concept the student needs to focus on"
        }},
        ...
      ],
      "summary": "Brief overall analysis of student performance and recommendations"
    }}
    
    Return ONLY valid JSON with no additional text.
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2}
        )
        
        response_text = response.text
        
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            analysis_result = json.loads(json_text)
            
            if "weak_topics" in analysis_result:
                st.session_state.weak_topics.update(analysis_result["weak_topics"])
                
            return analysis_result
        else:
            st.error("Failed to parse analysis data")
            return None
            
    except Exception as e:
        st.error(f"Error analyzing test results: {str(e)}")
        return None

def display_chat():
    """Display the chat interface."""
    st.subheader("Chat with your Study Buddy")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Get user input
    user_message = st.chat_input("Type your message here...")
    
    if user_message:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_message})
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_message)
        
        # Get and display AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                ai_response = get_chatbot_response(user_message)
                st.write(ai_response)
        
        # Add AI response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})

def display_quiz_generator():
    """Display the quiz generator interface."""
    st.subheader("Generate a Quiz")
    
    # Display identified weak topics
    if st.session_state.weak_topics:
        st.write("**Identified weak topics:**")
        for topic in st.session_state.weak_topics:
            st.write(f"- {topic}")
    else:
        st.write("No weak topics identified yet. Chat more or upload test results to help us understand your needs.")
    
    # Quiz generation form
    with st.form("quiz_form"):
        topic = st.text_input("Enter the quiz topic:")
        submit_quiz = st.form_submit_button("Generate Quiz")
        
        if submit_quiz and topic:
            st.session_state.quiz_questions = generate_quiz(topic)
            st.session_state.showing_quiz = True
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.session_state.answered_questions = set()
            st.success("Quiz generated successfully!")
            st.rerun()

def display_quiz():
    """Display the quiz interface."""
    if not st.session_state.quiz_questions:
        st.warning("No quiz questions available. Please generate a quiz first.")
        return
    
    questions = st.session_state.quiz_questions
    current_q_idx = st.session_state.current_question
    
    if current_q_idx >= len(questions):
        # Quiz completed
        st.success(f"Quiz completed! Your score: {st.session_state.score}/{len(questions)}")
        if st.button("Start New Quiz"):
            st.session_state.showing_quiz = False
            st.rerun()
        return
    
    question = questions[current_q_idx]
    
    # Display question
    st.subheader(f"Question {current_q_idx + 1} of {len(questions)}")
    st.write(question["question"])
    
    # Display answer options and handle selection
    if current_q_idx not in st.session_state.answered_questions:
        selected_option = st.radio(
            "Select your answer:",
            question["answers"],
            key=f"q_{current_q_idx}"
        )
        
        if st.button("Submit Answer"):
            selected_idx = question["answers"].index(selected_option)
            is_correct = selected_idx == question["correctAnswer"]
            
            if is_correct:
                st.success("Correct! 🎉")
                st.session_state.score += 1
            else:
                st.error(f"Incorrect. The correct answer is: {question['answers'][question['correctAnswer']]}")
            
            st.info(f"**Explanation:** {question['explanation']}")
            st.session_state.answered_questions.add(current_q_idx)
            
            if st.button("Next Question"):
                st.session_state.current_question += 1
                st.rerun()
    else:
        # If the question has been answered, show the result and explanation
        selected_idx = question["answers"].index(st.session_state[f"q_{current_q_idx}"])
        is_correct = selected_idx == question["correctAnswer"]
        
        if is_correct:
            st.success("Correct! 🎉")
        else:
            st.error(f"Incorrect. The correct answer is: {question['answers'][question['correctAnswer']]}")
        
        st.info(f"**Explanation:** {question['explanation']}")
        
        if st.button("Next Question"):
            st.session_state.current_question += 1
            st.rerun()

def display_pdf_analyzer():
    """Display the PDF test results analyzer interface."""
    st.subheader("Analyze Test Results")
    
    # File uploader for PDF
    uploaded_file = st.file_uploader("Upload your test result (PDF)", type=["pdf"])
    
    if uploaded_file:
        if st.button("Analyze Test Results"):
            with st.spinner("Extracting and analyzing test results..."):
                extracted_text = extract_text_from_pdf(uploaded_file)
                if not extracted_text:
                    st.error("Could not extract text. Please upload a clear PDF.")
                else:
                    analysis_result = analyze_test_results(extracted_text)
                    if analysis_result:
                        st.session_state.pdf_analysis_result = analysis_result
                        st.success("Analysis completed successfully!")
                        st.rerun()
    
    # Display analysis results if available
    if st.session_state.pdf_analysis_result:
        result = st.session_state.pdf_analysis_result
        
        # Display summary stats
        st.markdown("### 📊 Test Analysis Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Questions", result["analysis"]["total_questions"])
        with col2:
            st.metric("Correct Answers", result["analysis"]["correct_answers"])
        with col3:
            st.metric("Incorrect Answers", result["analysis"]["incorrect_answers"])
        with col4:
            st.metric("Accuracy", f"{result['analysis']['accuracy_percentage']}%")
        
        # Display weak topics
        st.markdown("### 🔍 Identified Weak Topics")
        if result["weak_topics"]:
            for topic in result["weak_topics"]:
                st.write(f"- {topic}")
        else:
            st.write("No significant weak topics identified.")
        
        # Display overall summary
        st.markdown("### 📝 Performance Summary")
        st.write(result["summary"])
        
        # Display detailed question analysis
        with st.expander("Detailed Question Analysis"):
            for i, q_analysis in enumerate(result["question_analysis"]):
                status = "✅" if q_analysis["is_correct"] else "❌"
                st.markdown(f"**Question {i+1}**: {status}")
                st.write(f"**Q**: {q_analysis['question']}")
                st.write(f"**Your Answer**: {q_analysis['student_answer']}")
                st.write(f"**Correct Answer**: {q_analysis['correct_answer']}")
                st.write(f"**Topic**: {q_analysis['topic']}")
                st.write(f"**Explanation**: {q_analysis['explanation']}")
                st.markdown("---")

def main():
    """Main application function."""
    st.title("JEE Study Buddy")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Chat", "Quiz Generator", "Test Results Analyzer"])
    
    if page == "Chat":
        display_chat()
    elif page == "Quiz Generator":
        if st.session_state.showing_quiz:
            display_quiz()
        else:
            display_quiz_generator()
    elif page == "Test Results Analyzer":
        display_pdf_analyzer()
    
    # Show weak topics in sidebar
    with st.sidebar.expander("Identified Weak Topics"):
        if st.session_state.weak_topics:
            for topic in st.session_state.weak_topics:
                st.sidebar.write(f"- {topic}")
        else:
            st.sidebar.write("No weak topics identified yet.")
    
    # Option to clear data
    if st.sidebar.button("Clear All Data"):
        st.session_state.chat = None
        st.session_state.chat_history = []
        st.session_state.weak_topics = set()
        st.session_state.quiz_questions = []
        st.session_state.showing_quiz = False
        st.session_state.pdf_analysis_result = None
        st.success("All data cleared!")
        st.rerun()

if __name__ == "__main__":
    main()
