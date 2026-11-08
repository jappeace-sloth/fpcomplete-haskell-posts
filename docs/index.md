---
layout: page
title: "FP Complete Haskell posts, mirrored"
---
{% raw %}
This is an unofficial mirror. FP Complete's websites (www.fpcomplete.com, tech.fpcomplete.com and later academy.fpblock.com) are offline as of November 2026, so this site republishes their technical Haskell writing from Wayback Machine captures to keep it readable. It is not run by or affiliated with FP Complete or FP Block.

The writing belongs to its authors. Every page names its author and links to its original URL and to the capture it was converted from. The conversion from HTML to Markdown can lose formatting, so check the capture when something looks off. If you wrote one of these posts and want it corrected or taken down, please [open an issue](https://github.com/jappeace-sloth/fpcomplete-haskell-posts/issues).

Only the technical posts are here: 83 blog posts and 41 tutorial and library pages. Product announcements, release notes, job ads, surveys and company posts are left out. The [repository](https://github.com/jappeace-sloth/fpcomplete-haskell-posts) keeps the raw captures of all 224 archived Haskell posts.

## Exceptions and resource safety

Start with the 2018 post and `haskell/tutorial/exceptions`. The 2016 best practices post says it was folded into that tutorial, and `haskell/library/safe-exceptions` now points to `UnliftIO.Exception`.

| Date | Title | Author |
|---|---|---|
| 2016-06-29 | [Announce: safe-exceptions, for async exception safety](blog/announce-safe-exceptions/) | Michael Snoyman |
| 2016-11-07 | [Exceptions Best Practices in Haskell](blog/exceptions-best-practices-haskell/) | Michael Snoyman |
| 2017-02-06 | [MonadMask vs MonadBracket](blog/monadmask-vs-monadbracket/) | Michael Snoyman |
| 2017-06-19 | [Understanding ResourceT](blog/understanding-resourcet/) | Michael Snoyman |
| 2017-06-26 | [A Tale of Two Brackets](blog/tale-of-two-brackets/) | Michael Snoyman |
| 2017-08-24 | [Exiting a Haskell process](blog/exiting-haskell-process/) | Michael Snoyman |
| 2018-04-26 | [Asynchronous Exception Handling in Haskell](blog/async-exception-handling-haskell/) | Michael Snoyman |
| 2018-10-04 | [ResourceT: A necessary evil](blog/resourcet-necessary-evil/) | Michael Snoyman |
| 2019-01-29 | [Defining exceptions in Haskell](blog/defining-exceptions-in-haskell/) | Chris Done |
| 2019-12-24 | [Async Exceptions in Haskell, and Rust](blog/async-exceptions-haskell-rust/) | Michael Snoyman |
| 2020-11-30 | [Error handling is hard](blog/error-handling-is-hard/) | Michael Snoyman |

## Concurrency

| Date | Title | Author |
|---|---|---|
| 2016-06-20 | [async exceptions, STM, and deadlocks](blog/async-exceptions-stm-deadlocks/) | Michael Snoyman |
| 2016-11-22 | [Comparative Concurrency with Haskell](blog/comparative-concurrency-with-haskell/) | Michael Snoyman |
| 2016-12-07 | [Concurrency and Node](blog/concurrency-and-node/) | Andrew Rademacher |
| 2017-01-06 | [Green Threads are like Garbage Collection](blog/green-threads-are-like-garbage-collection/) | Michael Snoyman |
| 2018-05-09 | [Pinpointing deadlocks in Haskell](blog/pinpointing-deadlocks-in-haskell/) | Alexey Kuleshevich |
| 2020-01-27 | [Transformations on Applicative Concurrent Computations](blog/transformations-on-applicative-concurrent-computations/) | Román González |

## Performance, strictness and memory

| Date | Title | Author |
|---|---|---|
| 2014-05-20 | [vectorBuilder: packed-representation yielding for conduit](blog/vectorbuilder-packed-conduit-yielding/) | Michael Snoyman |
| 2014-08-21 | [IAP: Speeding up conduit](blog/iap-speeding-up-conduit/) | Michael Snoyman |
| 2014-08-27 | [IAP: conduit stream fusion](blog/conduit-stream-fusion/) | Michael Snoyman |
| 2015-01-07 | [Announcing: mutable-containers 0.2](blog/announcing-mutable-containers-0-2/) | Michael Snoyman |
| 2015-02-17 | [Primitive Haskell](blog/primitive-haskell/) | Michael Snoyman |
| 2015-04-27 | [Flame graphs for GHC time profiles with ghc-prof-flamegraph](blog/ghc-prof-flamegraph/) | Francesco Mazzoli |
| 2016-03-14 | [Efficient binary serialization](blog/efficient-binary-serialization/) | Michael Snoyman |
| 2016-05-24 | [store: a new and efficient binary serialization library](blog/store-package/) | Michael Sloan |
| 2016-05-27 | [weigh: Measuring allocations in Haskell](blog/weigh-package/) | Chris Done |
| 2017-01-18 | [Speeding up a distributed computation in Haskell](blog/speeding-up-distributed-computation/) | Francesco Mazzoli |
| 2017-08-28 | [All About Strictness](blog/all-about-strictness/) | Michael Snoyman |
| 2018-03-15 | [Without performance tests, we will have a bad time, forever](blog/without-performance-tests-we-will-have-a-bad-time-forever/) | Niklas Hambüchen |

## Application design and libraries

| Date | Title | Author |
|---|---|---|
| 2015-05-20 | [Call C functions from Haskell without bindings](blog/inline-c/) | Francesco Mazzoli |
| 2017-02-24 | [The typed-process library](blog/typed-process/) | Michael Snoyman |
| 2017-06-12 | [The ReaderT Design Pattern](blog/readert-design-pattern/) | Michael Snoyman |
| 2017-07-17 | [Announcing: the new unliftio library](blog/announcing-new-unliftio-library/) | Michael Snoyman |
| 2017-07-24 | [The RIO Monad](blog/the-rio-monad/) | Michael Snoyman |
| 2017-09-12 | [Cryptographic Hashing in Haskell](blog/cryptographic-hashing-haskell/) | Michael Snoyman |
| 2017-12-28 | [Parsing command line arguments](blog/parsing-command-line-arguments/) | Tom Sydney Kerckhove |
| 2018-05-01 | [A new Haskell library for talking to ODBC databases](blog/haskell-library-talking-odbc-databases/) | Chris Done |
| 2020-02-12 | [Decimal Safety Right on The Money](blog/safe-decimal-right-on-the-money/) | Alexey Kuleshevich |

## Language and types

| Date | Title | Author |
|---|---|---|
| 2012-08-22 | [Ten Things You Should Know About Haskell Syntax](blog/ten-things-you-should-know-about-haskell-syntax/) | Bartosz Milewski |
| 2013-03-04 | [Learning Haskell Through Koans](blog/learning-through-koans/) | Chad Scherrer |
| 2013-06 | [Haskell from C: Where are the for Loops?](blog/haskell-from-c/) | Chad Scherrer |
| 2016-11-09 | [Covariance and Contravariance](blog/covariance-contravariance/) | Michael Snoyman |
| 2017-02-13 | [Immutability, Docker, and Haskell's ST type](blog/immutability-docker-haskells-st-type/) | Michael Snoyman |
| 2017-03-10 | [Partial patterns in do blocks: let vs return](blog/partial-patterns-do-blocks/) | Michael Snoyman |
| 2017-04-14 | [What pure functional programming is all about: Part 1](blog/pure-functional-programming/) | Chris Done |
| 2017-05-01 | [What pure functional programming is all about: Part 2](blog/pure-functional-programming-part-2/) | Chris Done |
| 2017-07-31 | [To Void or to void](blog/to-void-or-to-void/) | Michael Snoyman |
| 2018-01-02 | [Weakly Typed Haskell](blog/weakly-typed-haskell/) | Michael Snoyman |
| 2019-12-30 | [Teaching Haskell with Duet](blog/teaching-haskell-with-duet/) | Chris Done |
| 2020-12-14 | [Pattern matching](blog/pattern-matching/) | Michael Snoyman |
| 2021-05-25 | [Tying the Knot in Haskell](blog/tying-the-knot-haskell/) | Michael Snoyman |
| 2022-04-27 | [The Hidden Dangers of Haskell's Ratio Type](blog/hidden-dangers-of-ratio/) | Neil Mayhew |

## Testing

| Date | Title | Author |
|---|---|---|
| 2017-01-24 | [QuickCheck and Magic of Testing](blog/quickcheck/) | Alexey Kuleshevich |
| 2019-02-13 | [Randomization Testing for an SQL Translator](blog/randomization-testing-for-an-sql-translator/) | Alexey Kuleshevich |
| 2019-02-27 | [QuickCheck, Hedgehog, Validity](blog/quickcheck-hedgehog-validity/) | Tom Sydney Kerckhove |
| 2019-05-29 | [Faking SQL Server in Haskell](blog/faking-sql-server-in-haskell/) | Chris Done |

## Web and Yesod

| Date | Title | Author |
|---|---|---|
| 2012-10-01 | [Yesod Tutorial 1. My First Web Site](blog/yesod-tutorial-1-my-first-web-site/) | Bartosz Milewski |
| 2012-10-01 | [Yesod Tutorial 2. Playing with Routes and Links](blog/yesod-tutorial-2-playing-with-routes-and-links/) | Bartosz Milewski |
| 2021-04-26 | [The Pains of Path Parsing](blog/pains-path-parsing/) | Michael Snoyman |

## Practical programs, scripts and files

| Date | Title | Author |
|---|---|---|
| 2014-03-20 | [Monte carlo analysis in Haskell](blog/monte-carlo-haskell/) | Michael Snoyman |
| 2016-08-11 | [Practical Haskell: Bitrot-free Scripts](blog/bitrot-free-scripts/) | Michael Snoyman |
| 2016-09-14 | [Practical Haskell: Simple File Mirror (Part 1)](blog/practical-haskell-simple-file-mirror-1/) | Michael Snoyman |
| 2016-09-14 | [Working with data in Haskell](blog/data-haskell/) | Chris Done |
| 2016-09-21 | [Practical Haskell: Simple File Mirror (Part 2)](blog/practical-haskell-simple-file-mirror-2/) | Michael Snoyman |
| 2016-11-22 | [Scripting in Haskell](blog/scripting-in-haskell/) | Chris Done |
| 2019-03-12 | [Enhancing File Durability in Your Programs](blog/enhancing-file-durability-in-programs/) | Roman Gonzalez |
| 2019-07-01 | [When children processes exit - a debugging story](blog/when-children-processes-exit-debugging-story/) | Michael Snoyman |

## Building and deploying

| Date | Title | Author |
|---|---|---|
| 2015-05 | [Haskell Web Server in a 5MB Docker Image](blog/haskell-web-server-in-5mb/) |  |
| 2015-12-15 | [The split-image approach to building minimal runtime Docker images](blog/docker-split-images/) | Emanuel Borsboom |
| 2016-10-07 | [Static compilation with Stack](blog/static-compilation-with-stack/) | Tim Dysinger |
| 2017-07-13 | [Stack's New Extensible Snapshots](blog/stacks-new-extensible-snapshots/) | Michael Snoyman |
| 2017-12-21 | [Building Haskell Apps with Docker](blog/building-haskell-apps-with-docker/) | Deni Bertovic |
| 2018-07-19 | [Pantry, part 1: The Package Index](blog/pantry-part-1-package-index/) | Michael Snoyman |
| 2018-07-23 | [Pantry, part 2: Trees and keys](blog/pantry-part-2-trees-keys/) | Michael Snoyman |
| 2018-08 | [Pantry, part 3: Specifying Dependencies](blog/specifying-dependencies/) |  |
| 2018-08-23 | [Haskell Development Workflows (4 ways)](blog/haskell-development-workflows-4-ways/) | Roman Gonzalez |
| 2020-03-04 | [Storing generated cabal files](blog/storing-generated-cabal-files/) | Michael Snoyman |

## Haskell and Rust

| Date | Title | Author |
|---|---|---|
| 2017-07-10 | [Iterators and Streams in Rust and Haskell](blog/iterators-streams-rust-haskell/) | Michael Snoyman |
| 2018-07-30 | [Streaming UTF-8 in Haskell and Rust](blog/streaming-utf8-haskell-rust/) | Michael Snoyman |
| 2019-01-17 | [When Rust is safer than Haskell](blog/when-rust-is-safer-than-haskell/) | Michael Snoyman |
| 2020-10-06 | [Collect in Rust, traverse in Haskell and Scala](blog/collect-rust-traverse-haskell-scala/) | Michael Snoyman |
| 2021-01-11 | [Philosophies of Rust and Haskell](blog/philosophies-rust-haskell/) | Michael Snoyman |
| 2025-06-30 | [Reflections on Haskell and Rust](blog/rust-haskell-reflections/) | Sibi Prabakaran |

## Tutorials and library guides

From the Haskell section of the site. These pages have no byline, so no date or author.

| Page | Title |
|---|---|
| `haskell/library/aeson` | [aeson: Working with JSON data](haskell/library/aeson/) |
| `haskell/library/async` | [async: Asynchronous and Concurrent Programming](haskell/library/async/) |
| `haskell/library/binary` | [binary: Serializing data](haskell/library/binary/) |
| `haskell/library/conduit` | [conduit: Streaming data](haskell/library/conduit/) |
| `haskell/library/containers` | [containers: Maps, Sets, and more](haskell/library/containers/) |
| `haskell/library/gauge` | [gauge: Benchmarking](haskell/library/gauge/) |
| `haskell/library/hspec` | [hspec: Testing framework](haskell/library/hspec/) |
| `haskell/library/http-client` | [http-client: Making HTTP requests](haskell/library/http-client/) |
| `haskell/library/optparse-applicative` | [optparse-applicative: Command line options parsing](haskell/library/optparse-applicative/) |
| `haskell/library/rio` | [rio: A standard library](haskell/library/rio/) |
| `haskell/library/safe-exceptions` | [safe-exceptions: Safe and simple exception handling](haskell/library/safe-exceptions/) |
| `haskell/library/stm` | [stm: Software Transactional Memory](haskell/library/stm/) |
| `haskell/library/transformers` | [transformers: Monad transformers](haskell/library/transformers/) |
| `haskell/library/typed-process` | [typed-process: Run and interact with child processes](haskell/library/typed-process/) |
| `haskell/library/unliftio` | [unliftio: Lifting and unlifting IO actions](haskell/library/unliftio/) |
| `haskell/library/vector` | [vector: Efficient Packed-Memory Data Representations](haskell/library/vector/) |
| `haskell/library/weigh` | [weigh: Memory benchmarking](haskell/library/weigh/) |
| `haskell/library/yaml` | [yaml: Parsing and rendering YAML](haskell/library/yaml/) |
| `haskell/syllabus` | [Applied Haskell Syllabus](haskell/syllabus/) |
| `haskell/tutorial/all-about-strictness` | [All about strictness](haskell/tutorial/all-about-strictness/) |
| `haskell/tutorial/applicative-syntax` | [Crash Course to Applicative Syntax](haskell/tutorial/applicative-syntax/) |
| `haskell/tutorial/applied-haskell-101` | [Applied Haskell 101](haskell/tutorial/applied-haskell-101/) |
| `haskell/tutorial/best-practices` | [Haskell Best Practices](haskell/tutorial/best-practices/) |
| `haskell/tutorial/common-typeclasses` | [Common Typeclasses](haskell/tutorial/common-typeclasses/) |
| `haskell/tutorial/data-structures` | [Data Structures](haskell/tutorial/data-structures/) |
| `haskell/tutorial/data-types` | [Data types](haskell/tutorial/data-types/) |
| `haskell/tutorial/exceptions` | [Safe exception handling](haskell/tutorial/exceptions/) |
| `haskell/tutorial/fundeps` | [Functional Dependencies](haskell/tutorial/fundeps/) |
| `haskell/tutorial/lens` | [Lenses](haskell/tutorial/lens/) |
| `haskell/tutorial/libraries` | [Recommended Haskell libraries](haskell/tutorial/libraries/) |
| `haskell/tutorial/monad-transformers` | [Monad Transformers](haskell/tutorial/monad-transformers/) |
| `haskell/tutorial/mutable-variables` | [Mutable variables](haskell/tutorial/mutable-variables/) |
| `haskell/tutorial/operators` | [Operator Glossary](haskell/tutorial/operators/) |
| `haskell/tutorial/primitive-haskell` | [Primitive Haskell](haskell/tutorial/primitive-haskell/) |
| `haskell/tutorial/profiling` | [Profiling and Performance](haskell/tutorial/profiling/) |
| `haskell/tutorial/stack-build` | [How to Build with Stack](haskell/tutorial/stack-build/) |
| `haskell/tutorial/stack-play` | [How to Play with Stack](haskell/tutorial/stack-play/) |
| `haskell/tutorial/stack-script` | [How to Script with Stack](haskell/tutorial/stack-script/) |
| `haskell/tutorial/string-types` | [String Types](haskell/tutorial/string-types/) |
| `haskell/tutorial/synonyms` | [Synonyms in base](haskell/tutorial/synonyms/) |
| `haskell/tutorial/web-services` | [Web Services](haskell/tutorial/web-services/) |
{% endraw %}
