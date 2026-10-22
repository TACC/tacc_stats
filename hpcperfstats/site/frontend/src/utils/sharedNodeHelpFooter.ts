/**
 * Shared-node residual (host-wide) help footer copy and SPA gating.
 *
 * Mirrors ``SHARED_HOST_WIDE_HELP_FOOTER`` /
 * ``is_job_scoped_host_data_type`` in
 * ``hpcperfstats/analysis/metrics/lib/job_host_data_scope.py`` (same prose /
 * allowlist intent) per ``variable-metadata-cross-source-sync.mdc``.
 * Appended by ``VariableInfoLabel`` only when the job is shared **and** the
 * variable is not on the job-scoped allowlist.
 */

/** Job-scoped host_data.type names (mirror Python allowlist). */
const JOB_SCOPED_HOST_DATA_TYPES = new Set([
  "host_cpu",
  "cpu",
  "host_cpu_hw",
  "host_mem_job",
  "nvidia_gpu",
  "amd_gpu",
  "intel_gpu",
  "amd_x86_pmc",
  "intel_x86_pmc_gpr8",
  "intel_x86_pmc_gpr4",
  "intel_8pmc3",
  "intel_4pmc3",
]);

/**
 * Metric / variable names that are job-scoped on shared nodes (CPU/GPU/mem).
 * Residual fabric/FS/NUMA names stay off this list so the red footer shows.
 */
const JOB_SCOPED_VARIABLE_NAMES = new Set([
  "cpu",
  "mem",
  "avg_cpuusage",
  "mem_hwm",
  "avg_gpuutil",
  "avg_tensor_active",
  "avg_fp16_active",
  "avg_fp32_active",
  "avg_fp64_active",
  "max_gpu_power",
  "max_gpu_link_gbps",
  "gpu_count",
  "nv_gpu_util",
  "nv_mem_used_mb",
  "amd_flops",
  "amd_instr",
]);

export const SHARED_HOST_WIDE_HELP_FOOTER: string =
  "This counter is node-wide (host-level) on a shared node — it is not " +
  "disambiguated to this job. Job-scoped CPU, GPU, and cgroup memory use " +
  "separate surfaces without this disclaimer.";

/** True when the SPA variable maps to a job-scoped host_data surface. */
export function isJobScopedVariable(variableName: string): boolean {
  const name = String(variableName || "").trim();
  if (!name) return false;
  if (JOB_SCOPED_VARIABLE_NAMES.has(name)) return true;
  if (JOB_SCOPED_HOST_DATA_TYPES.has(name)) return true;
  if (
    name.startsWith("nv_") ||
    name.startsWith("amd_") ||
    name.startsWith("intel_") ||
    name.startsWith("gpu") ||
    name.startsWith("avg_fp") ||
    name.startsWith("avg_tensor")
  ) {
    return true;
  }
  return false;
}

/** Gate red shared-node footer: shared job and residual (non-job-scoped) variable. */
export function showSharedHostWideHelpFooter(
  isSharedNode: boolean,
  variableName: string,
): boolean {
  return Boolean(isSharedNode) && !isJobScopedVariable(variableName);
}
