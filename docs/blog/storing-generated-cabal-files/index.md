---
layout: page
title: "Storing generated cabal files"
---
{% raw %}
*By Michael Snoyman, 4 March 2020. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/storing-generated-cabal-files/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428053026/https://academy.fpblock.com/blog/storing-generated-cabal-files/).*

tl;dr: I'm moving towards recommending that hpack-using projects store their generated cabal files in their repos, and modifying Stack and Pantry to more strongly recommend this practice. This is a reversal of previous recommendations. [Vote and comment on this proposal](https://github.com/commercialhaskell/stack/issues/5210).

## Backstory

Stack 2.0 switched over to using the Pantry library to manage dependencies. Pantry does a number of things, but at its core it focuses heavily on reproducibility. The idea is that, with a fully qualified package specification, you should always get the same source code. As an example, `https://example.com/foo.tar.gz` would not be a fully qualified package specification, because the content in that tarball could silently change without being detected. Instead, with Pantry, you would specify something like:

``` yaml
size: 9526
url: https://github.com/snoyberg/filelock/archive/97e83ecc133cd60a99df8e1fa5a3c2739ad007dc.tar.gz
cabal-file:
  size: 1571
  sha256: d97c2ee2b4f0c72b35cbaf04ad37cda2e9e6a2eb1e162b5c6ab084acb94f4634
name: filelock
version: 0.1.1.2
sha256: 78332e0d964cb2f24fdbb6b07c2a6a84a029c4fe540a0435993c85ad58eab051
pantry-tree:
  size: 584
  sha256: 19914e8fb09ffe2116cebb8b9d19ab51452594940f1e3770e01357b874c65767
```

Of course, writing these out by hand is tedious and annoying, so Stack uses Pantry to generate these values for you and put them in a lock file.

Separately: Stack has long supported the ability to include hpack's `package.yaml` files in your source code, and to automate the generation of a `.cabal` file. There are two quirks we need to pay attention to with hpack:

- The cabal files it generates change from one version to the next. Some of those changes may be semantically meaningful. At the very least, each new version will stamp a different hpack version in the comments of the cabal file.
- hpack generation is a highly I/O-focused activity, looking at all of the files in a package. Furthermore, as [I was recently reminded](https://github.com/commercialhaskell/stack/issues/4906) it can refer to files outside of the specific package you're trying to build but inside the same Git repository or tarball.

Finally, Stack and Pantry make a stark distinction between two different kinds of packages. *Immutable* packages are things which we can assume never change. These would be one of the following:

- A package on Hackage, specified by a name, version number, and information on the Hackage revision
- A tarball or ZIP file given by a file path or URL. While these absolutely *can* change over time, Pantry makes an explicit recommendation that only immutable packages should be used. And the hashes and file size stored in the lock file provide protection against changes.
- A Git or Mercurial repository, specified by a commit.

On the other hand, mutable packages are packages stored as files on the file system. These are the packages that you are working on in your local project. Reproducibility is far less important here. We allow Stack to regularly check the timestamps and hashes of all of these files and determine when things need to be rebuilt.

## The conflict

There's been a debate for a while around how to manage your packages with Stack and hpack. The question is simple: do you store the generated `cabal` files in the repo? There are solid arguments in both directions:

- You shouldn't store the file, because generated files should in general not be stored in repositories. This can lead to unnecessary diffs, and when people are using different hpack versions, "commit battles" of the file jumping back and forth between different generated content.
- You should store the file, since for maximum reproducibility we want to ensure that we have identical cabal files as input to the build. Also, for people using build tools without built in support for hpack, it's more convenient to have a cabal file present.

I've had this discussion off and on over the years with many different people, and before Stack 2 had personally settled on the first approach: not storing the cabal files. Then I started working on Pantry.

## Early Pantry

Earlier in the development of Pantry, I made a decision to focus on reproducibility. I quickly ran into a problem with hpack: I needed to be able to tell the package name and version of a package easily, but the only code path I had for that was parsing the cabal file. In order to support hpack files for this, I would need to write the entire package contents to the filesystem, run hpack on the resulting directory, and then parse the generated file.

(I probably could have whipped up something hacky around parsing the hpack YAML file directly, but that felt like a can of worms.)

Performing these steps each time Stack or Pantry needed to know a package name/version would have been prohibitively expensive, so I dismissed the option. I also considered caching the generated cabal file, but since the generated file contents would change version by version, I didn't follow that path, since it would violate reproducibility.

## Current Pantry

An early beta tester of Stack 2.0 complained about this change. While hpack worked perfectly for mutable, local packages, it no longer worked for immutable packages. If you had a Git repository with a package, that repo didn't include the generated cabal file, *and* you wanted to use that repo as an extra-dep, things would fail. This didn't fail with Stack 1, so this was viewed (correctly) as a regression in functionality.

However, Stack 2 was aiming for caching and reproducibility goals that Stack 1 hadn't achieved. If anyone remembers, Stack 1 had a bad tendency to reclone Git repos far more often than you would think it should need to. Pantry's caching ultimately solved that problem, and did so by relying on reproducibility.

My initial recommendation was to require changing all Git repos used as extra-deps to include the generated cabal files. However, after further discussion with beta testers, we ended up changing Pantry instead. We added the ability to cache the generated cabal files (keyed on the version of hpack used). I was uneasy about this, but ultimately it seemed to work fine, and let us keep the functionality we wanted. So we shipped this in Pantry, in Stack 2, and continued recommending people not include generated cabal files.

## The problems arise

Unfortunately, things were far from rosey. There are now at least three problems I'm aware of with this situation:

- Continuing from before: people using build tools without hpack support are still out of luck with these repos.
- As raised in [issue \#4906](https://github.com/commercialhaskell/stack/issues/4906), due to how Pantry handles subdirectories in megarepos, cabal file generation will fail for extra-deps in some cases.
- Lock files have regularly become corrupted by changing generated cabal files. If you use a new version of Stack using a different version of hpack, it will generate a different cabal file, which will change the hashes associated with a package in the lock file. This can cause a lot of frustration between teams, and undermines the whole purpose of lock files in the first place.

There are probably solutions to the second and third problem. But there's definitely no solution to the first short of including the cabal files again.

## Changes

Based on all of this, I'm recommending that we make the following changes:

- Starting immediately: update docs and Stack templates to recommend checking in generated cabal files. This would involve a few minor doc improvements, and removing `*.cabal` from a few `.gitignore` files.
- For the next releases of Pantry and Stack, add a warning any time an immutable package does not include a `.cabal` file. Reference potentially this blog post, and warn that lock files may be broken by doing this.
- Personally: I'll start including the generated cabal files in my repos. Since I have a bunch of them, I'll appreciate people sending PRs to modify my .gitignore files and adding the generated files, as you discover them.

For those who are truly set against including generated cabal files, all is not lost. For those cases, my recommendation would be pretty simple: keep the generated file out of your repository, and then generate a source tarball with `stack sdist` to be used as an extra-dep. This will essentially mirror the `stack upload` step you would follow to upload a package to Hackage.

## Next steps

The changes necessary to make this a reality are small, and I'm happy to make the changes myself. I'm opening up a short discussion period for this topic, probably around a week, depending on how the discussion goes. If you have an opinion, please jump over to [issue \#5210](https://github.com/commercialhaskell/stack/issues/5210) and either leave an emoji reaction or a comment.
{% endraw %}
