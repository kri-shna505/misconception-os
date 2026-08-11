from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import attempt_routes
from app.core.database import get_db


class FakeDatabase:
    """Minimal dependency object used by route-level tests."""

    pass


@pytest.fixture
def fake_db() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def app(fake_db: FakeDatabase) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(
        attempt_routes.router,
        prefix="/api",
    )

    def override_get_db():
        yield fake_db

    test_app.dependency_overrides[get_db] = override_get_db

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def make_attempt_response(
    *,
    attempt_id: UUID | None = None,
    student_alias_id: UUID | None = None,
    problem_id: UUID | None = None,
    **overrides: object,
) -> SimpleNamespace:
    """
    Build a complete Sprint 10 attempt object accepted by AttemptResponse.
    """

    now = datetime(2026, 8, 11, 8, 0, 0)

    data: dict[str, object] = {
        "id": attempt_id or uuid4(),
        "student_alias_id": student_alias_id or uuid4(),
        "problem_id": problem_id or uuid4(),
        "parent_attempt_id": None,
        "retry_number": 0,
        "final_answer": "42",
        "written_reasoning": "I solved the problem using the submitted approach.",
        "normalized_reasoning": None,
        "source_code": "print(42)",
        "speech_transcript": None,
        "speech_audio_reference": None,
        "speech_audio_retained": False,
        "speech_processing_status": "not_provided",
        "input_modality": "text_code",
        "input_language": "english",
        "detected_language": None,
        "selected_language": "python",
        "response_time_seconds": 30,
        "created_at": now,
        "updated_at": now,
    }

    data.update(overrides)

    return SimpleNamespace(**data)


def valid_attempt_payload(
    *,
    student_alias_id: UUID | None = None,
    problem_id: UUID | None = None,
    **overrides: object,
) -> dict[str, object]:
    data: dict[str, object] = {
        "student_alias_id": str(student_alias_id or uuid4()),
        "problem_id": str(problem_id or uuid4()),
        "final_answer": "42",
        "written_reasoning": (
            "I solved the problem using the submitted approach."
        ),
        "source_code": "print(42)",
        "speech_transcript": None,
        "selected_language": "python",
        "response_time_seconds": 30,
        "normalized_reasoning": None,
        "speech_audio_reference": None,
        "speech_audio_retained": False,
        "speech_processing_status": "not_provided",
        "input_modality": "text_code",
        "input_language": "english",
        "detected_language": None,
    }

    data.update(overrides)
    return data


def test_post_attempt_route_accepts_sprint10_text_code_payload(
    client: TestClient,
    fake_db: FakeDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    student_alias_id = uuid4()
    problem_id = uuid4()
    attempt_id = uuid4()

    captured: dict[str, object] = {}

    def fake_create_attempt(*, db, payload):
        captured["db"] = db
        captured["payload"] = payload

        return make_attempt_response(
            attempt_id=attempt_id,
            student_alias_id=student_alias_id,
            problem_id=problem_id,
        )

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            student_alias_id=student_alias_id,
            problem_id=problem_id,
        ),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == str(attempt_id)
    assert body["student_alias_id"] == str(student_alias_id)
    assert body["problem_id"] == str(problem_id)
    assert body["input_modality"] == "text_code"
    assert body["input_language"] == "english"
    assert body["speech_processing_status"] == "not_provided"

    assert captured["db"] is fake_db

    payload = captured["payload"]

    assert payload.student_alias_id == student_alias_id
    assert payload.problem_id == problem_id
    assert payload.input_modality == "text_code"
    assert payload.input_language == "english"


def test_post_attempt_route_normalizes_language_and_modality(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    student_alias_id = uuid4()
    problem_id = uuid4()

    captured: dict[str, object] = {}

    def fake_create_attempt(*, db, payload):
        captured["payload"] = payload

        return make_attempt_response(
            student_alias_id=student_alias_id,
            problem_id=problem_id,
            input_modality="text_code",
            input_language="telugu",
            detected_language="telugu",
        )

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            student_alias_id=student_alias_id,
            problem_id=problem_id,
            input_modality="text+code",
            input_language="TE",
            detected_language="tel",
        ),
    )

    assert response.status_code == 201

    payload = captured["payload"]

    assert payload.input_modality == "text_code"
    assert payload.input_language == "telugu"
    assert payload.detected_language == "telugu"

    body = response.json()

    assert body["input_modality"] == "text_code"
    assert body["input_language"] == "telugu"
    assert body["detected_language"] == "telugu"


def test_post_attempt_route_accepts_normalized_reasoning(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized_reasoning = (
        "Binary search requires sorted input; use linear search here."
    )

    captured: dict[str, object] = {}

    def fake_create_attempt(*, db, payload):
        captured["payload"] = payload

        return make_attempt_response(
            normalized_reasoning=normalized_reasoning,
        )

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            normalized_reasoning=normalized_reasoning,
        ),
    )

    assert response.status_code == 201
    assert (
        captured["payload"].normalized_reasoning
        == normalized_reasoning
    )
    assert response.json()["normalized_reasoning"] == normalized_reasoning


