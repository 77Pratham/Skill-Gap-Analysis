"""
Flask Web Application
Main entry point for the AI Skill Gap Analyser.
"""

import os
import json
import sys

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, jsonify, send_file
import io

from agents.orchestrator import OrchestratorAgent
from utils.resume_parser import parse_resume
from utils.pdf_generator import generate_pdf_report

app = Flask(__name__)
app.secret_key = "skillgap_analyser_2024"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

orchestrator = OrchestratorAgent()

ROLE_SUGGESTIONS = [
    "Data Scientist", "Machine Learning Engineer", "Data Engineer",
    "NLP Engineer", "MLOps Engineer", "GenAI Engineer",
    "Backend Engineer", "Full Stack Developer", "Data Analyst",
    "Research Scientist", "DevOps Engineer", "AI Engineer",
]

@app.route("/")
def index():
    return render_template("index.html", role_suggestions=ROLE_SUGGESTIONS)


@app.route("/analyse", methods=["POST"])
def analyse():
    try:
        # --- Parse form inputs ---
        target_role = request.form.get("target_role", "").strip()
        target_location = request.form.get("target_location", "India").strip()
        learning_mode = request.form.get("learning_mode", "both")
        timeline_weeks = int(request.form.get("timeline_weeks", 12))
        budget_inr = int(request.form.get("budget_inr", 10000))
        resume_text_input = request.form.get("resume_text", "").strip()

        if not target_role:
            return jsonify({"error": "Please enter a target job role."}), 400

        # --- Handle resume ---
        resume_text = ""
        candidate_name = "Candidate"

        if "resume_file" in request.files and request.files["resume_file"].filename:
            file = request.files["resume_file"]
            file_bytes = file.read()
            resume_text, candidate_name = parse_resume(file_bytes, file.filename)
        elif resume_text_input:
            resume_text = resume_text_input
            candidate_name = request.form.get("candidate_name", "Candidate").strip() or "Candidate"

        if not resume_text:
            return jsonify({"error": "Please provide a resume (upload a file or paste text)."}), 400

        # --- Run the agent pipeline ---
        report = orchestrator.run(
            resume_text=resume_text,
            target_role=target_role,
            target_location=target_location,
            learning_mode=learning_mode,
            budget_inr=budget_inr,
            timeline_weeks=timeline_weeks,
            candidate_name=candidate_name,
        )

        # --- Serialise report for JSON response ---
        response_data = _serialise_report(report)
        return jsonify({"success": True, "report": response_data})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    try:
        report_data = request.get_json()
        report = _deserialise_report(report_data)
        pdf_bytes = generate_pdf_report(report)

        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        filename = f"skill_gap_report_{report.candidate_name.replace(' ', '_').lower()}.pdf"
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/sample_resume")
def sample_resume():
    """Return a sample resume for demo purposes."""
    sample = """Arjun Sharma
arjun.sharma@email.com | +91-98765-43210 | LinkedIn: linkedin.com/in/arjunsharma | GitHub: github.com/arjunsharma
Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Passionate software engineer with 2 years of experience in data science and backend development. 
Skilled in Python, machine learning, and building REST APIs. Looking to transition into a dedicated 
Data Science / ML Engineering role.

WORK EXPERIENCE

Software Engineer — Analytics | TechStartup Pvt Ltd, Bengaluru | June 2022 – Present
• Built a customer churn prediction model using Scikit-learn (XGBoost, Random Forest) achieving 87% accuracy
• Developed ETL pipelines using Python and SQL to process 5M+ daily transactions
• Created REST APIs with Flask for internal ML model serving
• Worked with PostgreSQL, Redis for data storage and caching
• Used Git, Docker for version control and deployment
• Conducted A/B testing for product feature rollouts

Data Analyst Intern | FinTech Corp, Mumbai | Jan 2022 – May 2022
• Performed statistical analysis on customer transaction data using Pandas and NumPy
• Built dashboards and visualisations using Matplotlib and Seaborn
• Wrote complex SQL queries for business reporting on BigQuery
• Collaborated with product teams using Agile/Scrum methodology

EDUCATION
B.Tech Computer Science & Engineering | VIT University | 2018–2022 | CGPA: 8.4

TECHNICAL SKILLS
Programming: Python, SQL, JavaScript
ML/AI: Scikit-learn, Pandas, NumPy, Matplotlib, Seaborn, XGBoost, Statistical Analysis
Data Engineering: ETL pipelines, PostgreSQL, Redis, BigQuery
Web: Flask, REST API, HTML, CSS
DevOps: Docker, Git, Linux, CI/CD basics
Tools: Jupyter Notebook, VS Code, JIRA, Agile

PROJECTS
• Customer Churn Predictor — XGBoost model with feature engineering, 87% accuracy
• Sales Forecasting Dashboard — Time series model (ARIMA) + Plotly dashboard
• Resume Parser API — NLP-based Flask API for parsing resumes using Python

CERTIFICATIONS
• Python for Data Science — Coursera (2022)
• SQL for Data Analysis — Mode Analytics (2021)
"""
    return jsonify({"resume": sample})


