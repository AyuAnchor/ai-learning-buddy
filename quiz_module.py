import streamlit as st
import google.generativeai as genai
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from utils import get_solution_link, get_youtube_solution_link

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
        questions = []  # Initialize empty list first
        
        # Clean response text
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        json_start = response_text.find("[")
        json_end = response_text.rfind("]") + 1
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            try:
                questions = json.loads(json_text)
            except json.JSONDecodeError as je:
                st.error(f"JSON Decode Error: {str(je)}")
                return []
        else:
            st.error("Failed to find valid JSON array in response")
            return []
        
        # Process questions and add solution links
        if questions:
            for question in questions:
                # Ensure explanation structure exists
                question.setdefault('explanation', {})
                question['explanation'].setdefault('detailed_steps', 
                    "Explanation not generated. Please refer to solution links.")
                question['explanation'].setdefault('youtube_link', "")
            
            return questions
        else:
            st.error("Generated quiz is empty")
            return []
            
    except Exception as e:
        st.error(f"Error generating quiz: {str(e)}")
        return []

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

    # --- Progress Indicators (New) ---
    total_questions = len(questions)
    
    # Corrected: questions_attempted should be based on the number of answered_questions
    questions_attempted = len(st.session_state.answered_questions) 
    
    current_quiz_correct_answers = sum(1 for q_idx, ans_info in st.session_state.answered_questions.items() if ans_info.get("is_correct", False))

    current_quiz_accuracy = (current_quiz_correct_answers / questions_attempted * 100) if questions_attempted > 0 else 0

    st.subheader(f"Question {current_q_idx + 1} of {total_questions}")
    st.progress((questions_attempted) / total_questions, text=f"Progress: {questions_attempted}/{total_questions} questions attempted.")

    col_prog1, col_prog2 = st.columns(2)
    with col_prog1:
        st.metric("Correct Answers", current_quiz_correct_answers)
    with col_prog2:
        st.metric("Current Accuracy", f"{current_quiz_accuracy:.2f}%")
    st.markdown("---")
    # --- End Progress Indicators ---

    if current_q_idx >= total_questions:
        st.balloons()
        x= st.session_state.score / total_questions * 100
        st.success(f"🎉 Quiz Completed! Your final score: {x:.2f}% 🎉")
        
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
            answer_info = st.session_state.answered_questions.get(i, {})
            user_answer_idx = answer_info.get("selected_idx")
            is_correct = answer_info.get("is_correct", False)
            is_skipped = answer_info.get("is_skipped", False) # New: Check if skipped
            is_bookmarked = answer_info.get("is_bookmarked", False) # Check if bookmarked
            
            st.markdown(f"--- \n**Question {i+1}:** {' 🔖' if is_bookmarked else ''}")
            st.markdown(q_data['question']) # Display question using markdown
            
            if is_skipped:
                st.write("You skipped this question.")
            elif user_answer_idx is not None:
                st.write(f"Your answer: {q_data['answers'][user_answer_idx]} ({'Correct' if is_correct else 'Incorrect'})")
            else:
                st.write("You did not answer this question.") # Fallback, should ideally not happen if handled correctly
            
            st.write(f"Correct answer: {q_data['answers'][q_data['correctAnswer']]}")

            with st.spinner("Searching for solution..."):
                txt_link = get_solution_link(q_data['question'])
                yt_link = get_youtube_solution_link(q_data['question'])

            with st.expander("View Detailed Explanation"):
                explanation_obj = q_data.get("explanation", {})
                if isinstance(explanation_obj, dict):
                    detailed_steps = explanation_obj.get('detailed_steps', 'Not provided.')
                    st.markdown(f"**Teacher's Explanation:**\n{detailed_steps}") # Use markdown for steps

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
    
    st.markdown(f"**{question['question']}**") # Display question using markdown
    

    if current_q_idx in st.session_state.answered_questions:
        answer_info = st.session_state.answered_questions[current_q_idx]
        is_skipped = answer_info.get("is_skipped", False) # Check if skipped
        is_bookmarked = answer_info.get("is_bookmarked", False) # Check if bookmarked
        
        # Display bookmark status 
        col_bookmark = st.columns([1])[0]
        with col_bookmark:
            if st.button("🔖 " + ("Unbookmark" if is_bookmarked else "Bookmark") + " Question", key=f"bookmark_q_{current_q_idx}_answered"):
                # Toggle bookmark status
                answer_info["is_bookmarked"] = not is_bookmarked
                st.session_state.answered_questions[current_q_idx] = answer_info
                
                # Update bookmarked questions list
                question_with_meta = question.copy()
                question_with_meta["quiz_topic"] = st.session_state.current_quiz_main_topic
                question_with_meta["question_idx"] = current_q_idx
                
                if not is_bookmarked:  # If previously not bookmarked, add to bookmarks
                    st.session_state.bookmarked_questions.append(question_with_meta)
                else:  # If previously bookmarked, remove from bookmarks
                    # Remove from bookmarked questions by filtering
                    st.session_state.bookmarked_questions = [
                        q for q in st.session_state.bookmarked_questions 
                        if not (q.get("question") == question["question"] and 
                                q.get("quiz_topic") == st.session_state.current_quiz_main_topic)
                    ]
                st.rerun()
        
        # The key issue starts here - need to handle the bookmarked-only case
        if "selected_idx" not in answer_info and not is_skipped:
            # This case handles when only bookmarked (no submit/skip yet)
            options = question["answers"]
            selected_option = st.radio(
                "Select your answer:",
                options,
                key=f"q_{current_q_idx}_options"
            )

            col_submit, col_skip = st.columns([1, 1])
            
            with col_submit:
                if st.button("Submit Answer", key=f"submit_q_{current_q_idx}_after_bookmark"):
                    selected_idx = options.index(selected_option)
                    is_correct = (selected_idx == question["correctAnswer"])
                    
                    answer_info["selected_idx"] = selected_idx
                    answer_info["is_correct"] = is_correct
                    answer_info["is_skipped"] = False
                    st.session_state.answered_questions[current_q_idx] = answer_info

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
            
            with col_skip:
                if st.button("Skip Question", key=f"skip_q_{current_q_idx}_after_bookmark"):
                    answer_info["selected_idx"] = None
                    answer_info["is_correct"] = False
                    answer_info["is_skipped"] = True
                    st.session_state.answered_questions[current_q_idx] = answer_info
                    st.session_state.current_question += 1
                    st.rerun()
                    
        elif is_skipped:
            st.info("You skipped this question.")
            # Options are disabled as no answer was selected
            st.radio(
                "Select your answer:",
                question["answers"],
                index=0, # Can set a default, but it's disabled anyway
                disabled=True, 
                key=f"q_{current_q_idx}_skipped_options"
            )
        else:
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
        
        # Only show explanation if question was answered or skipped
        if "selected_idx" in answer_info or is_skipped:
            with st.spinner("Searching for textual solution..."):
                txt_link = get_solution_link(question['question'])
                yt_link = get_youtube_solution_link(question['question'])

            explanation_obj = question.get("explanation", {})
            if isinstance(explanation_obj, dict):
                detailed_steps = explanation_obj.get('detailed_steps', 'Not provided.')
                st.info(f"**Teacher's Explanation:**\n{detailed_steps}")

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

        # Add bookmark button before submission
        col_bookmark, col_submit, col_skip = st.columns([1, 1, 1]) # Use columns for buttons
        
        with col_bookmark:
            if st.button("🔖 Bookmark Question", key=f"bookmark_q_{current_q_idx}"):
                # We need to save a temporary record that this question is bookmarked
                # even before the answer is submitted or skipped
                if current_q_idx not in st.session_state.answered_questions:
                    st.session_state.answered_questions[current_q_idx] = {
                        "is_bookmarked": True
                    }
                else:
                    st.session_state.answered_questions[current_q_idx]["is_bookmarked"] = True
                
                # Add to bookmarked questions
                question_with_meta = question.copy()
                question_with_meta["quiz_topic"] = st.session_state.current_quiz_main_topic
                question_with_meta["question_idx"] = current_q_idx
                st.session_state.bookmarked_questions.append(question_with_meta)
                
                st.success("Question bookmarked! You can view it later in your profile.")
                st.rerun()
        
        with col_submit:
            if st.button("Submit Answer", key=f"submit_q_{current_q_idx}"):
                selected_idx = options.index(selected_option)
                is_correct = (selected_idx == question["correctAnswer"])
                
                # Check if the question is already marked as bookmarked
                is_bookmarked = False
                if current_q_idx in st.session_state.answered_questions:
                    is_bookmarked = st.session_state.answered_questions[current_q_idx].get("is_bookmarked", False)
                
                st.session_state.answered_questions[current_q_idx] = {
                    "selected_idx": selected_idx,
                    "is_correct": is_correct,
                    "is_skipped": False, # Mark as not skipped
                    "is_bookmarked": is_bookmarked # Preserve bookmark status
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
        
        with col_skip:
            if st.button("Skip Question", key=f"skip_q_{current_q_idx}"):
                # Check if the question is already marked as bookmarked
                is_bookmarked = False
                if current_q_idx in st.session_state.answered_questions:
                    is_bookmarked = st.session_state.answered_questions[current_q_idx].get("is_bookmarked", False)
                
                # Mark as skipped
                st.session_state.answered_questions[current_q_idx] = {
                    "selected_idx": None, # No answer selected
                    "is_correct": False, # Not correct
                    "is_skipped": True, # Explicitly mark as skipped
                    "is_bookmarked": is_bookmarked # Preserve bookmark status
                }
                st.session_state.current_question += 1
                st.rerun()