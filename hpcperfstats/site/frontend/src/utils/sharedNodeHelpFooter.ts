/**
 * Shared-node co-tenant help footer copy.
 *
 * Mirrors ``SHARED_HOST_WIDE_HELP_FOOTER`` in
 * ``hpcperfstats/analysis/metrics/lib/job_host_data_scope.py`` (same prose,
 * same keys) per ``variable-metadata-cross-source-sync.mdc`` pairing
 * discipline. Appended by ``VariableInfoLabel`` (and the matching Bokeh
 * ``?`` help marker server-side) only when the job ran on a shared node.
 */
export const SHARED_HOST_WIDE_HELP_FOOTER: string =
  "This job ran on a shared node. Values may include host-wide telemetry, " +
  "not only this job's share.";
