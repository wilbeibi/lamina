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
