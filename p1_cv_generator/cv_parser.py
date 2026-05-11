import re


def parse_cv(raw_text):
    """
    Parses structured CV text from generator.py
    into a clean Python dictionary.
    Uses line-by-line parsing with label detection.
    """

    lines = [l.strip() for l in raw_text.split("\n")]

    data = {
        "header": {},
        "summary": "",
        "skills": [],
        "education": [],
        "experience": [],
        "certifications": []
    }

    current_section = None
    current_job = None
    collecting_bullets = False

    for line in lines:

        # Skip empty lines and dividers
        if not line or line.startswith("===") or line.startswith("---"):
            continue

       
        # DETECT SECTION HEADERS
      
        upper = line.upper()

        if upper == "HEADER":
            current_section = "header"
            continue

        elif upper == "SUMMARY":
            current_section = "summary"
            continue

        elif upper == "SKILLS":
            current_section = "skills"
            continue

        elif upper == "EDUCATION":
            current_section = "education"
            continue

        elif upper in ["EXPERIENCE", "WORK EXPERIENCE"]:
            current_section = "experience"
            continue

        elif upper in ["CERTIFICATIONS", "CERTIFICATION", "CERTIFICATION & TRAINING"]:
            current_section = "certifications"
            continue

       
        # HEADER SECTION
       
        if current_section == "header":
            for key in ["NAME", "ADDRESS", "EMAIL", "PHONE", "LINKEDIN", "DOB"]:
                if line.upper().startswith(key + ":"):
                    value = line[len(key)+1:].strip()
                    data["header"][key.lower()] = value
                    break

        
        # SUMMARY SECTION
       
        elif current_section == "summary":
            if line.upper().startswith("TEXT:"):
                data["summary"] = line[5:].strip()
            elif data["summary"] and not line.upper().startswith("TEXT:"):
                # Append continuation lines
                data["summary"] += " " + line.strip()

    
        # SKILLS SECTION
      
        elif current_section == "skills":
            if line.upper().startswith("SKILL:"):
                skill = line[6:].strip().lstrip("●•-").strip()
                if skill:
                    data["skills"].append(skill)
            elif line.startswith("-") or line.startswith("•") or line.startswith("●"):
                skill = line.lstrip("-•●").strip()
                if skill and skill.upper() not in ["EDUCATION", "EXPERIENCE", "CERTIFICATIONS"]:
                    data["skills"].append(skill)

      
        # EDUCATION SECTION
       
        elif current_section == "education":

            if line.upper().startswith("SCHOOL:"):
                edu = {
                    "school": line[7:].strip(),
                    "degree": "",
                    "grade": "",
                    "dates": "",
                    "location": ""
                }
                data["education"].append(edu)

            elif data["education"]:
                edu = data["education"][-1]

                if line.upper().startswith("DEGREE:"):
                    edu["degree"] = line[7:].strip()

                elif line.upper().startswith("GRADE:"):
                    edu["grade"] = line[6:].strip()

                elif line.upper().startswith("DATES:"):
                    edu["dates"] = line[6:].strip()

                elif line.upper().startswith("LOCATION:"):
                    edu["location"] = line[9:].strip()

      
        # EXPERIENCE SECTION
        
        elif current_section == "experience":

            if line.upper() == "JOB:":
                current_job = {
                    "title": "",
                    "company": "",
                    "location": "",
                    "dates": "",
                    "bullets": []
                }
                collecting_bullets = False

            elif line.upper() == "END_JOB":
                if current_job:
                    data["experience"].append(current_job)
                    current_job = None
                collecting_bullets = False

            elif current_job is not None:

                if line.upper().startswith("TITLE:"):
                    current_job["title"] = line[6:].strip()

                elif line.upper().startswith("COMPANY:"):
                    current_job["company"] = line[8:].strip()

                elif line.upper().startswith("LOCATION:"):
                    current_job["location"] = line[9:].strip()

                elif line.upper().startswith("DATES:"):
                    current_job["dates"] = line[6:].strip()

                elif line.upper() == "BULLETS:":
                    collecting_bullets = True

                elif collecting_bullets and (
                    line.startswith("-") or line.startswith("•")
                ):
                    bullet = line.lstrip("-•").strip()
                    if bullet:
                        current_job["bullets"].append(bullet)

        # CERTIFICATIONS SECTION
        
        elif current_section == "certifications":

            if line.upper().startswith("CERT:"):
                cert = line[5:].strip()
                if cert:
                    data["certifications"].append(cert)

            elif line.startswith("-") or line.startswith("•"):
                cert = line.lstrip("-•").strip()
                if cert:
                    data["certifications"].append(cert)

    # Save any unclosed job block
    if current_job:
        data["experience"].append(current_job)

    return data