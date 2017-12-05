Summary: Job-level Tracking and Analysis System
Name: tacc_statsd
Version: 2.3.3
Release: 2%{?dist}
License: GPL
Vendor: Texas Advanced Computing Center
Group: System Environment/Base
Packager: TACC - rtevans@tacc.utexas.edu
Source: tacc_stats-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

#%include rpm-dir.inc
%define debug_package %{nil}
%{!?rmqserver: %{error: define rmqserver!} exit 1 }
%{!?system:    %{error: define system name!} exit 1}

%define _bindir /opt/%{name}
%define _sysconfdir /etc/systemd/system

%description
This package provides the jtrase daemon, along with a systemv
unit file.

%prep
%setup -n tacc_stats-%{version}

%build
./configure --bindir=%{_bindir} --sysconfdir=%{_sysconfdir} --disable-infiniband --disable-opa CPPFLAGS=-I/admin/build/admin/rpms/stampede2/SOURCES/opa-ff/builtinclude.OPENIB_FF.release LDFLAGS=-L/admin/build/admin/rpms/stampede2/SOURCES/opa-ff/builtlibs.OPENIB_FF.release --enable-rabbitmq
make

%install
rm -rf %{buildroot}
cd src
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 0755 -d %{buildroot}/%{_sysconfdir}
install -m 6755 tacc_stats %{buildroot}/%{_bindir}/tacc_stats
install -m 0664 taccstats.service %{buildroot}/%{_sysconfdir}/taccstats.service

%post
systemctl enable taccstats
sed -i 's/localhost/%{rmqserver}/' %{_sysconfdir}/taccstats.service
sed -i 's/default/%{system}/' %{_sysconfdir}/taccstats.service
systemctl restart taccstats

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
%attr(0744,root,root) %{_sysconfdir}/taccstats.service


