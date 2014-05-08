if [ $1 == 0 ]; then
  rm %{crontab_file} || :
fi