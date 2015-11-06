#!/usr/bin/env python

"""
Parts of this file were taken from the pyzmq project
(https://github.com/zeromq/pyzmq) which have been permitted for use under the
BSD license. Parts are from lxml (https://github.com/lxml/lxml)
"""

import os
import sys
import shutil
import warnings
import re
import ConfigParser
import multiprocessing

from setuptools import setup, Command, find_packages
from setuptools.command.build_ext import build_ext

setuptools_kwargs = {}

from distutils.extension import Extension
from distutils.command.build import build
from distutils.command.bdist_rpm import bdist_rpm
from distutils.command.sdist import sdist

from os.path import join as pjoin

DESCRIPTION = ("A job-level performance monitoring and analysis package for \
High Performance Computing Platforms")
LONG_DESCRIPTION = """
TACC Stats unifies and extends the measurements taken by Linux monitoring utilities such as systat/SAR, iostat, etc.~and resolves measurements by job and hardware device so that individual job/applications can be analyzed separately.  It also provides a set of analysis and reporting tools which analyze TACC Stats resource use data and report jobs/applications with low resource use efficiency. TACC Stats initializes at the beginning of a job and collects data at specified intervals during job execution and at the end of a job. When executed at the default interval (every 10 minutes), the overhead is less than 0.1\%. This low overhead enables TACC Stats to be active on all nodes at all times. This data can then be used to generate analyses and reports such as average cycles per instruction (CPI), average and peak memory use, average and peak memory bandwidth use, and more on each job and over arbitrary sets of jobs.   These reports enable systematic identification of jobs or application codes which could benefit from architectural adaptation and performance tuning or catch user mistakes such as allocating multiple nodes to a single-node shared-memory parallelized application.
"""

DISTNAME = 'tacc_stats'
LICENSE = 'LGPL'
AUTHOR = "Texas Advanced Computing Center"
EMAIL = "rtevans@tacc.utexas.edu"
URL = "http://www.tacc.utexas.edu"
DOWNLOAD_URL = 'https://github.com/TACC/tacc_stats'
CLASSIFIERS = [
    'Development Status :: 1 - Beta',
    'Environment :: Console',
    'Operating System :: Linux',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Topic :: Scientific/Engineering',
]

MAJOR = 2
MINOR = 2
MICRO = 1
ISRELEASED = True
VERSION = '%d.%d.%d' % (MAJOR, MINOR, MICRO)
QUALIFIER = ''
FULLVERSION = VERSION
write_version = True

if not ISRELEASED:
    import subprocess
    FULLVERSION += '.dev'

    pipe = None
    for cmd in ['git','git.cmd']:
        try:
            pipe = subprocess.Popen([cmd, "describe", "--always", "--match", "v[0-9]*"],
                                stdout=subprocess.PIPE)
            (so,serr) = pipe.communicate()
            if pipe.returncode == 0:
                break
        except:
            pass

    if pipe is None or pipe.returncode != 0:
        # no git, or not in git dir
        if os.path.exists('tacc_stats/version.py'):
            warnings.warn("WARNING: Couldn't get git revision, using existing tacc_stats/version.py")
            write_version = False
        else:
            warnings.warn("WARNING: Couldn't get git revision, using generic version string")
    else:
      # have git, in git dir, but may have used a shallow clone (travis does this)
      rev = so.strip()
      # makes distutils blow up on Python 2.7
      if sys.version_info[0] >= 3:
          rev = rev.decode('ascii')

      if not rev.startswith('v') and re.match("[a-zA-Z0-9]{7,9}",rev):
          rev ="v%s.dev-%s" % (VERSION, rev)
      FULLVERSION = rev.lstrip('v')
else:
    FULLVERSION += QUALIFIER



def write_version_py(filename=None):
    cnt = """\
version = '%s'
short_version = '%s'
"""
    filename = os.path.join(
        os.path.dirname(__file__), 'tacc_stats', 'version.py')

    with open(filename, 'w') as fd:
        fd.write(cnt % (FULLVERSION, VERSION))

if write_version:
    write_version_py()

def read_site_cfg():
    config = ConfigParser.ConfigParser()
    cfg_filename = os.path.abspath('setup.cfg')
    config.read(cfg_filename)
    return config

