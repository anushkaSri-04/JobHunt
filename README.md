# JobHunt – Personal Job Search & Matching System

JobHunt is a Python-based job discovery and matching application that automates the process of finding relevant job opportunities across multiple company career platforms.

It fetches job postings from Greenhouse, Lever and Ashby, filters them based on job roles, locations and posting freshness, and calculates a skill-match percentage by comparing job requirements against a user's technical profile.

The application provides a password-protected web dashboard to review opportunities, identify matched and missing skills, track application status, and receive personalized job digests through Gmail.

## Features

### 1. Multi-Source Job Discovery
- Fetches job postings from Greenhouse, Lever and Ashby.
- Supports multiple configured company career boards.
- Normalizes job postings into a common format.
- Avoids duplicate job entries.

### 2. Configurable Job Filtering
- Regex-based job title inclusion and exclusion.
- Location-based filtering.
- Remote job support.
- Configurable job freshness limit.
- Filters irrelevant and unsuitable job titles.

### 3. Skill-Based Job Matching
- Dictionary-based technical skill extraction.
- Matches job requirements against the user's skill profile.
- Calculates a match percentage.
- Identifies matched and missing skills.
- Separates required skills from nice-to-have skills.
- Uses deterministic matching without requiring an LLM.

### 4. Web Dashboard
- Password-protected authentication.
- Displays available job opportunities.
- Sorts jobs by match percentage.
- Shows company name, location and experience requirements.
- Displays matched and missing skill badges.
- Provides direct links to original job postings.
- Tracks Applied and Skipped job statuses.

### 5. Email Notifications
- Gmail SMTP integration.
- Sends personalized job digests.
- Supports a configurable matching threshold.
- Sends up to five eligible job opportunities.
- Includes a link to open the JobHunt dashboard.

### 6. Database Management
- SQLite database using SQLAlchemy ORM.
- Stores job postings, companies, user skills and pipeline execution history.
- Maintains application statuses and email tracking information.

---

## Tech Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend | FastAPI |
| Database | SQLite, SQLAlchemy |
| Frontend | HTML, Jinja2, Tailwind CSS |
| Job Filtering | Python Regex |
| Configuration | YAML, JSON |
| API Integration | Greenhouse, Lever, Ashby |
| Email | Gmail SMTP |
| Authentication | Argon2, SessionMiddleware |
| Testing | Pytest |
| Server | Uvicorn |

---

## Project Architecture

```text
JobHunt
   |
   |-- ATS Job Fetching
   |      |-- Greenhouse
   |      |-- Lever
   |      |-- Ashby
   |
   |-- Job Processing Engine
   |      |-- Job Normalization
   |      |-- Title Filtering
   |      |-- Location Filtering
   |      |-- Freshness Filtering
   |      |-- Deduplication
   |
   |-- Skill Matching Engine
   |      |-- Skill Dictionary
   |      |-- Skill Extraction
   |      |-- Required / Optional Classification
   |      |-- Profile Matching
   |      |-- Match Percentage
   |
   |-- SQLite Database
   |
   |-- Application Layer
          |-- FastAPI Dashboard
          |-- Job Status Tracking
          |-- Gmail Email Digest
```

---

## Project Structure

```text
jobHunt/
│
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py
│   ├── runner.py
│   ├── main.py
│   ├── emailer.py
│   │
│   └── templates/
│       ├── base.html
│       ├── login.html
│       └── feed.html
│
├── engine/
│   ├── __init__.py
│   ├── digest.py
│   ├── fetch.py
│   ├── llm.py
│   ├── mailer.py
│   ├── mock.py
│   ├── prefilter.py
│   ├── providers.py
│   ├── skills.py
│   └── skills.yaml
│
├── tests/
│
├── manage.py
├── config.yaml
├── companies.yaml
├── profile.json
├── requirements.txt
├── .env
├── jobhunt.db
└── README.md
```

---

## Installation and Setup

### Prerequisites

