"""
Agent 1: Job Description Fetcher
Fetches relevant job descriptions from the curated database based on target role.
In production, this would query LinkedIn, Naukri, Indeed APIs.
"""

import json
import os
import re
from typing import List
from core.models import JobDescription
from core.state import AgentState

JOB_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "job_database.json")


class JDFetcherAgent:
    """
    Fetches job descriptions matching the target role.
    Simulates real job portal queries with a curated database.
    """

    def __init__(self):
        self.name = "JD Fetcher"
        with open(JOB_DB_PATH) as f:
            self.db = json.load(f)

    def run(self, state: AgentState) -> AgentState:
        state.log(self.name, f"Starting JD fetch for role: '{state.target_role}' in '{state.target_location}'")

        target = state.target_role.strip().lower()
        matched_jobs = []

        for job in self.db["jobs"]:
            score = self._match_score(target, job)
            if score > 0:
                matched_jobs.append((score, job))

        if not matched_jobs:
            state.log(self.name, "No exact matches found — using all available jobs as reference.")
            matched_jobs = [(0.1, job) for job in self.db["jobs"]]

        # Sort by score and take top matches
        matched_jobs.sort(key=lambda x: x[0], reverse=True)
        top_jobs = matched_jobs[:10]

        state.job_descriptions = []
        companies_seen = set()

        for score, job in top_jobs:
            # Vary company name for diversity
            company = job["company"]
            if company in companies_seen:
                company = f"{company} (Senior)"
            companies_seen.add(company)

            jd = JobDescription(
                title=job["title"],
                company=company,
                location=job.get("location", state.target_location or "India"),
                required_skills=job.get("required_skills", []),
                nice_to_have_skills=job.get("nice_to_have_skills", []),
                description=job.get("description", ""),
                experience_years=job.get("experience_years", 2),
                source="job_database",
            )
            state.job_descriptions.append(jd)

        state.log(self.name, f"Fetched {len(state.job_descriptions)} relevant JDs: {[j.company for j in state.job_descriptions]}")
        return state

    def _match_score(self, target: str, job: dict) -> float:
        score = 0.0
        job_title = job["title"].lower()
        variants = [v.lower() for v in job.get("variants", [])]

        # Exact title match
        if target == job_title:
            score += 3.0
        elif target in job_title or job_title in target:
            score += 2.0

        # Variant matches
        for variant in variants:
            if target == variant:
                score += 2.5
            elif self._words_overlap(target, variant) > 0.5:
                score += 1.5
            elif self._words_overlap(target, variant) > 0.3:
                score += 0.8

        # Keyword matches
        target_words = set(target.split())
        title_words = set(job_title.split())
        common = target_words & title_words
        if common:
            score += len(common) * 0.5

        return score

    def _words_overlap(self, a: str, b: str) -> float:
        a_words = set(a.split())
        b_words = set(b.split())
        if not a_words or not b_words:
            return 0.0
        return len(a_words & b_words) / max(len(a_words), len(b_words))
