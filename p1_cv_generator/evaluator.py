import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# =========================
# MAIN EVALUATION
# =========================
def evaluate_cv(cv_text):

    prompt = f"""
You are a senior HR expert.

Evaluate this CV strictly.

Return ONLY valid JSON.

CV:
{cv_text}

JSON FORMAT:
{{
  "score": 0,
  "verdict": "",
  "grade": "",
  "summary": "",
  "ats_score": 0,
  "ats_feedback": "",
  "nigerian_market_fit": 0,
  "nigerian_market_feedback": "",
  "strengths": [],
  "weaknesses": [],
  "improvements": []
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Return ONLY valid JSON. No explanation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1500
        )

        raw = response.choices[0].message.content.strip()

        return safe_json_parse(raw)

    except Exception as e:
        print(f"Evaluation error: {e}")

        # LOCAL FALLBACK
        return default_evaluation(cv_text)


# =========================
# SAFE JSON PARSER
# =========================
def safe_json_parse(text):

    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        fixed = try_fix_json(text)

        try:
            return json.loads(fixed)

        except:
            return default_evaluation()


# =========================
# SIMPLE JSON FIXER
# =========================
def try_fix_json(text):

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        return text[start:end+1]

    return text


# =========================
# LOCAL FALLBACK EVALUATION
# =========================
def default_evaluation(cv_text=""):

    text = cv_text.lower()

    score = 0
    strengths = []
    weaknesses = []
    improvements = []

    # CONTACT
    if "@" in text:
        score += 10
        strengths.append("Email address included")
    else:
        weaknesses.append("Missing email address")

    # PHONE
    if "+234" in text or "080" in text or "081" in text:
        score += 10
        strengths.append("Phone number included")
    else:
        weaknesses.append("Missing phone number")

    # SKILLS
    if "skills" in text:
        score += 15
        strengths.append("Skills section included")
    else:
        weaknesses.append("Skills section missing")
        improvements.append("Add a strong skills section")

    # EXPERIENCE
    if "experience" in text:
        score += 20
        strengths.append("Work experience provided")
    else:
        weaknesses.append("No work experience section")
        improvements.append("Include relevant work experience")

    # EDUCATION
    if "education" in text:
        score += 15
        strengths.append("Education section included")
    else:
        weaknesses.append("Education section missing")

    # CERTIFICATIONS
    if "certification" in text:
        score += 10
        strengths.append("Certifications included")

    # ACHIEVEMENTS
    if "achievement" in text:
        score += 10
        strengths.append("Achievements included")

    # SUMMARY
    if "summary" in text:
        score += 10
        strengths.append("Professional summary included")

    # LIMIT SCORE
    if score > 100:
        score = 100

    # VERDICT
    if score >= 75:
        verdict = "Pass"
        grade = "A"

    elif score >= 50:
        verdict = "Needs Work"
        grade = "B"

    else:
        verdict = "Poor"
        grade = "C"

    return {
        "score": score,
        "verdict": verdict,
        "grade": grade,
        "summary": f"This CV scored {score}% based on structure and completeness.",
        "ats_score": score,
        "ats_feedback": "Basic ATS evaluation completed locally.",
        "nigerian_market_fit": score,
        "nigerian_market_feedback": "Local evaluation mode used.",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improvements": improvements
    }