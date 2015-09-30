def get_host_list_dir(machine):
	return "/hpc/tacc_stats_site/%s/hostfile_logs" % machine

def get_host_name_ext(machine):
	return "%s.tacc.utexas.edu" % machine

batch_system = "SLURM"

def get_tacc_stats_home(machine):
	return "/hpc/tacc_stats_site/%s" % machine

def get_pickles_dir(machine):
	return "/hpc/tacc_stats_site/%s/pickles" % machine

server = "tacc-stats.tacc.utexas.edu"

def get_acct_path(machine):
	return "/hpc/tacc_stats_site/%s/accounting/tacc_jobs_completed" % machine

def get_base_dir(machine):
	return "/hpc/tacc_stats_site/%s" % machine

seek = 0