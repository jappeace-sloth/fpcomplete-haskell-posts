---
layout: page
title: "Pantry, part 3: Specifying Dependencies"
---
{% raw %}
*By unknown author, August 2018. Mirrored from FP Complete's blog: [original URL](https://www.fpcomplete.com/blog/specifying-dependencies/) (offline), [Wayback Machine copy](https://web.archive.org/web/20230921162443/https://www.fpcomplete.com/blog/specifying-dependencies/).*

  

This is part three of a series of blog posts on Pantry, a new storage and download system for Haskell packages. You can see [part 1](../pantry-part-1-package-index/) and [part 2](../pantry-part-2-trees-keys/).

What’s wrong with this `stack.yaml` file?

``` yaml
resolver: lts-12.0
```

Not sure? OK, try this:

``` yaml
resolver: lts-12.0
extra-deps:
- acme-missiles-0.3
```

Well, that one is a bit easier to point out: we haven’t pinned down which revision of the cabal file we should use for `acme-missiles-0.3`. As it stands, our build plan is *not* reproducible. At some point in the future, the cabal file could be revised, and we’ll get a different plan. Fixing that is fairly easy:

``` yaml
resolver: lts-12.0
extra-deps:
- acme-missiles-0.3@rev:0
```

The `@rev:0` pins us down to a specific revision. However, we *still* have a problem. Let’s analyze how this `stack.yaml` file is treated by Stack.

## Resolving acme-missiles

Stack is going to need to get both the `acme-missiles-0.3.tar.gz` sdist tarball, and the `acme-missiles.cabal` file at revision one. In order to do both of these steps, Stack will:

1.  Use `hackage-security` to download the `01-index.tar` file and validate the download using the Hackage public keys. These keys are hard-coded into Stack, or can be overridden via configuration.
2.  Find the `acme-missiles/0.3/package.json` file to get the SHA256 and filesize of the `acme-missiles-0.3.tar.gz` file.
3.  Find the first file in the `01-index.tar` file with a file path `acme-missiles/0.3/acme-missiles.cabal`, which corresponds to the the `@rev:0` bit.

All well and good. The Hackage Security layer prevents a malicious man-in-the-middle attack, as well as other attacks. However, it doesn’t prevent some other possibilities:

- Hackage itself is compomised and starts sending off malicious code
- A bug occurred which results in a modified sdist tarball (as [mentioned last time](https://github.com/haskell/hackage-server/issues/573#issuecomment-283299524))
- For some unknown reason, a decision is made to change the contents of the sdist tarball or cabal file revision

Just to be clear: this isn’t specific to Hackage. Consider the following Stack configuration:

``` yaml
resolver: lts-12.0
extra-deps:
- https://example.com/my-file.tar.gz
```

Who’s to say that `my-file.tar.gz` isn’t changed at some point, even if I control that domain name? Stack has no way of guaranteeing such stability with the provided information.

Already today, Stack provides a more reliable way to specify the cabal file revision:

``` yaml
resolver: lts-12.0
extra-deps:
- acme-missiles-0.3@sha256:2ba66a092a32593880a87fb00f3213762d7bca65a687d45965778deb8694c5d1,613
```

However, we still rely on Hackage metadata for ensuring the sdist tarball is unmodified. Why not just double down on the hashing approach? With Pantry, we do just that! As an example (I’ll share the source a bit later):

``` yaml
- hackage: ALUT-2.4.0.2@sha256:6fbceae566b3d63118c67db71645f48ba22b195c58328863d274a76fba086fc1,3895
  pantry-tree:
    size: 2402
    sha256: 8985dfc0fe299d313690cd4db86c511340f805df5e6d3fab79c15d36ac5d8c71
```

We’ve already [discussed trees](../pantry-part-2-trees-keys/). In this case, that 8985dfc… hash is a hash of the binary representation of the tree, and that binary representation is of size 2,402 bytes. Anyone following the same Pantry algorithm who downloads the same `ALUT-2.4.0.2.tar.gz` file with the same cabal file revision will end up with that same hash and file size. Any Pantry caching server (which we still haven’t spoken about!) will be able to serve up that information.

“You really expect me to enter all of that information each time I add a dependency?” you may ask. The answer is: no, of course not. That would be sadistic. Keep reading.

## Resolving resolvers

The story with figuring out what `lts-12.0` is much the same. Stack parses that string and realizes it’s looking for an LTS snapshot, major version 12, minor version 0, and goes to the [appropriate URL](https://github.com/commercialhaskell/lts-haskell/blob/master/lts-12.0.yaml), downloads the contents, saves them locally… and hopes they never change at any point in the future.

I run that repo. I promise, unless there’s a major bug to be fixed (like incorrect hashes), I don’t intend to modify those files. They *should* be reproducible. But you shouldn’t trust me. Seriously, assume I’m trying to break your project: it’s the right mindset for thinking through reproducible builds.

Tomorrow, I could upload a new version of `conduit` with a back door in it, modify the `lts-12.0.yaml` file to use it, and the next time you run `stack build` with a non-cached download, you’ll get my bug. The original time you built and tested, everything would have worked just fine. But now you’re wide open for an attack.

I probably sound like a broken record by now, but I think you can guess where this is headed. That’s right: hash the snapshot files too! Instead of `resolver: lts-12.0`, you’ll have something like the following (exact syntax still in flux):

``` yaml
resolver:
  url: https://raw.githubusercontent.com/commercialhaskell/stackage-snapshots/master/lts/12/0.yaml
  sha256: a55695a7236e46740e369d778d83e44475ed4f1c80783071835dae43658bada6
  size: 500006
```

You may have noticed that this is using a different repo than previously. That’s because the Stackage snapshot file format is changing with the new Pantry-based Stack to be the same as the existing custom snapshot format. I’ve just completed converting all of the LTS Haskell and Stackage Nightly snapshots over, feel free to [take a look](https://github.com/commercialhaskell/stackage-snapshots) if you’re interested. Bonus: these files are *much* smaller by eliminating a bunch of extraneous information, which we’ll keep separate from the snapshtos themselves.

## Are you sadistic?

So back to that point: who in their right mind wants to right down this kind of information? Obviously nobody. But this is exactly the kind of thing tools are really good at writing instead! Here’s my planned execution:

- Add support for all of these hashes in Stack, retaining support for the hash-less configuration formats
- Add a command (maybe `stack freeze`? bike shedding welcome) which either converts your config files in place to include the hashes, or spits out hashed version that you can copy-paste. The latter may be nicer to avoid trashing YAML file comments.
- Add a warning to Stack when it detects you have hash-less values in your config files, and recommend running `stack freeze`

And here’s the mental model. You will end up being vulnerable to bad content from upstream when you initially say `lts-12.0`. But when you initially choose *any* upstream snapshots or packages, you’re vulnerable to them containing incorrect or malicious code. It’s your responsibility to ensure you’re getting something you can trust, and no tool can fix that for you.

But once you’ve vetted those files, you want your tool to ensure that those files are never changed out from under you. Initially specifying the simple format (e.g., `lts-12.0`), testing your configuration, and then adding in the hashes, achieves this goal. And fortunately, our tooling can make this (relatively) painless.

## What’s next?

I still haven’t implemented the freeze command, so that’s on the horizon. There are also still lots of pieces of unimplemented code in the `pantry` branch. But most likely I’m going to take a break from the Stack work itself soon, and start working on a new Stackage curator tool that works with Pantry, and makes it much easier for others to test their own snapshots. It will also make it easier to create snapshots with packages outside of Hackage for easier testing of proposed code changes. Stay tuned!
{% endraw %}
