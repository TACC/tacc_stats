"""Optional host filter on jid_scoped_distinct_host_time_count (0038 UNION).

Bounded function replace only — no index DDL / decompress.
"""

from django.db import migrations

# Drop 3-arg overload so DEFAULT NULL 4-arg is the sole signature.
DROP_THREE_ARG = """
DROP FUNCTION IF EXISTS jid_scoped_distinct_host_time_count(
  text, timestamptz, timestamptz
);
"""

CREATE_JID_DISTINCT_HOSTS = """
CREATE OR REPLACE FUNCTION jid_scoped_distinct_host_time_count(
  p_jid text,
  p_start timestamptz,
  p_end timestamptz,
  p_hosts text[] DEFAULT NULL
) RETURNS bigint
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(SUM(ph.cnt), 0)::bigint
  FROM (
    SELECT u.host, COUNT(DISTINCT u.time)::bigint AS cnt
    FROM (
      SELECT h.host, h.time
      FROM host_data h
      WHERE h.jid = p_jid
        AND h.time >= p_start
        AND h.time <= p_end
        AND (p_hosts IS NULL OR h.host = ANY(p_hosts))
      UNION
      SELECT h.host, h.time
      FROM host_data h
      WHERE h.dev = ('j:' || p_jid)
        AND h.time >= p_start
        AND h.time <= p_end
        AND (p_hosts IS NULL OR h.host = ANY(p_hosts))
    ) u
    GROUP BY u.host
  ) ph;
$$;
"""

DROP_FOUR_ARG = """
DROP FUNCTION IF EXISTS jid_scoped_distinct_host_time_count(
  text, timestamptz, timestamptz, text[]
);
"""

# Restore 0038 three-arg UNION body on reverse.
REVERT_JID_DISTINCT_UNION = """
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
    SELECT u.host, COUNT(DISTINCT u.time)::bigint AS cnt
    FROM (
      SELECT h.host, h.time
      FROM host_data h
      WHERE h.jid = p_jid
        AND h.time >= p_start
        AND h.time <= p_end
      UNION
      SELECT h.host, h.time
      FROM host_data h
      WHERE h.dev = ('j:' || p_jid)
        AND h.time >= p_start
        AND h.time <= p_end
    ) u
    GROUP BY u.host
  ) ph;
$$;
"""

FORWARD = DROP_THREE_ARG + CREATE_JID_DISTINCT_HOSTS
REVERSE = DROP_FOUR_ARG + REVERT_JID_DISTINCT_UNION


class Migration(migrations.Migration):

  dependencies = [
    ("machine", "0038_host_data_dev_j_prefix_idx"),
  ]

  operations = [
    migrations.RunSQL(FORWARD, REVERSE),
  ]
