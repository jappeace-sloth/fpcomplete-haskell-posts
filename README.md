# FP Complete Haskell posts

Private archive of FP Complete's Haskell writing: 224 blog posts from 2012 to
2025 and 55 pages from the Haskell section of their site (tutorials, library
guides, getting started). Their Rust, devops, cloud, blockchain and company
posts are left out. The original sites (www.fpcomplete.com, tech.fpcomplete.com
and academy.fpblock.com) no longer resolve, so every page here is a Wayback
Machine capture. The text remains the work of its authors, which is why this
repository stays private.

Collected 7 and 8 Nov 2026 by cabal@lenovo-tablet.

## Reading

`reading-list.md` is the short way in: 83 technical blog posts grouped by
topic, plus the 41 tutorial and library pages. It skips product announcements,
release notes, job ads, surveys, webinar recaps and company essays.

`index.md` lists every blog post with its date, author and a Wayback link, and
every Haskell section page with its title and a Wayback link. The Haskell
section pages carry no byline, so they have no date or author.

For exceptions, read `blog/async-exception-handling-haskell` and
`haskell/tutorial/exceptions` first. The 2016 best practices post says it was
absorbed into that tutorial, and `haskell/library/safe-exceptions` recommends
`UnliftIO.Exception` instead, so the older exception posts are dated on that
point.

## Layout

Each page directory holds the raw capture as `index.html` and a `w3m -dump`
rendering as `index.txt`. Stylesheets and images were not archived.

- `blog/<slug>/`: one copy per post. When a post existed on several hosts, the
  academy.fpblock.com capture is used, falling back to tech.fpcomplete.com and
  then www.fpcomplete.com.
- `haskell/<path>/`: the Haskell section, mirroring its original URLs.
- `manifest.tsv`: directory, date, author, title, original URL, Wayback capture
  timestamp and why the page was selected.

Dates and authors come from the byline on the post. Four dates are set by hand:

- `blog/haskell-web-server-in-5mb` and `blog/specifying-dependencies` have no
  byline in their captures, so they get the month from the dated URL the post
  had on www.fpcomplete.com, and no author.
- `blog/bitrot-free-scripts` has a byline of August 11, 2015, but the post uses
  `lts-6.11`, which Stackage published on 2016-08-10, and its URL is
  `/blog/2016/08/`. It is dated 2016-08-11.
- `blog/haskell-from-c` has a byline of March 19, 2013, but it cites GHC ticket
  7954, opened on 2013-06-02, and its URL is `/blog/2013/06/`. It is dated
  2013-06, as the day is unknown.

On 14 other posts the `/blog/YYYY/MM/` URL month is later than the byline: by
one month on 12 posts and two months on 2. Their bylines are used; those posts
were not checked against their contents.

## Selection

`selected_by` in `manifest.tsv` says how each post got in:

- `haskell tag`: listed on academy.fpblock.com's own Haskell tag pages (157).
- `content review`: untagged, but about Haskell, its tooling or FP Complete's
  Haskell products such as FP Haskell Center, School of Haskell, Stackage and
  stack (67). Chosen by counting Haskell, Rust and other topic terms in each
  body and reading the opening of the borderline ones. This includes job ads
  for Haskell roles and Bartosz Milewski's 2012 posts on functional patterns in
  C++.

Left out after review although they touch on Haskell: "Is Rust functional?",
"Type Safety Doesn't Matter", "Docker demons: PID-1, orphans, zombies, and
signals", "Our history with containerization", "10 Common Mistakes to Avoid in
FinTech Software Development" and "FP Complete and Cardano Blockchain Audit
Partnership".

Not archived: six Haskell section URLs whose captures are "Page not found"
pages (among them `haskell/tutorial/exception-safety`), the mailing list signup
form, and three non-Haskell posts that the Wayback Machine failed to serve.

## Reopening a page

Use `https://web.archive.org/web/<capture>/<original URL>`, both from
`manifest.tsv`. Inserting `id_` after the capture timestamp returns the raw
bytes. Those bytes can be gzip-compressed, so use `curl --compressed` or check
for the gzip magic number.
