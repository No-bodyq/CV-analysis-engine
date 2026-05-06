import time
import datetime
import traceback

from gemini_service import analyze_match
from matcher import compute_match


def match_cv(cv_text, job_text):
    """
    Main orchestrator for CV-job matching system.
    """

    # -----------------------------
    # Step 1: Validate Inputs
    # -----------------------------
    if not cv_text or not cv_text.strip():
        return error_response("CV text cannot be empty")

    if not job_text or not job_text.strip():
        return error_response("Job description cannot be empty")

    try:
        start_time = time.time()

        # -----------------------------
        # Step 2: AI Analysis
        # -----------------------------
        gemini_result = analyze_match(cv_text, job_text)

        if not isinstance(gemini_result, dict):
            gemini_result = {}

        # -----------------------------
        # Step 3: Post Processing
        # -----------------------------
        final_result = compute_match(gemini_result)

        end_time = time.time()

        # Add performance metric
        final_result["processing_time"] = round(end_time - start_time, 2)

        # -----------------------------
        # Step 4: Return Response
        # -----------------------------
        return {
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
            "data": final_result
        }

    except Exception as e:
        print("Error in match_cv:", str(e))
        print(traceback.format_exc())
        return error_response("Internal processing error")


# -----------------------------
# Helper Function
# -----------------------------
def error_response(message):
    return {
        "status": "error",
        "message": message
    }


# -----------------------------
# TEST RUN
# -----------------------------
if __name__ == "__main__":

    cv = """
    Adaeze Okonkwo
    Python Developer with 2 years experience.
    Skills: Python, SQL, Data Analysis, Microsoft Excel, Power BI
    Education: BSc Computer Science, University of Lagos
    Experience: Data Analyst at Interswitch Nigeria (2022-2024)
    """

    job = """
    Job Title: Data Analyst — Flutterwave Nigeria
    Required Skills: Python, SQL, Tableau, Power BI, Machine Learning
    Experience: 2+ years in data analysis
    Education: BSc in Computer Science or related field
    """

    result = match_cv(cv, job)
    print(result)