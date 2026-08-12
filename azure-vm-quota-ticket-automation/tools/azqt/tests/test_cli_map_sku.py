"""CLI tests for ``azqt map-sku``.

**Validates: Requirements 2.6, 2.9, 9.3**
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from azqt.cli import main
from azqt.runstate.init_run import init_run


def _read_sku_resolution_events(log_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["event_type"] == "sku-resolution"
    ]


def _start_run(tmp_path: Path) -> tuple[str, Path]:
    run = init_run("quota-request.txt", state_dir=tmp_path)
    return run["run_id"], run["log_path"]


def test_map_sku_resolves_a_sku_flag_and_audits_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ``--sku`` form produces its documented result and one audit event."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    run_id, log_path = _start_run(tmp_path)

    exit_code = main(
        [
            "map-sku",
            "--run",
            run_id,
            "--candidate-id",
            "sku-candidate",
            "--sku",
            " standard_ d2S_ v5 ",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "resolutions": [
            {
                "candidate_id": "sku-candidate",
                "quota_family": "standardDSv5Family",
                "matched_input": " standard_ d2S_ v5 ",
                "ambiguous_candidates": [],
                "unmatched": False,
            }
        ]
    }

    events = _read_sku_resolution_events(log_path)
    assert len(events) == 1
    assert events[0]["data"] == {
        "candidate_id": "sku-candidate",
        "input": {
            "vm_sku_name": " standard_ d2S_ v5 ",
            "informal_size_description": None,
        },
        "outcome": payload["resolutions"][0],
    }


def test_map_sku_resolves_informal_size_flags_and_audits_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ``--vcpu``/``--memory-gib`` form preserves ambiguous candidates for clarification."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    run_id, log_path = _start_run(tmp_path)

    exit_code = main(
        [
            "map-sku",
            "--run",
            run_id,
            "--candidate-id",
            "size-candidate",
            "--vcpu",
            "2",
            "--memory-gib",
            "8",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    resolution = payload["resolutions"][0]
    assert resolution["candidate_id"] == "size-candidate"
    assert resolution["quota_family"] is None
    assert set(resolution["ambiguous_candidates"]) == {
        "standardDSv3Family",
        "standardDSv4Family",
        "standardDSv5Family",
        "standardDav6Family",
        "standardDSv6Family",
        "standardDADSv6Family",
    }
    assert resolution["unmatched"] is False

    events = _read_sku_resolution_events(log_path)
    assert len(events) == 1
    assert events[0]["data"]["candidate_id"] == "size-candidate"
    assert events[0]["data"]["outcome"] == resolution


def test_map_sku_resolves_batch_candidates_and_audits_each_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Batch mode uses the same resolver and appends exactly one entry per candidate."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    run_id, log_path = _start_run(tmp_path)
    candidates_path = tmp_path / "candidates.json"
    candidates_path.write_text(
        json.dumps(
            [
                {"candidate_id": "matched", "vm_sku_name": "Standard_D2s_v5"},
                {
                    "candidate_id": "ambiguous",
                    "vm_sku_name": None,
                    "informal_size_description": {"vcpu": 8, "memory_gib": 64},
                },
                {"candidate_id": "unmatched", "vm_sku_name": "Standard_ZZ99_not_a_real_sku"},
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["map-sku", "--run", run_id, "--input", str(candidates_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    resolutions = payload["resolutions"]
    assert [resolution["candidate_id"] for resolution in resolutions] == [
        "matched",
        "ambiguous",
        "unmatched",
    ]
    assert resolutions[0]["quota_family"] == "standardDSv5Family"
    assert resolutions[1]["quota_family"] is None
    assert resolutions[1]["ambiguous_candidates"] == [
        "standardESv3Family",
        "standardESv5Family",
        "standardEav6Family",
        "standardESv6Family",
        "standardEADSv6Family",
    ]
    assert resolutions[2]["unmatched"] is True

    events = _read_sku_resolution_events(log_path)
    assert len(events) == len(resolutions) == 3
    assert [event["data"]["candidate_id"] for event in events] == [
        "matched",
        "ambiguous",
        "unmatched",
    ]
    assert [event["data"]["outcome"] for event in events] == resolutions
