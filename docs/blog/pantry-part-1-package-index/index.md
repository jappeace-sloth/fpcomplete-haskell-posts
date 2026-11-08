---
layout: page
title: "Pantry, part 1: The Package Index"
---
{% raw %}
*By Michael Snoyman, 19 July 2018. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2018/07/pantry-part-1-package-index/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250625023830/https://academy.fpblock.com/blog/2018/07/pantry-part-1-package-index/).*

Back in January, I published a [two](https://web.archive.org/web/2025/https://academy.fpblock.com/blog/2018/01/hash-based-package-downloads-part-1-of-2) [part](https://web.archive.org/web/2025/https://academy.fpblock.com/blog/2018/01/hash-based-package-downloads-part-2-of-2) blog post on hash-based package downloads. Some project needs at FP Complete have pushed this to the forefront recently, and as a result I've gotten started on implementing these ideas. I'm hoping to publish regular blog posts on the topic as I continue implementation.

There are a few major goals in the refactoring I'm working on:

- Increased security and reproducibility of build plans
- More shared code across tooling (especially Stackage and Stack)
- Performance improvements (especially in Stack)
- More flexibility for the Stackage team

Today's post won't hit on all of these points, as I'm only going to discuss the first bit of rewrite I've completed: package index management. This work is occurring on the pantry branch of Stack, though you should be well aware that that branch is currently totally unusable outside of the `stack update` command.

## What's a package index?

A package index is a term that comes from the Cabal and Hackage worlds. Hackage itself provides a package index, and `cabal-install` and Stack both download this index to discover packages. The index itself is a tarball (the `01-index.tar` file) containing a single cabal file for each revision of a package/version combination. It also contains some other metadata files, like JSON files providing cryptographic hash information on package tarballs. The `01-index.tar` file is intended to be downloaded by [hackage-security](https://github.com/haskell/hackage-security), which provides both security (signature checking and other protections) and resumable downloads.

## The need for an index

In its common use case, Stack discovers available packages via a snapshot configuration (e.g., `lts-12.0`), which tells it the name, version, and Hackage revision of any package available. As a result, it may seem like Stack doesn't really need the package index. However, it's still necessary for a few things:

- It's the only location for downloading the revised cabal files from Hackage
- When displaying error messages, we sometimes want to provide helpful information on the latest versions available on Hackage
- When using the solver from `cabal-install`, we must have an index available so that the solver can discover new packages

Stack will automatically download the index today when needed (e.g., a snapshot refers to a revision not yet downloaded locally), and can be told to explicitly download a new index via `stack update`. Because it is highly inefficient to traverse the tarball each time a lookup needs to occur, Stack will also create a cache file mapping package name/version/revision to the offset inside the tarball that it is located.

## Configurable indices

Stack—like `cabal-install`—allows alternative package indices to be specified. One use case for this is the “corporate firewall” situation (though it applies to other cases too). Some companies have restrictive firewalls in place which block outgoing connections. Or, alternatively, bandwidth may be throttled, and a local mirror would be preferable. Either way, configuring an alternative location to download the Hackage package index from is case 1. To get ahead of myself a bit: there's no problem with this use case, and Stack will continue to support configurable mirror location.

The second case is for providing access to packages which are not on Hackage. I've [used this approach in the past](https://www.stackage.org/package/yackage) myself. It was one of the original ways you could configure `cabal-install` to use Stackage. With such an alternative index in place, `foo-1.2.3` could mean something different on your machine than on mine. (Epic foreshadowment right there.)

## Problems with the index

Let's start with the easy one: building up the offset indexing is slow and memory hungry today. I've tried optimizing this in the past, but this is really a pessimal case for Haskell's memory management: lots of binary blobs getting inserted into a `HashMap`. Chris Done recently reported to me that this can take over 1GB of memory, discovered due to a build failure on a VPS with swap space disabled.

But there's a more fundamental problem with indices. I [raised an issue](https://github.com/commercialhaskell/stack/issues/4137) two weeks back about a long time concern I've had with package indices. Remember that epic foreshadowment above? Allowing alternative, non-Hackage package indices means that `foo-1.2.3` is now ambiguous. And worse yet, because package index configuration can live in a user-wide configuration file, looking at your project's `stack.yaml` may not reveal this at all.

This kind of trade-off made sense in the past. However, we've got two things in Stack pushing against such behavior:

- Stack's main goal is to provide reproducible build plans. Encouraging a situation where the build plan will be altered this way is an anti-pattern.
- Stack has built in support for specifying package locations not on Hackage, via archives (HTTPS links to tarballs/zip files), repos (Git and Mercurial), and local file paths. There is no compelling reason for using the package index hack.

Since we'll allow overriding the package index location for mirroring, there's obviously no way to *stop* a user from providing a location that doesn't mirror Hackage itself. However, we can discourage this by allowing just one package index location instead of the current cascading fallback. We can also drop support for legacy pre-hackage-security `00-index.tar` indices, which do not provide security guarantees or access to revision information.

The second change we can make is to be much more thorough about referencing packages via cryptographic hashes instead of by name/version information. This is already necessary for proper reproducibility in a world of Hackage revisions. Part of the ongoing Pantry work will be to automate the process of rewriting configuration files to use cryptographic hashes, which currently is a pain.

Alright, so that's change one: **you only get one package index in Stack**, and it should be a Hackage mirror.

## SQLite for the win

The overarching Pantry plans involve referencing many different kinds of files via their cryptographic hashes. We'll be able to query them over the network securely, and cache them locally. For that local cache, we're going to use SQLite, which is a great choice for [lots of small files](https://www.sqlite.org/fasterthanfs.html).

The `pantry` branch of Stack no longer creates that cache with tarball offsets. Instead, when it downloads a new `01-index.tar` file from Hackage, it populates an SQLite database with the raw file contents, as well as a table which is essentially `Map (PackageName, Version, RevisionNumber) HashOfCabalFile`.

As I was [bragging about a bit on Twitter](https://twitter.com/snoyberg/status/1018846501076897792), this completely solves the high memory usage for cache creation I mentioned above. Now, updating all ~111,000 cabal files from Hackage takes less than 4mb of resident memory.

At first, it seemed like due to inability to detect Hackage rebases (where the `01-index.tar` gets updated), we'd need to totally recalcuate the cache each time `stack update` runs. This is the slow behavior we already have today. Fortunately, thanks to some insight from Oleg Grenrus, this turns out to [not be necessary](https://github.com/commercialhaskell/stack/commit/33ef253544ed8fa4a995240ff0d99e9c49f74074), and we can instead track hashes of the tarball. See [Hackage issue \#779](https://github.com/haskell/hackage-server/issues/779) for the full discussion, as well as potentially alternative implementations like parsing the `x-revision` info.

There is a downside to this approach, namely we will end up storing all of the cabal files twice. Fortunately, the SQLite storage format with proper table normalization turns out to be pretty good, resulting in about 0.5GB of storage (around the same as the `01-index.tar` file itself). However, when we get to Pantry's network layer in later posts, we'll see that in many common cases, we won't need to download the full index at all, saving both bandwidth and disk space. For now, we're treating disk space as a cheap commodity, which is basically in line with how all of Haskell tooling behaves.

Besides the advantages above, some other nice outcomes of this are:

- No need for loading up a large binary offset cache each time Stack runs. We can instead use SQLite's intelligent indexing capabilities.
- To go along with the above: we're not relying on any Haskell-specific binary serialization, which can get changed through versions of Stack. This means less time wasted recalculating that cache. This likely affects Stack developers more than anyone else.
- This provides the potential for a unified interface for looking up cabal files for packages coming from any location. I haven't implemented this yet, but it's coming down the pipeline for a future blog post.

## What's next?

Now that we're caching the contents of the cabal files themselves in the SQLite database, the next thing will be caching the contents of the tarballs as well. This raises some interesting design questions regarding whether we cache the full original tarballs as they are, or normalize to a more compact format to allow for more data sharing. After weighing the options, we're going to go with the latter. I've already implemented a proof-of-concept for this which works quite well. Now I need to integrate that with the Stack code base.

If you're interested in the work going on here and would like to discuss, come hit me up on [Stack's Gitter channel](https://gitter.im/commercialhaskell/stack).
{% endraw %}
