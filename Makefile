# Framework-level targets. A site has its own Makefile (see example/Makefile).
all: example

example:
	@uv run lamina --root example build

check:
	@uv run lamina --root example check

serve:
	@uv run lamina --root example serve

vendor:
	@uv run lamina vendor

clean:
	rm -rf example/output

.PHONY: all example check serve vendor clean
