# 🎓 College FAQ Agent – AI-Powered College Information Assistant

A production-grade, AI-powered **College FAQ Assistant** built with Python, Google Gemini, and Streamlit. The agent empowers college students to get immediate, verified answers to questions regarding academic regulations, examinations, attendance criteria, fee schedules, timetables, holiday calendars, faculty directories, and campus guidelines.

The system is strictly grounded in **approved institutional documents** (PDF, TXT, CSV, JSON) and features an **escalation pipeline** that automatically detects and forwards unverified inquiries to college administrators rather than hallucinating answers.

---

## 🌟 Core Features

- **Grounded AI Question Answering**: Answers student queries in natural language using Google Gemini API (`gemini-2.5-flash`), strictly adhering to official college documents.
- **Zero-Hallucination & Provenance Verification**: Every response provides source citations (document name, page number, and section). Fake or non-existent citations are strictly prevented.
- **Multilingual Support (English & தமிழ்)**: Students can query in English or Tamil (e.g., questions on attendance, holidays, fee structures).
- **Multi-Format Document Processing**:
  - **PDF**: Page-by-page text extraction with header detection (`pypdf`).
  - **TXT**: Structured section chunking based on markdown headings and paragraphs.
  - **CSV**: Tabular parsing into readable key-value schema records (`csv.DictReader`).
  - **JSON**: Hierarchical record extraction for departments, FAQs, and event calendars.
- **High-Precision BM25 Search**: Pure-Python Okapi BM25 retrieval engine with multilingual tokenization, stop-word suppression, section weighting, and concept coverage verification.
- **Unanswered Question Escalation**:
  - Automatically flags queries that cannot be verified from approved documents.
  - Persists queries in `data/unanswered_questions.json` with timestamp, domain category, and pending status.
  - Displays a clear notification to the student with an escalation badge.
- **Modern Streamlit Web Application**:
  - **Student Assistant**: Interactive chat interface with quick-action FAQ buttons, verified source badges, and chat history management.
  - **Administrator Portal**: Password-protected dashboard with document upload/deletion, live re-indexing, unanswered inquiry review queue, and analytics charts.
- **Resilient Fallback Mode**: If a Gemini API key is not yet configured, the system provides an extractive fallback from the highest-scoring matching approved document chunk without crashing.

---

## 🏗️ System Architecture & Project Structure

```
College FAQ Agent/
├── app.py                      # Streamlit interactive application (Student & Admin views)
├── faq_agent.py                # Core FAQ Agent orchestrating LLM, retrieval & escalation
├── document_processor.py       # Extraction & chunking for PDF, TXT, CSV, JSON
├── document_search.py          # Multilingual BM25 search engine & repository manager
├── admin.py                    # Escalation manager, authentication & query analytics
├── config.py                   # Configuration, paths, environment variables & thresholds
├── generate_sample_docs.py     # Script to generate realistic sample institutional documents
├── requirements.txt            # Minimal, lightweight Python dependencies
├── .env.example                # Configuration template for API keys & passwords
├── .gitignore                  # Git ignore rules for virtual environments & secrets
├── data/
│   ├── documents/              # Approved repository of college documents
│   │   ├── college_handbook_2026.pdf
│   │   ├── academic_regulations.txt
│   │   ├── fee_structure_and_deadlines.csv
│   │   ├── department_directory.json
│   │   └── holiday_calendar_2026.json
│   ├── unanswered_questions.json # Escalation queue for administrative review
│   └── query_history.json      # Complete query logs for analytics
├── sample_data/                # Backup copies of reference sample documents
├── tests/
│   ├── conftest.py             # Pytest environment & path setup
│   └── test_faq_agent.py       # 13 comprehensive automated unit & integration tests
└── README.md                   # Documentation and usage guide
```

---

## 📋 Response Schema

All internal question-answering interactions follow a structured JSON schema:

### When information is found:
```json
{
  "question": "What is the minimum attendance requirement?",
  "answer": "Every registered student must secure a minimum of 75% attendance in every course across lecture, tutorial, and practical sessions to be eligible to appear for the End-Semester Examinations.",
  "source": {
    "document": "college_handbook_2026.pdf",
    "page": 1,
    "section": "Section 1: Attendance Rules and Minimum Requirement"
  },
  "status": "answered",
  "needs_human_review": false
}
```

