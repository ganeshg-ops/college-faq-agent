import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import (
    UNANSWERED_QUESTIONS_FILE,
    QUERY_HISTORY_FILE,
    STUDENTS_FILE,
    ADMIN_PASSWORD,
    DOCUMENTS_DIR,
)


CATEGORIES = [
    "Attendance",
    "Examinations",
    "Fees & Payments",
    "Timetable & Schedules",
    "Admissions",
    "Holidays & Calendar",
    "Faculty & Departments",
    "Hostel & Facilities",
    "Placements & Careers",
    "General Regulations",
]


def categorize_question(question: str) -> str:
    """
    Heuristically categorizes the student query into standard college domains.
    Supports English and Tamil keyword clues.
    """
    q = question.lower()
    if any(k in q for k in ["attendance", "present", "absent", "leave", "onduty", "od", "வருகை"]):
        return "Attendance"
    elif any(k in q for k in ["exam", "arrear", "revaluation", "grade", "gpa", "mark", "hall ticket", "தேர்வு"]):
        return "Examinations"
    elif any(k in q for k in ["fee", "tuition", "payment", "fine", "scholarship", "கட்டணம்"]):
        return "Fees & Payments"
    elif any(k in q for k in ["holiday", "vacation", "pongal", "diwali", "calendar", "விடுமுறை"]):
        return "Holidays & Calendar"
    elif any(k in q for k in ["time table", "timetable", "schedule", "timing", "class", "நேர அட்டவணை"]):
        return "Timetable & Schedules"
    elif any(k in q for k in ["admission", "seat", "cutoff", "eligibility", "சேர்க்கை"]):
        return "Admissions"
    elif any(k in q for k in ["faculty", "hod", "professor", "department", "dean", "துறை", "பேராசிரியர்"]):
        return "Faculty & Departments"
    elif any(k in q for k in ["hostel", "mess", "canteen", "bus", "transport", "library", "நூலகம்", "விடுதி"]):
        return "Hostel & Facilities"
    elif any(k in q for k in ["placement", "internship", "job", "recruiter", "interview"]):
        return "Placements & Careers"
    return "General Regulations"


