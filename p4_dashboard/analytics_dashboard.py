import base64
import io
import json
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
P4_DIR = BASE_DIR
MOCK_JSON_PATH = os.path.join(P4_DIR, "mock_applications.json")
APPLICATION_CSV_PATH = os.path.join(P4_DIR, "application_metrics.csv")

STATUS_ORDER = ["Applied", "No response", "Shortlisted", "Interview", "Offer", "Rejected"]
NUMERIC_COLUMNS = ["match_score", "response_days", "interview_rounds", "follow_up_count", "offer_flag", "response_flag"]

DEFAULT_DATA = {
    "candidate": {
        "name": "John Doe",
        "level": "Beginner",
        "target_role": "Data Analyst / Data Science Intern",
        "location": "Abuja, Nigeria",
        "focus": ["Python", "Pandas", "SQL", "Visualization"],
    },
    "applications": []
}


def ensure_dashboard_storage():
    os.makedirs(P4_DIR, exist_ok=True)
    if not os.path.exists(MOCK_JSON_PATH):
        save_mock_data(DEFAULT_DATA)
    if not os.path.exists(APPLICATION_CSV_PATH):
        sync_csv_from_json()


def save_mock_data(payload):
    with open(MOCK_JSON_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_mock_data():
    ensure_dashboard_storage()
    try:
        with open(MOCK_JSON_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        save_mock_data(DEFAULT_DATA)
        return DEFAULT_DATA.copy()


def normalize_application(record, index=None):
    today = datetime.now().strftime("%Y-%m-%d")
    applied_date = record.get("applied_date") or today
    status = (record.get("status") or "Applied").strip().title()
    if status.lower() == "no response":
        status = "No response"

    normalized = {
        "application_id": record.get("application_id") or f"APP-{(index or 0) + 1:03d}",
        "company": record.get("company", "Unknown Company"),
        "job_title": record.get("job_title", "Unknown Role"),
        "source": record.get("source", "Unknown"),
        "applied_date": applied_date,
        "application_month": str(pd.to_datetime(applied_date, errors="coerce").to_period("M")) if pd.notna(pd.to_datetime(applied_date, errors="coerce")) else today[:7],
        "status": status,
        "response_days": int(record.get("response_days", 0) or 0),
        "match_score": int(record.get("match_score", 0) or 0),
        "interview_rounds": int(record.get("interview_rounds", 0) or 0),
        "follow_up_count": int(record.get("follow_up_count", 0) or 0),
        "feedback": record.get("feedback", ""),
        "next_step": record.get("next_step", ""),
    }

    normalized["response_flag"] = 1 if normalized["status"] not in {"Applied", "No response"} else 0
    normalized["offer_flag"] = 1 if normalized["status"] == "Offer" else 0
    return normalized


def _build_dataframe(records):
    normalized_rows = [normalize_application(record, index=i) for i, record in enumerate(records)]
    df = pd.DataFrame(normalized_rows)
    if df.empty:
        df = pd.DataFrame(columns=[
            "application_id",
            "company",
            "job_title",
            "source",
            "applied_date",
            "application_month",
            "status",
            "response_days",
            "match_score",
            "interview_rounds",
            "follow_up_count",
            "feedback",
            "next_step",
            "response_flag",
            "offer_flag",
        ])
    else:
        df["applied_date"] = pd.to_datetime(df["applied_date"], errors="coerce")
        df["application_month"] = df["applied_date"].dt.to_period("M").astype(str)
        df["applied_date"] = df["applied_date"].dt.strftime("%Y-%m-%d")
        df["status"] = df["status"].fillna("Applied")
    return df


def sync_csv_from_json():
    payload = load_mock_data()
    df = _build_dataframe(payload.get("applications", []))
    df.to_csv(APPLICATION_CSV_PATH, index=False)
    return df


def load_application_dataframe(refresh=False):
    ensure_dashboard_storage()
    if refresh or not os.path.exists(APPLICATION_CSV_PATH):
        return sync_csv_from_json()

    try:
        df = pd.read_csv(APPLICATION_CSV_PATH)
    except Exception:
        df = sync_csv_from_json()

    if df.empty:
        return df

    df["applied_date"] = pd.to_datetime(df["applied_date"], errors="coerce")
    if "application_month" not in df.columns:
        df["application_month"] = df["applied_date"].dt.to_period("M").astype(str)
    df["status"] = df["status"].fillna("Applied")
    for column in ["response_days", "match_score", "interview_rounds", "follow_up_count", "response_flag", "offer_flag"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return df


def append_application_feedback(record):
    payload = load_mock_data()
    applications = payload.get("applications", [])
    new_record = normalize_application(record, index=len(applications))
    application_id = new_record.get("application_id")
    updated = False

    if application_id:
        for index, existing in enumerate(applications):
            if existing.get("application_id") == application_id:
                applications[index] = new_record
                updated = True
                break

    if not updated:
        applications.append(new_record)

    payload["applications"] = applications
    payload["updated_at"] = datetime.now().isoformat()
    save_mock_data(payload)
    df = _build_dataframe(applications)
    df.to_csv(APPLICATION_CSV_PATH, index=False)
    return {"dataframe": df, "action": "updated" if updated else "created", "application": new_record}


def delete_application(application_id):
    payload = load_mock_data()
    applications = payload.get("applications", [])
    remaining = [application for application in applications if application.get("application_id") != application_id]

    deleted = len(remaining) != len(applications)
    if not deleted:
        return {"deleted": False, "application_id": application_id}

    payload["applications"] = remaining
    payload["updated_at"] = datetime.now().isoformat()
    save_mock_data(payload)
    df = _build_dataframe(remaining)
    df.to_csv(APPLICATION_CSV_PATH, index=False)
    return {"deleted": True, "application_id": application_id, "dataframe": df}


def _skew_label(value):
    if value >= 1:
        return "strong right skew"
    if value >= 0.5:
        return "moderate right skew"
    if value <= -1:
        return "strong left skew"
    if value <= -0.5:
        return "moderate left skew"
    return "roughly symmetric"


def _figure_to_base64(fig):
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _empty_chart(message):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color="#475569")
    return _figure_to_base64(fig)


def build_charts(df):
    if df.empty:
        return {
            "status_chart": _empty_chart("No application data yet."),
            "timeline_chart": _empty_chart("No timeline data yet."),
            "score_chart": _empty_chart("No match score data yet."),
            "skewness_chart": _empty_chart("No skewness data yet."),
            "scatter_chart": _empty_chart("No scatter data yet."),
        }

    status_counts = df["status"].value_counts().reindex(STATUS_ORDER).fillna(0).astype(int)
    monthly = df.groupby("application_month").size().sort_index()
    monthly_labels = list(monthly.index)
    monthly_positions = list(range(len(monthly_labels)))
    score_series = pd.to_numeric(df["match_score"], errors="coerce").dropna()
    numeric_df = df[[column for column in NUMERIC_COLUMNS if column in df.columns]].apply(pd.to_numeric, errors="coerce")
    skewness = numeric_df.skew(numeric_only=True).fillna(0).sort_values(ascending=False)
    scatter_df = df[["match_score", "response_days", "status"]].dropna()

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    colors = ["#0f766e" if value in {"Interview", "Offer", "Shortlisted"} else "#2563eb" if value == "Applied" else "#f97316" if value == "No response" else "#ef4444" for value in status_counts.index]
    ax.bar(status_counts.index, status_counts.values, color=colors, edgecolor="#0f172a")
    ax.set_title("Applications by Status", fontsize=14, fontweight="bold", color="#0f172a")
    ax.set_ylabel("Count")
    ax.set_ylim(0, max(status_counts.max() + 1, 1))
    ax.tick_params(axis="x", rotation=20)
    for index, value in enumerate(status_counts.values):
        ax.text(index, value + 0.08, str(value), ha="center", va="bottom", fontsize=10)
    status_chart = _figure_to_base64(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(monthly_positions, monthly.values, marker="o", linewidth=3, color="#0ea5e9")
    ax.fill_between(monthly_positions, monthly.values, color="#bae6fd", alpha=0.45)
    ax.set_title("Applications Over Time", fontsize=14, fontweight="bold", color="#0f172a")
    ax.set_ylabel("Applications")
    ax.set_xlabel("Month")
    ax.grid(alpha=0.2)
    ax.set_xticks(monthly_positions)
    ax.set_xticklabels(monthly_labels, rotation=20)
    for x_value, y_value in zip(monthly_positions, monthly.values):
        ax.text(x_value, y_value + 0.05, str(y_value), ha="center", va="bottom", fontsize=10)
    timeline_chart = _figure_to_base64(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.hist(score_series, bins=6, color="#22c55e", edgecolor="#0f172a", alpha=0.85)
    ax.set_title("Match Score Distribution", fontsize=14, fontweight="bold", color="#0f172a")
    ax.set_xlabel("Match Score")
    ax.set_ylabel("Number of Applications")
    score_chart = _figure_to_base64(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(skewness.index, skewness.values, color="#a855f7", edgecolor="#0f172a")
    ax.axhline(0, color="#0f172a", linewidth=1)
    ax.set_title("Skewness", fontsize=14, fontweight="bold", color="#0f172a")
    ax.set_ylabel("Skewness")
    ax.tick_params(axis="x", rotation=20)
    for index, value in enumerate(skewness.values):
        ax.text(index, value + (0.05 if value >= 0 else -0.15), f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    skewness_chart = _figure_to_base64(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    colors = scatter_df["status"].map({
        "Applied": "#2563eb",
        "No response": "#f97316",
        "Shortlisted": "#06b6d4",
        "Interview": "#0f766e",
        "Offer": "#16a34a",
        "Rejected": "#ef4444",
    }).fillna("#64748b")
    ax.scatter(scatter_df["response_days"], scatter_df["match_score"], c=colors, s=90, alpha=0.85, edgecolors="#0f172a")
    ax.set_title("Response Time vs Match Score", fontsize=14, fontweight="bold", color="#0f172a")
    ax.set_xlabel("Response Days")
    ax.set_ylabel("Match Score")
    ax.grid(alpha=0.2)
    scatter_chart = _figure_to_base64(fig)

    return {
        "status_chart": status_chart,
        "timeline_chart": timeline_chart,
        "score_chart": score_chart,
        "skewness_chart": skewness_chart,
        "scatter_chart": scatter_chart,
    }


def build_beginner_tables(df):
    if df.empty:
        return {
            "shape": {"rows": 0, "columns": 0},
            "describe_rows": [],
            "skewness_rows": [],
            "missing_values": [],
        }

    numeric_df = df[[column for column in NUMERIC_COLUMNS if column in df.columns]].apply(pd.to_numeric, errors="coerce")
    describe_df = numeric_df.describe().round(2).reset_index().rename(columns={"index": "metric"})
    describe_rows = describe_df.to_dict(orient="records")

    skew_series = numeric_df.skew(numeric_only=True).fillna(0).round(2)
    skewness_rows = [
        {
            "metric": column,
            "value": float(value),
            "label": _skew_label(float(value)),
        }
        for column, value in skew_series.items()
    ]

    missing_values = [
        {"column": column, "count": int(df[column].isna().sum())}
        for column in df.columns
        if int(df[column].isna().sum()) > 0
    ]

    return {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "describe_rows": describe_rows,
        "skewness_rows": skewness_rows,
        "missing_values": missing_values,
    }


def build_dashboard_payload():
    df = load_application_dataframe()
    if not df.empty:
        df = df.sort_values("applied_date")

    payload = load_mock_data()
    tables = build_beginner_tables(df)
    charts = build_charts(df)

    applications = []
    if not df.empty:
        recent = df.sort_values("applied_date", ascending=False).copy()
        recent["applied_date"] = recent["applied_date"].astype(str)
        applications = recent.to_dict(orient="records")

    total_applications = int(len(df))
    interview_count = int(df["status"].isin(["Shortlisted", "Interview", "Offer"]).sum()) if not df.empty else 0
    offer_count = int((df["status"] == "Offer").sum()) if not df.empty else 0
    response_count = int(df["response_flag"].sum()) if not df.empty else 0
    rejection_count = int((df["status"] == "Rejected").sum()) if not df.empty else 0
    avg_match_score = round(float(df["match_score"].mean()), 1) if not df.empty else 0.0
    avg_response_days = round(float(df.loc[df["response_flag"] == 1, "response_days"].mean()), 1) if not df.empty and response_count else 0.0

    success_rate = round((offer_count / total_applications) * 100, 1) if total_applications else 0.0
    response_rate = round((response_count / total_applications) * 100, 1) if total_applications else 0.0
    interview_rate = round((interview_count / total_applications) * 100, 1) if total_applications else 0.0
    application_months = df["application_month"].nunique() if not df.empty else 0

    summary_cards = [
        {"label": "Applications", "value": f"{total_applications}", "note": "Tracked job applications"},
        {"label": "Success Rate", "value": f"{success_rate}%", "note": "Offers divided by applications"},
        {"label": "Response Rate", "value": f"{response_rate}%", "note": "Any employer reply"},
        {"label": "Avg Match Score", "value": f"{avg_match_score}", "note": "Average fit score"},
        {"label": "Interview Rate", "value": f"{interview_rate}%", "note": "Shortlisted + interview + offer"},
        {"label": "Avg Response Days", "value": f"{avg_response_days}", "note": "Mean response time"},
    ]

    best_application = {}
    if not df.empty:
        best_row = df.sort_values(["match_score", "response_days"], ascending=[False, True]).iloc[0].to_dict()
        best_row["applied_date"] = str(best_row.get("applied_date", ""))
        best_application = best_row

    insights = []
    if total_applications:
        insights.append(f"You have tracked {total_applications} applications across {application_months} months.")
        insights.append(f"Your success rate is {success_rate}%, based on {offer_count} offer(s).")
        insights.append(f"Average response time is {avg_response_days} day(s), so follow-up timing matters.")
    else:
        insights.append("Add application data to see charts, success rate, and beginner metrics.")

    return {
        "candidate": payload.get("candidate", {}),
        "summary_cards": summary_cards,
        "metrics": {
            "applications": total_applications,
            "offers": offer_count,
            "rejections": rejection_count,
            "responses": response_count,
            "success_rate": success_rate,
            "response_rate": response_rate,
            "interview_rate": interview_rate,
            "avg_match_score": avg_match_score,
            "avg_response_days": avg_response_days,
        },
        "shape": tables["shape"],
        "describe_rows": tables["describe_rows"],
        "skewness_rows": tables["skewness_rows"],
        "missing_values": tables["missing_values"],
        "charts": charts,
        "recent_applications": applications,
        "insights": insights,
        "best_application": best_application,
    }
