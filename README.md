# potatosalad.io

Andrew Bennett's Jekyll blog, published at <https://potatosalad.io>.

The project is intentionally containerized: Ruby, Bundler, Jekyll, native build tools, Git, SSH, GnuPG, and `rsync` live in the image rather than on the host.

## Requirements

- [`just`](https://github.com/casey/just)
- Docker or Podman

The `justfile` selects a working Docker installation first and falls back to Podman. Override detection when needed:

```sh
CONTAINER_ENGINE=podman just build
```

## Commands

```sh
just build          # production build into _site/ plus regression checks
just dev            # development server at http://localhost:4000
just test           # fast source-level regression checks
just deploy-dry-run # exercise the containerized deployment without pushing
just deploy         # build and publish the generated site to master
```

`just dev` also exposes the LiveReload service on port 35729.

## Deployment

`just deploy` runs `util/deploy` inside the project image. The deployment script:

1. clones/resets the `master` publishing branch under `.tmp/_site`;
2. runs a production Jekyll build inside the container;
3. copies `_site/` into the publishing checkout;
4. creates a deployment commit and pushes `master`.

The recipe mounts the host's `~/.ssh` and `~/.gitconfig` read-only so the container can authenticate, and mounts `~/.gnupg` so GnuPG can access its agent and sign the deployment commit. Run `just deploy-dry-run` before publishing substantial changes.

## Disqus

Posts retain their historical `hash` front-matter values as stable Disqus identifiers. Both comment-count links and the embedded thread use that identifier; changing or removing it can split an existing discussion into a new thread.
