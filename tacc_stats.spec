Summary: TACC system statistics collector
Name: tacc_stats
Version: 1.0.0
Release: 0
Copyright: University of Texas at Austin
Vendor: TACC/Ranger
Group: System Environment/Base
Packager: TACC - jhammond@tacc.utexas.edu
Source: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
# define _topdir /export/home/build/rpms XXX XXX XXX XXX
%define crontab_file /etc/cron.d/%{name}
%define stats_dir /var/log/tacc_stats
%define archive_dir /tmp

%description
This package provides the tacc_stats command, along with a cron file
to trigger collection and archiving.

%prep
%setup -q

%build
make name=%{name} version=%{version} stats_dir=%{stats_dir}

%install
rm -rf %{buildroot}
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 6755 %{name} %{buildroot}/%{_bindir}/%{name}
install -m 0755 archive.sh %{buildroot}/%{_bindir}/%{name}_archive

%post
(
  archive_min=$(( ((RANDOM * 60) / 32768) %% 60 ))
  archive_hour=$(( (RANDOM %% 2) + 2 ))

  echo "55 11 * * * root %{_bindir}/%{name} rotate"
  echo "*/10 * * * * root %{_bindir}/%{name} collect"
  echo "${archive_min} ${archive_hour} * * * root %{_bindir}/%{name}_archive %{stats_dir} %{archive_dir}"
) > %{crontab_file}

/sbin/service crond restart || :

%preun
if [ $1 == 0 ]; then
  rm %{crontab_file} || :
fi

%clean
rm -rf %{buildroot}

%files
%attr(6755,root,root) %{_bindir}/%{name}
%attr(0755,root,root) %{_bindir}/%{name}_archive
