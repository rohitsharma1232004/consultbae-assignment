-- ConsultBae Assignment - Task 1 Database Schema
-- Run this file once to set up all tables

DROP TABLE IF EXISTS match_log;
DROP TABLE IF EXISTS staging_naukri;
DROP TABLE IF EXISTS staging_gig_workers;
DROP TABLE IF EXISTS staging_cbnexus;
DROP TABLE IF EXISTS people;

CREATE TABLE staging_naukri (
    row_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    city VARCHAR(100),
    experience_years DECIMAL(4,1),
    current_ctc DECIMAL(12,2),
    applied_date DATE,
    skills TEXT,
    person_id INT NULL
);

CREATE TABLE staging_gig_workers (
    row_id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255),
    worker_name VARCHAR(255),
    rate_amount DECIMAL(10,2),
    rate_unit VARCHAR(10),
    location VARCHAR(100),
    status VARCHAR(20),
    skill_tags TEXT,
    person_id INT NULL
);

CREATE TABLE staging_cbnexus (
    row_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255),
    phone VARCHAR(20),
    city VARCHAR(100),
    verified VARCHAR(10),
    projects_completed INT,
    person_id INT NULL
);

CREATE TABLE people (
    person_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(15),
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE match_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    person_id INT,
    source_table VARCHAR(50),
    source_row_id INT,
    match_method VARCHAR(50),
    match_confidence DECIMAL(5,2),
    notes VARCHAR(255),
    FOREIGN KEY (person_id) REFERENCES people(person_id)
);