def test_post_attempt_route_accepts_speech_multimodal_payload(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcript = (
        "Each recursive call uses a smaller argument until the base case."
    )
    audio_reference = "audio://attempt/test-001"

    captured: dict[str, object] = {}

    def fake_create_attempt(*, db, payload):
        captured["payload"] = payload

        return make_attempt_response(
            final_answer=None,
            source_code=None,
            speech_transcript=transcript,
            speech_audio_reference=audio_reference,
            speech_audio_retained=True,
            speech_processing_status="completed",
            input_modality="speech",
            input_language="telugu",
            detected_language="telugu",
        )

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            final_answer=None,
            source_code=None,
            speech_transcript=transcript,
            speech_audio_reference=audio_reference,
            speech_audio_retained=True,
            speech_processing_status="completed",
            input_modality="speech",
            input_language="TE",
            detected_language="tel",
        ),
    )

    assert response.status_code == 201

    payload = captured["payload"]

    assert payload.speech_transcript == transcript
    assert payload.speech_audio_reference == audio_reference
    assert payload.speech_audio_retained is True
    assert payload.speech_processing_status == "completed"
    assert payload.input_modality == "speech"
    assert payload.input_language == "telugu"

    body = response.json()

    assert body["speech_transcript"] == transcript
    assert body["speech_audio_reference"] == audio_reference
    assert body["speech_audio_retained"] is True
    assert body["speech_processing_status"] == "completed"
    assert body["input_modality"] == "speech"


def test_post_attempt_route_rejects_retained_audio_without_reference(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_called = False

    def fake_create_attempt(*, db, payload):
        nonlocal service_called
        service_called = True
        return make_attempt_response()

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            speech_transcript="Spoken reasoning.",
            speech_audio_reference=None,
            speech_audio_retained=True,
            speech_processing_status="completed",
            input_modality="speech",
        ),
    )

    assert response.status_code == 422
    assert service_called is False


def test_post_attempt_route_rejects_speech_metadata_without_speech_modality(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_called = False

    def fake_create_attempt(*, db, payload):
        nonlocal service_called
        service_called = True
        return make_attempt_response()

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            speech_transcript="Spoken reasoning.",
            speech_processing_status="completed",
            input_modality="text_code",
        ),
    )

    assert response.status_code == 422
    assert service_called is False


def test_post_attempt_route_rejects_invalid_modality(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_called = False

    def fake_create_attempt(*, db, payload):
        nonlocal service_called
        service_called = True
        return make_attempt_response()

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            input_modality="video",
        ),
    )

    assert response.status_code == 422
    assert service_called is False


def test_post_attempt_route_rejects_invalid_speech_processing_status(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_called = False

    def fake_create_attempt(*, db, payload):
        nonlocal service_called
        service_called = True
        return make_attempt_response()

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            speech_processing_status="finished",
        ),
    )

    assert response.status_code == 422
    assert service_called is False


def test_post_attempt_route_rejects_invalid_uuid_before_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_called = False

    def fake_create_attempt(*, db, payload):
        nonlocal service_called
        service_called = True
        return make_attempt_response()

    monkeypatch.setattr(
        attempt_routes,
        "create_attempt",
        fake_create_attempt,
    )

    response = client.post(
        "/api/attempts",
        json=valid_attempt_payload(
            student_alias_id="not-a-uuid",
        ),
    )

    assert response.status_code == 422
    assert service_called is False


def test_get_attempt_route_returns_sprint10_attempt(
    client: TestClient,
    fake_db: FakeDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_id = uuid4()
    student_alias_id = uuid4()
    problem_id = uuid4()

    captured: dict[str, object] = {}

    def fake_get_attempt_by_id(*, db, attempt_id):
        captured["db"] = db
        captured["attempt_id"] = attempt_id

        return make_attempt_response(
            attempt_id=attempt_id,
            student_alias_id=student_alias_id,
            problem_id=problem_id,
            normalized_reasoning="Normalized reasoning.",
            speech_transcript="Speech reasoning.",
            speech_processing_status="completed",
            input_modality="text_speech",
            input_language="telugu",
            detected_language="telugu",
        )

    monkeypatch.setattr(
        attempt_routes,
        "get_attempt_by_id",
        fake_get_attempt_by_id,
    )

    response = client.get(
        f"/api/attempts/{attempt_id}",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == str(attempt_id)
    assert body["normalized_reasoning"] == "Normalized reasoning."
    assert body["speech_transcript"] == "Speech reasoning."
    assert body["speech_processing_status"] == "completed"
    assert body["input_modality"] == "text_speech"
    assert body["input_language"] == "telugu"
    assert body["detected_language"] == "telugu"

    assert captured["db"] is fake_db
    assert captured["attempt_id"] == attempt_id


def test_get_attempt_route_rejects_invalid_uuid_before_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_called = False

    def fake_get_attempt_by_id(*, db, attempt_id):
        nonlocal service_called
        service_called = True
        return make_attempt_response()

    monkeypatch.setattr(
        attempt_routes,
        "get_attempt_by_id",
        fake_get_attempt_by_id,
    )

    response = client.get(
        "/api/attempts/not-a-uuid",
    )

    assert response.status_code == 422
    assert service_called is False