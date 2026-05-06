def compute_match(gemini_result):

    score = gemini_result.get("score", 0)
    matched = gemini_result.get("matched_skills", [])
    missing = gemini_result.get("missing_skills", [])

    section_scores = gemini_result.get("section_scores", {})
    suggestions = gemini_result.get("suggestions", [])
    summary = gemini_result.get("summary", "")

    keyword_frequency = gemini_result.get("keyword_frequency", {})
    experience_gap = gemini_result.get("experience_gap", {})
    cv_length = gemini_result.get("cv_length", {})
    seniority = gemini_result.get("seniority", {})

    # Normalize
    matched = [s.lower() for s in matched]
    missing = [s.lower() for s in missing]

    # Skill ratio (NEW)
    skill_ratio = len(matched) / (len(matched) + len(missing) + 1)

    final_score = round((score * 0.7) + (skill_ratio * 100 * 0.3))

    # Fit classification
    if final_score >= 80:
        fit_level = "Strong Fit"
        fit_color = "green"
    elif final_score >= 60:
        fit_level = "Moderate Fit"
        fit_color = "orange"
    else:
        fit_level = "Low Fit"
        fit_color = "red"

    # Sort missing skills
    sorted_missing = sorted(
        missing,
        key=lambda s: keyword_frequency.get(s.lower(), 0),
        reverse=True
    )

    structured_missing = []
    for skill in sorted_missing:
        freq = keyword_frequency.get(skill.lower(), 0)

        if freq >= 5:
            priority = "high"
        elif freq >= 3:
            priority = "medium"
        else:
            priority = "low"

        structured_missing.append({
            "skill": skill,
            "priority": priority
        })

    return {
        "score": score,
        "final_score": final_score,
        "fit_level": fit_level,
        "fit_color": fit_color,

        "matched_skills": matched,
        "missing_skills": structured_missing,

        "skill_ratio": round(skill_ratio, 2),

        "totals": {
            "matched": len(matched),
            "missing": len(missing)
        },

        "section_scores": section_scores,

        "analysis": {
            "experience_gap": experience_gap,
            "cv_length": cv_length,
            "seniority": seniority
        },

        "suggestions": suggestions,
        "summary": summary
    }