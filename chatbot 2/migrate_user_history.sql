USE vernacular_fd;

ALTER TABLE user_history
    CHANGE COLUMN goal_tag user_reason VARCHAR(255) NOT NULL;
