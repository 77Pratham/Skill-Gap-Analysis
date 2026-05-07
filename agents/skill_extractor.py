"""
Agent 2: Skill Extractor
Uses NLP (regex + taxonomy matching + TF-IDF) to extract skills from:
  - The candidate's resume
  - All fetched job descriptions
"""

import re
from typing import List, Set
from core.models import ExtractedSkills
from core.state import AgentState
from core.config import ALL_SKILLS, SKILLS_TAXONOMY


class SkillExtractorAgent:
    """
    Extracts structured skill lists from unstructured text.
    Uses a multi-pass approach:
      Pass 1 — Direct taxonomy lookup (exact + alias)
      Pass 2 — Fuzzy regex matching for common variations
      Pass 3 — Contextual NLP (collocations, skill-adjacent phrases)
    """

    def __init__(self):
        self.name = "Skill Extractor"
        self._build_patterns()

    def _build_patterns(self):
        """Pre-compile regex patterns for all skills and aliases."""
        self.patterns = []
        seen = set()
        for canonical, info in ALL_SKILLS.items():
            skill_name = info["name"]
            if skill_name in seen:
                continue
            seen.add(skill_name)

            # Build list of terms to match
            terms = [skill_name] + info.get("aliases", [])
            for term in terms:
                # Escape and allow flexible spacing/punctuation
                pattern = re.escape(term).replace(r"\ ", r"[\s\-_./]?")
                try:
                    compiled = re.compile(
                        r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])",
                        re.IGNORECASE,
                    )
                    self.patterns.append((compiled, skill_name))
                except re.error:
                    pass

    def run(self, state: AgentState) -> AgentState:
        state.log(self.name, "Extracting skills from resume...")
        resume_skills = self._extract_from_text(state.resume_text)
        state.log(self.name, f"Found {len(resume_skills)} skills in resume: {sorted(resume_skills)[:15]}...")

        # Aggregate required + optional JD skills
        jd_required: Set[str] = set()
        jd_optional: Set[str] = set()
        for jd in state.job_descriptions:
            jd_required.update(jd.required_skills)
            jd_optional.update(jd.nice_to_have_skills)

        # Normalise JD skills through taxonomy
        jd_required_normalised = self._normalise_skill_list(jd_required)
        jd_optional_normalised = self._normalise_skill_list(jd_optional)

        state.extracted_skills = ExtractedSkills(
            from_resume=sorted(resume_skills),
            from_jd_required=sorted(jd_required_normalised),
            from_jd_optional=sorted(jd_optional_normalised),
            resume_raw_text=state.resume_text,
        )

        state.log(self.name, f"JD requires {len(jd_required_normalised)} unique skills across {len(state.job_descriptions)} JDs.")
        return state

    def _extract_from_text(self, text: str) -> Set[str]:
        """Run all passes and return a deduplicated set of canonical skill names."""
        found: Set[str] = set()
        if not text:
            return found

        # Preprocess
        text = self._preprocess(text)

        # Pass 1: Direct pattern matching
        for pattern, canonical in self.patterns:
            if pattern.search(text):
                found.add(canonical)

        # Pass 2: Contextual patterns for common skill phrases
        found.update(self._contextual_extract(text))

        return found

    def _preprocess(self, text: str) -> str:
        """Normalise text for better matching."""
        # Expand abbreviations
        expansions = {
            r"\bML\b": "machine learning",
            r"\bDL\b": "deep learning",
            r"\bNLP\b": "natural language processing",
            r"\bCV\b": "computer vision",
            r"\bRL\b": "reinforcement learning",
            r"\bETL\b": "etl",
            r"\bRAG\b": "rag retrieval augmented generation",
            r"\bLLM\b": "llm large language models",
            r"\bLLMs\b": "llm large language models",
            r"\bGenAI\b": "generative ai",
            r"\bMLOps\b": "mlops machine learning operations",
            r"\bCI/CD\b": "ci/cd continuous integration continuous deployment",
            r"\bGCP\b": "google cloud gcp",
            r"\bk8s\b": "kubernetes k8s",
            r"\bDWH\b": "data warehousing",
        }
        for pattern, replacement in expansions.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _contextual_extract(self, text: str) -> Set[str]:
        """Extract skills from contextual phrases."""
        found = set()

        # Programming language context
        lang_pattern = re.compile(
            r"(?:proficient|experienced|skilled|knowledge|expertise|strong)\s+(?:in|with)?\s+"
            r"([\w\s,+#]+?)(?:\s+and\s+|\s*,\s*|\s*\.|$)",
            re.IGNORECASE,
        )
        for match in lang_pattern.finditer(text):
            fragment = match.group(1)
            for p, canonical in self.patterns:
                if p.search(fragment):
                    found.add(canonical)

        # Years of experience pattern
        exp_pattern = re.compile(
            r"(\d+)\+?\s+years?\s+(?:of\s+)?(?:experience\s+(?:in|with)\s+)?([\w\s\.\+#]+?)(?:\s*,|\s*\.|$)",
            re.IGNORECASE,
        )
        for match in exp_pattern.finditer(text):
            fragment = match.group(2)
            for p, canonical in self.patterns:
                if p.search(fragment):
                    found.add(canonical)

        return found

    def _normalise_skill_list(self, skills: Set[str]) -> Set[str]:
        """Map skill names to canonical taxonomy names."""
        normalised = set()
        for skill in skills:
            key = skill.lower().strip()
            if key in ALL_SKILLS:
                normalised.add(ALL_SKILLS[key]["name"])
            else:
                # Try partial match
                for alias_key, info in ALL_SKILLS.items():
                    if key == alias_key or (len(key) > 3 and (key in alias_key or alias_key in key)):
                        normalised.add(info["name"])
                        break
                else:
                    normalised.add(skill)  # Keep as-is if no match
        return normalised
