# lamina

## Demo

https://lamina-demo.pages.dev/ (the repo's About link) is `example/` built and
uploaded directly to Cloudflare Pages; the project has no git integration, so
it updates only when deployed by hand. From the repo root:

```sh
make check
wrangler pages deploy example/public --project-name lamina-demo --branch main \
  --commit-hash "$(git rev-parse HEAD)" --commit-message "$(git log -1 --format=%s)"
```

## Writing annotations

Asides follow Ink & Switch's margin notes: about two per 1,000 words,
never two on one paragraph.

- `^[~…]`: a skippable remark about one sentence, such as a source, example,
  caveat, detail or pointer. One or two sentences that stand alone; aim for
  35 words, never over 60. Put it at the end of the sentence; use
  `[words]^[~…]` only to gloss a term.
- `> [!ASIDE]`: a remark about a whole paragraph or section, or one of 35–60
  words. Inline, a long remark splits the paragraph on a phone.
- Over 60 words, or code or a figure: body text or an appendix, with a
  short aside pointing to it.
- Anything the argument needs goes in the body; a gloss under 10 words
  goes in parentheses.
- `[^n]`: formal citations, or a source cited more than once.
- Callouts: only what the reader must not skip.
- Never an image in an aside, or a figure's source (use the caption).