def _serialise_report(report) -> dict:
    """Convert SkillGapReport to JSON-serialisable dict."""
    return {
        "candidate_name": report.candidate_name,
        "target_role": report.target_role,
        "analysis_date": report.analysis_date,
        "matched_skills": report.matched_skills,
        "match_percentage": report.match_percentage,
        "estimated_learning_weeks": report.estimated_learning_weeks,
        "job_descriptions_analysed": report.job_descriptions_analysed,
        "top_companies_hiring": report.top_companies_hiring,
        "summary": report.summary,
        "agent_logs": report.agent_logs,
        "skill_gaps": [
            {
                "skill": g.skill,
                "category": g.category,
                "priority": g.priority.value,
                "frequency_in_jds": g.frequency_in_jds,
                "relevance_score": g.relevance_score,
                "reason": g.reason,
            }
            for g in report.skill_gaps
        ],
        "recommendations": [
            {
                "skill": r.skill,
                "title": r.title,
                "platform": r.platform,
                "url": r.url,
                "duration": r.duration,
                "level": r.level,
                "is_free": r.is_free,
                "rating": r.rating,
            }
            for r in report.recommendations
        ],
    }


def _deserialise_report(data: dict):
    """Reconstruct SkillGapReport from dict for PDF generation."""
    from core.models import SkillGapReport, SkillGap, CourseRecommendation, GapPriority

    report = SkillGapReport(
        candidate_name=data.get("candidate_name", "Candidate"),
        target_role=data.get("target_role", ""),
        analysis_date=data.get("analysis_date", ""),
        matched_skills=data.get("matched_skills", []),
        match_percentage=data.get("match_percentage", 0),
        estimated_learning_weeks=data.get("estimated_learning_weeks", 0),
        job_descriptions_analysed=data.get("job_descriptions_analysed", 0),
        top_companies_hiring=data.get("top_companies_hiring", []),
        summary=data.get("summary", ""),
        agent_logs=data.get("agent_logs", []),
    )

    for g in data.get("skill_gaps", []):
        report.skill_gaps.append(SkillGap(
            skill=g["skill"],
            category=g["category"],
            priority=GapPriority(g["priority"]),
            frequency_in_jds=g["frequency_in_jds"],
            relevance_score=g["relevance_score"],
            reason=g["reason"],
        ))

    for r in data.get("recommendations", []):
        report.recommendations.append(CourseRecommendation(
            skill=r["skill"],
            title=r["title"],
            platform=r["platform"],
            url=r["url"],
            duration=r["duration"],
            level=r["level"],
            is_free=r["is_free"],
            rating=r["rating"],
        ))

    return report


if __name__ == "__main__":
    print("🚀 AI Skill Gap Analyser is running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
