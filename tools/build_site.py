"""Build the GitHub Pages mirror in docs/ from the archived captures.

usage: nix-shell -p pandoc --run 'python3 -I tools/build_site.py .'

Publishes every page listed in reading-list.md, converted to Markdown, grouped
and ordered as in that file. Dates, authors and captures come from manifest.tsv.
Images the posts use are fetched from the Wayback Machine once and kept under
docs/assets/, so later rebuilds only need the network for new images. The plain
text of every page goes to docs/search/pages.json for the search page.
"""
import gzip
import json
import os
import posixpath
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape

FP_HOSTS = {"www.fpcomplete.com", "fpcomplete.com", "tech.fpcomplete.com", "academy.fpblock.com",
            "www.fpblock.com", "fpblock.com"}
# FP Complete's tutorial sites from before the haskell/ section absorbed them.
TUTORIAL_HOSTS = {"haskell-lang.org", "www.haskell-lang.org", "haskell.fpcomplete.com"}
SITE_DIR = "docs"
SEARCH_PAGES = os.path.join("search", "pages.json")
HEADING = re.compile(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", re.S | re.I)
# Pandoc draws plain-text tables with rules like +-----+ and =====, which are not words.
TABLE_RULE = re.compile(r"[-+=]{4,}")
SHARE_BAR = re.compile(r'<div class="share-bar-wrapper">.*?</div>\s*</div>', re.S)
CALL_TO_ACTION = re.compile(r'<p class="text-center">\s*<a class=\s*"btn[^>]*>.*?</a>\s*</p>', re.S)
PRE_BLOCK = re.compile(r"<pre\b([^>]*)>(.*?)</pre>", re.S | re.I)
LANGUAGES = {"haskell", "rust", "yaml", "bash", "javascript", "python", "c", "cpp", "sql", "diff",
             "dockerfile", "console", "xml", "toml", "lisp", "bat", "json", "nix", "text"}
LANGUAGE_ALIASES = {"haskel": "haskell", "sh": "bash", "shell": "bash", "shellsession": "console",
                    "batch": "bat"}
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]
REPOSITORY = "https://github.com/jappeace-sloth/fpcomplete-haskell-posts"
# Only archived at HubSpot's original path, which the academy URL does not reveal.
IMAGE_ORIGINALS = {
    "https://academy.fpblock.com/images/hubspot/fbb0f3b09a43ffc263893770aab947a304de9cb7d34cc7fc96f8a15e512bce13.jpeg":
        ["https://www.fpcomplete.com/hs-fs/hubfs/Blog/Software%20Bug%20-%20Small.jpg"
         "?width=320&name=Software%20Bug%20-%20Small.jpg"],
}


