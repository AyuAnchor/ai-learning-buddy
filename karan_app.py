import streamlit as st
import google.generativeai as genai
import json
import os
import fitz  # PyMuPDF
from typing import Set, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
# Configuration
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyASORpjRoDsPkkFT4Tg3F_LKiwSZjweczA")
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
if "num_questions" not in st.session_state:
    st.session_state.num_questions = 10  # Default number of questions
if "level" not in st.session_state:
    st.session_state.level = 1
if "total_attempted" not in st.session_state:
    st.session_state.total_attempted = 0
if "current_explanation" not in st.session_state:
    st.session_state.current_explanation = ""
if "show_explanation" not in st.session_state:
    st.session_state.show_explanation = False
if "user_answered" not in st.session_state:
    st.session_state.user_answered = False
if "correct_answers" not in st.session_state:
    st.session_state.correct_answers = 0


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

def generate_quiz(topic: str, num_questions: int) -> List[Dict[str, Any]]:
    """Generate a quiz based on the specified topic and weak topics."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    weak_topics = ", ".join(st.session_state.weak_topics) if st.session_state.weak_topics else "None identified"
    
    prompt = f"""
    Generate a quiz with exactly {num_questions} questions on the topic "{topic}" for a student who is preparing for Joint Entrance Exam (JEE).
    Pick the questions from existing previous year questions (PYQs) available for JEE Exam when possible.
    
    Create {num_questions} single choice questions. For each question, provide 4 answer choices, the correct answer, and a brief explanation.
    
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
        topic = st.text_input("Enter the quiz topic:", key="quiz_topic")
        num_questions = st.number_input(
            "Number of questions to generate:",
            min_value=1,
            max_value=50,
            value=10,
            key="num_questions_input"
        )
        submit_quiz = st.form_submit_button("Generate Quiz")
        
        if submit_quiz and topic:
            with st.spinner(f"Generating {num_questions} questions on {topic}..."):
                st.session_state.num_questions = num_questions
                st.session_state.quiz_questions = generate_quiz(topic, num_questions)
                if st.session_state.quiz_questions:  # Only proceed if questions were generated
                    st.session_state.showing_quiz = True
                    st.session_state.current_question = 0
                    st.session_state.score = 0
                    st.session_state.correct_answers = 0
                    st.session_state.answered_questions = set()
                    st.session_state.user_answered = False
                    st.session_state.show_explanation = False
                    st.success(f"Quiz with {num_questions} questions generated successfully!")
                    st.rerun()

def display_quiz():
    """Display the quiz interface."""
    # Create a container with custom CSS to shift content left
    left_column, right_column = st.columns([4, 1])
    
    with left_column:
        st.subheader("JEE Practice Quiz")
        
        questions = st.session_state.quiz_questions
        total_questions = len(questions)
        
        if total_questions == 0:
            st.warning("No questions available. Please generate a new quiz.")
            st.session_state.showing_quiz = False
            st.rerun()
            return
        
        current_q = st.session_state.current_question
        
        if current_q < total_questions:
            question = questions[current_q]
            
            st.write(f"**Question {current_q + 1} of {total_questions}**")
            st.write(question['question'])
            
            # Display answer options
            selected_answer = st.radio(
                "Select your answer:",
                question['answers'],
                key=f"answer_{current_q}"
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("Submit Answer", key=f"submit_{current_q}") and not st.session_state.user_answered:
                    correct_idx = question['correctAnswer']
                    is_correct = (selected_answer == question['answers'][correct_idx])
                    
                    if is_correct:
                        st.success("✅ Correct! (+4 points)")
                        st.session_state.score += 4
                        st.session_state.correct_answers += 1
                    else:
                        st.error(f"❌ Incorrect (-1 point). The correct answer is: {question['answers'][correct_idx]}")
                        st.session_state.score -= 1
                    
                    # Store explanation for viewing
                    st.session_state.current_explanation = question['explanation']
                    st.session_state.show_explanation = False
                    st.session_state.user_answered = True
                    st.session_state.total_attempted += 1
            
            with col2:
                if st.button("Skip Question", key=f"skip_{current_q}") and not st.session_state.user_answered:
                    st.info("Question skipped")
                    st.session_state.current_explanation = f"Skipped. The correct answer was: {question['answers'][question['correctAnswer']]}. " + question['explanation']
                    st.session_state.show_explanation = False
                    st.session_state.user_answered = True
            
            with col3:
                if st.session_state.user_answered:
                    if not st.session_state.show_explanation:
                        if st.button("View Explanation", key=f"view_explanation_{current_q}"):
                            st.session_state.show_explanation = True
                    else:
                        if st.button("Next Question", key=f"next_{current_q}"):
                            st.session_state.current_question += 1
                            st.session_state.user_answered = False
                            st.session_state.show_explanation = False
                            st.rerun()
            
            # Display explanation if requested
            if st.session_state.show_explanation and st.session_state.user_answered:
                st.write("**Explanation:**")
                st.write(st.session_state.current_explanation)
        
        else:
            # Quiz completed
            st.balloons()
            st.success("🎯 Quiz Completed!")
            st.write(f"**Final Score:** {st.session_state.score} points")
            
            # Correctly calculate accuracy as correct answers / total questions * 100
            accuracy = (st.session_state.correct_answers / total_questions) * 100 if total_questions > 0 else 0
            st.write(f"**Accuracy:** {accuracy:.1f}%")
            
            # Update level based on performance
            if accuracy > 75 and st.session_state.level < 5:
                st.session_state.level += 1
                st.write(f"🌟 Level Up! You're now at Level {st.session_state.level}")
            
            if st.button("Generate New Quiz", key="new_quiz"):
                st.session_state.showing_quiz = False
                st.session_state.quiz_questions = []
                st.rerun()
            
            if st.button("Review Weak Topics", key="review_topics"):
                st.session_state.showing_quiz = False
                st.rerun()
    
    # Display score and accuracy in right column
    with right_column:
        if current_q < total_questions:
            st.markdown("### Quiz Stats")
            
            # Calculate current score metrics
            current_score = st.session_state.score
            
            # Calculate accurate accuracy based on correct answers / questions attempted
            questions_attempted = current_q + (1 if st.session_state.user_answered else 0)
            if questions_attempted > 0:
                accuracy = (st.session_state.correct_answers / questions_attempted) * 100
            else:
                accuracy = 0
            
            st.markdown(f"**Score:** {current_score}")
            st.markdown(f"**Question:** {current_q + 1}/{total_questions}")
            st.markdown(f"**Accuracy:** {accuracy:.1f}%")
            
            # Create a visual progress indicator
            progress = (current_q + 1) / total_questions
            st.progress(progress)
            
            # Display color-coded accuracy indicator
            if accuracy >= 75:
                st.markdown("🟢 **Good progress!**")
            elif accuracy >= 50:
                st.markdown("🟡 **Making progress**")
            else:
                st.markdown("🔴 **Needs improvement**")

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
    
    # Show total questions attempted in sidebar
    with st.sidebar.expander("Progress Tracking"):
        st.sidebar.write(f"**Total Questions Attempted:** {st.session_state.total_attempted}")
    
    # Option to clear data
    if st.sidebar.button("Clear All Data"):
        st.session_state.chat = None
        st.session_state.chat_history = []
        st.session_state.weak_topics = set()
        st.session_state.quiz_questions = []
        st.session_state.showing_quiz = False
        st.session_state.pdf_analysis_result = None
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.correct_answers = 0
        st.session_state.num_questions = 10
        st.success("All data cleared!")
        st.rerun()

if __name__ == "__main__":
    main()