### When information cannot be verified:
```json
{
  "question": "What is tomorrow's dinner menu?",
  "answer": "This information could not be verified from the approved documents.",
  "source": null,
  "status": "unanswered",
  "needs_human_review": true
}
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Google Gemini API Key ([Get a free key at Google AI Studio](https://aistudio.google.com/))

### 2. Clone / Open Directory
```bash
cd "d:\College FAQ Agent"
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and set your configuration:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
ADMIN_PASSWORD=admin123
MAX_FILE_SIZE_MB=25
TOP_K_RESULTS=4
MIN_RELEVANCE_SCORE=0.20
```

*(Note: You can also enter or update the Gemini API key directly inside the Streamlit sidebar during runtime!)*

### 5. Generate Reference Documents
To generate initial sample documents (PDF, TXT, CSV, JSON):
```bash
python generate_sample_docs.py
```

### 6. Run the Application
Launch the Streamlit interface:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 💡 Example Questions

### English Questions
- **Attendance**: *"What is the minimum attendance requirement?"*
- **Attendance Condonation**: *"What are the rules for attendance condonation between 65% and 74%?"*
- **Revaluation**: *"How do I apply for photocopy and revaluation of exam answer sheets?"*
- **Fees**: *"What is the annual tuition fee for Government Quota engineering students?"*
- **Hostel**: *"What is the annual hostel room rent for AC rooms?"*
- **Library**: *"What is the book borrowing limit and overdue fine in the library?"*
- **Faculty / HOD**: *"Who is the Head of Department for Computer Science and Engineering?"*
- **Timetable**: *"What are the college daily shift timings and lunch interval?"*

### Tamil Questions (தமிழ் வினாக்கள்)
- **Holidays**: *"பொங்கல் பண்டிகை விடுமுறை நாட்கள் எவை?"*
- **Tamil Instruction**: *"தமிழ் வழியில் படிக்கும் மாணவர்களுக்கான வசதிகள் என்ன?"*
- **Out-of-domain (Escalation)**: *"நாளை செவ்வாய் கிரகத்தில் தேர்வுகள் நடக்குமா?"* *(Correctly flagged as unverified and escalated)*

---

## 🔐 Administrator Portal Features

Switch to the **Administrator Portal** using the sidebar:
1. **Authentication**: Enter the password (default: `admin123`).
2. **Analytics & Metrics**:
   - Total queries received, answered count, unanswered count, and answer rate %.
   - Interactive bar chart showing inquiries distributed across academic categories (Attendance, Examinations, Fees, Timetable, etc.).
3. **Escalated Questions Review Queue**:
   - Filter inquiries by status (`pending`, `reviewed`, `resolved`, `all`).
   - View student question text, category, and submission timestamp.
   - Add internal administrator notes and draft official responses.
   - Update inquiry lifecycle status.
4. **Approved Documents Manager**:
   - Upload new institutional notices, schedules, or handbooks (`PDF`, `TXT`, `CSV`, `JSON`).
   - Inspect indexed chunk counts and file sizes.
   - Delete obsolete circulars with instant automatic re-indexing.
   - One-click manual **Re-index All Documents** button.

---

## 🧪 Automated Testing

The project includes an automated test suite executed with `pytest`:

```bash
python -m pytest tests/ -v
```

### Tested Scenarios:
| Test ID | Test Description | Status |
|---|---|---|
| 01 | Question with verifiable answer in documents (Attendance 75%) | ✅ PASSED |
| 02 | Unanswerable question escalation (Logs to `unanswered_questions.json`) | ✅ PASSED |
| 03 | Unsupported file formats (.exe, .docx) rejection | ✅ PASSED |
| 04 | Invalid or empty input handling | ✅ PASSED |
| 05 | LLM API timeout/failure handling and graceful escalation | ✅ PASSED |
| 06 | Source reference verification (Prevents fabricated citations) | ✅ PASSED |
| 07 | Tamil language query detection and search retrieval | ✅ PASSED |
| 08 | Admin authentication and inquiry resolution lifecycle | ✅ PASSED |
| 09 | Structured CSV document query retrieval (Hostel mess fees) | ✅ PASSED |
| 10 | Structured JSON department directory retrieval (CSE HOD) | ✅ PASSED |
| 11 | TXT academic regulations retrieval (On-Duty OD leave rules) | ✅ PASSED |
| 12 | Tamil unanswerable question escalation message | ✅ PASSED |
| 13 | Live document indexing and deletion lifecycle | ✅ PASSED |

---

## 🛡️ Security & Privacy Practices

- **Zero Hardcoded Secrets**: Secrets and keys are loaded exclusively from `.env` or session state. `.env` is ignored by Git.
- **Untrusted Document Boundary**: Document text is strictly encapsulated within delimited context blocks and cannot override system instructions.
- **File Upload Protection**: Enforces strict file extension verification (`ALLOWED_EXTENSIONS`) and maximum file size thresholds (`MAX_FILE_SIZE_MB`).
- **Path Traversal Prevention**: Document paths are normalized to avoid relative directory traversal attacks.
- **No External Dispatches**: Unanswered inquiries are saved strictly to local persistent storage without making unsolicited external emails or network dispatches.

---

## 🔧 Troubleshooting

1. **"Gemini API key is not configured" Warning**:
   - Add `GEMINI_API_KEY=your_key` to `.env` or input your key directly into the Streamlit sidebar under **Update Gemini API Key**.
   - Note that in extractive fallback mode, the system will still answer factual questions directly from matched document excerpts.
2. **Document Upload Error**:
   - Ensure the file format is `.pdf`, `.txt`, `.csv`, or `.json` and under 25MB.
3. **ModuleNotFoundError**:
   - Run `pip install -r requirements.txt` to install all dependencies.
4. **Port in use when launching Streamlit**:
   - Run `streamlit run app.py --server.port 8502`.
