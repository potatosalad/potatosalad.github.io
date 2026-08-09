#!/usr/bin/env python3
"""Regression checks for the Chirpy-based Jekyll site."""

from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POST_PATH = "/2017/10/13/time-out-elixir-state-machines-versus-servers"
POST_ID = "post-2017-10-13-ad9a120f"
LEGACY_PATH = "/2016/02/06/erlang-nif-with-timeslice-reductions"
LEGACY_ID = "post-2016-02-06-ae71986a"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_chirpy_configuration() -> None:
    gemfile = (ROOT / "Gemfile").read_text()
    config = (ROOT / "_config.yml").read_text()

    require('gem "jekyll-theme-chirpy", "~> 7.6"' in gemfile, "Gemfile must use Chirpy 7.6")
    require("theme: jekyll-theme-chirpy" in config, "Jekyll must use the Chirpy theme")
    require("permalink: /:year/:month/:day/:title" in config, "historical post URLs must be preserved")
    require("provider: disqus" in config, "Chirpy comments must use Disqus")
    require("shortname: potatosalad" in config, "the existing Disqus site must be retained")
    require(not (ROOT / "public/css/main.scss").exists(), "Lanyon stylesheet entrypoint must be removed")


def test_chirpy_starter_structure() -> None:
    require((ROOT / "_tabs/about.md").is_file(), "Chirpy About tab must exist")
    require((ROOT / "_tabs/archives.md").is_file(), "Chirpy Archives tab must exist")
    require((ROOT / "_tabs/categories.md").is_file(), "Chirpy Categories tab must exist")
    require((ROOT / "_tabs/tags.md").is_file(), "Chirpy Tags tab must exist")
    require((ROOT / "_plugins/posts-lastmod-hook.rb").is_file(), "Chirpy last-modified hook must exist")
    require("layout: home" in (ROOT / "index.html").read_text(), "index must use Chirpy home layout")


def test_disqus_identifier_override() -> None:
    include = ROOT / "_includes/comments/disqus.html"
    require(include.is_file(), "Chirpy Disqus include must be overridden for historical threads")
    text = include.read_text()
    require("this.page.identifier = '{{ page.hash }}';" in text, "Disqus must use historical post hashes")
    require(LEGACY_ID in text, "legacy URL-identified thread exception must be preserved")
    require("this.page.identifier = '{{ page.url }}';" in text, "legacy thread must remain URL-identified")


def test_legacy_chart_dependencies() -> None:
    metadata = (ROOT / "_includes/metadata-hook.html").read_text()
    require(LEGACY_ID in metadata, "legacy chart dependencies must only load on their post")
    require("d3/3.5.17/d3.min.js" in metadata, "legacy D3 dependency must be preserved")
    require("nvd3/1.8.5/nv.d3.min.js" in metadata, "legacy NVD3 dependency must be preserved")


def test_theme_owns_404_page() -> None:
    require(not (ROOT / "404.html").exists(), "Chirpy's built-in 404 page must not be shadowed")


def test_container_engine_detection() -> None:
    helper = ROOT / "util/container-engine"
    require(helper.is_file(), "container-engine helper must exist")
    require(bool(helper.stat().st_mode & 0o111), "container-engine helper must be executable")
    if not (shutil.which("docker") or shutil.which("podman")):
        return
    detected = subprocess.run([helper], check=True, capture_output=True, text=True).stdout.strip()
    require(detected in {"docker", "podman"}, "helper must select Docker or Podman")


def generated_post(path: str) -> Path:
    return ROOT / "_site" / f"{path.lstrip('/')}.html"


def test_generated_chirpy_site() -> None:
    generated = generated_post(POST_PATH)
    require(generated.is_file(), f"generated post is missing: {generated}")
    html = generated.read_text()

    require("jekyll-theme-chirpy.css" in html, "generated pages must load Chirpy CSS")
    require("lanyon" not in html.lower(), "generated pages must not load Lanyon")
    require(
        f"this.page.identifier = '{POST_ID}';" in html,
        "generated Disqus embed must use the historical thread identifier",
    )
    require("https://potatosalad.disqus.com/embed.js" in html, "production build must include Disqus")

    home = (ROOT / "_site/index.html").read_text()
    require(
        f'href="{POST_PATH}/"' in home or f'href="{POST_PATH}"' in home,
        "home page must retain the historical post URL",
    )

    legacy = generated_post(LEGACY_PATH).read_text()
    require(
        f"this.page.identifier = '{LEGACY_PATH}';" in legacy,
        "legacy discussion must remain keyed by URL",
    )

    require((ROOT / "_site/public/cv.html").is_file(), "existing CV page must remain published")
    require((ROOT / "_site/assets/post-2017-08-05-b55da7d7/chart1.png").is_file(), "post assets must remain published")


def main() -> int:
    tests = [
        test_chirpy_configuration,
        test_chirpy_starter_structure,
        test_disqus_identifier_override,
        test_legacy_chart_dependencies,
        test_theme_owns_404_page,
        test_container_engine_detection,
    ]
    if "--built" in sys.argv:
        tests.append(test_generated_chirpy_site)
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
