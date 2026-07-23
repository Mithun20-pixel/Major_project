# Explainable AI Framework for Lifestyle-Based Disease Risk Prediction

> **Production-quality Flask + ML web application predicting risk for 10 chronic diseases
> using XGBoost, LightGBM, SHAP, and LIME with a premium glassmorphism UI.**

---

## 🚀 Quick Start (Development)

### Prerequisites
- Python 3.11+
- MySQL 8.0+ (or Docker)
- pip / venv

### 1. Clone and set up the environment

```bash
git clone <repo-url>
cd explainable-ai-health

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux

# Edit .env with your MySQL credentials and SMTP settings
```

### 3. Set up the MySQL database

```bash
# Create database from schema
mysql -u root -p < database/schema.sql
```

### 4. Apply Flask-Migrate migrations

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Run the development server

```bash
flask run
# Open http://localhost:5000
```

---

## 🐳 Docker Quick Start

```bash
# Copy and configure .env
copy .env.example .env

# Start all services (MySQL + Flask)
docker-compose up -d

# Check logs
docker-compose logs -f app

# Open http://localhost:8000
```

---

## 📁 Project Structure

```
explainable-ai-health/
│
├── app.py                    # Flask application factory
├── config.py                 # Dev / Test / Production configs
├── requirements.txt          # Python dependencies
├── Dockerfile                # Production Docker image
├── docker-compose.yml        # MySQL + App orchestration
├── .env.example              # Environment variable template
│
├── database/
│   └── schema.sql            # Full normalized MySQL schema
│
├── models/                   # SQLAlchemy ORM models
│   ├── user.py               # User with bcrypt, BMI helpers
│   ├── questionnaire.py      # 8-section health questionnaire
│   ├── prediction.py         # Disease probabilities + health scores
│   ├── recommendation.py     # Personalised recommendations
│   ├── report.py             # PDF report metadata
│   ├── model_log.py          # ML training run history
│   └── admin.py              # Separate admin user model
│
├── routes/                   # Flask Blueprints
│   ├── auth.py               # Register / Login / Email verify / Reset
│   ├── main.py               # Dashboard / Profile / History / Download
│   ├── predict.py            # 7-step questionnaire wizard
│   ├── admin.py              # Admin panel
│   └── api.py                # JSON REST endpoints for charts
│
├── services/
│   └── prediction_service.py # ML orchestration + recommendations
│
├── forms/                    # Flask-WTF forms with validators
│   ├── auth.py
│   ├── questionnaire.py
│   └── profile.py
│
├── utils/
│   ├── email_utils.py        # Verification / Reset emails
│   └── file_utils.py         # Secure file upload helpers
│
├── ml/                       # Machine Learning module (Phase 3)
│   └── saved_models/         # Trained model artifacts
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Master layout (dark/light toggle)
│   ├── main/                 # Landing, dashboard, profile, history
│   ├── auth/                 # Login, register, forgot/reset password
│   ├── predict/              # 7-step wizard + results
│   ├── admin/                # Admin panel templates
│   └── errors/               # 400 / 403 / 404 / 500 pages
│
├── static/
│   ├── css/main.css          # Full design system (glassmorphism)
│   └── js/                   # Dashboard charts, wizard logic
│
├── reports/                  # Generated PDF reports
├── uploads/                  # User uploads
└── datasets/                 # ML training datasets
```

---

## 🧩 Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **1** | ✅ Done | Project setup, DB design, Flask factory, all models, routes, base UI |
| **2** | ⏳ Next | Full authentication templates, questionnaire wizard UI, dashboard |
| **3** | 🔲 Todo | ML model training, SHAP/LIME integration, real predictions |
| **4** | 🔲 Todo | PDF report generation, health score gauges, recommendations UI |
| **5** | 🔲 Todo | Admin panel, model retraining, dataset management |
| **6** | 🔲 Todo | Testing, Docker production hardening, deployment |

---

## 🔐 Default Admin Credentials

After running `schema.sql`:
- **Email**: `admin@healthai.com`
- **Password**: `Admin@1234`

> ⚠️ Change this immediately in production!

---

## 🩺 Diseases Predicted

| Disease | Key Risk Factors |
|---------|-----------------|
| Diabetes | BMI, blood sugar, diet, family history |
| Heart Disease | Cholesterol, smoking, BP, stress |
| Stroke | Hypertension, smoking, age |
| Hypertension | BP, salt, weight, genetics |
| Obesity | Diet, exercise, metabolism |
| Kidney Disease | Diabetes, BP, hydration |
| Fatty Liver | BMI, alcohol, sugar |
| Depression | Stress, sleep, social factors |
| Sleep Disorder | Screen time, stress, BMI |
| Thyroid Disease | Genetics, gender |

---

## ⚕️ Medical Disclaimer

This application is for **educational purposes only** and does **not** constitute medical advice.
Always consult a qualified healthcare professional for diagnosis and treatment.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, Flask 3.0, Gunicorn |
| Database | MySQL 8.0, SQLAlchemy, Flask-Migrate |
| Auth | Flask-Login, Flask-WTF (CSRF), bcrypt |
| ML | XGBoost, LightGBM, scikit-learn |
| XAI | SHAP, LIME |
| Frontend | HTML5, Bootstrap 5.3, Chart.js |
| PDF | ReportLab |
| Deploy | Docker, docker-compose |
