# potatosalad.io

Andrew Bennett's Jekyll blog, published at <https://potatosalad.io>, using the
[Chirpy](https://github.com/cotes2020/jekyll-theme-chirpy) theme.

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

## Comments

Comments use Chirpy's native [giscus](https://giscus.app/) integration and map
each permanent post pathname to a Discussion in this repository's `Comments`
category. `giscus.json` restricts embeds to the production domains and local
preview origins. The four comments from the previous Disqus installation were
imported into the two corresponding GitHub Discussions with explicit attribution
to their original authors and timestamps, while preserving the text, reply
relationship, and historical reaction count.

Existing post `hash` values remain in front matter as Disqus migration records;
new posts do not require one.
