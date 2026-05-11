import os
import re
import time
from datetime import datetime, timedelta
from groq import Groq
from google import genai
from dotenv import load_dotenv

load_dotenv()

groq_api = os.getenv("GROQ_API_KEY")
gemini_api = os.getenv("GEMINI_API_KEY")

groq_client = Groq(api_key=groq_api) if groq_api else None
gemini_client = genai.Client(api_key=gemini_api) if gemini_api else None

# =============================
# CIRCUIT BREAKER
# =============================
api_status = {
    "groq_failed": False,
    "groq_retry_after": None,
    "gemini_failed": False,
    "gemini_retry_after": None
}


def is_api_available(api_name):
    """Check if API is available or still in cooldown."""
    failed_key = f"{api_name}_failed"
    retry_key = f"{api_name}_retry_after"

    if not api_status[failed_key]:
        return True

    retry_after = api_status[retry_key]
    if retry_after and datetime.now() > retry_after:
        # Cooldown expired — reset and try again
        api_status[failed_key] = False
        api_status[retry_key] = None
        print(f"{api_name.upper()} cooldown expired — retrying...")
        return True

    remaining = (retry_after - datetime.now()).seconds // 60
    print(f"{api_name.upper()} in cooldown — {remaining} mins remaining. Using local builder.")
    return False


def mark_api_failed(api_name, cooldown_minutes=30):
    """Mark API as failed and set cooldown."""
    api_status[f"{api_name}_failed"] = True
    api_status[f"{api_name}_retry_after"] = datetime.now() + timedelta(minutes=cooldown_minutes)
    print(f"{api_name.upper()} marked as failed. Will retry in {cooldown_minutes} mins.")


# =============================
# LOCAL CV BUILDER
# =============================
def build_local_cv(user_data):
    """
    Builds a structured CV directly from user input using regex.
    Used when both APIs are unavailable.
    """
    name = user_data.get("name", "")
    location = user_data.get("location", "")
    email = user_data.get("email", "")
    phone = user_data.get("phone", "")
    linkedin = user_data.get("linkedin", "")
    dob = user_data.get("dob", "")
    summary = user_data.get("summary", "")
    skills_raw = user_data.get("skills", "")
    experience_raw = user_data.get("experience", "")
    education_raw = user_data.get("education", "")
    certifications_raw = user_data.get("certifications", "")
    job_title = user_data.get("job_title", "")

    # ── Parse Skills ──
    skills = []
    for skill in re.split(r'[,;\n]+', skills_raw):
        skill = skill.strip().lstrip("-•").strip()
        if skill:
            skills.append(skill)

    skills_text = "\n".join([f"SKILL: {s}" for s in skills])

    # ── Parse Education ──
    edu_lines = [l.strip() for l in education_raw.split("\n") if l.strip()]

    school = ""
    degree = ""
    grade = ""
    dates = ""

    for line in edu_lines:
        line_lower = line.lower()

        # Detect school
        if any(word in line_lower for word in [
            "university", "college", "polytechnic",
            "institute", "school", "academy"
        ]):
            school = line

        # Detect degree
        elif any(word in line_lower for word in [
            "bsc", "b.sc", "ba", "b.a", "beng", "b.eng",
            "hnd", "ond", "msc", "m.sc", "bachelor",
            "master", "phd", "doctor", "diploma"
        ]):
            degree = line

        # Detect grade
        elif any(word in line_lower for word in [
            "first", "second", "third", "class",
            "upper", "lower", "cgpa", "grade", "distinction", "credit"
        ]):
            grade = line

        # Detect dates
        elif re.search(r'\d{4}', line):
            dates = line

        # If nothing detected, use as school
        elif not school:
            school = line

    edu_text = f"""SCHOOL: {school}
DEGREE: {degree}
GRADE: {grade}
DATES: {dates}"""

    # ── Parse Experience ──
    exp_lines = [l.strip() for l in experience_raw.split("\n") if l.strip()]

    jobs = []
    current_job = None

    for line in exp_lines:
        line_lower = line.lower()

        # Detect date range — likely a job entry separator
        date_match = re.search(
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|'
            r'march|april|june|july|august|september|october|november|december)'
            r'.{0,20}\d{4}',
            line_lower
        )

        # Detect bullet points
        if line.startswith(("-", "•", "*")):
            if current_job:
                current_job["bullets"].append(line.lstrip("-•*").strip())

        # Detect company line (contains — or -)
        elif "—" in line or ("–" in line and not date_match):
            if current_job:
                current_job["company"] = line

        # Detect date line
        elif date_match:
            if current_job is None:
                current_job = {
                    "title": job_title or "Professional",
                    "company": "",
                    "location": location,
                    "dates": line,
                    "bullets": []
                }
            else:
                current_job["dates"] = line

        # Detect job title (all caps or title case without dates)
        elif line.isupper() or (line.istitle() and len(line.split()) <= 5):
            if current_job:
                jobs.append(current_job)
            current_job = {
                "title": line,
                "company": "",
                "location": location,
                "dates": "",
                "bullets": []
            }

        # Otherwise treat as company or description
        else:
            if current_job:
                if not current_job["company"]:
                    current_job["company"] = line
                else:
                    current_job["bullets"].append(line)

    if current_job:
        jobs.append(current_job)

    # If no jobs detected, create one from raw text
    if not jobs and experience_raw:
        jobs = [{
            "title": job_title or "Professional",
            "company": experience_raw[:100],
            "location": location,
            "dates": "",
            "bullets": [experience_raw[100:200]] if len(experience_raw) > 100 else []
        }]

    exp_blocks = []
    for job in jobs:
        bullets = "\n".join([f"- {b}" for b in job["bullets"]])
        exp_blocks.append(f"""JOB:
TITLE: {job['title']}
COMPANY: {job['company']}
LOCATION: {job['location']}
DATES: {job['dates']}
BULLETS:
{bullets}
END_JOB""")

    exp_text = "\n".join(exp_blocks)

    # ── Parse Certifications ──
    certs = []
    for cert in re.split(r'[,;\n]+', certifications_raw):
        cert = cert.strip().lstrip("-•").strip()
        if cert:
            certs.append(cert)

    certs_text = "\n".join([f"CERT: {c}" for c in certs])

    # ── Build final structured text ──
    return f"""========================
HEADER
========================
NAME: {name}
ADDRESS: {location}
EMAIL: {email}
PHONE: {phone}
LINKEDIN: {linkedin}
DOB: {dob}

========================
SUMMARY
========================
TEXT: {summary if summary else f'Motivated {job_title or "professional"} with relevant skills and experience seeking opportunities to contribute to organizational growth.'}

========================
SKILLS
========================
{skills_text}

========================
EDUCATION
========================
{edu_text}

========================
EXPERIENCE
========================
{exp_text}

========================
CERTIFICATIONS
========================
{certs_text}
"""


