# Reading list

The technical Haskell writing: 83 of the 224 archived blog posts, grouped by topic and oldest first, then 41 tutorial and library pages.
`index.md` lists everything.

Left out: announcements for FP Haskell Center, School of Haskell, Stackage and stack releases, job ads, competitions, surveys, webinar recaps, company essays, and Bartosz Milewski's posts on functional patterns in C++.

## Exceptions and resource safety

Start with the 2018 post and `haskell/tutorial/exceptions`. The 2016 best practices post says it was folded into that tutorial, and `haskell/library/safe-exceptions` now points to `UnliftIO.Exception`.

| Date | Title | Author | Archive |
|---|---|---|---|
| 2016-06-29 | [Announce: safe-exceptions, for async exception safety](blog/announce-safe-exceptions/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250717144712/https://academy.fpblock.com/blog/2016/06/announce-safe-exceptions/) |
| 2016-11-07 | [Exceptions Best Practices in Haskell](blog/exceptions-best-practices-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250512111457/https://academy.fpblock.com/blog/2016/11/exceptions-best-practices-haskell/) |
| 2017-02-06 | [MonadMask vs MonadBracket](blog/monadmask-vs-monadbracket/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250624223553/https://academy.fpblock.com/blog/2017/02/monadmask-vs-monadbracket/) |
| 2017-06-19 | [Understanding ResourceT](blog/understanding-resourcet/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428051050/https://academy.fpblock.com/blog/2017/06/understanding-resourcet/) |
| 2017-06-26 | [A Tale of Two Brackets](blog/tale-of-two-brackets/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428053405/https://academy.fpblock.com/blog/2017/06/tale-of-two-brackets/) |
| 2017-08-24 | [Exiting a Haskell process](blog/exiting-haskell-process/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428055044/https://academy.fpblock.com/blog/2017/08/exiting-haskell-process/) |
| 2018-04-26 | [Asynchronous Exception Handling in Haskell](blog/async-exception-handling-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250405223544/https://academy.fpblock.com/blog/2018/04/async-exception-handling-haskell/) |
| 2018-10-04 | [ResourceT: A necessary evil](blog/resourcet-necessary-evil/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250624224244/https://academy.fpblock.com/blog/2018/10/resourcet-necessary-evil/) |
| 2019-01-29 | [Defining exceptions in Haskell](blog/defining-exceptions-in-haskell/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250428053629/https://academy.fpblock.com/blog/defining-exceptions-in-haskell/) |
| 2019-12-24 | [Async Exceptions in Haskell, and Rust](blog/async-exceptions-haskell-rust/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250611010103/https://academy.fpblock.com/blog/async-exceptions-haskell-rust/) |
| 2020-11-30 | [Error handling is hard](blog/error-handling-is-hard/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250407180320/https://academy.fpblock.com/blog/error-handling-is-hard/) |

## Concurrency

| Date | Title | Author | Archive |
|---|---|---|---|
| 2016-06-20 | [async exceptions, STM, and deadlocks](blog/async-exceptions-stm-deadlocks/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428055001/https://academy.fpblock.com/blog/2016/06/async-exceptions-stm-deadlocks/) |
| 2016-11-22 | [Comparative Concurrency with Haskell](blog/comparative-concurrency-with-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250624231725/https://academy.fpblock.com/blog/2016/11/comparative-concurrency-with-haskell/) |
| 2016-12-07 | [Concurrency and Node](blog/concurrency-and-node/index.txt) | Andrew Rademacher | [wayback](https://web.archive.org/web/20191016163447/https://tech.fpcomplete.com/blog/2016/12/concurrency-and-node/) |
| 2017-01-06 | [Green Threads are like Garbage Collection](blog/green-threads-are-like-garbage-collection/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250624225337/https://academy.fpblock.com/blog/2017/01/green-threads-are-like-garbage-collection/) |
| 2018-05-09 | [Pinpointing deadlocks in Haskell](blog/pinpointing-deadlocks-in-haskell/index.txt) | Alexey Kuleshevich | [wayback](https://web.archive.org/web/20250428060422/https://academy.fpblock.com/blog/2018/05/pinpointing-deadlocks-in-haskell/) |
| 2020-01-27 | [Transformations on Applicative Concurrent Computations](blog/transformations-on-applicative-concurrent-computations/index.txt) | Román González | [wayback](https://web.archive.org/web/20250803104158/https://academy.fpblock.com/blog/transformations-on-applicative-concurrent-computations/) |

## Performance, strictness and memory

| Date | Title | Author | Archive |
|---|---|---|---|
| 2014-05-20 | [vectorBuilder: packed-representation yielding for conduit](blog/vectorbuilder-packed-conduit-yielding/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250803105441/https://academy.fpblock.com/blog/2014/07/vectorbuilder-packed-conduit-yielding/) |
| 2014-08-21 | [IAP: Speeding up conduit](blog/iap-speeding-up-conduit/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250429120437/https://academy.fpblock.com/blog/2014/08/iap-speeding-up-conduit/) |
| 2014-08-27 | [IAP: conduit stream fusion](blog/conduit-stream-fusion/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250429120352/https://academy.fpblock.com/blog/2014/08/conduit-stream-fusion/) |
| 2015-01-07 | [Announcing: mutable-containers 0.2](blog/announcing-mutable-containers-0-2/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250803113601/https://academy.fpblock.com/blog/2015/01/announcing-mutable-containers-0-2/) |
| 2015-02-17 | [Primitive Haskell](blog/primitive-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250624232242/https://academy.fpblock.com/blog/2015/02/primitive-haskell/) |
| 2015-04-27 | [Flame graphs for GHC time profiles with ghc-prof-flamegraph](blog/ghc-prof-flamegraph/index.txt) | Francesco Mazzoli | [wayback](https://web.archive.org/web/20250717151717/https://academy.fpblock.com/blog/2015/04/ghc-prof-flamegraph/) |
| 2016-03-14 | [Efficient binary serialization](blog/efficient-binary-serialization/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250625022106/https://academy.fpblock.com/blog/2016/03/efficient-binary-serialization/) |
| 2016-05-24 | [store: a new and efficient binary serialization library](blog/store-package/index.txt) | Michael Sloan | [wayback](https://web.archive.org/web/20250515023626/https://academy.fpblock.com/blog/2016/05/store-package/) |
| 2016-05-27 | [weigh: Measuring allocations in Haskell](blog/weigh-package/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250717161318/https://academy.fpblock.com/blog/2016/05/weigh-package/) |
| 2017-01-18 | [Speeding up a distributed computation in Haskell](blog/speeding-up-distributed-computation/index.txt) | Francesco Mazzoli | [wayback](https://web.archive.org/web/20250515034302/https://academy.fpblock.com/blog/2017/01/speeding-up-distributed-computation/) |
| 2017-08-28 | [All About Strictness](blog/all-about-strictness/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250803105015/https://academy.fpblock.com/blog/2017/09/all-about-strictness/) |
| 2018-03-15 | [Without performance tests, we will have a bad time, forever](blog/without-performance-tests-we-will-have-a-bad-time-forever/index.txt) | Niklas Hambüchen | [wayback](https://web.archive.org/web/20250515035451/https://academy.fpblock.com/blog/without-performance-tests-we-will-have-a-bad-time-forever/) |

## Application design and libraries

| Date | Title | Author | Archive |
|---|---|---|---|
| 2015-05-20 | [Call C functions from Haskell without bindings](blog/inline-c/index.txt) | Francesco Mazzoli | [wayback](https://web.archive.org/web/20250625011621/https://academy.fpblock.com/blog/2015/05/inline-c/) |
| 2017-02-24 | [The typed-process library](blog/typed-process/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20191016180756/https://tech.fpcomplete.com/blog/2017/02/typed-process/) |
| 2017-06-12 | [The ReaderT Design Pattern](blog/readert-design-pattern/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20191017034240/https://tech.fpcomplete.com/blog/2017/06/readert-design-pattern/) |
| 2017-07-17 | [Announcing: the new unliftio library](blog/announcing-new-unliftio-library/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428064002/https://academy.fpblock.com/blog/2017/07/announcing-new-unliftio-library/) |
| 2017-07-24 | [The RIO Monad](blog/the-rio-monad/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428045416/https://academy.fpblock.com/blog/2017/07/the-rio-monad/) |
| 2017-09-12 | [Cryptographic Hashing in Haskell](blog/cryptographic-hashing-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250625023524/https://academy.fpblock.com/blog/2017/09/cryptographic-hashing-haskell/) |
| 2017-12-28 | [Parsing command line arguments](blog/parsing-command-line-arguments/index.txt) | Tom Sydney Kerckhove | [wayback](https://web.archive.org/web/20250512154244/https://academy.fpblock.com/blog/2017/12/parsing-command-line-arguments/) |
| 2018-05-01 | [A new Haskell library for talking to ODBC databases](blog/haskell-library-talking-odbc-databases/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250624225234/https://academy.fpblock.com/blog/2018/05/haskell-library-talking-odbc-databases/) |
| 2020-02-12 | [Decimal Safety Right on The Money](blog/safe-decimal-right-on-the-money/index.txt) | Alexey Kuleshevich | [wayback](https://web.archive.org/web/20250717153139/https://academy.fpblock.com/blog/safe-decimal-right-on-the-money/) |

## Language and types

| Date | Title | Author | Archive |
|---|---|---|---|
| 2012-08-22 | [Ten Things You Should Know About Haskell Syntax](blog/ten-things-you-should-know-about-haskell-syntax/index.txt) | Bartosz Milewski | [wayback](https://web.archive.org/web/20250624221719/https://academy.fpblock.com/blog/2012/09/ten-things-you-should-know-about-haskell-syntax/) |
| 2013-03-04 | [Learning Haskell Through Koans](blog/learning-through-koans/index.txt) | Chad Scherrer | [wayback](https://web.archive.org/web/20250803122710/https://academy.fpblock.com/blog/2013/03/learning-through-koans/) |
| 2013-06 | [Haskell from C: Where are the for Loops?](blog/haskell-from-c/index.txt) | Chad Scherrer | [wayback](https://web.archive.org/web/20250515030559/https://academy.fpblock.com/blog/2013/06/haskell-from-c/) |
| 2016-11-09 | [Covariance and Contravariance](blog/covariance-contravariance/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428052151/https://academy.fpblock.com/blog/2016/11/covariance-contravariance/) |
| 2017-02-13 | [Immutability, Docker, and Haskell's ST type](blog/immutability-docker-haskells-st-type/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250515034959/https://academy.fpblock.com/blog/2017/02/immutability-docker-haskells-st-type/) |
| 2017-03-10 | [Partial patterns in do blocks: let vs return](blog/partial-patterns-do-blocks/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250717145907/https://academy.fpblock.com/blog/2017/03/partial-patterns-do-blocks/) |
| 2017-04-14 | [What pure functional programming is all about: Part 1](blog/pure-functional-programming/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250717154519/https://academy.fpblock.com/blog/2017/04/pure-functional-programming/) |
| 2017-05-01 | [What pure functional programming is all about: Part 2](blog/pure-functional-programming-part-2/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250428062659/https://academy.fpblock.com/blog/2017/05/pure-functional-programming-part-2/) |
| 2017-07-31 | [To Void or to void](blog/to-void-or-to-void/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250717154437/https://academy.fpblock.com/blog/2017/07/to-void-or-to-void/) |
| 2018-01-02 | [Weakly Typed Haskell](blog/weakly-typed-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250418033647/https://academy.fpblock.com/blog/2018/01/weakly-typed-haskell/) |
| 2019-12-30 | [Teaching Haskell with Duet](blog/teaching-haskell-with-duet/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250515035033/https://academy.fpblock.com/blog/teaching-haskell-with-duet/) |
| 2020-12-14 | [Pattern matching](blog/pattern-matching/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250515023340/https://academy.fpblock.com/blog/pattern-matching/) |
| 2021-05-25 | [Tying the Knot in Haskell](blog/tying-the-knot-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250515034612/https://academy.fpblock.com/blog/tying-the-knot-haskell/) |
| 2022-04-27 | [The Hidden Dangers of Haskell's Ratio Type](blog/hidden-dangers-of-ratio/index.txt) | Neil Mayhew | [wayback](https://web.archive.org/web/20220512202510/https://www.fpcomplete.com/blog/hidden-dangers-of-ratio/) |

## Testing

| Date | Title | Author | Archive |
|---|---|---|---|
| 2017-01-24 | [QuickCheck and Magic of Testing](blog/quickcheck/index.txt) | Alexey Kuleshevich | [wayback](https://web.archive.org/web/20250624221003/https://academy.fpblock.com/blog/2017/01/quickcheck/) |
| 2019-02-13 | [Randomization Testing for an SQL Translator](blog/randomization-testing-for-an-sql-translator/index.txt) | Alexey Kuleshevich | [wayback](https://web.archive.org/web/20250803121427/https://academy.fpblock.com/blog/randomization-testing-for-an-sql-translator/) |
| 2019-02-27 | [QuickCheck, Hedgehog, Validity](blog/quickcheck-hedgehog-validity/index.txt) | Tom Sydney Kerckhove | [wayback](https://web.archive.org/web/20250515032748/https://academy.fpblock.com/blog/quickcheck-hedgehog-validity/) |
| 2019-05-29 | [Faking SQL Server in Haskell](blog/faking-sql-server-in-haskell/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250428050548/https://academy.fpblock.com/blog/faking-sql-server-in-haskell/) |

## Web and Yesod

| Date | Title | Author | Archive |
|---|---|---|---|
| 2012-10-01 | [Yesod Tutorial 1. My First Web Site](blog/yesod-tutorial-1-my-first-web-site/index.txt) | Bartosz Milewski | [wayback](https://web.archive.org/web/20250428063301/https://academy.fpblock.com/blog/2012/10/yesod-tutorial-1-my-first-web-site/) |
| 2012-10-01 | [Yesod Tutorial 2. Playing with Routes and Links](blog/yesod-tutorial-2-playing-with-routes-and-links/index.txt) | Bartosz Milewski | [wayback](https://web.archive.org/web/20250717144106/https://academy.fpblock.com/blog/2012/10/yesod-tutorial-2-playing-with-routes-and-links/) |
| 2021-04-26 | [The Pains of Path Parsing](blog/pains-path-parsing/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250515040231/https://academy.fpblock.com/blog/pains-path-parsing/) |

## Practical programs, scripts and files

| Date | Title | Author | Archive |
|---|---|---|---|
| 2014-03-20 | [Monte carlo analysis in Haskell](blog/monte-carlo-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428060738/https://academy.fpblock.com/blog/2014/03/monte-carlo-haskell/) |
| 2016-08-11 | [Practical Haskell: Bitrot-free Scripts](blog/bitrot-free-scripts/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250624215514/https://academy.fpblock.com/blog/2016/08/bitrot-free-scripts/) |
| 2016-09-14 | [Practical Haskell: Simple File Mirror (Part 1)](blog/practical-haskell-simple-file-mirror-1/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250515041901/https://academy.fpblock.com/blog/2016/09/practical-haskell-simple-file-mirror-1/) |
| 2016-09-14 | [Working with data in Haskell](blog/data-haskell/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250428054329/https://academy.fpblock.com/blog/2016/09/data-haskell/) |
| 2016-09-21 | [Practical Haskell: Simple File Mirror (Part 2)](blog/practical-haskell-simple-file-mirror-2/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250624214347/https://academy.fpblock.com/blog/2016/09/practical-haskell-simple-file-mirror-2/) |
| 2016-11-22 | [Scripting in Haskell](blog/scripting-in-haskell/index.txt) | Chris Done | [wayback](https://web.archive.org/web/20250624224433/https://academy.fpblock.com/blog/2016/11/scripting-in-haskell/) |
| 2019-03-12 | [Enhancing File Durability in Your Programs](blog/enhancing-file-durability-in-programs/index.txt) | Roman Gonzalez | [wayback](https://web.archive.org/web/20250624220241/https://academy.fpblock.com/blog/enhancing-file-durability-in-programs/) |
| 2019-07-01 | [When children processes exit - a debugging story](blog/when-children-processes-exit-debugging-story/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428062817/https://academy.fpblock.com/blog/when-children-processes-exit-debugging-story/) |

## Building and deploying

| Date | Title | Author | Archive |
|---|---|---|---|
| 2015-05 | [Haskell Web Server in a 5MB Docker Image](blog/haskell-web-server-in-5mb/index.txt) |  | [wayback](https://web.archive.org/web/20230921162946/https://www.fpcomplete.com/blog/haskell-web-server-in-5mb/) |
| 2015-12-15 | [The split-image approach to building minimal runtime Docker images](blog/docker-split-images/index.txt) | Emanuel Borsboom | [wayback](https://web.archive.org/web/20250428053934/https://academy.fpblock.com/blog/2015/12/docker-split-images/) |
| 2016-10-07 | [Static compilation with Stack](blog/static-compilation-with-stack/index.txt) | Tim Dysinger | [wayback](https://web.archive.org/web/20250512143449/https://academy.fpblock.com/blog/2016/10/static-compilation-with-stack/) |
| 2017-07-13 | [Stack's New Extensible Snapshots](blog/stacks-new-extensible-snapshots/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250515040711/https://academy.fpblock.com/blog/2017/07/stacks-new-extensible-snapshots/) |
| 2017-12-21 | [Building Haskell Apps with Docker](blog/building-haskell-apps-with-docker/index.txt) | Deni Bertovic | [wayback](https://web.archive.org/web/20250512143808/https://academy.fpblock.com/blog/2017/12/building-haskell-apps-with-docker/) |
| 2018-07-19 | [Pantry, part 1: The Package Index](blog/pantry-part-1-package-index/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250625023830/https://academy.fpblock.com/blog/2018/07/pantry-part-1-package-index/) |
| 2018-07-23 | [Pantry, part 2: Trees and keys](blog/pantry-part-2-trees-keys/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428052103/https://academy.fpblock.com/blog/2018/07/pantry-part-2-trees-keys/) |
| 2018-08 | [Pantry, part 3: Specifying Dependencies](blog/specifying-dependencies/index.txt) |  | [wayback](https://web.archive.org/web/20230921162443/https://www.fpcomplete.com/blog/specifying-dependencies/) |
| 2018-08-23 | [Haskell Development Workflows (4 ways)](blog/haskell-development-workflows-4-ways/index.txt) | Roman Gonzalez | [wayback](https://web.archive.org/web/20250624215423/https://academy.fpblock.com/blog/2018/08/haskell-development-workflows-4-ways/) |
| 2020-03-04 | [Storing generated cabal files](blog/storing-generated-cabal-files/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250428053026/https://academy.fpblock.com/blog/storing-generated-cabal-files/) |

## Haskell and Rust

| Date | Title | Author | Archive |
|---|---|---|---|
| 2017-07-10 | [Iterators and Streams in Rust and Haskell](blog/iterators-streams-rust-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250418040740/https://academy.fpblock.com/blog/2017/07/iterators-streams-rust-haskell/) |
| 2018-07-30 | [Streaming UTF-8 in Haskell and Rust](blog/streaming-utf8-haskell-rust/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250611010103/https://academy.fpblock.com/blog/2018/07/streaming-utf8-haskell-rust/) |
| 2019-01-17 | [When Rust is safer than Haskell](blog/when-rust-is-safer-than-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250717153212/https://academy.fpblock.com/blog/when-rust-is-safer-than-haskell/) |
| 2020-10-06 | [Collect in Rust, traverse in Haskell and Scala](blog/collect-rust-traverse-haskell-scala/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250611010103/https://academy.fpblock.com/blog/collect-rust-traverse-haskell-scala/) |
| 2021-01-11 | [Philosophies of Rust and Haskell](blog/philosophies-rust-haskell/index.txt) | Michael Snoyman | [wayback](https://web.archive.org/web/20250512150335/https://academy.fpblock.com/blog/philosophies-rust-haskell/) |
| 2025-06-30 | [Reflections on Haskell and Rust](blog/rust-haskell-reflections/index.txt) | Sibi Prabakaran | [wayback](https://web.archive.org/web/20251113171824/https://academy.fpblock.com/blog/rust-haskell-reflections/) |

## Tutorials and library guides

From the Haskell section of the site. These pages have no byline, so no date or author.

| Page | Title | Archive |
|---|---|---|
| `haskell/library/aeson` | [aeson: Working with JSON data](haskell/library/aeson/index.txt) | [wayback](https://web.archive.org/web/20250624233204/https://academy.fpblock.com/haskell/library/aeson/) |
| `haskell/library/async` | [async: Asynchronous and Concurrent Programming](haskell/library/async/index.txt) | [wayback](https://web.archive.org/web/20250515034200/https://academy.fpblock.com/haskell/library/async/) |
| `haskell/library/binary` | [binary: Serializing data](haskell/library/binary/index.txt) | [wayback](https://web.archive.org/web/20250409174957/https://academy.fpblock.com/haskell/library/binary/) |
| `haskell/library/conduit` | [conduit: Streaming data](haskell/library/conduit/index.txt) | [wayback](https://web.archive.org/web/20250428061539/https://academy.fpblock.com/haskell/library/conduit/) |
| `haskell/library/containers` | [containers: Maps, Sets, and more](haskell/library/containers/index.txt) | [wayback](https://web.archive.org/web/20250428045206/https://academy.fpblock.com/haskell/library/containers/) |
| `haskell/library/gauge` | [gauge: Benchmarking](haskell/library/gauge/index.txt) | [wayback](https://web.archive.org/web/20250624231654/https://academy.fpblock.com/haskell/library/gauge/) |
| `haskell/library/hspec` | [hspec: Testing framework](haskell/library/hspec/index.txt) | [wayback](https://web.archive.org/web/20250717160900/https://academy.fpblock.com/haskell/library/hspec/) |
| `haskell/library/http-client` | [http-client: Making HTTP requests](haskell/library/http-client/index.txt) | [wayback](https://web.archive.org/web/20250428043931/https://academy.fpblock.com/haskell/library/http-client/) |
| `haskell/library/optparse-applicative` | [optparse-applicative: Command line options parsing](haskell/library/optparse-applicative/index.txt) | [wayback](https://web.archive.org/web/20250624222450/https://academy.fpblock.com/haskell/library/optparse-applicative/) |
| `haskell/library/rio` | [rio: A standard library](haskell/library/rio/index.txt) | [wayback](https://web.archive.org/web/20250423141947/https://academy.fpblock.com/haskell/library/rio/) |
| `haskell/library/safe-exceptions` | [safe-exceptions: Safe and simple exception handling](haskell/library/safe-exceptions/index.txt) | [wayback](https://web.archive.org/web/20250624224209/https://academy.fpblock.com/haskell/library/safe-exceptions/) |
| `haskell/library/stm` | [stm: Software Transactional Memory](haskell/library/stm/index.txt) | [wayback](https://web.archive.org/web/20250624215209/https://academy.fpblock.com/haskell/library/stm/) |
| `haskell/library/transformers` | [transformers: Monad transformers](haskell/library/transformers/index.txt) | [wayback](https://web.archive.org/web/20250620223120/https://academy.fpblock.com/haskell/library/transformers/) |
| `haskell/library/typed-process` | [typed-process: Run and interact with child processes](haskell/library/typed-process/index.txt) | [wayback](https://web.archive.org/web/20250516015324/https://academy.fpblock.com/haskell/library/typed-process/) |
| `haskell/library/unliftio` | [unliftio: Lifting and unlifting IO actions](haskell/library/unliftio/index.txt) | [wayback](https://web.archive.org/web/20250717154604/https://academy.fpblock.com/haskell/library/unliftio/) |
| `haskell/library/vector` | [vector: Efficient Packed-Memory Data Representations](haskell/library/vector/index.txt) | [wayback](https://web.archive.org/web/20250418032440/https://academy.fpblock.com/haskell/library/vector/) |
| `haskell/library/weigh` | [weigh: Memory benchmarking](haskell/library/weigh/index.txt) | [wayback](https://web.archive.org/web/20250803122039/https://academy.fpblock.com/haskell/library/weigh/) |
| `haskell/library/yaml` | [yaml: Parsing and rendering YAML](haskell/library/yaml/index.txt) | [wayback](https://web.archive.org/web/20250515033126/https://academy.fpblock.com/haskell/library/yaml/) |
| `haskell/syllabus` | [Applied Haskell Syllabus](haskell/syllabus/index.txt) | [wayback](https://web.archive.org/web/20190917121627/https://tech.fpcomplete.com/haskell/syllabus/) |
| `haskell/tutorial/all-about-strictness` | [All about strictness](haskell/tutorial/all-about-strictness/index.txt) | [wayback](https://web.archive.org/web/20250505215557/https://academy.fpblock.com/haskell/tutorial/all-about-strictness/) |
| `haskell/tutorial/applicative-syntax` | [Crash Course to Applicative Syntax](haskell/tutorial/applicative-syntax/index.txt) | [wayback](https://web.archive.org/web/20250624233349/https://academy.fpblock.com/haskell/tutorial/applicative-syntax/) |
| `haskell/tutorial/applied-haskell-101` | [Applied Haskell 101](haskell/tutorial/applied-haskell-101/index.txt) | [wayback](https://web.archive.org/web/20250428052521/https://academy.fpblock.com/haskell/tutorial/applied-haskell-101/) |
| `haskell/tutorial/best-practices` | [Haskell Best Practices](haskell/tutorial/best-practices/index.txt) | [wayback](https://web.archive.org/web/20190916083952/https://tech.fpcomplete.com/haskell/tutorial/best-practices/) |
| `haskell/tutorial/common-typeclasses` | [Common Typeclasses](haskell/tutorial/common-typeclasses/index.txt) | [wayback](https://web.archive.org/web/20250428061300/https://academy.fpblock.com/haskell/tutorial/common-typeclasses/) |
| `haskell/tutorial/data-structures` | [Data Structures](haskell/tutorial/data-structures/index.txt) | [wayback](https://web.archive.org/web/20250624225409/https://academy.fpblock.com/haskell/tutorial/data-structures/) |
| `haskell/tutorial/data-types` | [Data types](haskell/tutorial/data-types/index.txt) | [wayback](https://web.archive.org/web/20250428054111/https://academy.fpblock.com/haskell/tutorial/data-types/) |
| `haskell/tutorial/exceptions` | [Safe exception handling](haskell/tutorial/exceptions/index.txt) | [wayback](https://web.archive.org/web/20250428060542/https://academy.fpblock.com/haskell/tutorial/exceptions/) |
| `haskell/tutorial/fundeps` | [Functional Dependencies](haskell/tutorial/fundeps/index.txt) | [wayback](https://web.archive.org/web/20250620095825/https://academy.fpblock.com/haskell/tutorial/fundeps/) |
| `haskell/tutorial/lens` | [Lenses](haskell/tutorial/lens/index.txt) | [wayback](https://web.archive.org/web/20250427123149/https://academy.fpblock.com/haskell/tutorial/lens/) |
| `haskell/tutorial/libraries` | [Recommended Haskell libraries](haskell/tutorial/libraries/index.txt) | [wayback](https://web.archive.org/web/20250515032227/https://academy.fpblock.com/haskell/tutorial/libraries/) |
| `haskell/tutorial/monad-transformers` | [Monad Transformers](haskell/tutorial/monad-transformers/index.txt) | [wayback](https://web.archive.org/web/20201001014001/https://www.fpcomplete.com/haskell/tutorial/monad-transformers/) |
| `haskell/tutorial/mutable-variables` | [Mutable variables](haskell/tutorial/mutable-variables/index.txt) | [wayback](https://web.archive.org/web/20250428060620/https://academy.fpblock.com/haskell/tutorial/mutable-variables/) |
| `haskell/tutorial/operators` | [Operator Glossary](haskell/tutorial/operators/index.txt) | [wayback](https://web.archive.org/web/20190916080428/https://tech.fpcomplete.com/haskell/tutorial/operators/) |
| `haskell/tutorial/primitive-haskell` | [Primitive Haskell](haskell/tutorial/primitive-haskell/index.txt) | [wayback](https://web.archive.org/web/20250803115303/https://academy.fpblock.com/haskell/tutorial/primitive-haskell/) |
| `haskell/tutorial/profiling` | [Profiling and Performance](haskell/tutorial/profiling/index.txt) | [wayback](https://web.archive.org/web/20250624220442/https://academy.fpblock.com/haskell/tutorial/profiling/) |
| `haskell/tutorial/stack-build` | [How to Build with Stack](haskell/tutorial/stack-build/index.txt) | [wayback](https://web.archive.org/web/20250407111021/https://academy.fpblock.com/haskell/tutorial/stack-build/) |
| `haskell/tutorial/stack-play` | [How to Play with Stack](haskell/tutorial/stack-play/index.txt) | [wayback](https://web.archive.org/web/20250515024751/https://academy.fpblock.com/haskell/tutorial/stack-play/) |
| `haskell/tutorial/stack-script` | [How to Script with Stack](haskell/tutorial/stack-script/index.txt) | [wayback](https://web.archive.org/web/20250514094552/https://academy.fpblock.com/haskell/tutorial/stack-script/) |
| `haskell/tutorial/string-types` | [String Types](haskell/tutorial/string-types/index.txt) | [wayback](https://web.archive.org/web/20250624224511/https://academy.fpblock.com/haskell/tutorial/string-types/) |
| `haskell/tutorial/synonyms` | [Synonyms in base](haskell/tutorial/synonyms/index.txt) | [wayback](https://web.archive.org/web/20250624231450/https://academy.fpblock.com/haskell/tutorial/synonyms/) |
| `haskell/tutorial/web-services` | [Web Services](haskell/tutorial/web-services/index.txt) | [wayback](https://web.archive.org/web/20250515041624/https://academy.fpblock.com/haskell/tutorial/web-services/) |
