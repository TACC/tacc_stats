NAME=supremm
VERSION=0.1
RELEASE=1

SRC_DIR=$(CURDIR)
BUILD_DIR=$(CURDIR)/build

PKGSRC_FILES=scripts \
			 monitor \
			 Makefile \
			 LICENSE \
			 README

all:
	@echo -n ""
	
package:
	mkdir -p $(BUILD_DIR)/$(NAME)-$(VERSION)
	cp -r $(PKGSRC_FILES) $(BUILD_DIR)/$(NAME)-$(VERSION)
	cd $(BUILD_DIR) && tar -czf $(NAME)_$(VERSION).orig.tar.gz $(NAME)-$(VERSION)
	cp -r debian $(BUILD_DIR)/$(NAME)-$(VERSION)
	cd $(BUILD_DIR)/$(NAME)-$(VERSION) && debuild -us -uc

install:
	$(MAKE) -C scripts install


.PHONY: clean-pkg
clean-pkg:
	rm -r $(BUILD_DIR)