- Python 3.10 or later.
- Git.
- Gmail account with an App Password for SMTP email delivery.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/JobHunt.git
cd JobHunt
```

### 2. Create a virtual environment

Windows CMD:

```cmd
python -m venv .venv
```

Activate it:

```cmd
.venv\Scripts\activate
```

### 3. Install dependencies

```cmd
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root.

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_gmail_app_password
MAIL_TO=your_email@gmail.com

APP_URL=http://127.0.0.1:8000

SESSION_SECRET=your_long_random_secret
DATABASE_URL=sqlite:///jobhunt.db
```

Replace the placeholder values with your own credentials.

**Important:** Never commit your `.env` file, Gmail App Password, session secret or personal credentials to GitHub.

### 5. Configure your job preferences

Edit `config.yaml` to customize:

- Job title inclusion patterns.
- Job title exclusion patterns.
- Preferred locations.
- Remote job preferences.
- Maximum job age.
- Skill matching threshold.

Edit `companies.yaml` to configure the company career boards you want to track.

Edit `profile.json` to define your personal technical skills and job-search profile.

---

## Running the Application

JobHunt uses manual execution. Run the following commands whenever you want to discover new jobs and receive an email digest.

### Step 1. Fetch and process jobs

```cmd
.venv\Scripts\python.exe manage.py run
```

This command:

1. Fetches jobs from configured ATS platforms.
2. Applies title, location and freshness filters.
3. Removes duplicates.
4. Extracts and matches technical skills.
5. Calculates match percentages.
6. Saves new jobs in the database.

### Step 2. Send the email digest

```cmd
.venv\Scripts\python.exe manage.py email
```

This sends up to five eligible jobs based on the configured matching threshold.

### Step 3. Start the web dashboard

```cmd
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open the application:

```text
http://127.0.0.1:8000
```

Log in using your configured application credentials.

---

## Dashboard Functionality

The dashboard provides:

- Job listings sorted by match percentage.
- Company and location information.
- Skill-match percentage.
- Matched and missing skill indicators.
- Required and nice-to-have skill classification.
- Direct links to company job postings.
- Applied and Skipped status tracking.

All non-skipped jobs are displayed, including jobs below the email matching threshold.

---

## Testing

Run the automated test suite:

```cmd
.venv\Scripts\python.exe -m pytest -q
```

Compile the application modules:

```cmd
.venv\Scripts\python.exe -m compileall app engine
```

The project has previously passed **86 automated tests**.

---

## Design Decisions

### Why dictionary-based skill matching?

JobHunt uses deterministic skill extraction and matching instead of requiring an LLM.

This approach provides:
- Predictable results.
- Lower operating costs.
- Explainable matching decisions.
- Easy customization through a YAML skill dictionary.

The limitation is that skills not present in the dictionary may not be detected until the dictionary is updated.

### Why multiple ATS integrations?

Companies use different applicant tracking systems. Integrating Greenhouse, Lever and Ashby provides a centralized way to discover opportunities across multiple career boards.

### Why a local SQLite database?

SQLite provides a lightweight database for a single-user application without requiring a separate database server.

---

## Current Project Scope

JobHunt V1 focuses on:

- Multi-source job discovery.
- Configurable job filtering.
- Dictionary-based skill extraction and matching.
- A password-protected job dashboard.
- Application status tracking.
- Personalized Gmail job digests.

The application is designed for manual execution rather than continuous background scheduling.

---

## Future Enhancements

Potential future improvements include:

- LLM-powered skill extraction.
- Resume parsing and personalized job recommendations.
- Automated cover letter generation.
- Resume bullet recommendations.
- Learning recommendations based on missing skills.

These features are outside the current V1 scope.

---

## Author

**Anushka Srivastava**

B.Tech – Artificial Intelligence and Data Science

GitHub: https://github.com/anushkaSri-04

---

## License

This project is intended for educational and personal portfolio purposes. Add an appropriate open-source license before permitting reuse or redistribution.