FROM node:22-bookworm-slim AS starry-night

WORKDIR /opt/starry-night

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts

FROM ruby:3.4.10-slim-bookworm

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        git \
        gnupg \
        openssh-client \
        python3 \
        rsync \
    && rm -rf /var/lib/apt/lists/*

ENV BUNDLE_PATH=/usr/local/bundle \
    BUNDLE_JOBS=4 \
    BUNDLE_RETRY=3 \
    STARRY_NIGHT_NODE_MODULES=/opt/starry-night/node_modules

COPY --from=starry-night /usr/local/bin/node /usr/local/bin/node
COPY --from=starry-night /opt/starry-night/node_modules /opt/starry-night/node_modules

WORKDIR /site

COPY Gemfile Gemfile.lock ./
RUN gem install bundler --version 4.0.18 --no-document \
    && bundle _4.0.18_ install

EXPOSE 4000 35729

CMD ["bundle", "exec", "jekyll", "serve", "--host", "0.0.0.0", "--livereload"]