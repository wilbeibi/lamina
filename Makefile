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

links:
	@uv run lamina --root example links

lint:
	@uv run mypy
	@uv run ruff check

clean:
	rm -rf example/public

.PHONY: all example check serve vendor links lint clean
