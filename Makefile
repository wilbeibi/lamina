# Framework-level targets. A site has its own Makefile (see example/Makefile).
all: example

example:
	@./lamina --root example build

check:
	@./lamina --root example check

serve:
	@./lamina --root example serve

vendor:
	@./lamina vendor

clean:
	rm -rf example/output

.PHONY: all example check serve vendor clean
