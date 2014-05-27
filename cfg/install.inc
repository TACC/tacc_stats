rm -rf %{buildroot}

python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

install -m 0755 -d %{buildroot}/%{_bindir}
install -m 6755 build/bin/monitor %{buildroot}/%{_bindir}/%{name}
install -m 0755 tacc_stats/archive.sh %{buildroot}/%{_bindir}/%{name}_archive

echo %{_bindir}/%{name} >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
echo %{_bindir}/%{name}_archive >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES