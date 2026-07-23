-- =============================================================================
-- database/schema.sql
-- Explainable AI Health Framework – Normalized Database Schema
-- MySQL 8.0+
-- Run: mysql -u root -p < database/schema.sql
-- =============================================================================

-- Create and select database
CREATE DATABASE IF NOT EXISTS explainable_ai_health
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE explainable_ai_health;

-- =============================================================================
-- TABLE: admins
-- Separate from users for clean role separation
-- =============================================================================
CREATE TABLE IF NOT EXISTS admins (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(120)  NOT NULL,
    email         VARCHAR(180)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    DATETIME      NULL,
    INDEX idx_admins_email (email)
) ENGINE=InnoDB;

-- =============================================================================
-- TABLE: users
-- Core application users
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name           VARCHAR(120)  NOT NULL,
    age                 TINYINT UNSIGNED NOT NULL,
    gender              VARCHAR(20)   NOT NULL,
    height_cm           FLOAT         NULL,
    weight_kg           FLOAT         NULL,
    email               VARCHAR(180)  NOT NULL UNIQUE,
    password_hash       VARCHAR(255)  NOT NULL,
    is_email_verified   TINYINT(1)    NOT NULL DEFAULT 0,
    role                VARCHAR(20)   NOT NULL DEFAULT 'user',
    is_active           TINYINT(1)    NOT NULL DEFAULT 1,
    is_deleted          TINYINT(1)    NOT NULL DEFAULT 0,
    profile_photo       VARCHAR(255)  NULL,
    verification_token  VARCHAR(255)  NULL,
    reset_token         VARCHAR(255)  NULL,
    reset_token_expiry  DATETIME      NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login          DATETIME      NULL,
    INDEX idx_users_email    (email),
    INDEX idx_users_role     (role),
    INDEX idx_users_deleted  (is_deleted)
) ENGINE=InnoDB;

-- =============================================================================
-- TABLE: questionnaires
-- One row per health questionnaire session
-- =============================================================================
CREATE TABLE IF NOT EXISTS questionnaires (
    id                        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id                   INT UNSIGNED NOT NULL,

    -- Section 1: Personal
    age                       TINYINT UNSIGNED NULL,
    gender                    VARCHAR(20)  NULL,
    height_cm                 FLOAT        NULL,
    weight_kg                 FLOAT        NULL,
    bmi                       FLOAT        NULL,
    occupation                VARCHAR(100) NULL,
    working_hours_per_day     FLOAT        NULL,

    -- Section 2: Lifestyle
    smoking_status            VARCHAR(50)  NULL,
    alcohol_intake            VARCHAR(50)  NULL,
    sleep_hours               FLOAT        NULL,
    screen_time_hours         FLOAT        NULL,
    stress_level              TINYINT      NULL COMMENT '1-10 scale',
    travel_frequency          VARCHAR(50)  NULL,

    -- Section 3: Food Habits
    diet_type                 VARCHAR(50)  NULL,
    meals_per_day             TINYINT      NULL,
    water_intake_L            FLOAT        NULL,
    fast_food_per_week        TINYINT      NULL,
    sugar_intake              VARCHAR(50)  NULL,
    fruit_veg_servings        TINYINT      NULL,

    -- Section 4: Exercise
    exercise_frequency        VARCHAR(50)  NULL,
    exercise_type             VARCHAR(100) NULL,
    exercise_duration_min     SMALLINT     NULL,
    heart_rate_resting        TINYINT UNSIGNED NULL,

    -- Section 5: Medical History
    existing_diseases         TEXT         NULL,
    current_medications       TEXT         NULL,
    blood_pressure_systolic   SMALLINT     NULL,
    blood_pressure_diastolic  SMALLINT     NULL,
    blood_sugar_fasting       FLOAT        NULL,
    cholesterol_level         FLOAT        NULL,
    vaccination_status        VARCHAR(100) NULL,

    -- Section 6: Family History (boolean flags)
    family_diabetes           TINYINT(1)   DEFAULT 0,
    family_heart_disease      TINYINT(1)   DEFAULT 0,
    family_stroke             TINYINT(1)   DEFAULT 0,
    family_hypertension       TINYINT(1)   DEFAULT 0,
    family_obesity            TINYINT(1)   DEFAULT 0,
    family_kidney_disease     TINYINT(1)   DEFAULT 0,
    family_cancer             TINYINT(1)   DEFAULT 0,
    family_thyroid            TINYINT(1)   DEFAULT 0,
    family_depression         TINYINT(1)   DEFAULT 0,

    -- Section 7: Mental Health
    depression_symptoms       TINYINT(1)   DEFAULT 0,
    anxiety_symptoms          TINYINT(1)   DEFAULT 0,
    mental_health_support     TINYINT(1)   DEFAULT 0,
    meditation_yoga           VARCHAR(50)  NULL,

    -- Section 8: Other
    pregnancy_status          VARCHAR(50)  NULL,
    daily_steps               INT UNSIGNED NULL,

    -- State
    is_complete               TINYINT(1)   NOT NULL DEFAULT 0,
    created_at                DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_questionnaires_user (user_id),
    INDEX idx_questionnaires_complete (is_complete)
) ENGINE=InnoDB;

