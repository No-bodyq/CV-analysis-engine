import time
import datetime
import traceback

from gemini_service import analyze_match
from matcher import compute_match


def match_cv(cv_text, job_text):

    # Main orchestrator for CV-job matching system.
    # Validates inputs, calls AI analysis, and returns structured result.


    # Validate inputs
    if not cv_text or not cv_text.strip():
        return error_response("CV text cannot be empty")

    if not job_text or not job_text.strip():
        return error_response("Job description cannot be empty")

    try:
        start_time = time.time()

        # Get AI analysis
        gemini_result = analyze_match(cv_text, job_text)

        # Safety check
        if not isinstance(gemini_result, dict):
            gemini_result = {}

        # Process and enrich result
        final_result = compute_match(gemini_result)

        # Add processing time
        final_result["processing_time"] = round(time.time() - start_time, 2)

        return {
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
            "data": final_result
        }

    except Exception as e:
        print("Error in match_cv:", str(e))
        print(traceback.format_exc())
        return error_response("Internal processing error")


def error_response(message):

    return {
        "status": "error",
        "message": message
    }