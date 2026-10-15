#!/usr/bin/env python3
"""Live-soak web/API traffic for Clang PGO (rank-0 jobs, Playwright + API).

Attributes:
  SCRIPT_DIR: Directory containing this script.
  REPO_ROOT: Parent git checkout path.
  BOOTSTRAP_SCRIPT: Path to in-container bootstrap helper.
  DISCOVER_SCRIPT: Path to in-container job discovery helper.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BOOTSTRAP_SCRIPT = os.path.join(SCRIPT_DIR, "pgo_soak_web_bootstrap.py")
DISCOVER_SCRIPT = os.path.join(SCRIPT_DIR, "pgo_soak_discover_jobs.py")

try:
  from playwright.sync_api import sync_playwright
except ModuleNotFoundError:
  sync_playwright = None  # type: ignore[misc, assignment]


def _soak_in_web_container() -> bool:
  """
  True when Playwright soak runs inside the running ``web`` service container.

  Returns:
    bool: Environment flag ``HPC_PGO_SOAK_IN_WEB=1``.

  Examples:
    >>> _soak_in_web_container()  # doctest: +SKIP
  """
  return os.environ.get("HPC_PGO_SOAK_IN_WEB", "").strip() == "1"


def _web_helper_script_path(repo_root: str, script_name: str) -> str:
  """
  Resolve bootstrap/discover helper path in checkout or baked image.

  Args:
    repo_root: Host or container checkout root.
    script_name: Basename under ``scripts/``.

  Returns:
    str: Existing script path.

  Raises:
    RuntimeError: When the script is missing.

  Examples:
    >>> _web_helper_script_path(
    ...   "/home/hpcperfstats", "pgo_soak_web_bootstrap.py"
    ... )  # doctest: +SKIP
  """
  for root in (repo_root, "/home/hpcperfstats"):
    path = os.path.join(root, "scripts", script_name)
    if os.path.isfile(path):
      return path
  raise RuntimeError(f"missing web soak helper script: {script_name}")


def _run_web_helper_script(
  repo_root: str,
  script_name: str,
  *,
  extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
  """
  Execute a bootstrap/discover helper with ``python3`` (in-container mode).

  Args:
    repo_root: Checkout root for ``cwd``.
    script_name: Script basename under ``scripts/``.
    extra_env: Optional environment overrides.

  Returns:
    subprocess.CompletedProcess[str]: Helper result.

  Examples:
    >>> _run_web_helper_script(
    ...   "/tmp", "pgo_soak_web_bootstrap.py"
    ... )  # doctest: +SKIP
  """
  path = _web_helper_script_path(repo_root, script_name)
  env = os.environ.copy()
  if extra_env:
    env.update(extra_env)
  return subprocess.run(
    ["python3", path],
    cwd=repo_root if os.path.isdir(repo_root) else "/home/hpcperfstats",
    capture_output=True,
    text=True,
    check=False,
    env=env,
  )


def _compose_project() -> str:
  """
  Return compose project name from the environment.

  Returns:
    str: ``HPCPERFSTATS_COMPOSE_PROJECT`` or ``hpcperfstats``.

  Examples:
    >>> _compose_project()  # doctest: +SKIP
  """
  return os.environ.get("HPCPERFSTATS_COMPOSE_PROJECT", "hpcperfstats").strip()


def _compose_exec_web(
  repo_root: str,
  compose_project: str,
) -> subprocess.CompletedProcess[str]:
  """
  Run bootstrap Python on stdin inside the web container.

  Args:
    repo_root: Git checkout with ``docker-compose.yaml``.
    compose_project: Compose project name.

  Returns:
    subprocess.CompletedProcess[str]: Bootstrap exec result.

  Examples:
    >>> _compose_exec_web("/tmp", "hpcperfstats")  # doctest: +SKIP
  """
  if _soak_in_web_container():
    return _run_web_helper_script(repo_root, "pgo_soak_web_bootstrap.py")
  with open(BOOTSTRAP_SCRIPT, encoding="utf-8") as bootstrap_file:
    bootstrap_src = bootstrap_file.read()
  cmd = [
    "podman-compose",
    "--project-name",
    compose_project,
    "exec",
    "-T",
    "web",
    "python3",
    "-",
  ]
  return subprocess.run(
    cmd,
    cwd=repo_root,
    input=bootstrap_src,
    capture_output=True,
    text=True,
    check=False,
  )


def bootstrap_soak_site(
  repo_root: str | None = None,
  compose_project: str | None = None,
  *,
  compose_exec_fn: Any = None,
) -> dict[str, str]:
  """
  Resolve server name, API key, and base URL via podman-compose exec web.

  Args:
    repo_root: Git checkout containing docker-compose.yaml.
    compose_project: Compose project name (HPCPERFSTATS_COMPOSE_PROJECT).
    compose_exec_fn: Injectable exec for tests.

  Returns:
    dict: server, scheme, host_name_ext, raw_api_key, base_url.

  Raises:
    RuntimeError: When bootstrap fails.

  Examples:
    >>> bootstrap_soak_site(
    ...   compose_exec_fn=lambda *a, **k: None
    ... )  # doctest: +SKIP
  """
  root = repo_root or REPO_ROOT
  project = compose_project or _compose_project()
  exec_fn = compose_exec_fn or _compose_exec_web
  proc = exec_fn(root, project)
  if proc.returncode != 0:
    raise RuntimeError(
      "bootstrap exec web failed (exit {}): {}".format(
        proc.returncode,
        (proc.stderr or proc.stdout or "").strip(),
      ),
    )
  line = ""
  for raw_line in (proc.stdout or "").splitlines():
    raw_line = raw_line.strip()
    if raw_line.startswith("{"):
      line = raw_line
      break
  if not line:
    raise RuntimeError("bootstrap exec web produced no JSON line")
  data = json.loads(line)
  server_token = (data.get("server") or "").split(",")[0].strip()
  if server_token and "://" not in server_token:
    data["host_header"] = server_token
  else:
    data["host_header"] = urllib.parse.urlparse(server_token).hostname or ""
  data["base_url"] = _derive_base_url(data, compose_project)
  return data


def _derive_base_url(data: dict[str, str], compose_project: str) -> str:
  """
  Build Playwright/API base URL from bootstrap JSON and compose project.

  Args:
    data: Bootstrap payload including ``host_header``.
    compose_project: Compose project name.

  Returns:
    str: Absolute site base URL.

  Examples:
    >>> _derive_base_url(
    ...   {"host_header": "x"}, "hpcperfstats-dev"
    ... )  # doctest: +SKIP
  """
  override = os.environ.get("HPC_PGO_SOAK_BASE_URL", "").strip().rstrip("/")
  if override:
    return override
  scheme = (data.get("scheme") or "https").strip()
  https_port = os.environ.get("HPCPERFSTATS_HTTPS_PORT", "").strip()

  host_header = (data.get("host_header") or "").strip()
  if not https_port:
    https_port = (
      "8443"
      if compose_project in ("hpcperfstats-dev", "hpcperfstats-test")
      else "443"
    )

  # Playwright TLS needs SNI matching the cert (INI server), resolved to localhost via chromium MAP rule.
  if (
    compose_project in ("hpcperfstats-dev", "hpcperfstats-test") and host_header
  ):
    if https_port in ("443", ""):
      return f"https://{host_header}"
    return f"https://{host_header}:{https_port}"

  if not https_port:
    https_port = "443"

  server = (data.get("server") or "").split(",")[0].strip()
  if "://" in server:
    return server.rstrip("/")
  host = server or "127.0.0.1"
  if https_port in ("443", "") and scheme == "https":
    return f"{scheme}://{host}"
  if https_port in ("80", "") and scheme == "http":
    return f"{scheme}://{host}"
  return f"{scheme}://{host}:{https_port}"


class _LocalhostRedirectHandler(urllib.request.HTTPRedirectHandler):
  """Keep redirects on 127.0.0.1 when proxy returns https://INI-server/..."""

  def redirect_request(
    self,
    req: urllib.request.Request,
    fp: Any,
    code: int,
    msg: str,
    headers: Any,
    newurl: str,
  ) -> urllib.request.Request | None:
    """
    Rewrite external redirect targets back to the localhost proxy port.

    Args:
      req: Original request.
      fp: Response body stream.
      code: HTTP status code.
      msg: Status message.
      headers: Response headers.
      newurl: Redirect target URL.

    Returns:
      urllib.request.Request | None: Follow-up request or None.

    Examples:
      >>> _LocalhostRedirectHandler().redirect_request  # doctest: +SKIP
    """
    orig = urllib.parse.urlparse(req.full_url)
    newp = urllib.parse.urlparse(newurl)
    if orig.hostname in ("127.0.0.1", "localhost") and newp.hostname not in (
      "127.0.0.1",
      "localhost",
      None,
    ):
      newurl = urllib.parse.urlunparse(
        (
          orig.scheme,
          orig.netloc,
          newp.path,
          newp.params,
          newp.query,
          newp.fragment,
        ),
      )
    return urllib.request.HTTPRedirectHandler.redirect_request(
      self,
      req,
      fp,
      code,
      msg,
      headers,
      newurl,
    )


