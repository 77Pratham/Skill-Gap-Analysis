from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from core.models import JobDescription, ExtractedSkills, SkillGap, CourseRecommendation


@dataclass
class AgentState:
    """Shared state passed between all agents in the pipeline."""

    # Input
    resume_text: str = ""
    target_role: str = ""
    target_location: str = ""
    learning_mode: str = "both"
    budget_inr: int = 10000
    timeline_weeks: int = 12
    candidate_name: str = "Candidate"

    # Agent 1 output: JD Fetcher
    job_descriptions: List[JobDescription] = field(default_factory=list)

    # Agent 2 output: Skill Extractor
    extracted_skills: Optional[ExtractedSkills] = None

    # Agent 3 output: Gap Analyser
    skill_gaps: List[SkillGap] = field(default_factory=list)
    matched_skills: List[str] = field(default_factory=list)
    match_percentage: float = 0.0

    # Agent 4 output: Recommender
    recommendations: List[CourseRecommendation] = field(default_factory=list)
    estimated_weeks: int = 0

    # Metadata
    agent_logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    status: str = "pending"

    def log(self, agent_name: str, message: str):
        entry = f"[{agent_name}] {message}"
        self.agent_logs.append(entry)

    def error(self, agent_name: str, message: str):
        entry = f"[{agent_name}] ERROR: {message}"
        self.errors.append(entry)
        self.agent_logs.append(entry)
