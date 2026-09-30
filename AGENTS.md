# lamina

## Demo

https://lamina-demo.pages.dev/ (the repo's About link) is `example/` built and
uploaded directly to Cloudflare Pages; the project has no git integration, so
it updates only when deployed by hand. From the repo root:

```sh
make
wrangler pages deploy example/public --project-name lamina-demo --branch main \
  --commit-hash "$(git rev-parse HEAD)" --commit-message "$(git log -1 --format=%s)"
```

## Code

- Opinionated: conventions over config, no CLI flags, no plugins. Prefer
  removing an option to adding one. A dependency must be small, high quality,
  and replace real code (msgspec, markdown-it); the stdlib otherwise.
- Hand-formatted: single quotes, one blank line between definitions, no banner
  comments, no formatter. `make lint` runs mypy --strict and ruff.
- No tests. `make check` builds `example/`; a refactor must leave
  `example/public` byte-identical, and a feature change reports its diff.
- SKILL.md is the user-facing reference and the skill for their agents. Update
  it, `lamina --help` and `lamina/init/site.toml` with every user-visible change.

## Writing pages

SKILL.md, "Writing annotations", applies to `example/` too.
