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

MAJOR = 1
MINOR = 0
MICRO = 6
ISRELEASED = False
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

def read_site_cfg():
    config = ConfigParser.ConfigParser()

    cfg_filename = os.path.abspath('setup.cfg')

    print 'Read configure file ' + cfg_filename    
    if cfg_filename:
        config.read(cfg_filename)
    else:
        print 'Specify a filename e.g. (hostname + .cfg)'
        sys.exit()
        
    paths = dict(config.items('PATHS'))
    types = dict(config.items('TYPES'))

    return paths,types

def write_stats_x(types):

    filename = os.path.join(
        os.path.dirname(__file__), 'tacc_stats','src','monitor', 'stats.x')
    a = open(filename, 'w')
    
    try:
        for t,val in types.iteritems():            
            if val == 'True':
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
    print 'cleaning'
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

paths,types = read_site_cfg()
write_stats_x(types)
write_cfg_file(paths)


root='tacc_stats/src/monitor/'
sources=[pjoin(root,'schema.c'),pjoin(root,'dict.c'),pjoin(root,'stats.c'),pjoin(root,'collect.c'),pjoin(root,'stats_file.c'),pjoin(root,'monitor.c')]

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
               ('JOBID_FILE_PATH','\"'+paths['jobid_file']+'\"')]
             
flags = ['-D_GNU_SOURCE','-DDEBUG',
         '-O3','-Werror','-Wall','-g']
ext_data=dict(sources=[pjoin(root,'main.c')]+sources,
              include_dirs=['tacc_stats/src/monitor/'] + include_dirs,
              library_dirs=library_dirs,
              runtime_library_dirs=library_dirs,
              libraries=libraries,
              extra_compile_args = flags,
              define_macros=define_macros
              )

extensions = []
cmd = {}

# The build cache system does string matching below this point.
# if you change something, be careful.

class MyBuildExt(build_ext):
    def build_extension(self,ext):
        
        sources = ext.sources
        sources = list(sources)
        ext_path = self.get_ext_fullpath(ext.name)
        depends = sources + ext.depends
        extra_args = ext.extra_compile_args or []

        if os.path.isfile(pjoin('build','bin','monitor')) and \
                os.path.isfile(pjoin(ext_path)):
            return

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
        
        compiler_objects = objects
        compiler_objects.remove(pjoin(self.build_temp,'tacc_stats','src',
                                      'monitor','monitor.o'))
        self.compiler.link_executable(
            compiler_objects, 'build/bin/monitor',
            libraries=ext.libraries,
            library_dirs=ext.library_dirs,
            runtime_library_dirs=ext.runtime_library_dirs,
            extra_postargs=extra_args,
            target_lang=language)
        shutil.copyfile('tacc_stats/src/monitor/archive.sh','build/bin/archive.sh')

        objects.remove(pjoin(self.build_temp,'tacc_stats','src',
                             'monitor','main.o'))
        self.compiler.link_shared_object(
            objects, ext_path,
            libraries=self.get_libraries(ext),
            library_dirs=ext.library_dirs,
            runtime_library_dirs=ext.runtime_library_dirs,
            extra_postargs=extra_args,
            export_symbols=self.get_export_symbols(ext),
            debug=self.debug,
            build_temp=self.build_temp,
            target_lang=language)
        

extensions.append(Extension("tacc_stats.monitor", **ext_data))
cmd = {'build_ext' : MyBuildExt}

    
cfg_sh(pjoin(os.path.dirname(__file__), 'tacc_stats',
             'analysis','exams_cron.sh.in'),paths)
cfg_sh(pjoin(os.path.dirname(__file__), 'tacc_stats',
             'pickler','do_job_pickles_cron.sh.in'),paths)
cfg_sh(pjoin(os.path.dirname(__file__), 'tacc_stats',
             'site','update_cron.sh.in'),paths)

setup(name=DISTNAME,
      version=FULLVERSION,
      maintainer=AUTHOR,
      package_dir={'':'.'},
      packages=find_packages(),
      package_data = {'' : ['*.sh.in','*.cfg'] },
      scripts=['build/bin/monitor',
               'tacc_stats/analysis/job_sweeper.py',
               'tacc_stats/analysis/job_plotter.py',
               'tacc_stats/exams_cron.sh',
               'tacc_stats/update_cron.sh',
               'tacc_stats/do_job_pickles_cron.sh',
               'tacc_stats/site/ls4_update_db.py',
               'tacc_stats/site/update_db.py',
               'tacc_stats/pickler/job_pickles.py'],
      ext_modules=extensions,
      setup_requires=['nose>=1.0'],
      test_suite = 'nose.collector',
      maintainer_email=EMAIL,
      description=DESCRIPTION,
      zip_safe=False,
      license=LICENSE,
      cmdclass={'build_ext' : MyBuildExt},
      url=URL,
      download_url=DOWNLOAD_URL,
      long_description=LONG_DESCRIPTION,
      classifiers=CLASSIFIERS,
      platforms='any',
      **setuptools_kwargs)

for name,path in paths.iteritems():
    if os.path.exists(path): print ">>>", path, 'exists'
    else: print ">>>", path, 'does not exist'
