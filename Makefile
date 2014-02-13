NAME=supremm
VERSION=0.1
RELEASE=1

SRC_DIR=$(CURDIR)
BUILD_DIR=$(CURDIR)/build

PKGSRC_FILES=scripts \
			 pickler \
			 Makefile \
			 LICENSE \
			 README

prefix = $(DESTDIR)/usr/share/supremm
bindir = $(prefix)/bin
etcdir = $(prefix)/etc
libdir = $(prefix)/lib

CONFIG_FILES =  scripts/pickle.conf.lonestar \
				scripts/pickle.conf.rush \
				scripts/pickle.conf.stampede \
				scripts/supremm.conf \
				scripts/stampede.conf \
				scripts/lonestar.conf

SCRIPT_FILES =  scripts/summaryConvertToMongo.py \
				scripts/summary.py \
				scripts/summary_rush_slurm.py \
				scripts/summary_stampede_slurm.py \
				scripts/batchSummary.sh \
				scripts/rawTaccStatsTarTransfer.sh

PYTHONLIBS = pickler/amd64_pmc.py \
			 pickler/batch_acct.py \
			 pickler/intel_snb.py \
			 pickler/job_stats.py \
			 pickler/sge_acct.py \
			 pickler/torque_acct.py \
			 pickler/slurm_stampede_acct.py \
			 pickler/slurm_rush_acct.py \
			 pickler/getProcdumpData.py \
			 pickler/setup.py

all:
	@echo -n ""
	
package:
	mkdir -p $(BUILD_DIR)/$(NAME)-$(VERSION)
	cp -r $(PKGSRC_FILES) $(BUILD_DIR)/$(NAME)-$(VERSION)
	cd $(BUILD_DIR) && tar -czf $(NAME)_$(VERSION).orig.tar.gz $(NAME)-$(VERSION)
	cp -r debian $(BUILD_DIR)/$(NAME)-$(VERSION)
	cd $(BUILD_DIR)/$(NAME)-$(VERSION) && debuild -us -uc
	dpkg -I $(BUILD_DIR)/$(NAME)_$(VERSION)*.deb
	dpkg -c $(BUILD_DIR)/$(NAME)_$(VERSION)*.deb

install:
	install -d $(etcdir)
	install -m 644 $(CONFIG_FILES) $(etcdir)
	install -d $(bindir)
	install $(SCRIPT_FILES) $(bindir)
	cd pickler && python setup.py install --root=$(DESTDIR) --install-layout=deb --install-lib=/usr/share/supremm/bin --install-scripts=/usr/share/supremm


.PHONY: clean-pkg
clean-pkg:
	rm -r $(BUILD_DIR)
