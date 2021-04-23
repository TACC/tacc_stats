Summary: Job-level Tracking and Analysis System
Name: tacc_statsd
Version: 2.3.4
Release: 5%{?dist}
License: GPL
Vendor: Texas Advanced Computing Center
Group: System Environment/Base
Packager: TACC - rtevans@tacc.utexas.edu
Source: tacc_stats-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

%include rpm-dir.inc
%define debug_package %{nil}
%{!?server: %{error: define server!} exit 1 }
%{!?queue:    %{error: define queue name!} exit 1}

%define _bindir /opt/%{name}
%define _sysconfdir /etc/systemd/system

%description
This package provides the tacc_statsd daemon, along with a systemv
unit file.

%prep
%setup -n tacc_stats-%{version}

%build
./configure --bindir=%{_bindir} --sysconfdir=%{_sysconfdir} --enable-rabbitmq
make clean
make

%install
rm -rf %{buildroot}
cd src
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 0755 -d %{buildroot}/%{_sysconfdir}
install -m 6755 tacc_stats %{buildroot}/%{_bindir}/tacc_stats
install -m 0664 taccstats.service %{buildroot}/%{_sysconfdir}/taccstats.service

%post
sed -i 's/localhost/%{server}/' %{_sysconfdir}/taccstats.service
sed -i 's/default/%{queue}/' %{_sysconfdir}/taccstats.service
sed -i 's/tacc_statsd/%{name}/' %{_sysconfdir}/taccstats.service

systemctl daemon-reload
systemctl enable taccstats
#systemctl restart taccstats

%preun
if [ $1 == 0 ]; then
systemctl stop taccstats
systemctl disable taccstats
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%dir %{_bindir}/
%attr(6755,root,root) %{_bindir}/tacc_stats
%attr(0644,root,root) %{_sysconfdir}/taccstats.service
