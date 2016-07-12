ACLOCAL_AMFLAGS = -I m4

bin_PROGRAMS = tacc_stats

STATS_DIR_PATH = /var/log/tacc_stats
STATS_LOCK_PATH= /var/lock/tacc_stats
JOBID_FILE_PATH= /var/run/TACC_jobid

if DEBUG
tacc_stats_CFLAGS = \
	-DDEBUG
endif

tacc_stats_CPPFLAGS = \
	-D_GNU_SOURCE \
	-DSTATS_PROGRAM=\"@PACKAGE@\" \
	-DSTATS_VERSION=\"@PACKAGE_VERSION@\" \
	-DSTATS_DIR_PATH=\"$(STATS_DIR_PATH)\" \
	-DSTATS_LOCK_PATH=\"$(STATS_LOCK_PATH)\" \
	-DJOBID_FILE_PATH=\"$(JOBID_FILE_PATH)\"

tacc_stats_SOURCES = \
	collect.h \
	collect.c \
	cpuid.h \
	cpuid.c \
	dict.h \
	dict.c \
	intel_hsw_uncore.h \
	intel_pmc3.h \
	intel_snb_uncore.h \
	JOIN.h \
	pci.h \
	pci.c \
	pscanf.h \
	schema.h \
	schema.c \
	stats.h \
	stats.c \
	string1.h \
	trace.h

if RABBITMQ
tacc_stats_SOURCES += \
	monitor.c \
	stats_buffer.c \
	stats_buffer.h
else
tacc_stats_SOURCES += \
	main.c \
	stats_file.c \
	stats_file.h
endif

TYPES 	= \
	block.c \
	cpu.c \
	mem.c \
	net.c \
	nfs.c \
	numa.c \
	proc.c \
	ps.c \
	sysv_shm.c \
	tmpfs.c \
	vfs.c \
	vm.c

if HARDWARE
TYPES 	+= \
	amd64_pmc.c \
	intel_hsw.c \
	intel_hsw_cbo.c \
	intel_hsw_hau.c \
	intel_hsw_imc.c \
	intel_hsw_pcu.c \
	intel_hsw_qpi.c \
	intel_hsw_r2pci.c \
	intel_ivb.c \
	intel_ivb_cbo.c \
	intel_ivb_hau.c \
	intel_ivb_imc.c \
	intel_ivb_pcu.c \
	intel_ivb_qpi.c \
	intel_ivb_r2pci.c \
	intel_knl.c \
	intel_nhm.c \
	intel_rapl.c \
	intel_snb.c \
	intel_snb_cbo.c \
	intel_snb_hau.c \
	intel_snb_imc.c \
	intel_snb_pcu.c \
	intel_snb_qpi.c \
	intel_snb_r2pci.c \
	intel_wtm.c
endif

if INFINIBAND
TYPES	 += \
	ib.c \
	ib_ext.c \
	ib_sw.c
endif

tacc_stats_LDFLAGS =
if OPA
TYPES	+= \
	opa.c
tacc_stats_LDFLAGS += \
		-lpthread \
		-lmemusage
endif

if LUSTRE
tacc_stats_SOURCES += \
	lustre_obd_to_mnt.c \
	lustre_obd_to_mnt.h

TYPES += \
	mdc.c \
	llite.c \
	lnet.c \
	osc.c
endif

if MIC
tacc_stats_SOURCES += \
	miclib.h 
TYPES += \
	mic.c
endif

tacc_stats_SOURCES += \
	$(TYPES)

tacc_stats_LDFLAGS += \
	-lm

nodist_tacc_stats_SOURCES = \
	stats.x

BUILT_SOURCES = stats.x
CLEANFILES = stats.x
stats.o: stats.x
stats.x: Makefile
	echo '$(patsubst %.c, X(%),$(sort $(TYPES)))' > $@

if RABBITMQ
initddir = $(sysconfdir)/rc.d/init.d
initd_SCRIPTS = taccstats
sysconf_DATA = tacc_stats.conf
BUILT_SOURCES += taccstats
nodist_tacc_stats_SOURCES += \
	taccstats
CLEANFILES += $(initd_SCRIPTS) $(sysconfdir_DATA)

do_subst = sed -e 's,@STATS_LOCK_PATH@,$(STATS_LOCK_PATH),g' \
	-e 's,@SYSCONFDIR@,$(sysconfdir),g' \
	-e 's,@PREFIX@,$(bindir),g'
taccstats: taccstats.in Makefile
	$(do_subst) < taccstats.in > taccstats
	chmod +x taccstats
else
bin_SCRIPTS = archive
endif

EXTRA_DIST = taccstats.in tacc_stats.conf archive
