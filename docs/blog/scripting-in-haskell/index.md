---
layout: page
title: "Scripting in Haskell"
---
{% raw %}
*By Chris Done, 22 November 2016. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2016/11/scripting-in-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250624224433/https://academy.fpblock.com/blog/2016/11/scripting-in-haskell/).*

# Scripting in Haskell

Writing scripts in Haskell using Stack is straight-forward and reliable. We've made a screencast to demonstrate this:

<div class="iframe">

# Er is een fout opgetreden.

JavaScript kan niet worden uitgevoerd.

</div>

## Summary

Slides in the screencast cover:

- What Haskell is
- What Stack is
- We make a case for reproducible scripting

We cover the following example cases:

- Hello, World! as a Haskell script
- Generating a histogram of lines of a file
- Using FSNotify to watch a directory for any changes to files

In summary, we show:

1.  Scripting in Haskell is reproducible: it works over time without bitrot.
2.  It's easy to do, just add a shebang `#!/usr/bin/env stack` to the top of your file.
3.  We can use useful, practical libraries that are not available in traditional scripting languages.
4.  Our script is cross-platform: it'll work on OS X, Linux or Windows.
{% endraw %}
