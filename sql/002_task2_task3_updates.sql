-- Run this to add what Task 3 needs. (skill_category was already added
-- manually for Task 2, so only the CREATE TABLE below is needed.)

CREATE TABLE audio_submissions (
    submission_id INT PRIMARY KEY AUTO_INCREMENT,
    person_id INT,
    submitted_name VARCHAR(255),
    submitted_phone VARCHAR(20),
    file_path VARCHAR(500),
    duration_sec DECIMAL(8,2),
    sample_rate_hz INT,
    bitrate_kbps DECIMAL(8,2),
    loudness_db DECIMAL(6,2),
    noise_estimate_db DECIMAL(6,2),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES people(person_id)
);