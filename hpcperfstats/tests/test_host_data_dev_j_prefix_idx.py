"""Meta + migration contracts for host_data_dev_j_prefix_idx."""

from django.db.models import Index, Q

from hpcperfstats.site.lib.machine.models import host_data


def test_host_data_meta_has_partial_dev_j_prefix_index():
  named = {idx.name: idx for idx in host_data._meta.indexes if idx.name}
  idx = named.get("host_data_dev_j_prefix_idx")
  assert isinstance(idx, Index)
  assert list(idx.fields) == ["dev"]
  assert idx.condition == Q(dev__startswith="j:")