-- =============================================================================
-- TABLE: predictions
-- One row per completed prediction session
-- =============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id                    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id               INT UNSIGNED NOT NULL,
    questionnaire_id      INT UNSIGNED NOT NULL,

    -- Disease probabilities (0.0 – 100.0)
    diabetes_prob         FLOAT NULL,
    heart_disease_prob    FLOAT NULL,
    stroke_prob           FLOAT NULL,
    hypertension_prob     FLOAT NULL,
    obesity_prob          FLOAT NULL,
    kidney_disease_prob   FLOAT NULL,
    fatty_liver_prob      FLOAT NULL,
    depression_prob       FLOAT NULL,
    sleep_disorder_prob   FLOAT NULL,
    thyroid_prob          FLOAT NULL,

    -- Health scores (0.0 – 100.0)
    overall_health_score  FLOAT NULL,
    lifestyle_score       FLOAT NULL,
    fitness_score         FLOAT NULL,
    diet_score            FLOAT NULL,
    mental_health_score   FLOAT NULL,
    sleep_score           FLOAT NULL,
    hydration_score       FLOAT NULL,
    exercise_score        FLOAT NULL,

    -- XAI artefact file paths
    shap_summary_path     VARCHAR(512) NULL,
    shap_force_path       VARCHAR(512) NULL,
    shap_waterfall_path   VARCHAR(512) NULL,
    lime_explanation_path VARCHAR(512) NULL,

    -- SHAP top factor JSON blobs
    top_positive_factors  TEXT         NULL,
    top_negative_factors  TEXT         NULL,

    -- Model metadata
    model_version         VARCHAR(50)  NULL,
    model_name            VARCHAR(100) NULL,

    created_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)          REFERENCES users(id)           ON DELETE CASCADE,
    FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(id)  ON DELETE CASCADE,
    INDEX idx_predictions_user (user_id),
    INDEX idx_predictions_date (created_at)
) ENGINE=InnoDB;

-- =============================================================================
-- TABLE: recommendations
-- Personalised health recommendations per prediction
-- =============================================================================
CREATE TABLE IF NOT EXISTS recommendations (
    id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prediction_id    INT UNSIGNED NOT NULL,
    user_id          INT UNSIGNED NOT NULL,
    category         VARCHAR(60)  NOT NULL,
    title            VARCHAR(200) NOT NULL,
    description      TEXT         NOT NULL,
    priority         TINYINT      NOT NULL DEFAULT 5 COMMENT '1=highest, 10=lowest',
    icon             VARCHAR(60)  NULL,
    related_disease  VARCHAR(100) NULL,
    is_completed     TINYINT(1)   NOT NULL DEFAULT 0,
    completed_at     DATETIME     NULL,
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE,
    INDEX idx_rec_prediction (prediction_id),
    INDEX idx_rec_user       (user_id)
) ENGINE=InnoDB;

-- =============================================================================
-- TABLE: reports
-- Generated PDF report metadata
-- =============================================================================
CREATE TABLE IF NOT EXISTS reports (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       INT UNSIGNED NOT NULL,
    prediction_id INT UNSIGNED NOT NULL,
    file_name     VARCHAR(255) NOT NULL,
    file_path     VARCHAR(512) NOT NULL,
    file_size     INT UNSIGNED NULL COMMENT 'bytes',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE,
    INDEX idx_reports_user (user_id)
) ENGINE=InnoDB;

-- =============================================================================
-- TABLE: model_logs
-- ML training run history
-- =============================================================================
CREATE TABLE IF NOT EXISTS model_logs (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    disease           VARCHAR(100) NOT NULL,
    algorithm         VARCHAR(100) NOT NULL,
    version           VARCHAR(50)  NOT NULL,
    is_active         TINYINT(1)   NOT NULL DEFAULT 0,
    model_path        VARCHAR(512) NULL,
    accuracy          FLOAT        NULL,
    `precision`       FLOAT        NULL,
    recall            FLOAT        NULL,
    f1_score          FLOAT        NULL,
    roc_auc           FLOAT        NULL,
    extra_metrics     TEXT         NULL COMMENT 'JSON blob',
    training_samples  INT UNSIGNED NULL,
    training_duration FLOAT        NULL COMMENT 'seconds',
    trained_by        VARCHAR(100) NULL,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ml_disease  (disease),
    INDEX idx_ml_active   (is_active)
) ENGINE=InnoDB;

-- =============================================================================
-- SEED: default admin account
-- Password: Admin@1234  (hashed with bcrypt – update after first login)
-- =============================================================================
INSERT IGNORE INTO admins (full_name, email, password_hash)
VALUES (
    'System Admin',
    'admin@healthai.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhL3XQE7zrm.xRrSN4WkKK'
);

-- =============================================================================
-- End of schema.sql
-- =============================================================================
