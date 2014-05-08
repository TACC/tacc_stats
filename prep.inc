%define _bindir /opt/%{name}
%define crontab_file /etc/cron.d/%{name}
%define stats_dir /var/log/tacc_stats
%define archive_dir /scratch/projects/%{name}/archive
%setup -q