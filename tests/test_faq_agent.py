import pytest
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from config import (
    DOCUMENTS_DIR,
    SAMPLE_DATA_DIR,
    UNANSWERED_QUESTIONS_FILE,
    QUERY_HISTORY_FILE,
)
from document_processor import DocumentProcessor, DocumentProcessingError
from document_search import DocumentSearchManager, BM25SearchEngine, tokenize
from admin import AdminManager, categorize_question
from faq_agent import CollegeFAQAgent, is_tamil_text


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """Ensure sample documents are generated before running tests."""
    from generate_sample_docs import create_sample_documents
    create_sample_documents(DOCUMENTS_DIR)


@pytest.fixture
def clean_admin_manager(tmp_path):
    """Provides an isolated AdminManager with temporary JSON files."""
    unanswered_file = tmp_path / "test_unanswered.json"
    history_file = tmp_path / "test_history.json"
    return AdminManager(unanswered_file=unanswered_file, history_file=history_file)


@pytest.fixture
def search_manager():
    """Provides a fresh DocumentSearchManager indexing test documents."""
    return DocumentSearchManager(documents_dir=DOCUMENTS_DIR)


@pytest.fixture
def agent(search_manager, clean_admin_manager):
    """Provides a CollegeFAQAgent instance."""
    return CollegeFAQAgent(
        api_key="",  # No key defaults to deterministic extractive fallback
        search_manager=search_manager,
        admin_manager=clean_admin_manager,
    )


# ============================================================================
# 1. TEST CASE: Question with an answer in the documents
# ============================================================================
def test_question_with_answer_in_documents(agent):
    """Verify that a legitimate student question is answered with source citation."""
    question = "What is the minimum attendance requirement?"
    response = agent.ask(question)

    assert response is not None
    assert response["status"] == "answered"
    assert response["needs_human_review"] is False
    assert "75%" in response["answer"]
    assert response["source"] is not None
    assert response["source"]["document"] in ["college_handbook_2026.pdf", "academic_regulations.txt"]
    assert response["source"]["page"] is not None or response["source"]["section"] is not None


# ============================================================================
# 2. TEST CASE: Question with NO answer in the documents (Escalation)
# ============================================================================
def test_question_with_no_answer_escalation(agent, clean_admin_manager):
    """Verify that unanswerable question triggers fallback and logs to escalation JSON."""
    question = "What is the rocket launch schedule to Mars?"
    response = agent.ask(question)

    assert response["status"] == "unanswered"
    assert response["needs_human_review"] is True
    assert response["source"] is None
    assert "could not be verified" in response["answer"].lower()

    # Verify persistent escalation in JSON file
    unanswered_list = clean_admin_manager.get_unanswered_questions()
    assert len(unanswered_list) >= 1
    escalated_item = next((item for item in unanswered_list if item["question"] == question), None)
    assert escalated_item is not None
    assert escalated_item["status"] == "pending"


# ============================================================================
# 3. TEST CASE: Question involving an unsupported document format
# ============================================================================
def test_unsupported_document_format(tmp_path):
    """Verify that unsupported document types (.exe, .docx, .zip) are rejected safely."""
    processor = DocumentProcessor()
    bad_file = tmp_path / "malicious_file.exe"
    bad_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00")

    with pytest.raises(DocumentProcessingError) as exc_info:
        processor.process_file(bad_file)
    assert "Unsupported file format" in str(exc_info.value)

    bad_docx = tmp_path / "syllabus.docx"
    bad_docx.write_bytes(b"PK\x03\x04")
    with pytest.raises(DocumentProcessingError) as exc_info2:
        processor.process_file(bad_docx)
    assert "Unsupported file format" in str(exc_info2.value)


# ============================================================================
# 4. TEST CASE: Invalid or empty question
# ============================================================================
def test_invalid_or_empty_question(agent):
    """Verify graceful handling of empty strings and whitespace-only queries."""
    empty_res = agent.ask("")
    assert empty_res["status"] == "invalid_input"
    assert empty_res["source"] is None
    assert "valid question" in empty_res["answer"]

    whitespace_res = agent.ask("     ")
    assert whitespace_res["status"] == "invalid_input"
    assert whitespace_res["source"] is None


# ============================================================================
# 5. TEST CASE: API failure handling
# ============================================================================
def test_api_failure_handling(search_manager, clean_admin_manager):
    """Verify that LLM API timeouts or errors are caught and escalated cleanly."""
    mock_agent = CollegeFAQAgent(
        api_key="fake-test-api-key",
        search_manager=search_manager,
        admin_manager=clean_admin_manager,
    )

    # Mock Gemini client to simulate an API exception
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Simulated Google API 503 Server Error")
    mock_agent._client = mock_client

    response = mock_agent.ask("What is the tuition fee for government quota?")

    assert response["status"] == "api_error"
    assert response["needs_human_review"] is True
    assert response["source"] is None
    assert "error occurred" in response["answer"].lower()

    # Verify query logged despite API failure
    unanswered = clean_admin_manager.get_unanswered_questions()
    assert any("tuition fee" in item["question"].lower() for item in unanswered)


