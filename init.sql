CREATE DATABASE IF NOT EXISTS chatbot_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mydb;

CREATE TABLE IF NOT EXISTS chat_logs (
    id           INT          NOT NULL AUTO_INCREMENT,
    session_id   VARCHAR(36)  NOT NULL,
    user_message TEXT         NOT NULL,
    bot_response TEXT         NOT NULL,
    model        VARCHAR(100) NOT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_session_id (session_id),
    INDEX idx_session_created (session_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS keyword_caches (
    keywords        VARCHAR(100) NOT NULL,
    cached_response TEXT         NOT NULL,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (keywords)
) ENGINE=InnoDB;