# JEE Buddy: Your AI-Powered Study Assistant

JEE Buddy is an interactive AI-powered application designed to assist students preparing for the Joint Entrance Exam (JEE) in India. Leveraging large language models, it provides personalized study support, mock quizzes, PDF analysis, and performance tracking to help students identify their weak areas and strengthen their understanding.

## ✨ Features

* **Interactive Chat:** Engage in a natural language conversation with the AI to ask questions, clarify concepts, and get instant explanations on any JEE-related topic.
* **PDF Analysis & Weak Topic Identification:** Upload your study materials (like test papers or notes), and the AI will analyze them, answer questions based on the content, and identify your weak topics based on incorrect answers or areas where you need more clarification.
* **Custom Quiz Generator:** Generate personalized quizzes on specific topics and difficulty levels (JEE Mains / JEE Advanced).
* **Gamified Quiz Experience:**
    * **Real-time Progress:** See your progress, current score, and accuracy percentage during the quiz to stay engaged.
    * **Performance Metrics:** Track correct answers and overall accuracy within the quiz window.
    * **Bookmarks:** Bookmark challenging questions to review them later.
* **Detailed Explanations & Solutions:** After each quiz question, get a detailed step-by-step explanation. The app also attempts to provide relevant textual and YouTube video solutions from external sources.
* **Personalized Profile:**
    * View overall progress including total questions solved and accuracy.
    * Track performance across different topics.
    * Monitor your daily quiz streak.
    * Access all your bookmarked questions for focused revision.

## 🚀 Technologies Used

* **Streamlit:** For building the interactive web application interface.
* **Google Generative AI (Gemini API):** Powers the conversational AI, quiz generation, and content understanding.
* **PyMuPDF (fitz):** For extracting text content from PDF documents.
* **Python-dotenv:** For managing environment variables.
* **Google Search (via `googlesearch-python` and `google-api-python-client`):** For searching for textual and YouTube video solutions.
* **Requests & BeautifulSoup4:** For web scraping textual solutions from search results.

## ⚙️ Setup Instructions

To get JEE Buddy up and running on your local machine, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AyuAnchor/ai-learning-buddy.git
    cd ai-learning-buddy
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables:**
    Create a `.env` file in the root directory of your project and add your API keys:
    ```
    GEMINI_API_KEY="your_google_gemini_api_key_here"
    YOUTUBE_API_KEY="your_google_youtube_data_api_key_here"
    ```
    Replace `"your_google_gemini_api_key_here"` and `"your_google_youtube_data_api_key_here"` with your actual API keys. You can obtain these from the [Google AI Studio](https://ai.google.dev/) and [Google Cloud Console](https://console.cloud.google.com/apis/credentials).

5.  **Run the application:**
    ```bash
    streamlit run main.py
    ```

    The application will open in your web browser.

## 📚 Usage

* **Chat:** Navigate to the "Chat" section and type your JEE-related questions.
* **PDF Analysis:** Go to the "PDF Analyzer" section, upload a PDF file, and ask questions about its content.
* **Quiz Generator:** In the "Quiz Generator" section, specify a topic, difficulty, and number of questions to create a custom quiz.
* **Profile:** Check your progress, view statistics, and review bookmarked questions in the "Profile" section.

## 📂 Project Structure

* `main.py`: The primary Streamlit application file, handling page navigation and overall session state management.
* `config.py`: Stores configuration variables, including API keys and session state initializations.
* `chat_module.py`: Contains functions related to the chatbot functionality.
* `quiz_module.py`: Manages all quiz-related functionalities, including quiz generation, display, and gamification logic.
* `pdf_analyzer_module.py`: Encapsulates functions for PDF text extraction and test result analysis.
* `profile_module.py`: Contains functions for displaying the user profile, gamification statistics, and bookmarked questions.
* `utils.py`: Houses utility functions like `get_youtube_links`, `get_solution_link`, etc., shared across modules.
* `requirements.txt`: Lists all necessary Python dependencies.
* `.env`: Stores environment variables like API keys (not committed to version control).

---

Feel free to contribute to this project by opening issues or submitting pull requests!
