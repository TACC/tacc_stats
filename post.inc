(
  archive_min=$(( ((RANDOM * 60) / 32768) %% 60 ))
  archive_hour=$(( (RANDOM %% 2) + 2 ))

  echo "MAILTO=\"\""
  echo "*/10 * * * * root %{_bindir}/%{name} collect"
  echo "55 23 * * * root %{_bindir}/%{name} rotate"
  echo "${archive_min} ${archive_hour} * * * root %{_bindir}/%{name}_archive %{stats_dir} %{archive_dir}"
) > %{crontab_file}

/sbin/service crond restart || :

%{_bindir}/%{name} rotate

