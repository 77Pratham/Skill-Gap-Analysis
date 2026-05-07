# 🧠 AI-Powered Skill Gap Analysis Tool

A production-grade **multi-agent AI system** that analyses your resume against live job descriptions, identifies skill gaps, and generates a personalised learning roadmap — all powered by a coordinated pipeline of 4 AI agents.

---

## 🏗️ Architecture — Multi-Agent Pipeline

```
User Input (Resume + Target Role)
          │
          ▼
   ┌─────────────────────────────────────────────┐
   │           🧠  ORCHESTRATOR AGENT            │
   │   Plans tasks · Routes agents · Aggregates  │
   └──┬───────────┬────────────┬─────────────────┘
      │           │            │            │
      ▼           ▼            ▼            ▼
  ┌────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
  │   📥   │ │   🔍   │ │   📊   │ │    📚    │
  │   JD   │ │ Skill  │ │  Gap   │ │Recommender│
  │Fetcher │ │Extract │ │Analyser│ │  Agent   │
  └────────┘ └─────────┘ └─────────┘ └──────────┘
      │           │            │            │
      └───────────┴────────────┴────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │   📄 FINAL REPORT   │
              │ Match % · Gaps ·   │
              │ Courses · PDF       │
              └─────────────────────┘
```

### Agent Responsibilities

| Agent | Role | Technology |
|-------|------|-----------|
| **Orchestrator** | Sequences agents, manages state, handles retry logic | Pure Python state machine |
| **JD Fetcher** | Fetches relevant job descriptions by role matching | Curated DB + fuzzy title matching |
| **Skill Extractor** | Extracts skills from resume + JDs using NLP | Regex + taxonomy matching + context NLP |
| **Gap Analyser** | Computes gaps, scores by priority, weighs by frequency | TF-IDF cosine similarity + sklearn |
| **Recommender** | Maps gaps to courses, filters by mode/budget | Curated courses DB (100+ resources) |

---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.10+
pip install flask scikit-learn scipy reportlab pdfplumber
```

### Run the App
```bash
cd skill-gap-analyzer
python app.py
```
Open → **http://localhost:5000**

---

## 📁 Project Structure

```
skill-gap-analyzer/
├── app.py                      # Flask web server + API routes
├── agents/
│   ├── orchestrator.py         # Master orchestrator (controls pipeline)
│   ├── jd_fetcher.py           # Agent 1: Job description fetcher
│   ├── skill_extractor.py      # Agent 2: NLP skill extraction
│   ├── gap_analyser.py         # Agent 3: Gap scoring + TF-IDF
│   └── recommender.py          # Agent 4: Course recommender
├── core/
│   ├── models.py               # Data models (SkillGapReport, SkillGap, etc.)
│   ├── state.py                # Shared agent state (AgentState)
│   └── config.py               # Skills taxonomy (500+ skills, 10 categories)
├── data/
│   ├── job_database.json       # 15 curated job descriptions (top Indian companies)
│   └── courses_database.json   # 100+ curated learning resources
├── utils/
│   ├── resume_parser.py        # PDF / DOCX / text resume parsing
│   └── pdf_generator.py        # ReportLab PDF report generation
└── templates/
    └── index.html              # Full-featured web UI (dark theme)
```

---

## 🔬 How It Works

### 1. JD Fetcher Agent
Matches the target role against a curated database of job descriptions from top Indian companies (Flipkart, Amazon, Google, Swiggy, Razorpay, PhonePe, etc.) using fuzzy title matching with scoring.

### 2. Skill Extractor Agent (NLP)
Three-pass extraction pipeline:
- **Pass 1**: Direct taxonomy lookup — matches 500+ canonical skills + 1000+ aliases
- **Pass 2**: Regex pattern matching with flexible spacing/punctuation
- **Pass 3**: Contextual NLP — "proficient in X", "3 years of Y" patterns + abbreviation expansion (ML → Machine Learning, NLP → Natural Language Processing, etc.)

### 3. Gap Analyser Agent
Composite scoring system:
```
priority_score = (JD_frequency × 0.6) + (TF-IDF_similarity × 0.2) + (taxonomy_weight × 0.2)
```
- **Critical** (score ≥ 0.55): Must-have skills appearing in most JDs
- **Moderate** (0.35–0.55): Important skills for competitiveness
- **Minor** (< 0.35): Nice-to-have, optional upskilling

### 4. Recommender Agent
Maps each gap skill to curated courses from Coursera, DeepLearning.AI, Hugging Face, YouTube, official docs, and more. Filters by free/paid preference and budget.

---

## 📊 Supported Job Roles

- Data Scientist
- Machine Learning Engineer
- NLP Engineer
- Data Engineer
- GenAI / LLM Engineer
- MLOps Engineer
- Backend Engineer
- Full Stack Developer
- Data Analyst
- Research Scientist
- DevOps Engineer

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | Flask |
| NLP / Skill Extraction | Regex + Custom Taxonomy (500+ skills) |
| Similarity Scoring | scikit-learn TF-IDF + cosine similarity |
| PDF Generation | ReportLab |
| Resume Parsing | pdfplumber (PDF), python-docx (DOCX) |
| Frontend | Vanilla JS + CSS (dark theme, no dependencies) |
| Data | JSON-backed job + courses databases |

---

## 🔮 Extending to Production

### Real API Integration
```python
# In agents/jd_fetcher.py — replace with real APIs:
import serpapi  # Google Jobs scraping
import linkedin_api  # LinkedIn Jobs
# OR
import requests
response = requests.get("https://api.naukri.com/jobs", params={"role": target_role})
```

### LLM-Powered Extraction
```python
# In agents/skill_extractor.py — add LLM pass:
from langchain.llms import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o")
skills = llm.invoke(f"Extract all technical skills from this resume: {resume_text}")
```

### Real Agent Framework
```python
# Drop-in LangGraph replacement for orchestrator:
from langgraph.graph import StateGraph
workflow = StateGraph(AgentState)
workflow.add_node("jd_fetcher", jd_fetcher.run)
workflow.add_node("skill_extractor", skill_extractor.run)
# ...
```

### Vector Memory
```python
# Add ChromaDB for skill embeddings:
import chromadb
client = chromadb.Client()
collection = client.create_collection("skill_embeddings")
```

---

## 📄 API Reference

### `POST /analyse`
**Form data:**
- `target_role` (str, required) — e.g. "Data Scientist"
- `resume_file` (file) — PDF/DOCX/TXT
- `resume_text` (str) — or paste text
- `candidate_name` (str)
- `target_location` (str)
- `learning_mode` (str) — `free` | `paid` | `both`
- `budget_inr` (int)
- `timeline_weeks` (int)

**Response:** JSON `{success: true, report: SkillGapReport}`

### `POST /download_pdf`
**Body:** SkillGapReport JSON  
**Response:** `application/pdf`

---

## 👨‍💻 Built For

AI/ML Course Project — demonstrates:
- Multi-agent system design
- NLP-based information extraction
- TF-IDF vector similarity
- Full-stack Flask web application
- Professional PDF report generation

---

*Built with Python · Flask · scikit-learn · ReportLab*
