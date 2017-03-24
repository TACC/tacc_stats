Summary: TACC system statistics collector
Name: tacc_stats
Version: 2.3.0
Release: 1
License: GPL
Vendor: Texas Advanced Computing Center
Group: System Environment/Base
Packager: TACC - rtevans@tacc.utexas.edu
Source: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

#%include rpm-dir.inc
%define debug_package %{nil}
%{!?archivedir: %{error: define archivedir!} exit 1 }

%define _bindir /opt/%{name}
%define _sysconfdir /etc
%define crontab_file %{_sysconfdir}/cron.d/%{name}

%description
This package provides the tacc_stats command, along with a cron file
to trigger collection and archiving.

%prep
%setup -q

%build
./configure --bindir=%{_bindir} --sysconfdir=%{_sysconfdir} CPPFLAGS=-I/opt/ofed/include LDFLAGS=-L/opt/ofed/lib64
make

%install
rm -rf %{buildroot}
cd src
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 6755 %{name} %{buildroot}/%{_bindir}/%{name}
install -m 0755 archive %{buildroot}/%{_bindir}/archive

%post
(
  archive_min=$(( ((RANDOM * 60) / 32768) %% 60 ))
  archive_hour=$(( (RANDOM %% 2) + 2 ))

  echo "MAILTO=\"\""
  echo "*/10 * * * * root %{_bindir}/%{name} collect"
  echo "55 23 * * * root %{_bindir}/%{name} rotate"
  echo "${archive_min} ${archive_hour} * * * root %{_bindir}/archive %{archivedir}"
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
%attr(0755,root,root) %{_bindir}/archive
