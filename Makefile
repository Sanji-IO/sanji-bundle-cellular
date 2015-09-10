NAME    = $(shell cat bundle.json | sed -n 's/"name"//p' | tr -d '", :')
VERSION = $(shell cat bundle.json | sed -n 's/"version"//p' | tr -d '", :')

PROJECT = sanji-bundle-$(NAME)

DISTDIR = $(PROJECT)-$(VERSION)
ARCHIVE = $(CURDIR)/$(DISTDIR).tar.gz

SANJI_VER   ?= 1.0
INSTALL_DIR = $(DESTDIR)/usr/lib/sanji-$(SANJI_VER)/$(NAME)
STAGING_DIR = $(CURDIR)/staging
PROJECT_STAGING_DIR = $(STAGING_DIR)/$(DISTDIR)

TARGET_FILES = \
	LICENSE \
	bundle.json \
	requirements.txt \
	cellular.py \
	data/cellular.json.factory \
	hooks/cellular-dhclient-hook
DIST_FILES= \
	$(TARGET_FILES) \
	README.md \
	Makefile \
	tests/requirements.txt \
	tests/test_cellular.py \
	tests/test_e2e/bundle.json \
	tests/test_e2e/view_cellular.py
INSTALL_FILES=$(addprefix $(INSTALL_DIR)/,$(TARGET_FILES))
STAGING_FILES=$(addprefix $(PROJECT_STAGING_DIR)/,$(DIST_FILES))


all:

clean:
	rm -rf $(DISTDIR)*.tar.gz $(STAGING_DIR)
	@rm -rf .coverage
	@find ./ -name *.pyc | xargs rm -rf

distclean: clean

pylint:
	flake8 -v --exclude=.git,__init__.py .
test:
	nosetests --with-coverage --cover-erase --cover-package=$(NAME) -v

dist: $(ARCHIVE)

$(ARCHIVE): distclean $(STAGING_FILES)
	@mkdir -p $(STAGING_DIR)
	cd $(STAGING_DIR) && \
		tar zcf $@ $(DISTDIR)

$(PROJECT_STAGING_DIR)/%: %
	@mkdir -p $(dir $@)
	@cp -a $< $@

install: $(INSTALL_FILES)

$(INSTALL_DIR)/%: %
	@mkdir -p $(dir $@)
	@cp -a $< $@

uninstall:
	-rm $(addprefix $(INSTALL_DIR)/,$(TARGET_FILES))

.PHONY: clean dist pylint test