def _urlopen_request(req: urllib.request.Request, timeout: float) -> Any:
  """
  Open an HTTP(S) request with localhost-safe redirect handling.

  Args:
    req: Prepared request.
    timeout: Socket timeout seconds.

  Returns:
    Any: Open HTTP response object.

  Examples:
    >>> _urlopen_request  # doctest: +SKIP
  """
  handlers: list[Any] = [_LocalhostRedirectHandler()]
  if req.full_url.startswith("https://"):
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    handlers.insert(0, urllib.request.HTTPSHandler(context=ctx))
  opener = urllib.request.build_opener(*handlers)
  return opener.open(req, timeout=timeout)


def _api_get_json(
  base_url: str,
  raw_key: str,
  path: str,
  query: dict[str, str] | None = None,
  host_header: str = "",
) -> dict[str, Any]:
  """
  GET JSON from the site API using X-API-Key authentication.

  Args:
    base_url: Site root URL.
    raw_key: Raw API key value.
    path: API path beginning with ``/``.
    query: Optional query parameters.
    host_header: Optional ``Host`` header for proxy routing.

  Returns:
    dict[str, Any]: Parsed JSON object.

  Examples:
    >>> _api_get_json("https://x", "k", "/api/session/")  # doctest: +SKIP
  """
  url = base_url.rstrip("/") + path
  if query:
    url += "?" + urllib.parse.urlencode(query)
  headers = {
    "Accept": "application/json",
    "X-API-Key": raw_key,
  }
  if host_header:
    headers["Host"] = host_header
  req = urllib.request.Request(
    url,
    headers=headers,
    method="GET",
  )
  with _urlopen_request(req, timeout=120) as resp:
    body = resp.read().decode("utf-8")
  return json.loads(body)


def _discover_job_ids_via_exec(
  repo_root: str,
  compose_project: str,
  raw_api_key: str,
  *,
  list_days: int = 30,
  allow_metrics_only: bool = False,
) -> list[str]:
  """
  Discover job ids by running ``pgo_soak_discover_jobs.py`` inside web.

  Args:
    repo_root: Git checkout path.
    compose_project: Compose project name.
    raw_api_key: API key for authenticated list API.
    list_days: Job list time window.
    allow_metrics_only: Include performance rank 1 when true.

  Returns:
    list[str]: Job ids.

  Raises:
    RuntimeError: When exec fails or JSON is missing.

  Examples:
    >>> _discover_job_ids_via_exec("/r", "p", "k")  # doctest: +SKIP
  """
  extra_env = {
    "HPC_PGO_SOAK_RAW_API_KEY": raw_api_key,
    "HPC_PGO_SOAK_JOB_LIST_DAYS": str(list_days),
    "HPC_PGO_SOAK_ALLOW_METRICS_ONLY": "1" if allow_metrics_only else "0",
  }
  if _soak_in_web_container():
    proc = _run_web_helper_script(
      repo_root,
      "pgo_soak_discover_jobs.py",
      extra_env=extra_env,
    )
  else:
    with open(DISCOVER_SCRIPT, encoding="utf-8") as discover_file:
      src = discover_file.read()
    cmd = [
      "podman-compose",
      "--project-name",
      compose_project,
      "exec",
      "-T",
      "-e",
      f"HPC_PGO_SOAK_RAW_API_KEY={raw_api_key}",
      "-e",
      f"HPC_PGO_SOAK_JOB_LIST_DAYS={list_days}",
      "-e",
      "HPC_PGO_SOAK_ALLOW_METRICS_ONLY={}".format(
        "1" if allow_metrics_only else "0",
      ),
      "web",
      "python3",
      "-",
    ]
    proc = subprocess.run(
      cmd,
      cwd=repo_root,
      input=src,
      capture_output=True,
      text=True,
      check=False,
    )
  if proc.returncode != 0:
    raise RuntimeError(
      "discover exec web failed (exit {}): {}".format(
        proc.returncode,
        (proc.stderr or proc.stdout or "").strip(),
      ),
    )
  for raw_line in (proc.stdout or "").splitlines():
    raw_line = raw_line.strip()
    if raw_line.startswith("{"):
      payload = json.loads(raw_line)
      return [str(j) for j in payload.get("jids") or []]
  raise RuntimeError("discover exec web produced no JSON")


