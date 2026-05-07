from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class GapPriority(Enum):
    CRITICAL = "critical"
    MODERATE = "moderate"
    MINOR = "minor"


class LearningMode(Enum):
    FREE = "free"
    PAID = "paid"
    BOTH = "both"


@dataclass
class Skill:
    name: str
    category: str
    aliases: List[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class JobDescription:
    title: str
    company: str
    location: str
    required_skills: List[str] = field(default_factory=list)
    nice_to_have_skills: List[str] = field(default_factory=list)
    description: str = ""
    experience_years: int = 0
    source: str = "database"


@dataclass
class ExtractedSkills:
    from_resume: List[str] = field(default_factory=list)
    from_jd_required: List[str] = field(default_factory=list)
    from_jd_optional: List[str] = field(default_factory=list)
    resume_raw_text: str = ""


@dataclass
class SkillGap:
    skill: str
    category: str
    priority: GapPriority
    frequency_in_jds: int = 1
    relevance_score: float = 0.0
    reason: str = ""


@dataclass
class CourseRecommendation:
    title: str
    platform: str
    url: str
    duration: str
    level: str
    is_free: bool
    skill: str
    rating: float = 4.5


@dataclass
class SkillGapReport:
    candidate_name: str
    target_role: str
    analysis_date: str
    matched_skills: List[str] = field(default_factory=list)
    skill_gaps: List[SkillGap] = field(default_factory=list)
    recommendations: List[CourseRecommendation] = field(default_factory=list)
    job_descriptions_analysed: int = 0
    match_percentage: float = 0.0
    estimated_learning_weeks: int = 0
    top_companies_hiring: List[str] = field(default_factory=list)
    summary: str = ""
    agent_logs: List[str] = field(default_factory=list)
