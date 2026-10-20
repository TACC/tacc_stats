"""Align jid_scoped_distinct_host_time_count with jid OR dev=j:<jid>."""

from django.db import migrations

CREATE_JID_DISTINCT = """
CREATE OR REPLACE FUNCTION jid_scoped_distinct_host_time_count(
  p_jid text,
  p_start timestamptz,
  p_end timestamptz
) RETURNS bigint
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(SUM(ph.cnt), 0)::bigint
  FROM (
    SELECT h.host, COUNT(DISTINCT h.time)::bigint AS cnt
    FROM host_data h
    WHERE (h.jid = p_jid OR h.dev = ('j:' || p_jid))
      AND h.time >= p_start
      AND h.time <= p_end
    GROUP BY h.host
  ) ph;
$$;
"""

# Restore jid-only body from 0034 (forward fixes shared-node drift).
REVERT_JID_DISTINCT = """
CREATE OR REPLACE FUNCTION jid_scoped_distinct_host_time_count(
  p_jid text,
  p_start timestamptz,
  p_end timestamptz
) RETURNS bigint
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(SUM(ph.cnt), 0)::bigint
  FROM (
    SELECT h.host, COUNT(DISTINCT h.time)::bigint AS cnt
    FROM host_data h
    WHERE h.jid = p_jid
      AND h.time >= p_start
      AND h.time <= p_end
    GROUP BY h.host
  ) ph;
$$;
"""


class Migration(migrations.Migration):

  dependencies = [
    ("machine", "0036_job_affinity"),
  ]

  operations = [
    migrations.RunSQL(CREATE_JID_DISTINCT, REVERT_JID_DISTINCT),
  ]
