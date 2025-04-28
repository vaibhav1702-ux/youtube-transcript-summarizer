import streamlit as st
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Base Prompt for summarization
BASE_PROMPT = """You are a YouTube video summarizer. You will be taking the transcript text 
and summarizing the entire video and providing the important summary in points."""

# --- Utility Functions ---

# Extract video ID from YouTube URL
def get_video_id(youtube_url):
    parsed_url = urlparse(youtube_url)
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path[1:]
    if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
        return parse_qs(parsed_url.query).get("v", [None])[0]
    return None

# Fetch the transcript of the video
def extract_transcript_details(youtube_video_url, language='en', start=None, end=None):
    try:
        video_id = get_video_id(youtube_video_url)
        if not video_id:
            raise ValueError("Could not extract video ID from URL.")

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try fetching the transcript in the provided language
        try:
            transcript = transcript_list.find_transcript([language])
        except NoTranscriptFound:
            transcript = transcript_list.find_transcript([t.language_code for t in transcript_list])

        transcript_text = transcript.fetch()

        # If start and end times are provided, filter the transcript by time range
        if start is not None and end is not None:
            transcript_text = [i for i in transcript_text if start <= i.start <= end]

        # Combine transcript text into a single string
        transcript_combined = " ".join([snippet.text for snippet in transcript_text])
        return transcript_combined

    except TranscriptsDisabled:
        raise Exception("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise Exception("No available transcripts found for this video.")
    except Exception as e:
        raise Exception(f"Error while extracting transcript: {e}")

# Summarize the transcript using Google Generative AI
def summarize_video_transcript(transcript_text):
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        prompt = BASE_PROMPT + "\n\n" + transcript_text
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Error during summarization: {e}")

# --- Streamlit App ---
def main():
    st.title("YouTube Video Summarizer")

    # Get user input
    youtube_url = st.text_input("Enter YouTube Video URL:")
    language = st.selectbox("Select Language", ['en', 'es', 'fr', 'de', 'it'])

    # Extract and summarize the transcript
    if youtube_url:
        try:
            with st.spinner("Fetching transcript..."):
                transcript_text = extract_transcript_details(youtube_url, language)

            # Display the transcript
            st.write("Transcript Extracted (First 500 characters):")
            st.text_area("Transcript", transcript_text[:500], height=200)

            with st.spinner("Summarizing video..."):
                summary = summarize_video_transcript(transcript_text)

            # Display the summary
            st.write("Summary:")
            st.write(summary)

            # Download button (after generating summary)
            st.download_button(
                label="Download Summary",
                data=summary,
                file_name="youtube_video_summary.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
