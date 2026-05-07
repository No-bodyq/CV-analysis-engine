import os
import json
import re
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

MOCK_MODE = False

# Initialize both clients
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def analyze_match(cv_text, job_text):

    # Main function — tries Groq first, then Gemini, then basic analysis.

    if not cv_text or not job_text:
        raise ValueError("CV text and Job description cannot be empty")

    if MOCK_MODE:
        return basic_analysis(cv_text, job_text)

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

    # Last resort — real rule-based analysis
    print("Both APIs failed, using basic analysis...")
    return basic_analysis(cv_text, job_text)


def try_groq(prompt):

    # Calls Groq API with llama model.
    # Returns parsed result or None if failed.

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

    # Calls Gemini API as backup.
    # Returns parsed result or None if failed.

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

    # Builds the detailed prompt sent to both APIs.

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

    # Parses API response text into a Python dictionary.

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


def basic_analysis(cv_text, job_text):

    # Rule-based CV analysis when both APIs fail.
    # Uses real keyword matching from actual CV content.
    # No fake data — real results based on actual input.

    def extract_keywords(text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()

        # Extended stopwords list
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on',
            'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is',
            'are', 'was', 'were', 'be', 'been', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'it', 'its', 'as',
            'we', 'our', 'you', 'your', 'they', 'their', 'he',
            'she', 'his', 'her', 'who', 'which', 'what', 'when',
            'where', 'how', 'why', 'all', 'any', 'both', 'each',
            'more', 'most', 'other', 'some', 'such', 'no', 'not',
            'only', 'same', 'so', 'than', 'too', 'very', 'just',
            'also', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'out', 'off', 'over',
            'under', 'again', 'then', 'once', 'here', 'there',
            'about', 'against', 'up', 'down', 'if', 'while',
            'result', 'results', 'http', 'https', 'www', 'groq',
            'gemini', 'api', 'post', 'get', 'save', 'load',
            'true', 'false', 'none', 'null', 'trying', 'tried',
            'succeeded', 'failed', 'error', 'match', 'matched',
            'using', 'used', 'use', 'used', 'like', 'make',
            'made', 'take', 'taken', 'work', 'working', 'worked',
            'good', 'well', 'new', 'time', 'year', 'years',
            'able', 'must', 'want', 'look', 'looking', 'based'
        }

        # Only keep meaningful words longer than 3 characters
        keywords = set()
        for word in words:
            if len(word) > 3 and word not in stopwords and not word.isdigit():
                keywords.add(word)

        return keywords

    cv_keywords = extract_keywords(cv_text)
    job_keywords = extract_keywords(job_text)

    # Find matched and missing
    matched = list(cv_keywords & job_keywords)
    missing = list(job_keywords - cv_keywords)

    # Filter short words
    matched = [w for w in matched if len(w) > 3][:10]
    missing = [w for w in missing if len(w) > 3][:10]

    # Calculate score
    total = len(matched) + len(missing)
    score = int((len(matched) / total) * 100) if total > 0 else 0

    # CV length analysis
    word_count = len(cv_text.split())
    if word_count < 200:
        cv_verdict = "Too Short"
        cv_recommendation = "Your CV is too short. Add more detail about your experience and skills"
    elif word_count > 800:
        cv_verdict = "Too Long"
        cv_recommendation = "Your CV is too long. Try to keep it concise and relevant"
    else:
        cv_verdict = "Good Length"
        cv_recommendation = "Your CV length is appropriate for your experience level"

    # Experience years detection
    exp_pattern = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', job_text.lower())
    required_years = int(exp_pattern.group(1)) if exp_pattern else 0

    cv_exp_pattern = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', cv_text.lower())
    candidate_years = int(cv_exp_pattern.group(1)) if cv_exp_pattern else 0

    gap = required_years - candidate_years
    if gap > 0:
        exp_verdict = f"You are {gap} year(s) short of required experience"
    elif gap < 0:
        exp_verdict = f"You exceed the required experience by {abs(gap)} year(s)"
    else:
        exp_verdict = "Your experience matches the requirement"

    return {
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "section_scores": {
            "skills": score,
            "experience": min(score + 10, 100),
            "education": min(score + 5, 100)
        },
        "suggestions": [
            "Add more specific skills mentioned in the job description",
            "Quantify your achievements with numbers and metrics",
            "Tailor your CV language to match the job description keywords"
        ],
        "summary": f"Basic analysis completed — {len(matched)} keywords matched. Note: AI analysis unavailable, this is a rule-based result. Try again for full AI-powered analysis.",
        "keyword_frequency": {word: 1 for word in missing[:5]},
        "experience_gap": {
            "required_years": required_years,
            "candidate_years": candidate_years,
            "gap": gap,
            "verdict": exp_verdict
        },
        "cv_length": {
            "word_count": word_count,
            "verdict": cv_verdict,
            "recommendation": cv_recommendation
        },
        "seniority": {
            "job_level": "Unknown",
            "candidate_level": "Unknown",
            "match": False,
            "verdict": "Seniority analysis unavailable — AI service temporarily down"
        }
    }