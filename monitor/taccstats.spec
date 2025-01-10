Summary: Job-level Monitoring Client
Name: hpcperfstats
Version: 2.3.5
Release: 1%{?dist}
License: GPL
Vendor: Texas Advanced Computing Center
Group: System Environment/Base
Packager: TACC - sharrell@tacc.utexas.edu
Source: hpcperfstats-%{version}.tar.gz
BuildRequires: systemd libev

%{?systemd_requires}

%description
This package provides the hpcperfstatsd daemon, \
along with a systemd script to provide control.

%prep
%setup

%build
./configure
make
sed -i 's/CONFIGFILE/\%{_sysconfdir}\/taccstats\/taccstats.conf/' src/taccstats.service
sed -i 's/localhost/stats.frontera.tacc.utexas.edu/' src/taccstats.conf
sed -i 's/default/frontera/' src/taccstats.conf

%install
mkdir -p  %{buildroot}/%{_sbindir}/
mkdir -p  %{buildroot}/%{_sysconfdir}/taccstats/
mkdir -p  %{buildroot}/%{_unitdir}/
install -m 744 src/hpcperfstatsd %{buildroot}/%{_sbindir}/hpcperfstatsd
install -m 644 src/taccstats.conf %{buildroot}/%{_sysconfdir}/taccstats/taccstats.conf
install -m 644 src/taccstats.service %{buildroot}/%{_unitdir}/taccstats.service

%files
%{_sbindir}/hpcperfstatsd
%{_sysconfdir}/taccstats/taccstats.conf
%{_unitdir}/taccstats.service
%dir %{_sysconfdir}/taccstats

%post
%systemd_post taccstats.service

%preun
%systemd_preun taccstats.service

%postun
%systemd_postun_with_restart taccstats.service
