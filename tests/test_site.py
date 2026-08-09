#!/usr/bin/env python3
"""Regression checks for the generated Jekyll site."""

from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POST_PATH = "/2017/10/13/time-out-elixir-state-machines-versus-servers"
POST_ID = "post-2017-10-13-ad9a120f"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_disqus_templates() -> None:
    index = (ROOT / "index.html").read_text()
    post_layout = (ROOT / "_layouts/post.html").read_text()

    require(
        'data-disqus-identifier="{{ post.hash }}"' in index,
        "index comment links must identify the same Disqus thread as the embed",
    )
    require(
        'href="{{ post.url | relative_url }}#disqus_thread"' in index,
        "index comment links must use the post URL",
    )
    require(
        "unless post.hash == 'post-2016-02-06-ae71986a'" in index,
        "the legacy URL-identified thread must not receive a new identifier",
    )
    require(
        'data-disqus-identifier="{{ page.hash }}"' in post_layout,
        "post comment link must identify the embedded Disqus thread",
    )
    require(
        'href="{{ page.url | relative_url }}#disqus_thread"' in post_layout,
        "post layout must use page.url rather than undefined post.url",
    )
    require(
        "unless page.hash == 'post-2016-02-06-ae71986a'" in post_layout,
        "the legacy post count must remain URL-identified like its embed",
    )


def test_sass_uses_module_system() -> None:
    stylesheet = (ROOT / "public/css/main.scss").read_text()
    require('@use "poole";' in stylesheet, "site Sass must load poole with @use")
    require('@use "syntax";' in stylesheet, "site Sass must load syntax with @use")
    require('@use "lanyon";' in stylesheet, "site Sass must load lanyon with @use")


def test_container_engine_detection() -> None:
    helper = ROOT / "util/container-engine"
    require(helper.is_file(), "container-engine helper must exist")
    require(bool(helper.stat().st_mode & 0o111), "container-engine helper must be executable")
    if not (shutil.which("docker") or shutil.which("podman")):
        return
    detected = subprocess.run(
        [helper], check=True, capture_output=True, text=True
    ).stdout.strip()
    require(detected in {"docker", "podman"}, "helper must select Docker or Podman")


def test_generated_disqus_link() -> None:
    generated = ROOT / "_site" / f"{POST_PATH.lstrip('/')}.html"
    require(generated.is_file(), f"generated post is missing: {generated}")
    html = generated.read_text()
    pattern = re.compile(
        rf'<a[^>]+href="{re.escape(POST_PATH)}/?#disqus_thread"[^>]+'
        rf'data-disqus-identifier="{re.escape(POST_ID)}"'
    )
    require(
        pattern.search(html) is not None,
        "generated post comment link must contain its canonical path and Disqus identifier",
    )
    require(
        "https://potatosalad.disqus.com/embed.js" in html,
        "production build must include the Disqus embed",
    )


def main() -> int:
    tests = [
        test_disqus_templates,
        test_sass_uses_module_system,
        test_container_engine_detection,
    ]
    if "--built" in sys.argv:
        tests.append(test_generated_disqus_link)
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
