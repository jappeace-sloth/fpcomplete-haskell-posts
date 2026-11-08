---
layout: page
title: "Stack's New Extensible Snapshots"
---
{% raw %}
*By Michael Snoyman, 13 July 2017. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2017/07/stacks-new-extensible-snapshots/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250515040711/https://academy.fpblock.com/blog/2017/07/stacks-new-extensible-snapshots/).*

**NOTE** This blog post made the rounds last week before the branch was actually merged and the post was still on a review server. I'm officially publishing it as the [pull request is now merged](https://github.com/commercialhaskell/stack/pull/3249).

There is a collection of features in Stack that have been added in bit by bit, as opposed to being designed into a cohesive whole from the start. The features work, but could be a bit better. We've known for a while that, instead of putting in place strategic fixes, a more general refactoring of the core dependency management logic was in order. I'm happy to announce that these changes have landed in the master branch, and will be part of the next major release of Stack.

I'd like to motivate the limitations in Stack that encouraged this change, discuss the new system, mention some potential future changes, and share a few thoughts on the (very pleasant) Haskell refactoring process itself.

**NOTE** These features have *not currently been released*, so don't try using them in a stable Stack executable. If you'd like to test them out (and I'd certainly appreciate the extra testing), you can run `stack upgrade --git` to build a Stack executable from the master branch.

## Motivation

Consider this fairly standard snippet of a stack.yaml file:

``` yaml
resolver: lts-8.12
packages:
- ./site1
- ./site2
- location:
    git: https://github.com/yesodweb/yesod
    commit: 7038ae6317cb3fe4853597633ba7a40804ca9a46
  extra-dep: true
  subdirs:
  - yesod-core
  - yesod-bin
extra-deps:
- html-conduit-1.2.1.1
```

This is leveraging a number of features of Stack right off the bat:

- Using an LTS Haskell snapshot to capture a consistent set of dependencies
- Specify multiple *project packages*, in this case `site1` and `site2`.
- Specify an extra dependency from a Git repository.
- Specify multiple subdirectories for a Git repository to directly support "megarepos".
- Specify an extra dependency from the upstream package index (which is Hackage unless you've done something weird).

This is great, but there's a bit of pain involved in this:

- My personal pet peeve: that `extra-dep: true` for the Git repo. Because of how features were added, we included Git repos together with "project packages," and then added a hack to explicitly state that they should be treated as dependencies (so that `stack test`, for example, won't build their dependencies). This feels weird.
- We *also* have this `extra-deps` stanza, which accepts package name/version combos, but *doesn't* accept Git repos (or HTTP(S) tarballs, which are also supported in the `packages` section).
- As Hackage cabal file revisions become more common, it's taking away a level of reproducibility that `extra-deps` cannot specify the exact revision of a package we'd like to use.
- The `subdirs` feature is nice, but it's weird that it's not more directly connected to the Git repo information (notice how it's a level up).
- I've specified `yesod-bin` as an extra-dep, which provides an executable named `yesod`. Ideally, if one of my packages specified a dependency on that executable, Stack would automatically build the `yesod-bin` package. While this logic works for LTS Haskell and Stackage Nightly snapshots, it *doesn't* work for these extra-deps.
- Specifying dependencies like this inside the `stack.yaml` file makes them local to just the project I'm working on. There are advantages to this approach regarding disk space (which I won't get into here), but there's a big downside: I can't share precompiled libraries between projects that are defined this way. I'd like to be able to recapture that sharing ability.
- And more generally: why can't I just define this customized version of `lts-8.12` and share it among multiple projects, possibly even from an immutable URL?

As you can see, the problems aren't insurmountable, but they are annoyances, and they seem to overlap quite a bit.

## Updated syntax

Let's rewrite that `stack.yaml` file to be a little bit more straightforward:

``` yaml
resolver: lts-8.12
packages:
- ./site1
- ./site2
extra-deps:
- html-conduit-1.2.1.1@sha256:de32ca4d6df94a7c027a11db1b2e32ef1a7ccfe0565923f24528613ade821343
- git: https://github.com/yesodweb/yesod
  commit: 7038ae6317cb3fe4853597633ba7a40804ca9a46
  subdirs:
  - yesod-core
  - yesod-bin
```

The first thing to notice is that the `packages` value is now just a list of the actual code in our project, not the dependencies.

Next, we still have `html-conduit-1.2.1.1` coming from Hackage. But we have this funny `@sha256:...` bit at the end. This is a hash of the cabal file contents we want to use. This gives us much stronger guarantees of reproducibility than we had previously. Instead of getting whatever most recent version happens to be available, you'll get an exact cabal file. This feature has been present for a while in Stackage snapshots, but hasn't been accessible for local dependencies.

Next, we've moved the Git repo information out of `packages` and into `extra-deps` where it logically belongs. We also no longer need that extra `location` key. We had that so that we could also define `extra-dep` and `subdirs` keys. We now instead put the `subdirs` key next to the `git` and `commit` keys, and don't need `extra-dep` at all (since it's implied by being within `extra-deps`).

Behind the scenes, the code managing these things has changed drastically. Most importantly for our discussion here, Stack now uses the same code paths for loading up snapshots and loading up package information within the `stack.yaml` file. In addition to just being a good practice for keeping us sane, this means that build tool detection now works for project packages and dependencies too.

This answers a good deal of our points above (hold off for the last two when we get to custom snapshots).

### Four package locations

That probably seemed like a bit of a jumble, so let's start over. Every package has a *location*, which tells Stack where to get it from. Stack supports for different package locations:

- **Local file path**, like `./site1` above
- **Package index**, specified version a package name, version number, and optional cabal file hash. You're probably wondering "why not just call it Hackage?" The reason is that you can extend your list of package indices to augment or override Hackage (such as to use a corporate package repository). That's why we use the general term.
- **Git or Mercurial repo**, specified by a repo URL, a commit, and an optional list of subdirectories within the repo to look for packages. If omitted, Stack will look in the root of the repo.
- **HTTP(S) URL**, which isn't demonstrated above, but which is just a standard `http(s)://` URL pointing to a tarball.

All four of these have been supported in Stack since (almost) its inception. The differences now are that:

- `extra-deps` now supports all four forms

- `packages` still supports local file paths, Git repos, and HTTP(S) URLs, but for the latter two requires you to explicitly state `extra-dep:` as either `true` or `false`. We'll discuss this a bit more below. There are two reasons package index location isn't supported here:

  - It wasn't supported previously, and is an illogical thing to do: you would never have a situation of working on a package pulled from the index. If you want to do that, you should probably clone the source of that package (such as with a Git submodule).
  - It could introduce ambiguities in parsing between a package index and a filepath (imagine you have a local directory `foo-1.2.3`). We've allowed this ambiguity to exist in `extra-deps`; if you have such a filepath, you can always preface it with `./`.

This is all well and good, but isn't much more than a cosmetic improvement (though, in my opinion, it's a very nice cosmetic improvement). But this gets much cooler with custom snapshots.

## Custom snapshots

Stack has had some support for custom snapshots for a while, but it's never been fully implemented, since we've been waiting for this extensible snapshot concept to land. Since most people aren't very familiar with custom snapshots today, I'm not going to compare and contrast, but instead just jump in to explaining how they work now.

Stack configurations always discuss a *resolver*, which specifies a GHC version, a set of additional packages, build flags, and some other pieces of metadata. You've probably seen a few kinds of resolvers until now:

- `lts-8.12`, using LTS Haskell
- `nightly-2017-07-01`, using Stackage Nightly
- `ghc-8.0.2`, using a specific GHC version without any extra packages available

Custom snapshots answer a simple question: what if I want to define my own snapshot which isn't LTS Haskell or Stackage Nightly? And that's really all they are: a format for defining your own snapshots like Stackage does. However, they've got a number of cool features that Stackage snapshots don't:

- They are *extensible* (thus the whole blog post name): you can define a parent snapshot for any snapshot and inherit its settings.
- You can use all four types of package locations when defining a custom snapshot. Say you have a package that isn't ready to be released to Hackage, or is only for your internal team to use. You can stick it in a tarball on a webserver, or in a Git repo, and refer to it just as you would from `extra-deps` in your `stack.yaml` file.
- Unlike defining packages in `stack.yaml`, packages built in a custom snapshot can be shared in the package cache and reused between projects.

Let's see how this would modify our `stack.yaml` from above. First, I'm going to define a `my-snapshot.yaml` file:

``` yaml
resolver: lts-8.12
name: my-snapshot # For user display only
packages:
- html-conduit-1.2.1.1@sha256:de32ca4d6df94a7c027a11db1b2e32ef1a7ccfe0565923f24528613ade821343
- git: https://github.com/yesodweb/yesod
  commit: 7038ae6317cb3fe4853597633ba7a40804ca9a46
  subdirs:
  - yesod-core
  - yesod-bin
```

Notice how I've kept the same `resolver` value here. What I'm stating is that I'd like my snapshot to start off with the same GHC version and package set defined in `lts-8.12`, and then add new packages. Next, I've copied my entire `extra-deps` section in here, and called it `packages` instead (since these are the packages that actually make up the snapshot, not some extra dependencies added on top).

Note that, because a custom snapshot is intended to contain immutable package data, it does *not* support local filepaths as package location, as these are expected to change over time.

Now the `stack.yaml` file:

``` yaml
resolver: my-snapshot.yaml
packages:
- ./site1
- ./site2
```

Instead of a Stackage snapshot or compiler version, my `resolver` now gives the path to the snapshot config file. This can be a file path, or an HTTP(S) URL. The `packages` section stayed the same, but my `extra-deps` is no longer necessary: all of my dependencies are now defined within the custom snapshot.

And in case anyone wants to get cheeky: yes, a custom snapshot can put another custom snapshot in its `resolver` field. You can layer these things up as many layers as you'd like. Have fun!

Just to summarize, Stack supports three different kinds of resolver values:

- A compiler name
- A Stackage snapshot name (LTS or Nightly)
- A custom snapshot

## Where's the global package information?

Global packages are those packages which are shipped with GHC itself (or at least end up in its global database). A funny question I bet many people never thought about is: where are global packages defined? Are they in the snapshot, or does Stack look them up from GHC itself? There are advantages both way:

- If it comes from the snapshot, it may be wrong. For example, do you have the `Win32` or `unix` package?
- If it comes from GHC itself, then Stack can't do a `stack init` without first installing every GHC version it wants to test compatibility with.

Previously, global information came from the Stackage snapshots. But both because of the "possibly incorrect" reason, and because it would be a royal pain to define all of the global packages in each custom snapshot file, Stack now does something different:

- When you use `stack init` or `stack new` (which implicitly calls `stack init`), Stack will rely on *global hints* present in a snapshot as a good guess about which packages GHC provides.
- When you're ready to start building your code against a specific GHC version, Stack will query GHC's global database.

## Choosing between stack.yaml and custom snapshot

You may be conflicted about whether you should add extra dependencies into a stack.yaml file (as you've probably done until now) or define a custom snapshot. My answers may change over time with experience, but here are some good guesses:

- If you're making lots of rapid iterations over the dependencies (e.g., testing five different versions of a package), use extra-deps. You will avoid Stack having to create separate snapshot databases and do a bunch of "copying precompiled package" stuff.
- If you're using the same modified sets in many projects, use a custom snapshot
- If you're changing a package deep in the dependency hierarchy (like `mtl` or `stm`), make a custom snapshot to try and save work (though I'm not sure if my logic is sound here)

## Things we've lost

Besides the potential for some kind of breaking change in behavior to have crept in (**NOTE** please help me by testing against your projects!), the only lost features I'm aware of are:

- The custom snapshot configuration has changed significantly. Since very few people are using it, and it was always an experimental feature, this is probably an acceptable trade-off.
- We no longer have support for subdirs on tarballs and index packages. This is because the feature just doesn't make sense, and was only accidentally present. (We *do* have support for filepath locations, which is equally silly, but was also trivial to add support for and made one of the integration tests happy.)

## Future changes

Here's my biggest feature for consideration: making the project packages *only* support filepaths. I can think of no logical case where we'd want to support HTTP(S) or Git repos as "project packages" (meaning things that run tests, for instance). In my ideal world:

- The `packages` key would accept a list of filepaths
- The `extra-deps` key would accept exactly what it does now
- Everyone could transition from their current `extra-dep: true` syntax over the next few versions before we remove the old support

I'm not normally in favor of breaking backwards compatibility in Stack, but miscategorized extra deps has resulted in much confusion, so I'd be happy to see it go, even if it requires rewriting `stack.yaml` files over time.
{% endraw %}
