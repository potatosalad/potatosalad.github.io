#!/usr/bin/env python3
"""Regression checks for the Chirpy-based Jekyll site."""

from pathlib import Path
import re
import shutil
import struct
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
    require("highlighter: none" in config, "Jekyll must leave highlighting to Starry Night")
    require("syntax_highlighter_opts:" not in config, "Rouge highlighting options must be removed")
    require("title: potatosalad.io" in config, "sidebar title must read potatosalad.io")
    require('tagline: ""' in config, "sidebar must not display the old blog tagline")
    require(
        'canonical_url: "https://potatosalad.io"' in config,
        "Disqus must retain the production canonical URL during local development",
    )
    require("permalink: /:year/:month/:day/:title" in config, "historical post URLs must be preserved")
    require("provider: disqus" in config, "Chirpy comments must use Disqus")
    require("shortname: potatosalad" in config, "the existing Disqus site must be retained")
    require(
        "avatar: /public/apple-touch-icon-precomposed.png" in config,
        "sidebar must use the existing potatosalad logo",
    )
    require(not (ROOT / "public/css/main.scss").exists(), "Lanyon stylesheet entrypoint must be removed")


def test_chirpy_starter_structure() -> None:
    require((ROOT / "_tabs/about.md").is_file(), "Chirpy About tab must exist")
    require((ROOT / "_tabs/archives.md").is_file(), "Chirpy Archives tab must exist")
    require((ROOT / "_tabs/categories.md").is_file(), "Chirpy Categories tab must exist")
    require((ROOT / "_tabs/tags.md").is_file(), "Chirpy Tags tab must exist")
    require((ROOT / "_plugins/posts-lastmod-hook.rb").is_file(), "Chirpy last-modified hook must exist")
    require("layout: home" in (ROOT / "index.html").read_text(), "index must use Chirpy home layout")


def test_agent_instructions() -> None:
    agents = (ROOT / "AGENTS.md").read_text()
    config = (ROOT / "_config.yml").read_text()
    for command in ("just dev", "just test", "just build", "just deploy-dry-run", "just deploy"):
        require(command in agents, f"AGENTS.md missing workflow command: {command}")
    require("  - AGENTS.md" in config, "AGENTS.md must not be published as site content")


def test_post_categories() -> None:
    expected = {
        "2016-02-06-erlang-nif-with-timeslice-reductions.md": "Native Interoperability",
        "2017-08-05-latency-of-native-functions-for-erlang-and-elixir.md": "Native Interoperability",
        "2017-08-20-load-testing-cowboy-2-0-0-rc-1.md": "Performance Engineering",
        "2017-10-13-time-out-elixir-state-machines-versus-servers.md": "BEAM Architecture",
    }
    for filename, category in expected.items():
        post = (ROOT / "_posts" / filename).read_text()
        require(f"categories: [{category}]" in post, f"missing curated category for {filename}")


def test_post_topbar_home_link() -> None:
    topbar = ROOT / "_includes/topbar.html"
    require(topbar.is_file(), "post top bar must be locally customized")
    text = topbar.read_text()
    require("page.layout == 'post'" in text, "top bar customization must be scoped to posts")
    require(
        '<a href="{{ \'/\' | relative_url }}">potatosalad.io</a>' in text,
        "post top bar must link potatosalad.io back to the home page",
    )


def test_disqus_identifier_override() -> None:
    include = ROOT / "_includes/comments/disqus.html"
    require(include.is_file(), "Chirpy Disqus include must be overridden for historical threads")
    text = include.read_text()
    require(
        "this.page.url = '{{ site.canonical_url }}{{ page.url }}';" in text,
        "Disqus must use the production URL even on the dev server",
    )
    require("this.page.identifier = '{{ page.hash }}';" in text, "Disqus must use historical post hashes")
    require(LEGACY_ID in text, "legacy URL-identified thread exception must be preserved")
    require(
        "unless page.hash == 'post-2016-02-06-ae71986a'" in text,
        "legacy URL-keyed thread must omit an explicit identifier",
    )
    require(
        "this.page.identifier = '{{ page.url }}';" not in text,
        "legacy thread must not be moved to a path-string identifier",
    )


