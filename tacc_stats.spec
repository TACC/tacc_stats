Summary: TACC system statistics collector
Name: tacc_stats
Version: 1.0.3
Release: 1
License: GPL
Vendor: TACC/Ranger
Group: System Environment/Base
Packager: CCR - charngda@buffalo.edu
Source: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
%define _bindir /opt/%{name}
%define crontab_file /etc/cron.d/%{name}
%define stats_dir /var/log/tacc_stats
%define archive_dir /scratch/projects/%{name}/archive

%description
This package provides the tacc_stats command, along with a cron file
to trigger collection and archiving.

%prep
%setup -q

%build
sh build_ib
echo The following must be built on a Myrinet node, e.g. f12n37
sh build_mx

%install
rm -rf %{buildroot}
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 6755 %{name} %{buildroot}/%{_bindir}/%{name}
install -m 0755 archive.sh %{buildroot}/%{_bindir}/%{name}_archive

%post
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

%preun
if [ $1 == 0 ]; then
  rm %{crontab_file} || :
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%dir %{_bindir}/
%attr(6755,root,root) %{_bindir}/%{name}
%attr(0755,root,root) %{_bindir}/%{name}_archive
