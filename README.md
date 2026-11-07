# FP Complete exception posts

Private archive of the FP Complete / FP Block writing on Haskell exceptions and
async exceptions. The original sites no longer resolve, so these copies come
from the Wayback Machine. The text remains the work of its authors, which is why
this repository stays private.

Collected 7 Nov 2026 by cabal@lenovo-tablet.

Read `academy/blog/2018/04/async-exception-handling-haskell` and
`academy/haskell/tutorial/exceptions` first. The 2016 best practices post says
it was absorbed into that tutorial, and FP's `safe-exceptions` page recommends
`UnliftIO.Exception` instead, so the older posts are dated on that point.

Each page directory holds the raw capture as `index.html` and a `w3m -dump`
rendering as `index.txt`. Stylesheets and images were not archived.

To reopen a page in the Wayback Machine, use
`https://web.archive.org/web/<capture>/<original URL>`. Inserting `id_` after the
capture timestamp returns the raw bytes. Those bytes can be gzip-compressed, so
use `curl --compressed` or check for the gzip magic number.

## academy.fpblock.com captures

The most recent versions, and the ones to prefer.

| Directory under `academy/` | Capture | Author, date |
|---|---|---|
| `blog/2018/04/async-exception-handling-haskell` | 20250405223544 | Michael Snoyman, Apr 2018 |
| `haskell/tutorial/exceptions` | 20250428060542 | undated |
| `blog/2016/11/exceptions-best-practices-haskell` | 20250512111457 | Michael Snoyman, Nov 2016 |
| `blog/2016/06/announce-safe-exceptions` | 20250717144712 | Michael Snoyman, Jun 2016 |
| `blog/2016/06/async-exceptions-stm-deadlocks` | 20250428055001 | Michael Snoyman, Jun 2016 |
| `blog/2017/06/tale-of-two-brackets` | 20250428053405 | Michael Snoyman, Jun 2017 |
| `blog/2017/02/monadmask-vs-monadbracket` | 20250624223553 | Michael Snoyman, Feb 2017 |
| `blog/2017/07/announcing-new-unliftio-library` | 20250428064002 | Michael Snoyman, Jul 2017 |
| `blog/2018/05/pinpointing-deadlocks-in-haskell` | 20250428060422 | Alexey Kuleshevich, May 2018 |
| `blog/async-exceptions-haskell-rust` | 20250611010103 | Michael Snoyman, Dec 2019 |
| `blog/defining-exceptions-in-haskell` | 20250428053629 | Chris Done, Jan 2019 |
| `blog/how-to-handle-asynchronous-exceptions-in-haskell` | 20250428055932 | Robert Bobbett, Apr 2018 (webinar announcement) |
| `haskell/library/async` | 20250515034200 | undated |
| `haskell/library/unliftio` | 20250717154604 | undated |
| `haskell/library/safe-exceptions` | 20250624224209 | undated (short notice only) |

The original URL is `https://academy.fpblock.com/<directory>/`.

The webinar itself is at <https://www.youtube.com/watch?v=T5y8sFmCFnA>.

## www.fpcomplete.com captures

Older captures, kept as a cross-check. `green-threads-are-like-garbage-collection`
and the `topic/` listing pages exist only here.

| Top-level directory | Capture |
|---|---|
| `async-exception-handling-haskell` | 20230925221523 |
| `exceptions-best-practices-haskell` | 20230921151031 |
| `announce-safe-exceptions` | 20230921161307 |
| `async-exceptions-stm-deadlocks` | 20230921161927 |
| `async-exceptions-haskell-rust` | 20200817090528 |
| `tale-of-two-brackets` | 20230925231804 |
| `monadmask-vs-monadbracket` | 20230926001856 |
| `green-threads-are-like-garbage-collection` | 20230925223421 |
| `defining-exceptions-in-haskell` | 20190201053541 |
| `how-to-handle-asynchronous-exceptions-in-haskell` | 20180414082213 |
| `topic/async-exceptions` | 20190721063231 |
| `topic/asynchronous-exception-handling` | 20190721072620 |
| `topic/asynchronous-exceptions` | 20190721071836 |
| `topic/exception-safe-code` | 20190721064016 |

The original URL is `https://www.fpcomplete.com/blog/<directory>`, with a trailing
slash for the 2023 captures and the 2020 capture.