def test_disqus_comment_counts() -> None:
    count_link = ROOT / "_includes/disqus-count-link.html"
    count_script = ROOT / "_includes/disqus-count-script.html"
    require(count_link.is_file(), "reusable Disqus count link must exist")
    link_text = count_link.read_text()
    require("data-disqus-identifier" in link_text, "normal posts must count by historical identifier")
    require(LEGACY_ID in link_text, "legacy URL-keyed count exception must be preserved")
    require("site.canonical_url" in link_text, "legacy count must use its production URL")
    require(count_script.is_file(), "Disqus count loader must exist")
    require("potatosalad.disqus.com/count.js" in count_script.read_text(), "Disqus count script must load")

    home = (ROOT / "_layouts/home.html").read_text()
    post = (ROOT / "_layouts/post.html").read_text()
    require("include disqus-count-link.html post=post" in home, "home cards must show comment counts")
    require("comment-count position-absolute" in home, "home comment counts must be right-aligned")
    require("include disqus-count-link.html post=page" in post, "post header must show its comment count")
    require("include disqus-count-script.html" in home, "home must load count script")
    require("include disqus-count-script.html" in post, "posts must load count script")


def test_static_chart_dependencies() -> None:
    post = (ROOT / "_posts/2016-02-06-erlang-nif-with-timeslice-reductions.md").read_text()
    require("d3." not in post and "nv." not in post, "converted SVG charts must not retain D3/NVD3 code")
    require("<script>" not in post, "static chart post must not retain its obsolete chart script")
    require("/assets/{{ page.hash }}/chart1.svg" in post, "first static chart must remain embedded")
    require("/assets/{{ page.hash }}/chart2.svg" in post, "second static chart must remain embedded")
    require(post.count('class="theme-responsive-chart"') == 2, "both SVG charts must adapt to dark mode")
    require(
        not (ROOT / "_includes/metadata-hook.html").exists(),
        "static SVG charts must not load obsolete D3/NVD3 dependencies",
    )


def test_theme_responsive_content_colors() -> None:
    stylesheet = (ROOT / "assets/css/jekyll-theme-chirpy.scss").read_text()
    require(".theme-responsive-chart" in stylesheet, "custom CSS must style theme-responsive SVG charts")
    require("$sidebar-rail-width: 4.5rem" in stylesheet, "desktop sidebar must retain a collapsed rail")
    require("$sidebar-desktop-breakpoint: 1200px" in stylesheet, "collapsed rail must not leak into tablet/mobile layouts")
    require("max-width: calc($sidebar-desktop-breakpoint - 1px)" in stylesheet, "tablet widths must retain the drawer layout")
    require("body[sidebar-display] #main-wrapper" in stylesheet, "expanded sidebar must push the page content")
    require("#mask" in stylesheet, "desktop sidebar must disable the overlay mask")
    require("#avatar {" in stylesheet, "collapsed rail must use a purpose-sized avatar")
    require("width: calc(100% - $sidebar-rail-width)" in stylesheet, "collapsed content must fit the remaining viewport")
    require("> a {" in stylesheet, "collapsed rail must hide social links")
    require("content: '\\f138'" in stylesheet, "collapsed rail must use Font Awesome's expand icon")
    require("content: '\\f137'" in stylesheet, "expanded sidebar must use Font Awesome's collapse icon")
    require("content: '\\f042'" in stylesheet, "collapsed rail must visibly retain the theme switcher")
    require("#sidebar .sidebar-bottom #mode-toggle" in stylesheet, "theme switcher must keep the collapsed icon when expanded")
    require("transition: width" not in stylesheet, "sidebar width must not animate and make controls jump")
    require("transition: none !important" in stylesheet, "all sidebar controls must switch position without animation")
    require("text-decoration: none !important" in stylesheet, "sidebar toggle icon must not inherit link underlining")
    require('data-bs-theme="dark"' in stylesheet, "custom CSS must define dark-theme adaptations")
    require("contrast(0.82)" in stylesheet, "dark charts must retain visible gridline contrast")
    for css_class in ("metric-good", "metric-caution", "metric-bad"):
        require(f".{css_class}" in stylesheet, f"missing semantic table color class: {css_class}")

    post = (ROOT / "_posts/2017-08-05-latency-of-native-functions-for-erlang-and-elixir.md").read_text()
    require("background-color: #" not in post, "table cells must not retain light-only inline colors")
    for css_class in ("metric-good", "metric-caution", "metric-bad"):
        require(f'class="{css_class}' in post, f"post must use semantic table class: {css_class}")


def test_theme_owns_404_page() -> None:
    require(not (ROOT / "404.html").exists(), "Chirpy's built-in 404 page must not be shadowed")


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"not a PNG file: {path}")
    return struct.unpack(">II", data[16:24])


