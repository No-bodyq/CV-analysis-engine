import os
import json
import re
import time
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

MOCK_MODE = False

# Initialize both clients
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def analyze_match(cv_text, job_text):
    """
    Main function — tries Groq first, then Gemini, then mock data.
    """
    if not cv_text or not job_text:
        raise ValueError("CV text and Job description cannot be empty")

    if MOCK_MODE:
        return mock_response()

    prompt = build_prompt(cv_text, job_text)

    # Try Groq first (fastest and most reliable)
    print("Trying Groq API...")
    groq_result = try_groq(prompt)
    if groq_result:
        print("Groq API succeeded!")
        return groq_result

    # Try Gemini as backup
    print("Groq failed, trying Gemini API...")
    gemini_result = try_gemini(prompt)
    if gemini_result:
        print("Gemini API succeeded!")
        return gemini_result

    # Last resort — mock data
    print("Both APIs failed, using mock data...")
    return mock_response()


def try_groq(prompt):
    """
    Calls Groq API with llama model.
    Returns parsed result or None if failed.
    """
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Nigerian job market CV analyst. Always return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=2000
        )

        raw = response.choices[0].message.content
        return parse_response(raw)

    except Exception as e:
        print(f"Groq error: {e}")
        return None


def try_gemini(prompt):
    """
    Calls Gemini API as backup.
    Returns parsed result or None if failed.
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return parse_response(response.text)

    except Exception as e:
        print(f"Gemini error: {e}")
        return None


def build_prompt(cv_text, job_text):
    """
    Builds the prompt sent to both APIs.
    """
    return f"""
You are an expert Nigerian job market CV analyst.

Carefully analyze this CV against the job description.
Return ONLY valid JSON. No markdown, no explanation, no backticks.

Exact structure required:
{{
  "score": 0-100,
  "matched_skills": [],
  "missing_skills": [],
  "section_scores": {{
    "skills": 0-100,
    "experience": 0-100,
    "education": 0-100
  }},
  "suggestions": [],
  "summary": "",
  "keyword_frequency": {{}},
  "experience_gap": {{
    "required_years": 0,
    "candidate_years": 0,
    "gap": 0,
    "verdict": ""
  }},
  "cv_length": {{
    "word_count": 0,
    "verdict": "",
    "recommendation": ""
  }},
  "seniority": {{
    "job_level": "",
    "candidate_level": "",
    "match": true,
    "verdict": ""
  }}
}}

CV:
{cv_text}

JOB DESCRIPTION:
{job_text}
"""


def parse_response(text):
    """
    Parses API response text into a Python dictionary.
    """
    try:
        cleaned = (
            text.strip()
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        # Try direct JSON parse
        return json.loads(cleaned)

    except json.JSONDecodeError:
        try:
            # Try regex extraction as fallback
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        print("Could not parse JSON response")
        return None


def mock_response():
    """
    Returns fake data for development/testing.
    """
    return {
        "score": 72,
        "matched_skills": ["Python", "SQL", "Data Analysis"],
        "missing_skills": ["AWS", "Power BI"],
        "section_scores": {
            "skills": 75,
            "experience": 70,
            "education": 80
        },
        "suggestions": [
            "Add measurable achievements",
            "Include cloud technologies",
            "Improve CV formatting"
        ],
        "summary": "Strong foundation but missing key tools",
        "keyword_frequency": {
            "Python": 3,
            "AWS": 2
        },
        "experience_gap": {
            "required_years": 3,
            "candidate_years": 2,
            "gap": 1,
            "verdict": "1 year short"
        },
        "cv_length": {
            "word_count": 300,
            "verdict": "Good",
            "recommendation": "Length is appropriate"
        },
        "seniority": {
            "job_level": "Mid-level",
            "candidate_level": "Junior",
            "match": False,
            "verdict": "Applying above level"
        }
    }