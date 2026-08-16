"""
Mini audio collection app (Task 3).
Run with: streamlit run audio_app/app.py
"""
import os
import sys
import uuid

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from audio_utils import extract_audio_features
from db_utils import find_or_create_person, save_submission, get_all_submissions

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="ConsultBae Audio Collector", page_icon="🎙️", layout="centered")

page = st.sidebar.radio("Navigate", ["Submit Audio", "All Submissions"])

if page == "Submit Audio":
    st.title("🎙️ Submit Your Audio")
    st.write("Enter your details and record or upload an audio clip.")

    name = st.text_input("Full Name")
    phone = st.text_input("Phone Number")

    st.subheader("Record audio")
    recorded = st.audio_input("Record here")

    st.subheader("...or upload a file instead")
    uploaded = st.file_uploader("Upload audio", type=["wav", "mp3", "m4a", "ogg", "webm"])

    audio_source = recorded if recorded is not None else uploaded

    if audio_source is not None:
        st.audio(audio_source)

    if st.button("Submit", type="primary"):
        if not name.strip():
            st.error("Please enter your name.")
        elif not phone.strip():
            st.error("Please enter your phone number.")
        elif audio_source is None:
            st.error("Please record or upload an audio clip first.")
        else:
            with st.spinner("Processing your audio..."):
                ext = "wav" if recorded is not None else audio_source.name.split(".")[-1]
                filename = f"{uuid.uuid4().hex}.{ext}"
                file_path = os.path.join(UPLOAD_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(audio_source.getbuffer())

                try:
                    features = extract_audio_features(file_path)
                except Exception as e:
                    st.error(f"Couldn't process this audio file: {e}")
                    st.stop()

                person_id, phone_norm = find_or_create_person(name, phone)
                save_submission(person_id, name.strip(), phone_norm, file_path, features)

            st.success("Submitted! Here's what we extracted:")
            col1, col2 = st.columns(2)
            col1.metric("Duration", f"{features['duration_sec']} sec")
            col1.metric("Sample Rate", f"{features['sample_rate_hz'] / 1000:.1f} kHz")
            col2.metric("Bitrate", f"{features['bitrate_kbps']} kbps")
            col2.metric("Loudness", f"{features['loudness_db']} dB")
            if features["noise_estimate_db"] is not None:
                st.caption(f"Rough signal-to-noise estimate: {features['noise_estimate_db']} dB "
                           "(higher = cleaner recording)")

else:
    st.title("📋 All Submissions")
    submissions = get_all_submissions()

    if not submissions:
        st.info("No submissions yet.")
    else:
        st.write(f"**{len(submissions)} submission(s)**")
        for s in submissions:
            with st.container(border=True):
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.markdown(f"**{s['submitted_name']}**")
                    st.caption(f"{s['submitted_phone']} · person_id {s['person_id']}")
                    st.caption(s['submitted_at'].strftime("%d %b %Y, %I:%M %p"))
                with col2:
                    if os.path.exists(s['file_path']):
                        st.audio(s['file_path'])
                    else:
                        st.warning("Audio file not found on disk")
                    st.caption(
                        f"⏱️ {s['duration_sec']}s · 🎚️ {float(s['sample_rate_hz'])/1000:.1f}kHz · "
                        f"📊 {s['bitrate_kbps']}kbps · 🔊 {s['loudness_db']}dB"
                        + (f" · SNR {s['noise_estimate_db']}dB" if s['noise_estimate_db'] is not None else "")
                    )