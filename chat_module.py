import streamlit as st
import google.generativeai as genai
from typing import Set
from utils import get_youtube_links # Import get_youtube_links

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
    
    # Get detected topics
    new_topics = process_message(message)
    youtube_links = {}
    
    # Get YouTube links for detected topics
    if new_topics:
        for topic in new_topics:
            videos = get_youtube_links(topic)
            if videos:
                youtube_links[topic] = videos[:2]  # Get top 2 videos per topic

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
        response_text = response.text
        
        # Add YouTube links if available
        if youtube_links:
            response_text += "\n\n**Recommended Study Videos:**\n"
            for topic, videos in youtube_links.items():
                response_text += f"\n📺 **{topic.title()}**:\n"
                for vid in videos:
                    response_text += f"- [{vid['title']}]({vid['url']})\n"
        
        st.session_state.weak_topics.update(new_topics)
        return response_text
        
    except Exception as e:
        st.error(f"Error generating chatbot response: {str(e)}")
        return "Sorry, something went wrong. Please try again later."
    
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