import streamlit as st
import google.generativeai as genai
import fitz # PyMuPDF
import json
from typing import Any, Dict

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
            try:
                analysis_result = json.loads(json_text)
                
                if "weak_topics" in analysis_result and isinstance(analysis_result["weak_topics"], list):
                    st.session_state.weak_topics.update(topic for topic in analysis_result["weak_topics"] if isinstance(topic, str))
                    
                return analysis_result
            except json.JSONDecodeError as je:
                st.error(f"JSON Decode Error analyzing test results: {str(je)}. Raw response: {response_text}")
                return None
        else:
            st.error(f"Failed to parse analysis data from LLM. Raw response: {response_text}")
            return None
            
    except Exception as e:
        st.error(f"Error analyzing test results: {str(e)}. Raw response: {response_text}")
        return None

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