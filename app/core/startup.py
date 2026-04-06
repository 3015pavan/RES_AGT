from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.db.supabase_repo import SupabaseRepository


@dataclass
class ReadinessState:
    ready: bool
    reason: str


def run_startup_checks(settings: Settings) -> ReadinessState:
    required = [
        settings.supabase_url,
        settings.supabase_key,
        settings.llm_api_key,
        settings.hf_api_key,
        settings.api_key,
    ]

    if settings.email_automation_enabled:
        required.extend(
            [
                settings.imap_host,
                settings.imap_user,
                settings.imap_password,
                settings.smtp_host,
                settings.smtp_user,
                settings.smtp_password,
                settings.smtp_from,
            ]
        )

    if any(not item for item in required):
        return ReadinessState(ready=False, reason="Missing required environment variables")

    try:
        repo = SupabaseRepository(settings)
        repo.client.table("students").select("id").limit(1).execute()

        migrations_dir = Path(__file__).resolve().parents[1] / "db" / "migrations"
        required_versions = {
            path.stem
            for path in migrations_dir.glob("*.sql")
            if path.stem and not path.stem.startswith("_")
        }
        applied_versions = repo.list_migration_versions()
        missing_versions = sorted(required_versions - applied_versions)
        if missing_versions:
            return ReadinessState(
                ready=False,
                reason=f"Pending migrations: {', '.join(missing_versions)}",
            )
    except Exception as exc:
        return ReadinessState(ready=False, reason=f"Supabase connectivity check failed: {exc}")

    return ReadinessState(ready=True, reason="ok")
