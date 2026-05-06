# P3  Job Match Calculator

Part of the **CV Rating Engine** — Nigerian Job Fit Scoring System

---

## What This Module Does

Compares a candidate's CV against a job description and returns a detailed match analysis powered by AI.

---

## Features

- Match percentage (0–100%)
- Matched and missing skills with priority ranking
- Keyword frequency analysis
- Experience gap detection
- CV length checker
- Role seniority matching
- Section scores (Skills, Experience, Education)
- Weighted scoring system (AI + skill ratio)
- PDF and DOCX CV upload support
- Auto-fill job description from P5 browser extension
- Auto-saves results to P4 dashboard

---

## Tech Stack

- Python 3.10
- Flask (web server)
- Groq API — llama-3.3-70b (primary AI)
- Gemini API — gemini-2.5-flash (backup AI)
- pdfplumber (PDF reading)
- python-docx (Word document reading)
- python-dotenv (environment variables)

---

## Setup

1. Install dependencies: pip install -r requirements.txt
2. Create a `.env` file: GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
3. Run the app: python app.py
4. Open browser at: http://127.0.0.1:5000
