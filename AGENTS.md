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
  comments, no formatter. `make lint` runs ty and ruff
  (ANN stands in for the annotations mypy --strict required).
- No tests. `make` builds `example/`; a refactor must leave
  `example/public` byte-identical, and a feature change reports its diff.
- SKILL.md is the user-facing reference and the skill for their agents. Update
  it, `lamina --help` and `example/site.toml` with every user-visible change.

## Updating dependencies

Check monthly, bump one source at a time, and commit each bump separately.

- Python: `uv tree --outdated --depth 1`, then `uv lock --upgrade` (widen a
  `~=` range in pyproject.toml only for a release outside it). A new ty or
  ruff may add findings; `make lint`.
- Pele, Temml: `npm view pele version`, `npm view temml version`; bump the
  URLs at the top of `lamina/build.py` (Temml's JS and CSS share a version).
  Read the changelog first: pele follows a Mermaid syntax release, Temml's
  0.x minors change MathML output.
- Prism: `npm view prismjs version`; rebuild `lamina/theme/prism.js` as its
  header says, same components, header version updated.
- Verify: snapshot `example/public` and `~/dump/public` before, `make`, and
  `diff -r`. A browser-lib bump changes only its URL or `prism.js`; a Python
  bump must leave pages byte-identical or explain each differing line. Then look
  at code, the diagram and math on the example page, light and dark.
- Sites that self-host a library in `theme/` keep their old copy; name the
  new version in the commit so they can update.
- The README chart, `assets/page-weight.svg`, is gzip -9 of `style.css` +
  `lamina.js`, plus `prism.js`, Temml's JS, CSS and font, or pele. Redraw it
  when a bump moves a number by 1 KB or more.

## Writing pages

SKILL.md, "Writing annotations", applies to `example/` too.
