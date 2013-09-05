Summary: TACC system statistics collector
Name: tacc_stats
Version: 1.0.3
Release: 1
License: GPL
Vendor: TACC/Ranger
Group: System Environment/Base
Packager: CCR
Source: %{name}.tar.gz
#Source: %{name}-%{Version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
%define _bindir /opt/%{name}
%define crontab_file /etc/cron.d/%{name}
%define stats_dir /var/log/tacc_stats
%define archive_dir /scratch/projects/%{name}/archive
%define intel ib_intel
%define amd ib_amd

%description

This package provides the tacc_stats command, along with a cron file
to trigger collection and archiving.

%prep

%setup -q -n tacc_stats-master/monitor

%build

# Build both intel and amd, symlink to correct one in %post
make clean
cp -f config.%{intel} config
make config=config NCPUS=64 name=%{name} version=%{version} -j 4
mv -f %{name} %{name}.%{intel}
mv -f schema-%{version}-config schema-%{version}-config-%{intel}
make clean
cp -f config.%{amd} config
make config=config NCPUS=32 name=%{name} version=%{version} -j 4
mv -f %{name} %{name}.%{amd}
mv -f schema-%{version}-config schema-%{version}-config-%{amd}

%install

rm -rf %{buildroot}
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 6755 %{name}.%{intel} %{buildroot}/%{_bindir}/%{name}.%{intel}
install -m 6755 %{name}.%{amd} %{buildroot}/%{_bindir}/%{name}.%{amd}
install -m 0755 archive.sh %{buildroot}/%{_bindir}/%{name}_archive

%post

# Symlink to correct tacc_stats bin based on arch
cpuvendor=$(awk '/^vendor_id/{print $3; exit}' /proc/cpuinfo)
case ${cpuvendor} in
  "GenuineIntel")
    ln -sf %{_bindir}/%{name}.%{intel} %{_bindir}/%{name}
    ;;
  "AuthenticAMD")
    ln -sf %{_bindir}/%{name}.%{amd} %{_bindir}/%{name}
    ;;
  *)
    # Unsupported CPU
    ;;
esac

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
  rm -f %{_bindir}/%{name}
  rm %{crontab_file} || :
fi

%clean

rm -rf %{buildroot}

%files

%defattr(-,root,root,-)
%dir %{_bindir}/
%attr(6755,root,root) %{_bindir}/%{name}.%{intel}
%attr(6755,root,root) %{_bindir}/%{name}.%{amd}
%attr(0755,root,root) %{_bindir}/%{name}_archive