def write_stats_x(cfg_data):    
    chip_types = [
        'amd64_pmc', 'intel_nhm', 'intel_wtm',
        'intel_hsw', 'intel_hsw_cbo', 'intel_hsw_pcu', 'intel_hsw_imc', 'intel_hsw_qpi', 'intel_hsw_hau', 'intel_hsw_r2pci',
        'intel_ivb', 'intel_ivb_cbo', 'intel_ivb_pcu', 'intel_ivb_imc', 'intel_ivb_qpi', 'intel_ivb_hau', 'intel_ivb_r2pci',
        'intel_snb', 'intel_snb_cbo', 'intel_snb_pcu', 'intel_snb_imc', 'intel_snb_qpi', 'intel_snb_hau', 'intel_snb_r2pci'
        ]
    ib_types   = [
        'ib', 'ib_sw', 'ib_ext'
        ]
    lfs_types  = [
        'llite', 'lnet', 'mdc', 'osc'
        ]
    phi_types = [
        'mic'
        ]
    os_types  = [         
        'block', 'cpu', 'mem', 'net', 'nfs', 'numa', 'proc',
        'ps', 'sysv_shm', 'tmpfs', 'vfs', 'vm'
        ]

    types = chip_types + os_types
    if cfg_data.getboolean('OPTIONS', 'IB'):
        types += ib_types
    if cfg_data.getboolean('OPTIONS', 'LFS'):
        types += lfs_types
    if cfg_data.getboolean('OPTIONS', 'PHI'):
        types += phi_types

    filename = pjoin(
        os.path.dirname(__file__), 'tacc_stats','src','monitor', 'stats.x')
    with open(filename, 'w') as fd:        
        for val in sorted(types):            
            print 'Adding monitoring support for device type',val
            fd.write('X('+val+') ')
        fd.write('\n')

def write_cfg_file(cfg_data):
    paths = dict(cfg_data.items('PORTAL_OPTIONS'))

    filename = pjoin(
        os.path.dirname(__file__), 'tacc_stats', 'cfg.py')
    print '\n--- Configure Web Portal Module ---\n'
    with open(filename, 'w') as fd:
        for name,path in paths.iteritems():
            print name,'=', path
            fd.write(name + " = " + "\"" + path + "\"" + "\n")
        fd.write("seek = 0\n")        

def cfg_sh(filename_in,paths):
    f = open(filename_in, 'r').read()
    for name,path in paths.iteritems():
        f = f.replace(name,path)
    a = open(pjoin(os.path.dirname(__file__),'tacc_stats',
                   os.path.basename(filename_in.split('.in')[0])), 'w')
    a.write(f)
    a.close()


class CleanCommand(Command):
    """Custom distutils command to clean the .so and .pyc files."""

    user_options = [("all", "a", "")]
    def initialize_options(self):
        self.all = True
        self._clean_me = []
        self._clean_trees = []
        self._clean_exclude = []
        for root, dirs, files in os.walk('tacc_stats'):
            for f in files:
                if f in self._clean_exclude:
                    continue
                if os.path.splitext(f)[-1] in ('.pyc', '.so', '.o',
                                               '.pyo', '.x',
                                               '.pyd'):
                    self._clean_me.append(pjoin(root, f))
            for d in dirs:
                if d == '__pycache__':
                    self._clean_trees.append(pjoin(root, d))
        for d in os.listdir(os.getcwd()):
            if '.egg' in d:
                self._clean_trees.append(d)
        for d in ('build', 'dist'):
            if os.path.exists(d):
                self._clean_trees.append(d)
    def finalize_options(self):
        pass
    def run(self):
        for clean_me in self._clean_me:
            try:
                os.unlink(clean_me)
            except Exception:
                pass
        for clean_tree in self._clean_trees:
            try:
                shutil.rmtree(clean_tree)
            except Exception:
                pass

root = pjoin('tacc_stats', 'src', 'monitor')
cfg_data = read_site_cfg()
write_stats_x(cfg_data)
write_cfg_file(cfg_data)

### Determine source files to use
sources=[
    pjoin(root,'schema.c'), pjoin(root,'dict.c'),
    pjoin(root,'cpuid.c'), pjoin(root,'pci.c'),
    pjoin(root,'collect.c'),  pjoin(root,'stats.c')
    ]
with open(pjoin(root, 'stats.x'), 'r') as fd:
    for dev_type in fd.read().split():        
        sources += [pjoin(root, dev_type.lstrip('X(').rstrip(')') + '.c')]

FREQUENCY = cfg_data.get('OPTIONS', 'FREQUENCY')
include_dirs = []
library_dirs = []
libraries    = []

if cfg_data.getboolean('OPTIONS', 'IB'):
    ib_dir        = "/usr"
    include_dirs += [pjoin(ib_dir,'include')]
    include_dirs += ['/opt/ofed/include']
    library_dirs += [pjoin(ib_dir,'lib64')]

    ib_dir        = "/opt/ofed"
    include_dirs += [pjoin(ib_dir,'include')]
    library_dirs += [pjoin(ib_dir,'lib64')]

    libraries    += ['ibmad']

if cfg_data.getboolean('OPTIONS', 'PHI'):
    library_dirs += ['/usr/lib64']
    libraries    += ['scif', 'micmgmt']

