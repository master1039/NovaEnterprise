"""The operator command supports a write-free canonical dry run."""

import json

from backend.app.ingestion.command import main


def test_dry_run_validates_canonical_documents(capsys) -> None:
    assert main(["--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)

    assert len(report) >= 10
    assert all(item["status"] == "validated" for item in report)
    assert all(item["chunks"] >= 1 for item in report)
    assert any(item["hostile_chunks"] >= 1 for item in report)
