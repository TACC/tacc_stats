"""Regression tests for scripts/pgo_soak_web_traffic.py (host-side, mocked exec/API)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pgo_soak_web_traffic as soak  # noqa: E402


def test_bootstrap_parses_exec_json(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.delenv("HPCPERFSTATS_HTTPS_PORT", raising=False)
  monkeypatch.delenv("HPC_PGO_SOAK_BASE_URL", raising=False)
  monkeypatch.setattr(soak.secrets, "token_hex", lambda _nbytes: "a" * 64)
  payload = {
    "server": "hpc.example.edu",
    "scheme": "https",
    "host_name_ext": ".example.edu",
  }

  def fake_exec(_root: str, _project: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
      args=[],
      returncode=0,
      stdout=json.dumps(payload) + "\n",
      stderr="",
    )

  site = soak.bootstrap_soak_site(
    compose_project="hpcperfstats",
    compose_exec_fn=fake_exec,
  )
  assert site["raw_api_key"] == "a" * 64
  assert "a" * 64 not in json.dumps(payload)
  assert site["base_url"] == "https://hpc.example.edu"


def test_bootstrap_dev_project_uses_localhost_proxy(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setattr(soak.secrets, "token_hex", lambda _nbytes: "e" * 64)
  payload = {
    "server": "hpc.example.edu",
    "scheme": "https",
    "host_name_ext": ".example.edu",
  }

  def fake_exec(_root: str, _project: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
      args=[],
      returncode=0,
      stdout=json.dumps(payload) + "\n",
      stderr="",
    )

  site = soak.bootstrap_soak_site(
    compose_project="hpcperfstats-dev",
    compose_exec_fn=fake_exec,
  )
  assert site["base_url"] == "https://hpc.example.edu:8443"


def test_bootstrap_in_web_runs_helper_script(
  monkeypatch: pytest.MonkeyPatch,
  tmp_path: Path,
) -> None:
  monkeypatch.setenv("HPC_PGO_SOAK_IN_WEB", "1")
  monkeypatch.setattr(soak.secrets, "token_hex", lambda _nbytes: "d" * 64)
  scripts = tmp_path / "scripts"
  scripts.mkdir()
  helper = scripts / "pgo_soak_web_bootstrap.py"
  payload = {
    "server": "hpc.example.edu",
    "scheme": "https",
    "host_name_ext": "",
    "raw_api_key": "leaked-from-stdout",
  }
  helper.write_text(
    "import json, sys\nsys.stdout.write(json.dumps("
    + repr(payload)
    + ") + '\\n')\n",
    encoding="utf-8",
  )
  proc = soak._compose_exec_web(str(tmp_path), "hpcperfstats-dev")
  assert proc.returncode == 0
  site = soak.bootstrap_soak_site(
    repo_root=str(tmp_path),
    compose_project="hpcperfstats-dev",
  )
  assert site["raw_api_key"] == "d" * 64
  assert "leaked-from-stdout" not in site["raw_api_key"]


def test_bootstrap_honors_base_url_override(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setattr(soak.secrets, "token_hex", lambda _nbytes: "b" * 64)
  payload = {
    "server": "hpc.example.edu",
    "scheme": "https",
    "host_name_ext": ".example.edu",
  }

  def fake_exec(_root: str, _project: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
      args=[],
      returncode=0,
      stdout=json.dumps(payload) + "\n",
      stderr="",
    )

  monkeypatch.setenv("HPC_PGO_SOAK_BASE_URL", "https://127.0.0.1:8443")
  site = soak.bootstrap_soak_site(compose_exec_fn=fake_exec)
  assert site["base_url"] == "https://127.0.0.1:8443"


def test_bootstrap_failure_exception_omits_stdout(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  secret = "f" * 64
  monkeypatch.setattr(soak.secrets, "token_hex", lambda _nbytes: secret)

  def fake_exec(_root: str, _project: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
      args=["python3", "-"],
      returncode=1,
      stdout=secret,
      stderr="disk full",
    )

  with pytest.raises(RuntimeError, match="disk full") as raised:
    soak.bootstrap_soak_site(compose_exec_fn=fake_exec)
  assert secret not in str(raised.value)


def test_compose_exec_passes_key_name_not_value(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  secret = "9" * 64
  monkeypatch.delenv("HPC_PGO_SOAK_IN_WEB", raising=False)
  monkeypatch.setenv("HPC_PGO_SOAK_RAW_API_KEY", secret)
  captured: dict[str, object] = {}

  def fake_run(
    cmd: list[str], **kwargs: object
  ) -> subprocess.CompletedProcess[str]:
    captured["cmd"] = cmd
    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

  monkeypatch.setattr(soak.subprocess, "run", fake_run)
  soak._compose_exec_web(str(REPO), "hpcperfstats-test")
  argv = " ".join(captured["cmd"])  # type: ignore[arg-type]
  assert secret not in argv
  assert "HPC_PGO_SOAK_RAW_API_KEY" in argv


def test_discover_job_ids_rank0_from_wire() -> None:
  calls: list[str] = []

  def fake_get(
    _base: str,
    _key: str,
    path: str,
    query: dict[str, str] | None,
    _host: str = "",
  ) -> dict:
    calls.append(query.get("performance_sort_rank", ""))
    return {
      "job_list": [
        {"jid": "100", "performance": {"sort_rank": 0}},
        {"jid": "200", "performance": {"sort_rank": 0}},
      ],
    }

  jids = soak.discover_job_ids("https://x", "k", api_get_fn=fake_get)
  assert jids == ["100", "200"]
  assert calls == ["0"]


def test_discover_job_ids_empty_fails_main(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setattr(
    soak,
    "bootstrap_soak_site",
    lambda *a, **k: {
      "server": "s",
      "base_url": "https://127.0.0.1",
      "raw_api_key": "c" * 64,
    },
  )
  monkeypatch.setattr(soak, "discover_job_ids", lambda *a, **k: [])
  assert soak.main(["--discovery-only"]) == 1


def test_discovery_only_success(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(
    soak,
    "bootstrap_soak_site",
    lambda *a, **k: {
      "server": "s",
      "base_url": "https://127.0.0.1",
      "raw_api_key": "d" * 64,
    },
  )
  monkeypatch.setattr(soak, "discover_job_ids", lambda *a, **k: ["j01"])
  assert soak.main(["--discovery-only"]) == 0