# ============================================================================
# 6. TEST CASE: Source reference verification & anti-hallucination test
# ============================================================================
def test_source_reference_verification_prevents_fake_citation(search_manager, clean_admin_manager):
    """Verify that if LLM hallucinates an ungrounded document name, it is corrected."""
    agent_with_mock = CollegeFAQAgent(
        api_key="fake-key",
        search_manager=search_manager,
        admin_manager=clean_admin_manager,
    )

    fake_llm_json = json.dumps({
        "question": "What is the library borrowing entitlement?",
        "answer": "UG students can borrow 4 books for 14 days.",
        "source": {
            "document": "invented_fake_handbook.pdf",
            "page": 999,
            "section": "Invented Section"
        },
        "status": "answered",
        "needs_human_review": False
    })

    mock_response = MagicMock()
    mock_response.text = fake_llm_json
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    agent_with_mock._client = mock_client

    response = agent_with_mock.ask("What is the library borrowing entitlement?")

    assert response["status"] == "answered"
    # The fake citation must be replaced by the legitimate retrieved document
    assert response["source"]["document"] != "invented_fake_handbook.pdf"
    assert "college_handbook_2026.pdf" in response["source"]["document"]


# ============================================================================
# 7. TEST CASE: Tamil Language Support
# ============================================================================
def test_tamil_query_support(agent):
    """Verify Tamil language detection, tokenization, and search retrieval."""
    tamil_query = "பொங்கல் பண்டிகை விடுமுறை நாட்கள் எவை?"
    assert is_tamil_text(tamil_query) is True

    response = agent.ask(tamil_query)
    assert response["status"] == "answered"
    assert response["source"] is not None
    assert response["source"]["document"] == "holiday_calendar_2026.json"


# ============================================================================
# 8. TEST CASE: Admin Manager operations and escalation lifecycle
# ============================================================================
def test_admin_manager_lifecycle(clean_admin_manager):
    """Verify admin password verification, resolution workflow, and metrics."""
    assert clean_admin_manager.verify_password("admin123") is True
    assert clean_admin_manager.verify_password("wrong-password") is False

    # Escalate a question
    item = clean_admin_manager.escalate_unanswered_question("Is there a cricket ground in college?")
    item_id = item["id"]

    # Update resolution
    updated = clean_admin_manager.update_unanswered_question(
        item_id=item_id,
        status="resolved",
        admin_notes="Approved proposal to add sports facility document.",
        official_response="Yes, the college has an international-size cricket ground.",
    )
    assert updated is True

    # Check updated status
    resolved_items = clean_admin_manager.get_unanswered_questions(status_filter="resolved")
    assert any(x["id"] == item_id for x in resolved_items)

    # Check analytics
    analytics = clean_admin_manager.get_analytics()
    assert analytics["pending_review_count"] == 0


# ============================================================================
# 9. TEST CASE: CSV Document Query Retrieval
# ============================================================================
def test_csv_document_query(agent):
    """Verify answering queries sourced from structured CSV tables."""
    response = agent.ask("What is the hostel mess fee?")
    assert response["status"] == "answered"
    assert response["source"]["document"] == "fee_structure_and_deadlines.csv"
    assert "42000" in response["answer"] or "mess" in response["answer"].lower()


# ============================================================================
# 10. TEST CASE: JSON Directory Query Retrieval
# ============================================================================
def test_json_directory_query(agent):
    """Verify answering queries sourced from JSON department directories."""
    response = agent.ask("Who is the HOD of Computer Science and Engineering?")
    assert response["status"] == "answered"
    assert response["source"]["document"] == "department_directory.json"
    assert "Senthil Kumar" in response["answer"]


# ============================================================================
# 11. TEST CASE: TXT Regulations Query Retrieval
# ============================================================================
def test_txt_regulations_query(agent):
    """Verify answering queries sourced from academic regulations TXT."""
    response = agent.ask("What is the maximum permitted On-Duty OD leave?")
    assert response["status"] == "answered"
    assert response["source"]["document"] == "academic_regulations.txt"
    assert "10" in response["answer"]


# ============================================================================
# 12. TEST CASE: Tamil Unanswered Question Escalation
# ============================================================================
def test_tamil_unanswered_escalation(agent, clean_admin_manager):
    """Verify Tamil queries with no answer return Tamil escalation text and log."""
    tamil_unanswerable = "நாளை செவ்வாய் கிரகத்தில் தேர்வுகள் நடக்குமா?"
    response = agent.ask(tamil_unanswerable)
    assert response["status"] == "unanswered"
    assert response["needs_human_review"] is True
    assert "கிடைக்கவில்லை" in response["answer"]

    unanswered = clean_admin_manager.get_unanswered_questions()
    assert any(x["question"] == tamil_unanswerable for x in unanswered)


# ============================================================================
# 13. TEST CASE: Document Indexing and Deletion Lifecycle
# ============================================================================
def test_document_indexing_lifecycle(tmp_path):
    """Verify adding, searching, deleting, and re-indexing documents."""
    test_docs_dir = tmp_path / "lifecycle_docs"
    test_docs_dir.mkdir()

    # Create a temporary txt circular
    circ_file = test_docs_dir / "sports_circular.txt"
    circ_file.write_text("The annual college sports day will be held on December 15, 2026 at the athletic ground.")

    mgr = DocumentSearchManager(documents_dir=test_docs_dir)
    assert len(mgr.chunks) >= 1

    search_res = mgr.search_documents("sports day athletic ground")
    assert search_res["has_match"] is True

    # Delete document
    deleted = mgr.delete_document("sports_circular.txt")
    assert deleted is True
    assert len(mgr.chunks) == 0

