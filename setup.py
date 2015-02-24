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
LICENSE = 'BSD'
AUTHOR = "Texas Advanced Computing Center"
EMAIL = "rtevans@tacc.utexas.edu"
URL = "http://www.tacc.utexas.edu"
DOWNLOAD_URL = ''
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
MINOR = 1
MICRO = 0
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
          # partial clone, manually construct version string
          # this is the format before we started using git-describe
          # to get an ordering on dev version strings.
          rev ="v%s.dev-%s" % (VERSION, rev)

      # Strip leading v from tags format "vx.y.z" to get th version string
      FULLVERSION = rev.lstrip('v')

else:
    FULLVERSION += QUALIFIER


def write_version_py(filename=None):
    cnt = """\
version = '%s'
short_version = '%s'
"""
    if not filename:
        filename = os.path.join(
            os.path.dirname(__file__), 'tacc_stats', 'version.py')

    a = open(filename, 'w')
    try:
        a.write(cnt % (FULLVERSION, VERSION))
    finally:
        a.close()

if write_version:
    write_version_py()

if '--monitor-only' in sys.argv:
    MONITOR_ONLY = True
    sys.argv.remove('--monitor-only')
else:
    MONITOR_ONLY = False

def read_site_cfg():
    config = ConfigParser.ConfigParser()

    cfg_filename = os.path.abspath('setup.cfg')

    print 'Read configure file ' + cfg_filename    
    if cfg_filename:
        config.read(cfg_filename)
    else:
        print 'Specify a filename e.g. (setup.cfg)'
        sys.exit()
        
    paths = dict(config.items('PATHS'))
    types = dict(config.items('TYPES'))
    options = dict(config.items('OPTIONS'))
    return paths,types,options

def write_stats_x(types):

    filename = os.path.join(
        os.path.dirname(__file__), 'tacc_stats','src','monitor', 'stats.x')
    a = open(filename, 'w')
    import operator
    try:
        for t,val in sorted(types.iteritems(), key=operator.itemgetter(0)):            
            if val == 'True':
                print '>>>>>>>>>>>>>>>>>>>>>>',t,val
                a.write('X('+t+') ')
    finally:
        a.write('\n')
        a.close()

def write_cfg_file(paths):
    
    filename = pjoin(os.path.dirname(__file__), 'tacc_stats', 
                     'cfg.py')
    a = open(filename, 'w')    
    try:
        for name,path in paths.iteritems():
            a.write(name + " = " + "\"" + path + "\"" + "\n")
        a.write("seek = 0\n")
    finally:
        a.close()

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

paths,types,options = read_site_cfg()
write_stats_x(types)
write_cfg_file(paths)

root='tacc_stats/src/monitor/'
sources=[
    pjoin(root,'schema.c'),pjoin(root,'dict.c'),pjoin(root,'collect.c'),
    pjoin(root,"pci_busid_map.c"),
    pjoin(root,'stats_file.c'),pjoin(root,'stats_buffer.c'),pjoin(root,'stats.c')
    ]


RMQ = False
if options['rmq'] == 'True': 
    RMQ = True

if RMQ: sources.append(pjoin(root,'amqp_listen.c'))

MODE = options['mode']
if MODE == "DAEMON": 
    print "Building a monitoring daemon."
    sources.append(pjoin(root,'monitor.c'))
elif MODE == "CRON": 
    print "Building an executable to be called by cron."
    sources.append(pjoin(root,'main.c'))
else:
    print "BUILD ERROR: Set mode to either DAEMON or CRON"
SERVER = options['server']
FREQUENCY = options['frequency']

for root,dirs,files in os.walk('tacc_stats/src/monitor/'):
    for f in files:
        name,ext = os.path.splitext(f)        
        if ext == '.c' and name in types.keys():
            if types[name] == 'True':
                sources.append(pjoin(root,f))

include_dirs = []
library_dirs = []
libraries = []

if types['ib'] == 'True' or types['ib_sw'] == 'True' or types['ib_ext'] == 'True':    
    include_dirs=['/opt/ofed/include']
    library_dirs=['/opt/ofed/lib64']
    libraries=['ibmad']

if types['llite'] == 'True' or types ['lnet'] == 'True' or \
        types['mdc'] == 'True' or types['osc'] == 'True':
    sources.append('tacc_stats/src/monitor/lustre_obd_to_mnt.c')

define_macros=[('STATS_DIR_PATH','\"'+paths['stats_dir']+'\"'),
               ('STATS_VERSION','\"'+VERSION+'\"'),
               ('STATS_PROGRAM','\"tacc_stats\"'),
               ('STATS_LOCK_PATH','\"'+paths['stats_lock']+'\"'),
               ('JOBID_FILE_PATH','\"'+paths['jobid_file']+'\"'),
               ('FREQUENCY',FREQUENCY)]
