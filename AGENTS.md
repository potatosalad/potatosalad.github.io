# AGENTS.md

## Rules

- Source lives on `develop`; `master` is generated production output.
- Commit directly to `develop` with a GPG signature and `potatosaladx@gmail.com`.
- Use the containerized `just` workflow; do not install/run Ruby or `util/deploy` on the host.
- Preserve post URLs and historical `hash` values. The 2016 NIF Disqus thread is URL-keyed; others use `hash`.
- Use site-relative assets (`/assets/...`) and semantic, light/dark-aware CSS.

## Posts

- Draft in `_drafts/<slug>.md`.
- Publish by moving to `_posts/YYYY-MM-DD-<slug>.md` with `layout`, `title`, focused `tags`, a broad `categories` value, and a stable `hash`.
- Preview with `just dev`; restart it after `_config.yml` changes.

## Ship

```sh
just test
just build
just deploy-dry-run
git commit -S && git push origin develop
just deploy
```

Use `CONTAINER_ENGINE=podman just build` when changing the build/tooling path. `just deploy` builds and signs the generated `master` commit.