if cfg_data.getboolean('OPTIONS', 'LFS'):
    sources += [pjoin(root,'lustre_obd_to_mnt.c')]

paths = dict(cfg_data.items('MONITOR_PATHS'))
define_macros=[('STATS_DIR_PATH','\"'+paths['stats_dir']+'\"'),
               ('STATS_VERSION','\"'+VERSION+'\"'),
               ('STATS_PROGRAM','\"tacc_stats\"'),
               ('STATS_LOCK_PATH','\"'+paths['stats_lock']+'\"'),
               ('JOBID_FILE_PATH','\"'+paths['jobid_file']+'\"'),
               ('FREQUENCY',FREQUENCY)]

MODE = cfg_data.get('OPTIONS', 'MODE') 
if MODE == 'DAEMON': 
    print "\n--- Building linux daemon for monitoring ---\n"
    sources   += [pjoin(root,'amqp_listen.c'), 
                  pjoin(root,'stats_buffer.c'), pjoin(root,'monitor.c')]
    libraries += ['rabbitmq']

    SERVER = cfg_data.get('RMQ_CFG', 'RMQ_SERVER')
    define_macros += [('HOST_NAME_QUEUE',
                       '\"'+cfg_data.get('RMQ_CFG', 'HOST_NAME_QUEUE')+'\"')]
elif MODE == "CRON": 
    print "Building executable for monitoring w/ cron"
    sources += [pjoin(root,'stats_file.c'), pjoin(root,'main.c')]
else:
    print "BUILD ERROR: Set mode to either DAEMON or CRON"
    sys.exit(1)
flags = ['-D_GNU_SOURCE', '-Wp,-U_FORTIFY_SOURCE',
         '-O3', '-Wall', '-g', '-UDEBUG']

ext_data=dict(
    sources            = sources,
    include_dirs       = [root] + include_dirs,
    library_dirs       = library_dirs,
    libraries          = libraries,
    extra_compile_args = flags,
    define_macros      = define_macros
    )

extensions = []
cmd = {}

class MyBDist_RPM(bdist_rpm):
    # Just a Python distutils bug fix.  
    # Very frustrating, rpms cannot build with extensions
    # without this hack.
    def run(self):        
        try:            
            from distutils.sysconfig import get_python_version
            import __builtin__
            __builtin__.get_python_version = get_python_version
        except:
            # Supposedly corrected in Python3 where __builtin__ -> builtin
            pass
        bdist_rpm.run(self)

    # Make the spec file my way!
    def initialize_options(self):
        bdist_rpm.initialize_options(self)
        try: os.stat('build')
        except: os.mkdir('build')
   
        ### Prep section
        self.prep_script = "build/bdist_rpm_prep"
        prep_cmds = """
%define _bindir /opt/%{name}
%setup -n %{name}-%{unmangled_version}
"""
        prep_cmds += "%define lockfile " + paths['stats_lock'] + "\n"
        if MODE == "CRON":
            prep_cmds += """
%define crontab_file /etc/cron.d/%{name}
%define stats_dir /var/log/%{name}
%define archive_dir """ + paths["archive_dir"]

        #if MODE == "DAEMON":
        #    prep_cmds += "%define server " + "-s "+SERVER
        open(self.prep_script,"w").write(prep_cmds)
        
        ### Build Section
        self.build_script = "build/bdist_rpm_build"        
        build_cmds = """
rm -rf %{buildroot}
python setup.py build_ext
"""
        open(self.build_script,"w").write(build_cmds)

        ### Install Section
        self.install_script = "build/bdist_rpm_install"
        install_cmds = """
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 6755 build/bin/monitor %{buildroot}/%{_bindir}/%{name}
echo %{_bindir}/%{name} >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
"""
        if MODE == "CRON":
            install_cmds += """
install -m 0755 tacc_stats/archive.sh %{buildroot}/%{_bindir}/archive
echo %{_bindir}/archive >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
"""
        if MODE == "DAEMON":
            install_cmds += """
install -m 0755 tacc_stats/taccstats %{buildroot}/%{_bindir}/taccstats
echo %{_bindir}/taccstats >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
"""
        open(self.install_script,"w").write(install_cmds)


        ### Post Install Section
        self.post_install = "build/bdist_rpm_postinstall"

        if MODE == "CRON":
            post_install_cmds = """
(
 archive_min=$(( ((RANDOM * 60) / 32768) %% 60 ))
 archive_hour=$(( (RANDOM %% 2) + 2 ))
 echo \"MAILTO=\\"\\"\"
 echo \"*/10 * * * * root %{_bindir}/%{name} collect\"
 echo \"55 23 * * * root %{_bindir}/%{name} rotate\"
 echo \"${archive_min} ${archive_hour} * * * root %{_bindir}/archive %{stats_dir} %{archive_dir}\"
) > %{crontab_file}
/sbin/service crond restart || :
%{_bindir}/%{name} rotate
"""
        if MODE == "DAEMON":
            post_install_cmds = """
cp %{_bindir}/taccstats /etc/init.d/
chkconfig --add taccstats
/sbin/service taccstats restart
"""
        open(self.post_install,"w").write(post_install_cmds)

        ### Pre Uninstall
        self.pre_uninstall = "build/bdist_rpm_preuninstall"
        if MODE == "CRON":
            pre_uninstall_cmds = """
if [ $1 == 0 ]; then
rm %{crontab_file} || :
fi
"""        
        if MODE == "DAEMON":
            pre_uninstall_cmds = """
if [ $1 == 0 ]; then
/sbin/service taccstats stop || :
chkconfig --del taccstats || :
rm /etc/init.d/taccstats || :
fi
"""
        open(self.pre_uninstall,"w").write(pre_uninstall_cmds)