if RMQ:
    define_macros.append(('RMQ',True))
    libraries.append("rabbitmq")

flags = ['-D_GNU_SOURCE', '-Wp,-U_FORTIFY_SOURCE',
         '-O3', '-Wall', '-g']#, '-DDEBUG']
ext_data=dict(sources=sources,
              include_dirs=['tacc_stats/src/monitor/'] + include_dirs,
              library_dirs=library_dirs,
              runtime_library_dirs=library_dirs,
              libraries=libraries,
              extra_compile_args = flags,
              define_macros=define_macros
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
        
        self.prep_script = "build/bdist_rpm_prep"
        prep = """
%define _bindir /opt/%{name}
%define crontab_file /etc/cron.d/%{name}
"""
        if RMQ:
            prep += "%define server " + "-s "+SERVER
        else:
            prep += "%define server"
        if MODE == "DAEMON":
            prep += "\n%define pidfile " + paths['stats_lock']
        if MODE == "CRON":
            prep += """
%define stats_dir /var/log/%{name}
%define archive_dir /scratch/projects/%{name}/archive
"""
        prep += """
%setup -n %{name}-%{unmangled_version}
"""        
        open(self.prep_script,"w").write(prep)
        

        self.build_script = "build/bdist_rpm_build"        
        build_cmds = """
rm -rf %{buildroot}
python setup.py build_ext
"""
        open(self.build_script,"w").write(build_cmds)


        self.install_script = "build/bdist_rpm_install"
        install_cmds = """
install -m 0755 -d %{buildroot}/%{_bindir}
install -m 6755 build/bin/monitord %{buildroot}/%{_bindir}/%{name}_monitord
echo %{_bindir}/%{name}_monitord >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
"""
        if MODE == "CRON":
            install_cmds += """
install -m 0755 tacc_stats/archive.sh %{buildroot}/%{_bindir}/%{name}_archive
echo %{_bindir}/%{name}_archive >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
"""
        else:
            install_cmds += """
install -m 0755 tacc_stats/taccstats %{buildroot}/%{_bindir}/taccstats
echo %{_bindir}/taccstats >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
"""

        if RMQ: 
            install_cmds += """
install -m 0755 build/bin/amqp_listend %{buildroot}/%{_bindir}/%{name}_listend
echo %{_bindir}/%{name}_listend >> %{_builddir}/%{name}-%{unmangled_version}/INSTALLED_FILES
"""     
        open(self.install_script,"w").write(install_cmds)

        self.clean_script = None
        self.verify_script = None

        self.post_install = "build/bdist_rpm_postinstall"

        if MODE == "CRON":
            post_install_cmds = """
(
 archive_min=$(( ((RANDOM * 60) / 32768) %% 60 ))
 archive_hour=$(( (RANDOM %% 2) + 2 ))
 echo \"MAILTO=\\"\\"\"
 echo \"*/10 * * * * root %{_bindir}/%{name}_monitord collect %{server}\"
 echo \"55 23 * * * root %{_bindir}/%{name}_monitord  rotate %{server}\"
"""
            self.pre_uninstall = "build/bdist_rpm_preuninstall"
            open(self.pre_uninstall,"w").write("""
if [ $1 == 0 ]; then
rm %{crontab_file} || :
fi
""")

            if not RMQ:
                post_install_cmds += """
 echo \"${archive_min} ${archive_hour} * * * root %{_bindir}/%{name}_archive %{stats_dir} %{archive_dir}\"
"""
            post_install_cmds += """
) > %{crontab_file}
/sbin/service crond restart || :
%{_bindir}/%{name}_monitord rotate %{server}
"""
        if MODE == "DAEMON":
            post_install_cmds = """
cp %{_bindir}/taccstats /etc/init.d/
chkconfig --add taccstats
service taccstats restart
"""
        open(self.post_install,"w").write(post_install_cmds)
        self.pre_install = None
        if MODE == "DAEMON":
            self.post_uninstall = "build/bdist_rpm_post_uninstall"
            post_uninstall_cmds = """
chkconfig --del taccstats
rm /etc/init.d/taccstats
rmdir %{_bindir}
"""
            open(self.post_uninstall,"w").write(post_uninstall_cmds)

#(
# echo \"55 23 * * * root service taccstats rotate\"
#) > %{crontab_file}
#/sbin/service crond restart || :

# Make executable
# C extensions
class MyBuildExt(build_ext):
    def build_extension(self,ext):
        
        sources = ext.sources
        sources = list(sources)
        ext_path = self.get_ext_fullpath(ext.name)
        depends = sources + ext.depends
        extra_args = ext.extra_compile_args or []
        macros = ext.define_macros[:]
        for undef in ext.undef_macros:
            macros.append((undef,))

        objects = self.compiler.compile(sources,
                                        output_dir=self.build_temp,
                                        macros=macros,
                                        include_dirs=ext.include_dirs,
                                        extra_postargs=extra_args,
                                        depends=ext.depends)
        self._built_objects = objects[:]

        if ext.extra_objects:
            objects.extend(ext.extra_objects)
        extra_args = ext.extra_link_args or []

        language = ext.language or self.compiler.detect_language(sources)

        if RMQ:
            self.compiler.link_executable([pjoin(self.build_temp,
                                                 'tacc_stats','src','monitor',
                                                 'amqp_listen.o')],
                                          'build/bin/amqp_listend',
                                          libraries=ext.libraries,
                                          library_dirs=ext.library_dirs,
                                          runtime_library_dirs=ext.runtime_library_dirs,
                                          extra_postargs=extra_args,
                                          target_lang=language)
            objects.remove(pjoin(self.build_temp,'tacc_stats','src',
                                 'monitor','amqp_listen.o'))

        self.compiler.link_executable(objects, 
                                      'build/bin/monitord',
                                      libraries=ext.libraries,
                                      library_dirs=ext.library_dirs,
                                      runtime_library_dirs=ext.runtime_library_dirs,
                                      extra_postargs=extra_args,
                                      target_lang=language)
        self.compiler.link_shared_object(objects, 
                                         ext_path,
                                         libraries=ext.libraries,
                                         library_dirs=ext.library_dirs,
                                         runtime_library_dirs=ext.runtime_library_dirs,
                                         extra_postargs=extra_args,
                                         debug=self.debug,
                                         build_temp=self.build_temp,
                                         target_lang=language)

extensions.append(Extension('tacc_stats.monitor', **ext_data))

if not RMQ:
    cfg_sh(pjoin(os.path.dirname(__file__), 'tacc_stats',
                 'src','monitor','archive.sh.in'),paths)
if MODE == "DAEMON":
    cfg_sh(pjoin(os.path.dirname(__file__), 'tacc_stats',
                 'src','monitor','taccstats.in'),dict(paths.items()+options.items()))

if MONITOR_ONLY:
    scripts=['build/bin/monitord']

    if MODE == "CRON":
        scripts += ['tacc_stats/archive.sh']
        package_data = {'' : ['*.sh.in'] },
    else:
        scripts += ['tacc_stats/taccstats']
        package_data = {'' : ['taccstats.in']}
    setup(name=DISTNAME,
          version=FULLVERSION,
          maintainer=AUTHOR,
          packages=['tacc_stats/src/monitor'],
          package_data = package_data,
          scripts=scripts,
          ext_modules=extensions,
          maintainer_email=EMAIL,
          description=DESCRIPTION,
          zip_safe=False,
          license=LICENSE,
          cmdclass={'build_ext' : MyBuildExt, 
                    'clean' : CleanCommand,
                    'bdist_rpm' : MyBDist_RPM},
          url=URL,
          download_url=DOWNLOAD_URL,
          long_description=LONG_DESCRIPTION,
          classifiers=CLASSIFIERS,
          platforms='any',
          **setuptools_kwargs)
else:
    scripts=['build/bin/monitord',             
             'tacc_stats/analysis/job_sweeper.py',
             'tacc_stats/analysis/job_plotter.py',
             'tacc_stats/site/lonestar/ls4_update_db.py',
             'tacc_stats/site/stampede/update_db.py',
             'tacc_stats/site/stampede/update_thresholds.py',
             'tacc_stats/site/stampede/thresholds.cfg',
             'tacc_stats/pickler/job_pickles.py']
    if RMQ: scripts += ['build/bin/amqp_listend']
    if MODE == "CRON":
        scripts += ['tacc_stats/archive.sh']
        package_data = {'' : ['*.sh.in'] },
    else:
        scripts += ['tacc_stats/taccstats']

    setup(name=DISTNAME,
          version=FULLVERSION,
          maintainer=AUTHOR,
          package_dir={'':'.'},
          packages=find_packages(),
          package_data = {'' : ['*.in','*.cfg','*.html','*.png','*.jpg','*.h'] },
          scripts=scripts,
          ext_modules=extensions,
          setup_requires=['nose'],
          install_requires=['argparse','numpy','matplotlib','scipy'],
          test_suite = 'nose.collector',
          maintainer_email=EMAIL,
          description=DESCRIPTION,
          zip_safe=False,
          license=LICENSE,
          cmdclass={'build_ext' : MyBuildExt, 
                    'clean' : CleanCommand,
                    'bdist_rpm' : MyBDist_RPM},
          url=URL,
          download_url=DOWNLOAD_URL,
          long_description=LONG_DESCRIPTION,
          classifiers=CLASSIFIERS,
          platforms='any',
          **setuptools_kwargs)

for name,path in paths.iteritems():
    if os.path.exists(path): print ">>>", path, 'exists'
    else: print ">>>", path, 'does not exist'
