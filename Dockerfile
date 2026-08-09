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
    BUNDLE_RETRY=3

WORKDIR /site

COPY Gemfile Gemfile.lock ./
RUN gem install bundler --version 4.0.18 --no-document \
    && bundle _4.0.18_ install

EXPOSE 4000 35729

CMD ["bundle", "exec", "jekyll", "serve", "--host", "0.0.0.0", "--livereload"]