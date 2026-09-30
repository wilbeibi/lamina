# Framework-level targets. A site needs none: `lamina` builds, `lamina serve` serves.
all: example

example serve links:
	@cd example && uv run lamina $(subst example,,$@)

lint:
	@uv run mypy
	@uv run ruff check

clean:
	rm -rf example/public

.PHONY: all example serve links lint clean
