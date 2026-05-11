from cv_parser import parse_cv  # ← changed from parser to cv_parser


def format_cv(raw_cv_text, user_data):

    structured = parse_cv(raw_cv_text)

    formatted_text = build_formatted_cv(structured, user_data)

    return {
        "formatted_text": formatted_text,
        "sections": structured
    }


def build_formatted_cv(sections, user_data):

    lines = []

    # HEADER
    name = user_data.get("name", "").upper()
    email = user_data.get("email", "")
    phone = user_data.get("phone", "")
    location = user_data.get("location", "")
    linkedin = user_data.get("linkedin", "")
    dob = user_data.get("dob", "")

    lines.append(name)
    lines.append("")

    if location:
        lines.append(location)

    contact = " | ".join([c for c in [email, phone] if c])
    if contact:
        lines.append(contact)

    if linkedin:
        lines.append(f"LinkedIn: {linkedin}")

    if dob:
        lines.append(f"DOB: {dob}")

    lines.append("")

    # SUMMARY
    if sections.get("summary"):
        lines.append("PROFESSIONAL SUMMARY")
        lines.append(sections["summary"])
        lines.append("")

    # SKILLS
    skills = sections.get("skills", [])
    if skills:
        lines.append("SKILLS")
        for s in skills:
            # Clean any existing bullet symbols from user input
            clean_skill = s.strip().lstrip("●•-").strip()
            if clean_skill:
                lines.append(f"• {clean_skill}")
        lines.append("")

    # EDUCATION
    education = sections.get("education", [])
    if education:
        lines.append("EDUCATION")
        for edu in education:
            lines.append(edu.get("school", ""))
            lines.append(edu.get("degree", ""))
            lines.append(edu.get("grade", ""))
            lines.append(edu.get("dates", ""))
            lines.append("")

    # EXPERIENCE
    experience = sections.get("experience", [])
    if experience:
        lines.append("WORK EXPERIENCE")
        for job in experience:
            lines.append(job.get("title", "").strip())
            lines.append(job.get("company", "").strip())
            lines.append(job.get("dates", "").strip())
            for b in job.get("bullets", []):
                # Clean existing bullet symbols
                clean_bullet = b.strip().lstrip("●•-").strip()
                if clean_bullet:
                    lines.append(f"• {clean_bullet}")
            lines.append("")

    # CERTIFICATIONS
    certs = sections.get("certifications", [])
    if certs:
        lines.append("CERTIFICATIONS")
        for c in certs:
            lines.append(f"• {c}")

    return "\n".join(lines)