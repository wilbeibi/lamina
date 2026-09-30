# Framework-level targets. A site has its own Makefile (see example/Makefile).
all: example

example:
	@cd example && uv run lamina build

check serve links:
	@cd example && uv run lamina $@

lint:
	@uv run mypy
	@uv run ruff check

clean:
	rm -rf example/public

.PHONY: all example check serve links lint clean