# =============================
# MAIN GENERATOR
# =============================
def generate_cv(user_data):

    start_time = time.time()

    prompt = build_prompt(user_data)

    # ── Try Groq ──
    if groq_client and is_api_available("groq"):
        try:
            print("Trying Groq API...")
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an elite Nigerian CV writer.
Follow the EXACT structure given. Use labels exactly as written.
Do NOT add extra text or change the format."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )

            cv_text = response.choices[0].message.content.strip()
            print("Groq API succeeded!")
            return {
                "success": True,
                "provider": "groq",
                "cv_text": cv_text,
                "timestamp": datetime.now().isoformat(),
                "processing_time": round(time.time() - start_time, 2),
                "error": None
            }

        except Exception as e:
            print(f"Groq error: {e}")
            mark_api_failed("groq", cooldown_minutes=30)

    # ── Try Gemini ──
    if gemini_client and is_api_available("gemini"):
        try:
            print("Trying Gemini API...")
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            cv_text = response.text.strip()
            print("Gemini API succeeded!")
            return {
                "success": True,
                "provider": "gemini",
                "cv_text": cv_text,
                "timestamp": datetime.now().isoformat(),
                "processing_time": round(time.time() - start_time, 2),
                "error": None
            }

        except Exception as e:
            print(f"Gemini error: {e}")
            mark_api_failed("gemini", cooldown_minutes=30)

    # ── Local fallback ──
    print("Using LOCAL CV BUILDER — building from user input...")
    cv_text = build_local_cv(user_data)

    return {
        "success": True,
        "provider": "local",
        "cv_text": cv_text,
        "timestamp": datetime.now().isoformat(),
        "processing_time": round(time.time() - start_time, 2),
        "error": "APIs unavailable — used local builder"
    }


def build_prompt(user_data):
    """Builds the structured prompt for AI."""

    skills_formatted = "\n".join([
        f"SKILL: {s.strip()}"
        for s in user_data.get('skills', '').split(',')
        if s.strip()
    ])

    certs_formatted = "\n".join([
        f"CERT: {c.strip()}"
        for c in user_data.get('certifications', '').split(',')
        if c.strip()
    ])

    return f"""Generate a professional Nigerian CV using EXACTLY this structure:

========================
HEADER
========================
NAME: {user_data.get('name', '')}
ADDRESS: {user_data.get('location', '')}
EMAIL: {user_data.get('email', '')}
PHONE: {user_data.get('phone', '')}
LINKEDIN: {user_data.get('linkedin', '')}
DOB: {user_data.get('dob', '')}

========================
SUMMARY
========================
TEXT: Write a professional 3-4 sentence summary for {user_data.get('job_title', 'a professional')}. Background: {user_data.get('summary', '')}

========================
SKILLS
========================
{skills_formatted}

========================
EDUCATION
========================
SCHOOL: Extract school from: {user_data.get('education', '')}
DEGREE: Extract degree from: {user_data.get('education', '')}
GRADE: Extract grade from: {user_data.get('education', '')}
DATES: Extract dates from: {user_data.get('education', '')}

========================
EXPERIENCE
========================
JOB:
TITLE: Extract job title from: {user_data.get('experience', '')}
COMPANY: Extract company from: {user_data.get('experience', '')}
LOCATION: Extract location from: {user_data.get('experience', '')}
DATES: Extract dates from: {user_data.get('experience', '')}
BULLETS:
- Extract first achievement from: {user_data.get('experience', '')}
- Extract second achievement from: {user_data.get('experience', '')}
- Extract third achievement from: {user_data.get('experience', '')}
END_JOB

========================
CERTIFICATIONS
========================
{certs_formatted}
"""