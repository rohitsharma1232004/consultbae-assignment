"""
DB helpers for the audio submission app.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import mysql.connector
from config import DB_CONFIG
from normalize import normalize_phone, normalize_name


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def find_or_create_person(name, phone):
    phone_norm = normalize_phone(phone)
    name_norm = normalize_name(name)

    conn = get_connection()
    cur = conn.cursor()

    if phone_norm:
        cur.execute("SELECT person_id FROM people WHERE phone = %s", (phone_norm,))
        row = cur.fetchone()
        if row:
            cur.close()
            conn.close()
            return row[0], phone_norm

    cur.execute(
        "INSERT INTO people (full_name, phone) VALUES (%s, %s)",
        (name_norm, phone_norm)
    )
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    conn.close()
    return new_id, phone_norm


def save_submission(person_id, name, phone, file_path, features):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO audio_submissions
           (person_id, submitted_name, submitted_phone, file_path,
            duration_sec, sample_rate_hz, bitrate_kbps, loudness_db, noise_estimate_db)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (person_id, name, phone, file_path,
         features["duration_sec"], features["sample_rate_hz"],
         features["bitrate_kbps"], features["loudness_db"], features["noise_estimate_db"])
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_submissions():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT s.submission_id, s.submitted_name, s.submitted_phone, s.file_path,
                  s.duration_sec, s.sample_rate_hz, s.bitrate_kbps, s.loudness_db,
                  s.noise_estimate_db, s.submitted_at, p.person_id
           FROM audio_submissions s
           LEFT JOIN people p ON s.person_id = p.person_id
           ORDER BY s.submitted_at DESC"""
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows