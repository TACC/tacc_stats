#!/usr/bin/env python3
"""Run inside the web container (stdin: podman-compose exec -T web python3 -).

Emit one JSON line: server, scheme, host_name_ext, raw_api_key for PGO soak.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
  """
  Emit JSON bootstrap payload on stdout for host-side soak driver.

  Returns:
    int: Zero on success.

  Examples:
    >>> main()  # doctest: +SKIP
  """
  os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "hpcperfstats.site.hpcperfstats_site.settings",
  )
  import django

  django.setup()
  from hpcperfstats.dbload.lib import conf_parser as cfg
  from hpcperfstats.site.lib.machine.models import ApiKey

  username = "__pgo_soak_automation__"
  raw = os.environ.get("HPC_PGO_SOAK_RAW_API_KEY", "").strip()
  ApiKey.objects.filter(username=username).update(is_active=False)
  if raw:
    key_hash = ApiKey.hash_raw_key(raw)
    ApiKey.objects.create(
      key=key_hash,
      key_prefix=raw[:12],
      username=username,
      is_staff=True,
      is_active=True,
    )
  else:
    _obj, raw = ApiKey.create_from_raw_key(username, is_staff=True)

  server = (cfg.get_server_name() or "").strip()
  scheme = (cfg.get_cors_origin_scheme() or "https").strip()
  host_ext = (cfg.get_host_name_ext() or "").strip()
  payload = {
    "server": server,
    "scheme": scheme,
    "host_name_ext": host_ext,
    "raw_api_key": raw,
  }
  sys.stdout.write(json.dumps(payload) + "\n")
  sys.stdout.flush()
  if not server:
    sys.stderr.write("pgo_soak_web_bootstrap: [DEFAULT] server is empty\n")
    return 1
  if not raw:
    sys.stderr.write("pgo_soak_web_bootstrap: no API key\n")
    return 1
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