def discover_job_ids(
  base_url: str,
  raw_api_key: str,
  *,
  list_days: int = 30,
  allow_metrics_only: bool = False,
  host_header: str = "",
  api_get_fn: Any = None,
  repo_root: str | None = None,
  compose_project: str | None = None,
) -> list[str]:
  """
  Return job ids from GET /api/jobs/ filtered by performance_sort_rank.

  Args:
    base_url: Site root (proxy or web).
    raw_api_key: X-API-Key header value.
    list_days: end_time window lookback.
    allow_metrics_only: When true, also query rank 1 (metrics without plots).
    host_header: Optional HTTP Host header for proxy virtual hosts.
    api_get_fn: Injectable GET for tests.
    repo_root: When set with compose_project, discovery runs in web container.
    compose_project: Compose project for in-container discovery.

  Returns:
    list[str]: Unique jids, order preserved.

  Raises:
    RuntimeError: When API fails.

  Examples:
    >>> discover_job_ids(
    ...   "https://x", "k", api_get_fn=lambda *a, **k: {"job_list": []}
    ... )  # doctest: +SKIP
  """
  if api_get_fn is None and repo_root and compose_project:
    return _discover_job_ids_via_exec(
      repo_root,
      compose_project,
      raw_api_key,
      list_days=list_days,
      allow_metrics_only=allow_metrics_only,
    )

  getter = api_get_fn or _api_get_json
  now = datetime.now(UTC)
  gte = (now - timedelta(days=list_days)).isoformat()
  lte = (now + timedelta(hours=1)).isoformat()
  ranks = ["0"]
  if allow_metrics_only:
    ranks.append("1")
  seen: set[str] = set()
  jids: list[str] = []
  for rank in ranks:
    payload = getter(
      base_url,
      raw_api_key,
      "/api/jobs/",
      {
        "performance_sort_rank": rank,
        "end_time__gte": gte,
        "end_time__lte": lte,
      },
      host_header,
    )
    for row in payload.get("job_list") or []:
      jid = row.get("jid")
      if not jid or jid in seen:
        continue
      seen.add(jid)
      jids.append(str(jid))
  return jids


def _wait_plot_response(
  request_ctx: Any,
  url: str,
  timeout_s: float = 30.0,
) -> Any:
  """
  Poll a plot API URL until it leaves HTTP 202 loading state.

  Args:
    request_ctx: Playwright API request context.
    url: Plot API URL.
    timeout_s: Maximum wait seconds.

  Returns:
    Any: Final HTTP response object.

  Examples:
    >>> _wait_plot_response  # doctest: +SKIP
  """
  deadline = time.monotonic() + timeout_s
  response = request_ctx.get(url)
  while response.status == 202 and time.monotonic() < deadline:
    time.sleep(0.25)
    response = request_ctx.get(url)
  return response


