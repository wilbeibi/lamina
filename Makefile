# Framework-level targets. A site has its own Makefile (see example/Makefile).
all: example

example:
	@./folio --root example build

check:
	@./folio --root example check

serve:
	@./folio --root example serve

vendor:
	@./folio vendor

clean:
	rm -rf example/output

.PHONY: all example check serve vendor clean