def load_manifest(repo):
    manifest = {}
    with open(os.path.join(repo, "manifest.tsv"), encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        for line_number, line in enumerate(handle, start=2):
            fields = line.rstrip("\n").split("\t")
            if len(fields) != len(header):
                raise SystemExit(f"manifest.tsv line {line_number}: {len(fields)} fields, header has {len(header)}")
            row = dict(zip(header, fields))
            manifest[row["dir"]] = row
    return manifest


def load_reading_list(repo):
    """Sections of reading-list.md as (heading, intro lines, page directories)."""
    sections = []
    with open(os.path.join(repo, "reading-list.md"), encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("## "):
                sections.append((line[3:], [], []))
            elif sections and line.startswith("|"):
                link = re.search(r"\]\(((?:blog|haskell)/[^)]*)/index\.txt\)", line)
                if link:
                    sections[-1][2].append(link.group(1))
            elif sections and line and not sections[-1][2]:
                sections[-1][1].append(line)
    if not sections:
        raise SystemExit("reading-list.md has no sections")
    return sections


def read_capture(repo, directory):
    raw = open(os.path.join(repo, directory, "index.html"), "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def first_marker(html, markers, start, directory):
    positions = [html.find(marker, start) for marker in markers]
    found = [position for position in positions if position >= 0]
    if not found:
        raise SystemExit(f"{directory}: none of {markers} after the body start")
    return min(found)


def extract_body(html, directory):
    """The article HTML without site chrome, for the four templates the captures use."""
    if "container my-5 blog-body" in html:
        share = SHARE_BAR.search(html, html.index("container my-5 blog-body"))
        if not share:
            raise SystemExit(f"{directory}: blog body without a share bar")
        end = first_marker(html, ['<p class="text-center spark-pricing-top"', '<p class="blog-contact"'],
                           share.end(), directory)
        return html[share.end():end]
    if '<div class="container py-3">' in html:
        start = html.index('<div class="container py-3">') + len('<div class="container py-3">')
        body = html[start:html.index("<footer", start)].rstrip()
        if not body.endswith("</div>"):
            raise SystemExit(f"{directory}: section page body does not close its container")
        return body[:-len("</div>")]
    if '<div class="site-main post-' in html:
        share = SHARE_BAR.search(html, html.index('<div class="site-main post-'))
        if not share:
            raise SystemExit(f"{directory}: WordPress post without a share bar")
        end = first_marker(html, ['<p class="text-center" style="border', '<div class="post-tags">'],
                           share.end(), directory)
        return html[share.end():end]
    if "<main>" in html:
        body = html[html.index("<main>") + len("<main>"):html.index("</main>")]
        body = re.sub(r"<h1>.*?</h1>", "", body, count=1, flags=re.S)
        body = re.sub(r'<p class="byline">.*?</p>', "", body, count=1, flags=re.S)
        return CALL_TO_ACTION.sub("", body)
    raise SystemExit(f"{directory}: unknown page template")


def code_language(attributes):
    tokens = re.findall(r'(?:class|data-lang|lang)=\s*"([^"]*)"', attributes)
    for token in " ".join(tokens).lower().split():
        name = token.removeprefix("language-").rstrip(":")
        name = LANGUAGE_ALIASES.get(name, name)
        if name in LANGUAGES:
            return name
    return None


def normalize_code_block(match):
    """Rebuild a <pre> as plain escaped text with one language class.

    The captures wrap code in highlighter spans (hscolour, syntect) and spread the
    language over pre, code, class and data-lang; pandoc only needs the text.
    """
    attributes, inner = match.group(1), match.group(2)
    code_tag = re.match(r"\s*<code\b([^>]*)>", inner)
    language = code_language(attributes + (code_tag.group(1) if code_tag else ""))
    if language is None:
        language = "haskell" if 'class="hs-' in inner or "class=\n\"hs-" in inner else "text"
    text = re.sub(r"<br\s*/?>", "\n", inner, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return f'<pre><code class="language-{language}">{text}</code></pre>'


def wayback_url(url, capture="2025"):
    return f"https://web.archive.org/web/{capture}/{url}"


def is_dead_fp_url(url):
    """True for FP Complete locations that no longer serve, so only the Wayback Machine has them."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname in FP_HOSTS or parsed.hostname in TUTORIAL_HOSTS:
        return True
    return parsed.hostname == "s3.amazonaws.com" and parsed.path.startswith("/download.fpcomplete.com/")


def site_target(url, site_pages):
    """The mirrored page directory an FP Complete URL points to, if it is mirrored."""
    parsed = urllib.parse.urlsplit(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname in TUTORIAL_HOSTS and parts and parts[0] in ("tutorial", "library"):
        candidate = "/".join(["haskell"] + parts)
    elif parsed.hostname not in FP_HOSTS:
        return None
    elif len(parts) >= 2 and parts[0] == "blog":
        candidate = f"blog/{parts[-1]}"
    elif parts and parts[0] == "haskell":
        candidate = "/".join(parts)
    else:
        return None
    return candidate if candidate in site_pages else None


def rewrite_link(href, page, site_pages):
    if href.startswith(("#", "mailto:", "javascript:")):
        return href
    absolute = urllib.parse.urljoin(page["original_url"], href)
    parsed = urllib.parse.urlsplit(absolute)
    if not is_dead_fp_url(absolute):
        return href
    target = site_target(absolute, site_pages)
    if target is None:
        return wayback_url(absolute)
    relative = posixpath.relpath(target, page["dir"]) + "/"
    return relative + (f"#{parsed.fragment}" if parsed.fragment else "")


def fetch_image(url, capture, destination):
    request = urllib.request.Request(f"https://web.archive.org/web/{capture}im_/{url}",
                                     headers={"User-Agent": "fpcomplete-haskell-posts mirror build"})
    # The Wayback Machine refuses connections for a while when it rate limits.
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                content_type = response.headers.get("Content-Type", "")
                data = response.read()
            break
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(30 * (attempt + 1))
    if not content_type.startswith("image/"):
        raise ValueError(f"got {content_type or 'no content type'}")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "wb") as handle:
        handle.write(data)


def image_candidates(absolute, srcset):
    """Archived URLs that may hold this image, best first.

    The academy site re-hosted images under new paths, and many of those were
    never captured, while the srcset variants or the same path on the older
    hosts often were.
    """
    candidates = [absolute] + [urllib.parse.urljoin(absolute, entry.split()[0])
                               for entry in srcset.split(",") if entry.strip()]
    for url in list(candidates):
        parsed = urllib.parse.urlsplit(url)
        for host in ("tech.fpcomplete.com", "www.fpcomplete.com"):
            if parsed.hostname != host:
                candidates.append(urllib.parse.urlunsplit(parsed._replace(netloc=host)))
    candidates += IMAGE_ORIGINALS.get(absolute, [])
    return list(dict.fromkeys(candidates))


def local_image(absolute, srcset, page, repo, failures):
    """Site-relative path of a downloaded copy, or a Wayback URL when no copy is archived."""
    name = posixpath.basename(urllib.parse.urlsplit(absolute).path) or "image"
    asset = posixpath.join("assets", page["dir"], name)
    destination = os.path.join(repo, SITE_DIR, asset)
    if not os.path.exists(destination):
        problems = []
        for candidate in image_candidates(absolute, srcset):
            try:
                fetch_image(candidate, page["capture"], destination)
                break
            except (urllib.error.URLError, TimeoutError, ValueError) as problem:
                problems.append(f"{candidate}: {problem}")
        else:
            failures.append(f"{page['dir']}: {absolute}: {'; '.join(problems)}")
            return wayback_url(absolute, page["capture"] + "im_")
    return posixpath.relpath(asset, page["dir"])


def rewrite_image_tag(match, page, repo, failures):
    tag = match.group(0)
    src = re.search(r'\ssrc=\s*"([^"]*)"', tag)
    if not src:
        raise SystemExit(f"{page['dir']}: image without src: {tag}")
    absolute = urllib.parse.urljoin(page["original_url"], src.group(1))
    if not is_dead_fp_url(absolute):
        return tag
    srcset = re.search(r'\ssrcset=\s*"([^"]*)"', tag)
    alt = re.search(r'\salt=\s*"([^"]*)"', tag)
    path = local_image(absolute, srcset.group(1) if srcset else "", page, repo, failures)
    return f'<img alt="{alt.group(1) if alt else ""}" src="{path}">'


def rewrite_references(body, page, site_pages, repo, failures):
    # Pandoc keeps a link as raw HTML when it has attributes Markdown cannot express.
    body = re.sub(r'(<a\b[^>]*?)\s(?:target|rel)=\s*"[^"]*"', r"\1", body, flags=re.S)
    body = re.sub(r'(<a\b[^>]*?)\s(?:target|rel)=\s*"[^"]*"', r"\1", body, flags=re.S)
    body = re.sub(r'(<a\b[^>]*?\shref=\s*")([^"]*)(")',
                  lambda m: m.group(1) + rewrite_link(m.group(2), page, site_pages) + m.group(3), body, flags=re.S)
    return re.sub(r"<img\b[^>]*>", lambda m: rewrite_image_tag(m, page, repo, failures), body, flags=re.S)


def fenced_block_count(markdown):
    """Fenced code blocks, where a block opened by N backticks closes only on N or more."""
    count = 0
    open_fence = None
    for line in markdown.splitlines():
        fence = re.match(r"(`{3,})\s*(\S*)\s*$", line.strip())
        if open_fence is None and fence:
            open_fence = fence.group(1)
            count += 1
        elif open_fence is not None and fence and not fence.group(2) and len(fence.group(1)) >= len(open_fence):
            open_fence = None
    return count


def to_markdown(body, directory):
    result = subprocess.run(["pandoc", "-f", "html-native_divs-native_spans", "-t", "gfm", "--wrap=none", "--no-highlight"],
                            input=body.encode("utf-8"), capture_output=True, check=True)
    markdown = result.stdout.decode("utf-8")
    # Code inside HTML tables (side by side comparisons) stays raw <pre> in GFM.
    converted = fenced_block_count(markdown) + len(re.findall(r"<pre\b", markdown))
    blocks = len(PRE_BLOCK.findall(body))
    if converted != blocks:
        raise SystemExit(f"{directory}: {blocks} code blocks in the HTML but {converted} in the Markdown")
    if "{% endraw %}" in markdown:
        raise SystemExit(f"{directory}: body contains a Liquid endraw tag")
    return markdown


def to_plain_text(body):
    """The page as one line of text, for the search index and its snippets."""
    result = subprocess.run(["pandoc", "-f", "html-native_divs-native_spans", "-t", "plain", "--wrap=none"],
                            input=body.encode("utf-8"), capture_output=True, check=True)
    return " ".join(TABLE_RULE.sub(" ", result.stdout.decode("utf-8")).split())


def heading_text(body):
    headings = [" ".join(unescape(re.sub(r"<[^>]+>", "", heading)).split()) for heading in HEADING.findall(body)]
    return " ".join(headings)


def display_date(date):
    parts = date.split("-")
    if len(parts) == 3:
        return f"{int(parts[2])} {MONTH_NAMES[int(parts[1]) - 1]} {parts[0]}"
    if len(parts) == 2:
        return f"{MONTH_NAMES[int(parts[1]) - 1]} {parts[0]}"
    raise SystemExit(f"unexpected date {date!r}")


def byline(page):
    """Author and date of a blog post; the Haskell section pages have neither."""
    if not page["dir"].startswith("blog/"):
        return ""
    return f"{page['author'] or 'unknown author'}, {display_date(page['date'])}"


def page_header(page):
    archived = wayback_url(page["original_url"], page["capture"])
    links = f"[original URL]({page['original_url']}) (offline), [Wayback Machine copy]({archived})"
    if page["dir"].startswith("blog/"):
        return f"*By {byline(page)}. Mirrored from FP Complete's blog: {links}.*"
    return f"*Mirrored from the Haskell section of FP Complete's site: {links}.*"


def write_page(repo, page, markdown):
    directory = os.path.join(repo, SITE_DIR, page["dir"])
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "index.md"), "w", encoding="utf-8") as handle:
        handle.write("---\nlayout: page\n")
        handle.write(f"title: {json.dumps(page['title'], ensure_ascii=False)}\n---\n")
        handle.write("{% raw %}\n" + page_header(page) + "\n\n" + markdown.rstrip() + "\n{% endraw %}\n")


def search_entry(identifier, page, section, body):
    return {"id": identifier, "path": page["dir"] + "/", "title": page["title"], "author": page["author"],
            "byline": byline(page), "section": section, "headings": heading_text(body),
            "text": to_plain_text(body)}


def write_search_pages(repo, entries):
    path = os.path.join(repo, SITE_DIR, SEARCH_PAGES)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def table_cell(text):
    return text.replace("|", "\\|")


def write_index(repo, sections, manifest):
    blog_count = sum(len([d for d in pages if d.startswith("blog/")]) for _, _, pages in sections)
    guide_count = sum(len([d for d in pages if d.startswith("haskell/")]) for _, _, pages in sections)
    lines = ["---", "layout: page", 'title: "FP Complete Haskell posts, mirrored"', "---", "{% raw %}",
             "This is an unofficial mirror. FP Complete's websites (www.fpcomplete.com, tech.fpcomplete.com "
             "and later academy.fpblock.com) are offline as of November 2026, so this site republishes their "
             "technical Haskell writing from Wayback Machine captures to keep it readable. It is not run by or "
             "affiliated with FP Complete or FP Block.", "",
             "The writing belongs to its authors. Every page names its author and links to its original URL "
             "and to the capture it was converted from. The conversion from HTML to Markdown can lose "
             "formatting, so check the capture when something looks off. If you wrote one of these posts and "
             f"want it corrected or taken down, please [open an issue]({REPOSITORY}/issues).", "",
             f"Only the technical posts are here: {blog_count} blog posts and {guide_count} tutorial and "
             "library pages. Product announcements, release notes, job ads, surveys and company posts are left "
             f"out. The [repository]({REPOSITORY}) keeps the raw captures of all 224 archived Haskell posts.", "",
             "The search box at the top searches the full text of every page here, code included."]
    for heading, intro, pages in sections:
        lines += ["", f"## {heading}", ""]
        if intro:
            lines += [" ".join(intro), ""]
        if pages[0].startswith("blog/"):
            lines += ["| Date | Title | Author |", "|---|---|---|"]
            for directory in pages:
                page = manifest[directory]
                lines.append(f"| {page['date']} | [{table_cell(page['title'])}]({directory}/) | "
                             f"{table_cell(page['author'])} |")
        else:
            lines += ["| Page | Title |", "|---|---|"]
            for directory in pages:
                lines.append(f"| `{directory}` | [{table_cell(manifest[directory]['title'])}]({directory}/) |")
    lines.append("{% endraw %}")
    with open(os.path.join(repo, SITE_DIR, "index.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    repo = sys.argv[1]
    manifest = load_manifest(repo)
    sections = load_reading_list(repo)
    site_pages = {directory for _, _, pages in sections for directory in pages}
    section_of = {directory: heading for heading, _, pages in sections for directory in pages}
    missing = sorted(site_pages - set(manifest))
    if missing:
        raise SystemExit(f"reading-list.md pages missing from manifest.tsv: {missing}")
    failures = []
    search_entries = []
    for directory in sorted(site_pages):
        page = manifest[directory]
        body = extract_body(read_capture(repo, directory), directory)
        body = PRE_BLOCK.sub(normalize_code_block, body)
        body = rewrite_references(body, page, site_pages, repo, failures)
        write_page(repo, page, to_markdown(body, directory))
        search_entries.append(search_entry(len(search_entries), page, section_of[directory], body))
    write_index(repo, sections, manifest)
    write_search_pages(repo, search_entries)
    print(f"wrote {len(site_pages)} pages, the index and {SEARCH_PAGES} to {SITE_DIR}/")
    for failure in failures:
        print("image not archived, linked to the Wayback Machine instead:", failure)


main()