class AdminManager:
    """
    Handles administrator authentication, escalation records storage,
    unanswered questions resolution, and question analytics.
    """

    def __init__(
        self,
        unanswered_file: Path = UNANSWERED_QUESTIONS_FILE,
        history_file: Path = QUERY_HISTORY_FILE,
        students_file: Path = STUDENTS_FILE,
    ):
        self.unanswered_file = Path(unanswered_file)
        self.history_file = Path(history_file)
        self.students_file = Path(students_file)
        self._ensure_files()

    def _ensure_files(self) -> None:
        """Ensure JSON files exist and contain valid JSON arrays."""
        self.unanswered_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.unanswered_file.exists():
            with open(self.unanswered_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

        if not self.history_file.exists():
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

        if not self.students_file.exists():
            default_students = [
                {
                    "name": "Student",
                    "email": "student@amman.edu",
                    "password": "student123",
                    "department": "CSE"
                },
                {
                    "name": "Priya S",
                    "email": "priya@amman.edu",
                    "password": "student123",
                    "department": "AI&DS"
                }
            ]
            with open(self.students_file, "w", encoding="utf-8") as f:
                json.dump(default_students, f, indent=2)

    def verify_password(self, password: str) -> bool:
        """Securely verifies admin password against configured secret."""
        if not password or not ADMIN_PASSWORD:
            return False
        return password.strip() == ADMIN_PASSWORD.strip()

    def get_students(self) -> List[Dict[str, Any]]:
        """Returns the list of registered students."""
        try:
            with open(self.students_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def verify_student_login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Validates student credentials and returns student profile if successful."""
        clean_email = (email or "").strip().lower()
        clean_pass = (password or "").strip()
        if not clean_email or not clean_pass:
            return None
        students = self.get_students()
        for s in students:
            if s.get("email", "").lower().strip() == clean_email and s.get("password") == clean_pass:
                return s
        return None

    def register_student(self, name: str, email: str, password: str, department: str = "General") -> bool:
        """Registers a new student account."""
        clean_email = (email or "").strip().lower()
        clean_pass = (password or "").strip()
        clean_name = (name or "").strip()
        if not clean_email or not clean_pass or not clean_name:
            return False
        students = self.get_students()
        if any(s.get("email", "").lower() == clean_email for s in students):
            return False
        students.append({
            "name": clean_name,
            "email": clean_email,
            "password": clean_pass,
            "department": department.strip() or "General"
        })
        try:
            with open(self.students_file, "w", encoding="utf-8") as f:
                json.dump(students, f, indent=2)
            return True
        except Exception:
            return False

    def log_query(
        self,
        question: str,
        status: str,
        answer: str,
        source: Optional[Dict[str, Any]] = None,
        needs_human_review: bool = False,
    ) -> Dict[str, Any]:
        """
        Logs student query to persistent history.
        If unanswered or needs review, automatically creates an escalation entry.
        """
        now = datetime.now(timezone.utc).isoformat()
        category = categorize_question(question)
        entry_id = str(uuid.uuid4())[:8]

        record = {
            "id": entry_id,
            "question": question.strip(),
            "timestamp": now,
            "category": category,
            "status": status,
            "answer": answer,
            "source": source,
            "needs_human_review": needs_human_review,
        }

        # 1. Append to full query history
        try:
            with open(self.history_file, "r+", encoding="utf-8") as f:
                history = json.load(f)
                history.append(record)
                f.seek(0)
                f.truncate()
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([record], f, indent=2, ensure_ascii=False)

        # 2. If needs review or status == "unanswered", record in escalation queue
        if needs_human_review or status == "unanswered":
            self.escalate_unanswered_question(
                question=question,
                category=category,
                entry_id=entry_id,
                timestamp=now,
            )

        return record

    def escalate_unanswered_question(
        self,
        question: str,
        category: Optional[str] = None,
        entry_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Saves unanswered question into data/unanswered_questions.json.
        Avoids duplicate active entries for identical queries.
        """
        entry_id = entry_id or str(uuid.uuid4())[:8]
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        category = category or categorize_question(question)

        item = {
            "id": entry_id,
            "question": question.strip(),
            "timestamp": timestamp,
            "category": category,
            "status": "pending",  # pending | reviewed | resolved
            "admin_notes": "",
            "official_response": "",
        }

        try:
            with open(self.unanswered_file, "r+", encoding="utf-8") as f:
                items = json.load(f)
                # Check for existing pending query
                for existing in items:
                    if (
                        existing.get("question", "").lower().strip() == question.lower().strip()
                        and existing.get("status") == "pending"
                    ):
                        return existing

                items.append(item)
                f.seek(0)
                f.truncate()
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception:
            with open(self.unanswered_file, "w", encoding="utf-8") as f:
                json.dump([item], f, indent=2, ensure_ascii=False)

        return item

    def get_unanswered_questions(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves unanswered questions, optionally filtered by status."""
        try:
            with open(self.unanswered_file, "r", encoding="utf-8") as f:
                items = json.load(f)
            if status_filter and status_filter != "all":
                items = [x for x in items if x.get("status") == status_filter]
            return items
        except Exception:
            return []

    def update_unanswered_question(
        self,
        item_id: str,
        status: str,
        admin_notes: str = "",
        official_response: str = "",
    ) -> bool:
        """Updates review status, administrator notes, and official response."""
        try:
            with open(self.unanswered_file, "r+", encoding="utf-8") as f:
                items = json.load(f)
                found = False
                for item in items:
                    if item.get("id") == item_id:
                        item["status"] = status
                        item["admin_notes"] = admin_notes
                        item["official_response"] = official_response
                        item["resolved_at"] = datetime.now(timezone.utc).isoformat()
                        found = True
                        break
                if found:
                    f.seek(0)
                    f.truncate()
                    json.dump(items, f, indent=2, ensure_ascii=False)
                    return True
            return False
        except Exception:
            return False

    def get_analytics(self) -> Dict[str, Any]:
        """Computes system metrics: total questions, answered, unanswered, categories."""
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

        try:
            with open(self.unanswered_file, "r", encoding="utf-8") as f:
                unanswered_items = json.load(f)
        except Exception:
            unanswered_items = []

        total_questions = len(history)
        answered_count = sum(1 for q in history if q.get("status") == "answered")
        unanswered_count = sum(1 for q in history if q.get("status") == "unanswered")
        pending_review_count = sum(1 for q in unanswered_items if q.get("status") == "pending")

        answer_rate = round((answered_count / total_questions * 100), 1) if total_questions > 0 else 0.0

        categories_count = {}
        for q in history:
            cat = q.get("category", "General Regulations")
            categories_count[cat] = categories_count.get(cat, 0) + 1

        return {
            "total_questions": total_questions,
            "answered_count": answered_count,
            "unanswered_count": unanswered_count,
            "pending_review_count": pending_review_count,
            "answer_rate": answer_rate,
            "categories_distribution": categories_count,
        }
