Summary: TACC system statistics collector
Name: tacc_statsd
Version: 2.3.1
Release: 1%{?dist}
License: GPL
Vendor: Texas Advanced Computing Center
Group: System Environment/Base
Packager: TACC - rtevans@tacc.utexas.edu
Source: tacc_stats-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

#%include rpm-dir.inc

%{!?rmqserver: %{error: define rmqserver!} exit 1 }
%{!?system:    %{error: define system name!} exit 1}

%define _bindir /opt/%{name}
%define _sysconfdir /etc

%description
This package provides the tacc_stats daemon, along with an /etc/init.d
script to provide control.

%prep
%setup -n tacc_stats-%{version}

%build
./configure --bindir=%{_bindir} --sysconfdir=%{_sysconfdir} --enable-rabbitmq \
            CPPFLAGS=-I/opt/ofed/include LDFLAGS=-L/opt/ofed/lib64
make

%install
rm -rf %{buildroot}
cd src
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 0755 -d %{buildroot}/%{_sysconfdir}
install -m 0755 -d %{buildroot}/%{_sysconfdir}/init.d
install -m 6755 tacc_stats %{buildroot}/%{_bindir}/tacc_stats
install -m 0511 tacc_stats.conf %{buildroot}/%{_sysconfdir}/tacc_stats.conf
install -m 0755 taccstats %{buildroot}/%{_sysconfdir}/init.d/taccstats

%post
chkconfig --add taccstats
sed -i 's/localhost/%{rmqserver}/' %{_sysconfdir}/tacc_stats.conf
sed -i 's/default/%{system}/' %{_sysconfdir}/tacc_stats.conf
/sbin/service taccstats restart

%preun
if [ $1 == 0 ]; then
/sbin/service taccstats stop || :
chkconfig --del taccstats || :
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%dir %{_bindir}/
%attr(6755,root,root) %{_bindir}/tacc_stats
%attr(0744,root,root) %{_sysconfdir}/tacc_stats.conf
%attr(0744,root,root) %{_sysconfdir}/init.d/taccstats

