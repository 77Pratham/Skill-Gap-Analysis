"""
Agent 4: Learning Recommender
Maps each skill gap to curated learning resources.
Filters by: learning mode (free/paid/both), budget, and priority.
Estimates total learning timeline.
"""

import json
import os
from typing import List, Dict
from core.models import CourseRecommendation, SkillGap, GapPriority
from core.state import AgentState

COURSES_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "courses_database.json")

# Estimated hours per gap priority
LEARNING_HOURS = {
    GapPriority.CRITICAL: 40,
    GapPriority.MODERATE: 20,
    GapPriority.MINOR: 8,
}

HOURS_PER_WEEK = 15  # Assumed learning hours per week


class RecommenderAgent:
    """
    Recommends learning resources for each skill gap.
    Personalises by learning mode preference and budget.
    """

    def __init__(self):
        self.name = "Recommender"
        with open(COURSES_DB_PATH) as f:
            self.courses_db = json.load(f)

    def run(self, state: AgentState) -> AgentState:
        state.log(self.name, f"Generating learning recommendations (mode={state.learning_mode}, budget=₹{state.budget_inr})...")

        recommendations: List[CourseRecommendation] = []
        total_hours = 0

        # Prioritise critical gaps first
        priority_order = {GapPriority.CRITICAL: 0, GapPriority.MODERATE: 1, GapPriority.MINOR: 2}
        sorted_gaps = sorted(state.skill_gaps, key=lambda g: priority_order[g.priority])

        for gap in sorted_gaps:
            courses = self._get_courses_for_skill(gap.skill, state.learning_mode)
            if not courses:
                courses = self._get_default_course(gap.skill)

            for course in courses[:3]:  # max 3 per skill
                recommendations.append(course)

            total_hours += LEARNING_HOURS.get(gap.priority, 10)

        state.recommendations = recommendations
        state.estimated_weeks = max(1, round(total_hours / HOURS_PER_WEEK))

        state.log(self.name, f"Generated {len(recommendations)} course recommendations.")
        state.log(self.name, f"Estimated learning timeline: {state.estimated_weeks} weeks ({total_hours} total hours).")
        return state

    def _get_courses_for_skill(self, skill: str, mode: str) -> List[CourseRecommendation]:
        """Fetch courses from database, filtered by mode."""
        skill_courses = self.courses_db["courses"].get(skill, [])

        # Try partial match if exact key missing
        if not skill_courses:
            for key in self.courses_db["courses"]:
                if key.lower() in skill.lower() or skill.lower() in key.lower():
                    skill_courses = self.courses_db["courses"][key]
                    break

        filtered = []
        for c in skill_courses:
            if mode == "free" and not c["is_free"]:
                continue
            if mode == "paid" and c["is_free"]:
                continue
            filtered.append(
                CourseRecommendation(
                    title=c["title"],
                    platform=c["platform"],
                    url=c["url"],
                    duration=c["duration"],
                    level=c["level"],
                    is_free=c["is_free"],
                    skill=skill,
                    rating=c.get("rating", 4.5),
                )
            )

        # Sort by rating
        filtered.sort(key=lambda x: x.rating, reverse=True)
        return filtered

    def _get_default_course(self, skill: str) -> List[CourseRecommendation]:
        default = self.courses_db["default_course"]
        return [
            CourseRecommendation(
                title=default["title"].replace("{skill}", skill),
                platform=default["platform"],
                url=default["url"].replace("{skill}", skill.replace(" ", "+")),
                duration=default["duration"],
                level=default["level"],
                is_free=default["is_free"],
                skill=skill,
                rating=default["rating"],
            )
        ]
