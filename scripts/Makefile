prefix = /usr
bindir = $(prefix)/bin
sharedir = $(prefix)/share
mandir = $(sharedir)/man
man1dir = $(mandir)/man1

all:
	echo "***** ALL *****"

clean:
	echo "***** CLEAN *****"

install: all
	install -d $(DESTDIR)$(sharedir)/supremm
	install *.py $(DESTDIR)$(sharedir)/supremm
