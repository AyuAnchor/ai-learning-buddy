import streamlit as st
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from googlesearch import search
import os
from googleapiclient.discovery import build
load_dotenv()
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)


@st.cache_data(ttl=3600)  # Cache results for 1 hour
def get_youtube_links(topic: str, max_results=3):
    """Search YouTube for educational content related to the topic."""
    try:
        search_response = youtube.search().list(
            q=f"JEE {topic} tutorial",
            part="id,snippet",
            maxResults=max_results,
            type="video",
            relevanceLanguage="en",
            safeSearch="strict"
        ).execute()

        videos = []
        for item in search_response.get("items", []):
            if item["id"]["kind"] == "youtube#video":
                videos.append({
                    "title": item["snippet"]["title"],
                    "id": item["id"]["videoId"],
                    "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                })
        return videos
    except Exception as e:
        st.error(f"YouTube API Error: {str(e)}")
        return []


@st.cache_data(ttl=3600)  # Cache results for 1 hour
def get_youtube_solution_link(jee_question):
    """
    Searches YouTube for a video solution of a given JEE question using YouTube Data API.
    Returns the URL of the most relevant video.
    """
    query = f"{jee_question} JEE solution"

    try:
        search_response = youtube.search().list(
            q=query,
            part="id",
            maxResults=1,
            type="video"
        ).execute()

        for item in search_response.get("items", []):
            video_id = item["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            return video_url  # Return the first valid result

    except Exception as e:
        print(f"Error while searching YouTube: {e}")
        return None

    return None  # No video found

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