def _ignore_https_browser_context(browser: Any, **kwargs: Any) -> Any:
  """
  Create a browser context that accepts the test proxy TLS certificate.

  Args:
    browser: Playwright browser handle.
    **kwargs: Forwarded to ``new_context``.

  Returns:
    Any: Browser context.

  Examples:
    >>> _ignore_https_browser_context  # doctest: +SKIP
  """
  return browser.new_context(ignore_https_errors=True, **kwargs)


def _ignore_https_api_context(playwright: Any, **kwargs: Any) -> Any:
  """
  Create an API request context that accepts the test proxy TLS certificate.

  Args:
    playwright: Playwright root object.
    **kwargs: Forwarded to ``request.new_context``.

  Returns:
    Any: API request context.

  Examples:
    >>> _ignore_https_api_context  # doctest: +SKIP
  """
  return playwright.request.new_context(ignore_https_errors=True, **kwargs)


def run_soak_loop(
  base_url: str,
  raw_api_key: str,
  jids: list[str],
  duration_s: int,
  *,
  host_header: str = "",
  dry_run: bool = False,
) -> None:
  """
  Drive SPA + API traffic until duration_s elapses.

  Args:
    base_url: Site root for Playwright navigation.
    raw_api_key: API key header value.
    jids: Job ids to rotate through.
    duration_s: Total soak wall time.
    host_header: Optional Host header and chromium MAP target.
    dry_run: Print plan only when true.

  Returns:
    None

  Raises:
    RuntimeError: When Playwright is not installed.

  Examples:
    >>> run_soak_loop("https://x", "k", ["1"], 1, dry_run=True)
  """
  if dry_run:
    print(
      "[dry-run] would soak {}s base_url={} jids={}".format(
        duration_s,
        base_url,
        ",".join(jids[:5]),
      ),
    )
    return
  if sync_playwright is None:
    raise RuntimeError("playwright is not installed in this Python environment")
  deadline = time.monotonic() + duration_s
  plot_kinds = ("summary_plot", "roofline", "gpu_roofline")
  resolver_args: list[str] = []
  parsed_base = urllib.parse.urlparse(base_url)
  internal_proxy = (parsed_base.hostname or "").strip() == "proxy"
  if (
    host_header
    and not _soak_in_web_container()
    and not internal_proxy
    and "127.0.0.1" not in base_url
    and "localhost" not in base_url
  ):
    resolver_args = [
      f"--host-resolver-rules=MAP {host_header} 127.0.0.1",
    ]
  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(args=resolver_args)
    extra_headers = {"X-API-Key": raw_api_key}
    parsed_base = urllib.parse.urlparse(base_url)
    if (
      host_header
      and (parsed_base.hostname or "").lower() != host_header.lower()
    ):
      extra_headers["Host"] = host_header
    context = _ignore_https_browser_context(
      browser, extra_http_headers=extra_headers
    )
    page = context.new_page()
    api = _ignore_https_api_context(
      playwright,
      base_url=base_url,
      extra_http_headers=extra_headers,
    )
    api.get("/api/session/")
    idx = 0
    while time.monotonic() < deadline:
      jid = jids[idx % len(jids)]
      idx += 1
      page.goto(
        "{}/machine/jobs/".format(base_url.rstrip("/")),
        wait_until="domcontentloaded",
      )
      api.get("/api/jobs/histograms/?group=metric&metric=runtime")
      page.goto(
        "{}/machine/job/{}".format(
          base_url.rstrip("/"), urllib.parse.quote(jid)
        ),
        wait_until="domcontentloaded",
      )
      for plot_kind in plot_kinds:
        _wait_plot_response(
          api,
          f"/api/jobs/{urllib.parse.quote(jid)}/plots/?plot={urllib.parse.quote(plot_kind)}",
        )
      time.sleep(1.0)


