"""integrations module — Adapter registry for دانشجو۳۶۰ (ARC-05, S360-01..10) + LMS event mapping.

Rule: the Club owns neither identity, skill graph, nor learning assessment. Local data is a
minimal snapshot with source & snapshot_at. Real vs simulator mode is explicit and queryable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class IdentitySnapshot:
    student_reference: str
    display_name: str
    university_id: str
    mode: str  # real | simulator


class IdentityAdapter(Protocol):
    mode: str
    def verify_token(self, token: str) -> IdentitySnapshot | None: ...
    def get_snapshot(self, student_reference: str) -> IdentitySnapshot | None: ...


class SimulatorIdentityAdapter:
    """Labelled test adapter — never used when ENABLE_SIMULATORS=false (EVT-11, ARC-05)."""
    mode = "simulator"

    def __init__(self, db=None):
        self.db = db

    def verify_token(self, token: str) -> IdentitySnapshot | None:
        if token.startswith("sim-"):
            _, uni, sid = token.split(":", 2)
            return IdentitySnapshot(student_reference=sid, display_name=f"کاربر آزمایشی {sid}", university_id=uni, mode=self.mode)
        return None

    def get_snapshot(self, student_reference: str) -> IdentitySnapshot | None:
        return IdentitySnapshot(student_reference=student_reference, display_name="دانشجوی آزمایشی", university_id="", mode=self.mode)


class OidcIdentityAdapter:
    """Configuration-complete OIDC adapter — activation requires client answers to Q1 (ACC-13)."""
    mode = "real"

    def __init__(self, issuer_url: str, client_id: str, client_secret: str):
        self.issuer_url, self.client_id, self.client_secret = issuer_url, client_id, client_secret

    def verify_token(self, token: str) -> IdentitySnapshot | None:  # pragma: no cover — needs real IdP
        raise NotImplementedError("OIDC verification requires approved S360 integration (open question Q1)")

    def get_snapshot(self, student_reference: str) -> IdentitySnapshot | None:  # pragma: no cover
        raise NotImplementedError("OIDC verification requires approved S360 integration (open question Q1)")


# LMS event-type mapping (EVT-02) — documented initial contract
LMS_EVENT_MAP = {
    "lecture_attended": "meaningful_attendance_verified",
    "lesson_completed": "study_completion_verified",
    "assignment_graded": "exercise_assessed",
    "adaptive_module_progress": "adaptive_progress_verified",
    "skill_badge_progress": "skill_progress_verified",
    "contribution_accepted": "contribution_approved",
    "peer_help_verified": "peer_support_verified",
    "content_approved": "educational_content_approved",
}

EVENT_TYPES = set(LMS_EVENT_MAP.values())


def get_identity_adapter(db=None) -> IdentityAdapter:
    from ...core.config import get_settings

    s = get_settings()
    if s.enable_simulators:
        return SimulatorIdentityAdapter(db)
    return OidcIdentityAdapter(
        issuer_url=__import__("os").environ.get("S360_OIDC_ISSUER", ""),
        client_id=__import__("os").environ.get("S360_OIDC_CLIENT_ID", ""),
        client_secret=__import__("os").environ.get("S360_OIDC_CLIENT_SECRET", ""),
    )


class StorageAdapter:
    """S3-compatible private storage with short-lived signed URLs (SEC-09)."""

    def __init__(self, backend: str = "local"):
        self.backend = backend

    def signed_url(self, key: str, ttl_seconds: int = 300) -> str:
        import hashlib
        import time

        from ...core.config import get_settings

        exp = int(time.time()) + ttl_seconds
        sig = hashlib.sha256(f"{get_settings().secret_key}:{key}:{exp}".encode()).hexdigest()[:32]
        return f"/api/v1/files/{key}?expires={exp}&signature={sig}"
