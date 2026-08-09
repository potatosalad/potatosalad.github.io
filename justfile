set shell := ["bash", "-euo", "pipefail", "-c"]

image := "potatosalad-jekyll:dev"
engine := `./util/container-engine`
network := `if [[ "$(./util/container-engine)" == podman && ! -e /dev/net/tun ]]; then printf '%s' '--network=host'; fi`
ports := `if [[ "$(./util/container-engine)" != podman || -e /dev/net/tun ]]; then printf '%s' '--publish 4000:4000 --publish 35729:35729'; fi`

default:
    @just --list

# Build or refresh the Jekyll development image.
image:
    {{ engine }} build {{ network }} --tag {{ image }} .

# Build the production site into _site/.
build: image
    rm -rf _site
    {{ engine }} run --rm --network=none --env JEKYLL_ENV=production --volume "$PWD:/site" --workdir /site {{ image }} bundle exec jekyll build --trace
    {{ engine }} run --rm --network=none --volume "$PWD:/site" --workdir /site {{ image }} python3 tests/test_site.py --built

# Serve the site with live reload at http://localhost:4000.
dev: image
    {{ engine }} run --rm --interactive --tty {{ network }} {{ ports }} --volume "$PWD:/site" --workdir /site {{ image }} bundle exec jekyll serve --host 0.0.0.0 --livereload --force_polling

# Run source-level regression checks.
test:
    python3 tests/test_site.py

# Build and publish master using util/deploy inside the container.
deploy: image
    {{ engine }} run --rm {{ network }} --env JEKYLL_ENV=production --volume "$PWD:/site" --volume "$HOME/.ssh:/root/.ssh:ro" --volume "$HOME/.gitconfig:/root/.gitconfig:ro" --volume "$HOME/.gnupg:/root/.gnupg" --workdir /site {{ image }} ./util/deploy

# Exercise the complete deploy flow without pushing to GitHub.
deploy-dry-run: image
    {{ engine }} run --rm {{ network }} --env JEKYLL_ENV=production --env DEPLOY_DRY_RUN=1 --volume "$PWD:/site" --volume "$HOME/.ssh:/root/.ssh:ro" --volume "$HOME/.gitconfig:/root/.gitconfig:ro" --volume "$HOME/.gnupg:/root/.gnupg" --workdir /site {{ image }} ./util/deploy