def test_branding_assets() -> None:
    favicon_dir = ROOT / "assets/img/favicons"
    expected_sizes = {
        "favicon-96x96.png": (96, 96),
        "apple-touch-icon.png": (180, 180),
        "web-app-manifest-192x192.png": (192, 192),
        "web-app-manifest-512x512.png": (512, 512),
    }
    require(
        (favicon_dir / "favicon.ico").read_bytes() == (ROOT / "favicon.ico").read_bytes(),
        "Chirpy must use the site's original favicon",
    )
    for name, size in expected_sizes.items():
        path = favicon_dir / name
        require(path.is_file(), f"missing branded favicon: {path}")
        require(png_size(path) == size, f"wrong dimensions for {name}")

    contacts = (ROOT / "_data/contact.yml").read_text()
    require("type: email" not in contacts, "sidebar must not expose an email link")


def test_post_images_use_site_relative_urls() -> None:
    for post in (ROOT / "_posts").glob("*.md"):
        require(
            "{{ site.url }}/assets" not in post.read_text(),
            f"post image URLs must work on dev and production: {post.name}",
        )


def test_static_svg_dimensions() -> None:
    chart_dir = ROOT / "assets/post-2017-08-20-ac796fcf"
    for chart in chart_dir.glob("*.svg"):
        svg_tag = chart.read_text().split(">", 1)[0]
        require('width="' in svg_tag, f"SVG needs an intrinsic width to render as an image: {chart.name}")
        require('height="' in svg_tag, f"SVG needs an intrinsic height to render as an image: {chart.name}")


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
        'data-highlighter="starry-night"' in html,
        "generated fenced code blocks must be processed by Starry Night",
    )
    require('class="pl-' in html, "generated fenced code must contain Starry Night token classes")
    stylesheet = (ROOT / "_site/assets/css/jekyll-theme-chirpy.css").read_text()
    require(".pl-c" in stylesheet, "generated CSS must include the Starry Night theme")
    require(
        f"this.page.identifier = '{POST_ID}';" in html,
        "generated Disqus embed must use the historical thread identifier",
    )
    require("https://potatosalad.disqus.com/embed.js" in html, "production build must include Disqus")
    require(
        '<div id="topbar-title"><a href="/">potatosalad.io</a></div>' in html,
        "generated post top bar must link potatosalad.io to home",
    )
    require(
        f'data-disqus-identifier="{POST_ID}"' in html,
        "generated post header must count comments by historical identifier",
    )

    home = (ROOT / "_site/index.html").read_text()
    require("mailto:" not in home, "generated sidebar must not expose an email link")
    categories = (ROOT / "_site/categories/index.html").read_text()
    for category in ("Native Interoperability", "Performance Engineering", "BEAM Architecture"):
        require(category in categories, f"generated categories page missing {category}")

    image_post = generated_post("/2017/08/20/load-testing-cowboy-2-0-0-rc-1").read_text()
    require("http://0.0.0.0:4000/assets" not in image_post, "generated images must not use Jekyll's bind address")
    require(
        'src="/assets/post-2017-08-20-ac796fcf/cowboy-1.1.2.1.svg"' in image_post,
        "generated image must use a site-relative asset URL",
    )

    require(
        'src="/public/apple-touch-icon-precomposed.png"' in home,
        "generated sidebar must display the existing logo",
    )

    require(
        f'href="{POST_PATH}/"' in home or f'href="{POST_PATH}"' in home,
        "home page must retain the historical post URL",
    )
    require(
        f'data-disqus-identifier="{POST_ID}"' in home,
        "home card must count comments by historical identifier",
    )

    legacy = generated_post(LEGACY_PATH).read_text()
    legacy_config = legacy.split("var disqus_config", 1)[1].split("};", 1)[0]
    require(
        f"this.page.url = 'https://potatosalad.io{LEGACY_PATH}';" in legacy_config,
        "legacy discussion must look up its production canonical URL",
    )
    require(
        "this.page.identifier" not in legacy_config,
        "legacy discussion must remain URL-keyed by omitting the identifier",
    )
    require(
        f'href="https://potatosalad.io{LEGACY_PATH}#disqus_thread"' in legacy,
        "legacy comment count must look up the production URL",
    )

    require((ROOT / "_site/public/cv.html").is_file(), "existing CV page must remain published")
    require((ROOT / "_site/assets/post-2017-08-05-b55da7d7/chart1.png").is_file(), "post assets must remain published")


def main() -> int:
    tests = [
        test_chirpy_configuration,
        test_chirpy_starter_structure,
        test_agent_instructions,
        test_post_categories,
        test_post_topbar_home_link,
        test_disqus_identifier_override,
        test_disqus_comment_counts,
        test_static_chart_dependencies,
        test_theme_responsive_content_colors,
        test_theme_owns_404_page,
        test_branding_assets,
        test_post_images_use_site_relative_urls,
        test_static_svg_dimensions,
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
