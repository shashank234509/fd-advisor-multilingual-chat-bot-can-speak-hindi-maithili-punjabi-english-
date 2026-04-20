CREATE DATABASE IF NOT EXISTS vernacular_fd;
USE vernacular_fd;

CREATE TABLE IF NOT EXISTS bank_offers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    bank_name VARCHAR(50) NOT NULL,
    tenor_months INT NOT NULL,
    rate DECIMAL(4,2) NOT NULL,
    goal_tag ENUM('Wedding', 'Education', 'Emergency') NOT NULL
);

CREATE TABLE IF NOT EXISTS dialect_jargon (
    id INT PRIMARY KEY AUTO_INCREMENT,
    term VARCHAR(50) NOT NULL,
    language VARCHAR(20) NOT NULL,
    local_translation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(80),
    language VARCHAR(20) NOT NULL,
    user_reason VARCHAR(255) NOT NULL,
    invested_amount DECIMAL(12,2) NOT NULL,
    suggested_bank VARCHAR(50) NOT NULL,
    suggested_rate DECIMAL(4,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