def _print_discovery(
  site: dict[str, str],
  jids: list[str],
) -> None:
  """
  Log discovery summary lines for operators and E2E log grep.

  Args:
    site: Bootstrap payload.
    jids: Discovered job ids.

  Returns:
    None

  Examples:
    >>> _print_discovery({"server": "s", "base_url": "https://x"}, ["j1"])
  """
  print("server={}".format(site.get("server", "")))
  print("base_url={}".format(site.get("base_url", "")))
  print(f"rank0_count={len(jids)}")
  if jids:
    sample = jids[:10]
    print("rank0_jids_sample={}".format(",".join(sample)))


def main(argv: list[str] | None = None) -> int:
  """
  CLI entry: bootstrap, discover rank-0 jobs, optional Playwright soak.

  Args:
    argv: Optional argument vector (defaults to ``sys.argv[1:]``).

  Returns:
    int: Process exit code (non-zero when discovery finds zero jobs).

  Examples:
    >>> main(["--dry-run", "--discovery-only"])  # doctest: +SKIP
  """
  parser = argparse.ArgumentParser(description="PGO live-soak web/API traffic")
  parser.add_argument(
    "--repo-root",
    default=REPO_ROOT,
    help="Checkout with docker-compose.yaml",
  )
  parser.add_argument(
    "--compose-project",
    default="",
    help="Override HPCPERFSTATS_COMPOSE_PROJECT",
  )
  parser.add_argument(
    "--discovery-only",
    action="store_true",
    help="Bootstrap + rank-0 discovery only; exit 0 when jids non-empty",
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print planned soak; skip Playwright",
  )
  parser.add_argument(
    "--job-ids",
    default="",
    help="Debug override: comma-separated jids (skips API discovery)",
  )
  parser.add_argument(
    "--duration",
    type=int,
    default=int(os.environ.get("HPC_PGO_SOAK_SECONDS", "900")),
    help="Soak duration seconds (default 900)",
  )
  parser.add_argument(
    "--list-days",
    type=int,
    default=int(os.environ.get("HPC_PGO_SOAK_JOB_LIST_DAYS", "30")),
    help="Job list end_time lookback days",
  )
  args = parser.parse_args(argv)
  project = (args.compose_project or _compose_project()).strip()
  allow_metrics = (
    os.environ.get("HPC_PGO_SOAK_ALLOW_METRICS_ONLY", "").strip() == "1"
  )

  if args.dry_run and args.discovery_only:
    print("[dry-run] bootstrap + discover rank-0 jobs")
    return 0

  site = bootstrap_soak_site(args.repo_root, project)
  raw_key = site["raw_api_key"]
  base_url = site["base_url"]
  host_header = site.get("host_header") or ""

  if args.job_ids.strip():
    jids = [part.strip() for part in args.job_ids.split(",") if part.strip()]
  else:
    try:
      jids = discover_job_ids(
        base_url,
        raw_key,
        list_days=args.list_days,
        allow_metrics_only=allow_metrics,
        host_header=host_header,
        repo_root=args.repo_root,
        compose_project=project,
      )
    except (
      urllib.error.URLError,
      urllib.error.HTTPError,
      json.JSONDecodeError,
    ) as exc:
      sys.stderr.write(f"discover_job_ids failed: {exc}\n")
      return 1

  _print_discovery(site, jids)
  if not jids:
    sys.stderr.write(
      "pgo_soak: zero rank-0 jobs in window — run update_metrics / wait for "
      "plot artifacts (or set HPC_PGO_SOAK_ALLOW_METRICS_ONLY=1)\n",
    )
    return 1

  if args.discovery_only:
    return 0

  try:
    run_soak_loop(
      base_url,
      raw_key,
      jids,
      args.duration,
      host_header=host_header,
      dry_run=args.dry_run,
    )
  except RuntimeError as exc:
    sys.stderr.write(f"{exc}\n")
    return 1
  print(
    f"pgo_soak: completed duration_s={args.duration} jids_exercised={len(jids)}"
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
