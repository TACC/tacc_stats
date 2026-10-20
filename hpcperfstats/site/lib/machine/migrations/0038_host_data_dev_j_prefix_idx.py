"""Partial index on shared-node ``dev=j:%`` and UNION rewrite of live-distinct.

Large hypertables: create the index with ``statement_timeout = 0`` (this
migration) via a one-shot ``migrate`` with ``web`` stopped when startup migrate
would exceed restart budgets (see ``startup-migration-bounded-work.mdc``).
"""

from django.db import migrations, models
from django.db.models import Q

CREATE_DEV_J_PREFIX_IDX = """
SET statement_timeout = 0;
CREATE INDEX IF NOT EXISTS host_data_dev_j_prefix_idx
ON host_data (dev)
WHERE dev LIKE 'j:%';
"""

DROP_DEV_J_PREFIX_IDX = """
SET statement_timeout = 0;
DROP INDEX IF EXISTS host_data_dev_j_prefix_idx;
"""

# UNION arms: jid-time index + partial dev=j: index (not OR BitmapOr).
CREATE_JID_DISTINCT_UNION = """
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

# Restore 0037 OR body on reverse.
REVERT_JID_DISTINCT_OR = """
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


class Migration(migrations.Migration):

  atomic = False

  dependencies = [
    ("machine", "0037_jid_scoped_distinct_or_dev"),
  ]

  operations = [
    migrations.SeparateDatabaseAndState(
      database_operations=[
        migrations.RunSQL(
          sql=CREATE_DEV_J_PREFIX_IDX,
          reverse_sql=DROP_DEV_J_PREFIX_IDX,
        ),
      ],
      state_operations=[
        migrations.AddIndex(
          model_name="host_data",
          index=models.Index(
            fields=["dev"],
            name="host_data_dev_j_prefix_idx",
            condition=Q(dev__startswith="j:"),
          ),
        ),
      ],
    ),
    migrations.RunSQL(CREATE_JID_DISTINCT_UNION, REVERT_JID_DISTINCT_OR),
  ]