# Make executable
# C extensions
class MyBuildExt(build_ext):
    def build_extension(self,ext):
        
        sources = list(ext.sources)
        ext_path = self.get_ext_fullpath(ext.name)
        extra_args = ext.extra_compile_args or []
        macros = ext.define_macros[:]
        for undef in ext.undef_macros:
            macros.append((undef,))
        
        objects = self.compiler.compile(sources,
                                        output_dir=self.build_temp,
                                        macros=macros,
                                        include_dirs=ext.include_dirs,
                                        extra_preargs=extra_args,
                                        depends=ext.depends)
        self._built_objects = objects[:]

        language = ext.language or self.compiler.detect_language(sources)

        if MODE == "DAEMON":
            self.compiler.link_executable([pjoin(self.build_temp,
                                                 root,
                                                 'amqp_listen.o')],
                                          'build/bin/listend',
                                          libraries=ext.libraries,
                                          library_dirs=ext.library_dirs,
                                          extra_postargs=extra_args,
                                          target_lang=language)
            objects.remove(pjoin(self.build_temp, root, 'amqp_listen.o'))

        self.compiler.link_executable(objects, 
                                      'build/bin/monitor',
                                      libraries=ext.libraries,
                                      library_dirs=ext.library_dirs,
                                      extra_preargs=extra_args,
                                      target_lang=language)

        self.compiler.link_shared_object(objects, 
                                         ext_path,
                                         libraries=ext.libraries,
                                         library_dirs=ext.library_dirs,
                                         extra_preargs=extra_args,
                                         debug=self.debug,
                                         build_temp=self.build_temp,
                                         target_lang=language)

extensions.append(Extension('monitor', **ext_data))

scripts=[
    'build/bin/monitor',             
    'tacc_stats/analysis/job_sweeper.py',
    'tacc_stats/analysis/job_plotter.py',
    'tacc_stats/analysis/job_printer.py',
    'tacc_stats/site/manage.py',
    'tacc_stats/site/machine/update_db.py',
    'tacc_stats/site/machine/update_thresholds.py',
    'tacc_stats/site/machine/thresholds.cfg',
    'tacc_stats/pickler/job_pickles.py'
    ]

if MODE == "DAEMON": 
    print 'data will go to',SERVER
    cfg_sh(pjoin(root, 'taccstats.in'), 
           dict(paths.items() + cfg_data.items('RMQ_CFG')))

    scripts  += ['build/bin/listend', 
                 'tacc_stats/taccstats']
    DISTNAME += "d"

if MODE == "CRON":
    cfg_sh(pjoin(root, 'archive.sh.in'), paths)
    scripts += ['tacc_stats/archive.sh']
    package_data = {'' : ['*.sh.in'] },

setup(
    name = DISTNAME,
    version = FULLVERSION,
    maintainer = AUTHOR,
    package_dir = {'':'.'},
    packages = find_packages(),
    package_data = {'' : ['*.in','*.cfg','*.html','*.png','*.jpg','*.h'] },
    scripts = scripts,
    ext_modules = extensions,
    setup_requires = ['nose'],
    install_requires = ['argparse','numpy','matplotlib','scipy'],
    test_suite = 'nose.collector',
    maintainer_email = EMAIL,
    description = DESCRIPTION,
    zip_safe = False,
    license = LICENSE,
    cmdclass = {'build_ext' : MyBuildExt, 
                'clean' : CleanCommand,
                'bdist_rpm' : MyBDist_RPM},
    url = URL,
    download_url = DOWNLOAD_URL,
    long_description = LONG_DESCRIPTION,
    classifiers = CLASSIFIERS,
    platforms = 'any',
    **setuptools_kwargs
    )
