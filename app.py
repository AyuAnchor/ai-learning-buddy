import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os

# ---- CONFIG ----
st.set_page_config(page_title="Learning Buddy", layout="centered")

# ---- API KEY ----
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---- Functions ----
def extract_text_from_pdf(pdf_file):
    text = ""
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    for page in doc:
        text += page.get_text()
    return text.strip()

def analyze_with_gemini(text):
    prompt = f"""
You are a smart AI learning assistant. A student has uploaded their test answers and solutions.

Here is the extracted content from the test result:
{text}

Please do the following:
1. Identify the subjects and topics covered.
2. Point out areas where the student seems to be struggling.
3. Provide motivational feedback.
4. Recommend personalized learning strategies and resources.

Keep your tone friendly and helpful.
"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

# ---- UI ----
st.title("📘 Universal Learning Buddy")
st.subheader("Upload your test result and get smart feedback")

uploaded_file = st.file_uploader("Upload your test result (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Extracting text from PDF..."):
        extracted_text = extract_text_from_pdf(uploaded_file)
        if not extracted_text:
            st.error("Could not extract text. Please upload a clear PDF.")
        else:
            st.success("PDF text extracted successfully.")

            if st.button("🔍 Analyze and Get Feedback"):
                with st.spinner("Analyzing with Gemini Flash..."):
                    feedback = analyze_with_gemini(extracted_text)
                    st.markdown("### 📊 Your Personalized Feedback")
                    st.markdown(feedback)

