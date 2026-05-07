"""
Orchestrator Agent
Coordinates the multi-agent pipeline:
  1. JD Fetcher Agent
  2. Skill Extractor Agent
  3. Gap Analyser Agent
  4. Recommender Agent

Handles retry logic, state validation, and error recovery.
"""

import time
from datetime import datetime
from core.state import AgentState
from core.models import SkillGapReport, GapPriority
from agents.jd_fetcher import JDFetcherAgent
from agents.skill_extractor import SkillExtractorAgent
from agents.gap_analyser import GapAnalyserAgent
from agents.recommender import RecommenderAgent


class OrchestratorAgent:
    """
    Master orchestrator that sequences sub-agents,
    validates intermediate outputs, and builds the final report.
    """

    def __init__(self):
        self.name = "Orchestrator"
        self.jd_fetcher = JDFetcherAgent()
        self.skill_extractor = SkillExtractorAgent()
        self.gap_analyser = GapAnalyserAgent()
        self.recommender = RecommenderAgent()

    def run(
        self,
        resume_text: str,
        target_role: str,
        target_location: str = "India",
        learning_mode: str = "both",
        budget_inr: int = 10000,
        timeline_weeks: int = 12,
        candidate_name: str = "Candidate",
    ) -> SkillGapReport:
        """Main entry point. Returns a complete SkillGapReport."""

        start_time = time.time()

        # Initialise shared state
        state = AgentState(
            resume_text=resume_text,
            target_role=target_role,
            target_location=target_location,
            learning_mode=learning_mode,
            budget_inr=budget_inr,
            timeline_weeks=timeline_weeks,
            candidate_name=candidate_name,
        )

        state.log(self.name, f"=== Skill Gap Analysis Pipeline Started ===")
        state.log(self.name, f"Candidate: {candidate_name} | Target: {target_role} | Mode: {learning_mode}")

        # --- Step 1: Fetch Job Descriptions ---
        state.log(self.name, "Dispatching Agent 1: JD Fetcher")
        state.status = "fetching_jds"
        state = self._run_with_retry(self.jd_fetcher, state)

        if not state.job_descriptions:
            state.error(self.name, "No JDs fetched. Using fallback skill extraction only.")

        # --- Step 2: Extract Skills ---
        state.log(self.name, "Dispatching Agent 2: Skill Extractor")
        state.status = "extracting_skills"
        state = self._run_with_retry(self.skill_extractor, state)

        if not state.extracted_skills:
            state.error(self.name, "Skill extraction failed. Aborting pipeline.")
            return self._build_empty_report(state)

        # --- Step 3: Analyse Gaps ---
        state.log(self.name, "Dispatching Agent 3: Gap Analyser")
        state.status = "analysing_gaps"
        state = self._run_with_retry(self.gap_analyser, state)

        # --- Step 4: Recommend Resources ---
        state.log(self.name, "Dispatching Agent 4: Recommender")
        state.status = "recommending"
        state = self._run_with_retry(self.recommender, state)

        # --- Step 5: Build Final Report ---
        elapsed = round(time.time() - start_time, 2)
        state.log(self.name, f"=== Pipeline Completed in {elapsed}s ===")
        state.status = "completed"

        return self._build_report(state)

    def _run_with_retry(self, agent, state: AgentState, max_retries: int = 2) -> AgentState:
        for attempt in range(max_retries):
            try:
                return agent.run(state)
            except Exception as e:
                state.error(agent.name, f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    state.error(agent.name, "Max retries reached. Continuing with partial state.")
        return state

    def _build_report(self, state: AgentState) -> SkillGapReport:
        """Assemble the final report from agent state."""
        # Count gaps by priority
        critical = [g for g in state.skill_gaps if g.priority == GapPriority.CRITICAL]
        moderate = [g for g in state.skill_gaps if g.priority == GapPriority.MODERATE]
        minor = [g for g in state.skill_gaps if g.priority == GapPriority.MINOR]

        # Build executive summary
        summary = self._build_summary(state, critical, moderate, minor)

        # Top companies from JDs
        companies = list({jd.company for jd in state.job_descriptions})[:5]

        return SkillGapReport(
            candidate_name=state.candidate_name,
            target_role=state.target_role,
            analysis_date=datetime.now().strftime("%d %B %Y, %I:%M %p"),
            matched_skills=state.matched_skills,
            skill_gaps=state.skill_gaps,
            recommendations=state.recommendations,
            job_descriptions_analysed=len(state.job_descriptions),
            match_percentage=state.match_percentage,
            estimated_learning_weeks=state.estimated_weeks,
            top_companies_hiring=companies,
            summary=summary,
            agent_logs=state.agent_logs,
        )

    def _build_summary(self, state, critical, moderate, minor) -> str:
        match = state.match_percentage
        total_gaps = len(state.skill_gaps)

        if match >= 80:
            strength = "strong"
            outlook = "You are well-positioned for this role."
        elif match >= 60:
            strength = "moderate"
            outlook = "With focused upskilling, you can become a strong candidate."
        elif match >= 40:
            strength = "developing"
            outlook = "A structured learning plan over the recommended timeline will bridge the gap effectively."
        else:
            strength = "early-stage"
            outlook = "This role requires significant upskilling. Follow the roadmap systematically."

        return (
            f"Your profile shows a {strength} match ({match}%) for {state.target_role} roles. "
            f"You matched {len(state.matched_skills)} of the required skills. "
            f"Analysis of {len(state.job_descriptions)} live job descriptions revealed {total_gaps} skill gaps — "
            f"{len(critical)} critical, {len(moderate)} moderate, and {len(minor)} minor. "
            f"{outlook} "
            f"Estimated time to close all gaps: {state.estimated_weeks} weeks (~15 hrs/week)."
        )

    def _build_empty_report(self, state: AgentState) -> SkillGapReport:
        return SkillGapReport(
            candidate_name=state.candidate_name,
            target_role=state.target_role,
            analysis_date=datetime.now().strftime("%d %B %Y, %I:%M %p"),
            summary="Analysis could not be completed. Please check your inputs.",
            agent_logs=state.agent_logs,
        )
