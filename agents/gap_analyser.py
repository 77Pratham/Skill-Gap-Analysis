"""
Agent 3: Gap Analyser
Computes skill gaps between candidate and target role using:
  - Set-based matching (exact)
  - TF-IDF cosine similarity (semantic proximity)
  - Frequency weighting (how often each skill appears across JDs)
  - Priority classification: Critical / Moderate / Minor
"""

from typing import List, Set, Dict, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from core.models import SkillGap, GapPriority
from core.state import AgentState
from core.config import ALL_SKILLS, APP_CONFIG


class GapAnalyserAgent:
    """
    Identifies skill gaps and scores their importance.
    Uses frequency-weighted scoring + semantic similarity.
    """

    def __init__(self):
        self.name = "Gap Analyser"

    def run(self, state: AgentState) -> AgentState:
        if not state.extracted_skills:
            state.error(self.name, "No extracted skills available. Aborting.")
            return state

        state.log(self.name, "Computing skill gap analysis...")

        resume_skills = set(state.extracted_skills.from_resume)
        jd_required = set(state.extracted_skills.from_jd_required)
        jd_optional = set(state.extracted_skills.from_jd_optional)

        # Step 1: Compute matched skills
        matched = resume_skills & jd_required
        state.matched_skills = sorted(matched)

        # Step 2: Frequency count across JDs
        skill_freq = self._compute_skill_frequency(state)

        # Step 3: Find gaps in required skills
        required_gaps = jd_required - resume_skills
        optional_gaps = (jd_optional - resume_skills) - jd_required

        # Step 4: Compute semantic similarity scores
        similarity_scores = self._compute_semantic_similarity(
            state.resume_text, list(required_gaps | optional_gaps)
        )

        # Step 5: Score and classify gaps
        all_gaps: List[SkillGap] = []
        total_required = len(jd_required) if jd_required else 1

        for skill in required_gaps:
            freq = skill_freq.get(skill, 1)
            freq_ratio = freq / len(state.job_descriptions) if state.job_descriptions else 0.5
            sim_score = similarity_scores.get(skill, 0.0)

            # Composite priority score
            priority_score = (freq_ratio * 0.6) + (sim_score * 0.2) + (
                self._get_skill_weight(skill) * 0.2
            )

            priority = self._classify_priority(priority_score, is_required=True)
            gap = SkillGap(
                skill=skill,
                category=self._get_skill_category(skill),
                priority=priority,
                frequency_in_jds=freq,
                relevance_score=round(priority_score, 3),
                reason=self._build_reason(skill, freq, len(state.job_descriptions), priority_score),
            )
            all_gaps.append(gap)

        for skill in optional_gaps:
            freq = skill_freq.get(skill, 1)
            freq_ratio = freq / len(state.job_descriptions) if state.job_descriptions else 0.3
            sim_score = similarity_scores.get(skill, 0.0)
            priority_score = (freq_ratio * 0.5) + (sim_score * 0.3) + (
                self._get_skill_weight(skill) * 0.2
            )

            priority = self._classify_priority(priority_score, is_required=False)
            gap = SkillGap(
                skill=skill,
                category=self._get_skill_category(skill),
                priority=priority,
                frequency_in_jds=freq,
                relevance_score=round(priority_score, 3),
                reason=self._build_reason(skill, freq, len(state.job_descriptions), priority_score),
            )
            all_gaps.append(gap)

        # Sort: Critical first, then by relevance score
        priority_order = {GapPriority.CRITICAL: 0, GapPriority.MODERATE: 1, GapPriority.MINOR: 2}
        all_gaps.sort(key=lambda g: (priority_order[g.priority], -g.relevance_score))

        state.skill_gaps = all_gaps

        # Compute match percentage
        if jd_required:
            state.match_percentage = round((len(matched) / len(jd_required)) * 100, 1)
        else:
            state.match_percentage = 0.0

        state.log(self.name, f"Match: {state.match_percentage}% | Matched: {len(matched)} | Gaps: {len(all_gaps)} ({len(required_gaps)} critical/moderate, {len(optional_gaps)} optional)")
        return state

    def _compute_skill_frequency(self, state: AgentState) -> Dict[str, int]:
        """Count how many JDs require each skill."""
        freq: Counter = Counter()
        for jd in state.job_descriptions:
            for skill in jd.required_skills + jd.nice_to_have_skills:
                # Normalise to canonical
                key = skill.lower().strip()
                canonical = ALL_SKILLS.get(key, {}).get("name", skill)
                freq[canonical] += 1
        return dict(freq)

    def _compute_semantic_similarity(self, resume_text: str, gap_skills: List[str]) -> Dict[str, float]:
        """
        Use TF-IDF cosine similarity to measure how semantically close
        each gap skill is to the resume text.
        """
        if not resume_text or not gap_skills:
            return {}

        try:
            docs = [resume_text] + gap_skills
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(docs)
            resume_vec = tfidf_matrix[0]
            skill_vecs = tfidf_matrix[1:]
            similarities = cosine_similarity(resume_vec, skill_vecs).flatten()
            return {skill: float(sim) for skill, sim in zip(gap_skills, similarities)}
        except Exception:
            return {skill: 0.0 for skill in gap_skills}

    def _classify_priority(self, score: float, is_required: bool) -> GapPriority:
        if is_required:
            if score >= 0.55:
                return GapPriority.CRITICAL
            elif score >= 0.35:
                return GapPriority.MODERATE
            else:
                return GapPriority.MINOR
        else:
            if score >= 0.6:
                return GapPriority.MODERATE
            else:
                return GapPriority.MINOR

    def _get_skill_weight(self, skill: str) -> float:
        info = ALL_SKILLS.get(skill.lower(), {})
        return info.get("weight", 0.7)

    def _get_skill_category(self, skill: str) -> str:
        info = ALL_SKILLS.get(skill.lower(), {})
        return info.get("category", "General")

    def _build_reason(self, skill: str, freq: int, total_jds: int, score: float) -> str:
        pct = int((freq / total_jds * 100)) if total_jds else 0
        if pct >= 70:
            return f"Required in {pct}% of {total_jds} JDs analysed — core skill for this role."
        elif pct >= 40:
            return f"Appears in {pct}% of JDs — strongly recommended for this role."
        elif pct >= 20:
            return f"Mentioned in {pct}% of JDs — adds significant competitive advantage."
        else:
            return f"Nice-to-have skill that appears in {pct}% of JDs."
