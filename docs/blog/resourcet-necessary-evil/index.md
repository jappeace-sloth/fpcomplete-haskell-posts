---
layout: page
title: "ResourceT: A necessary evil"
---
{% raw %}
*By Michael Snoyman, 4 October 2018. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2018/10/resourcet-necessary-evil/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250624224244/https://academy.fpblock.com/blog/2018/10/resourcet-necessary-evil/).*

Alternative title: “ResourceT considered harmful”

Summary: ResourceT is a great tool, used to solve real problems when dealing with constrained resources and runtime exceptions. However, in the wild, it is often overused for situations where its full power isn’t needed. If you want more information on ResourceT, check out [its README.md](https://github.com/snoyberg/conduit/tree/master/resourcet#readme).

How do you copy a file in Haskell? Let’s ignore the obvious answer ([`System.Directory.copyFile`](https://www.stackage.org/haddock/lts-12.10/directory-1.3.1.5/System-Directory.html#v:copyFile)) and the cheeky answer:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import System.Exit
import System.Process
main = rawSystem "cp" ["src", "dest"] >>= exitWith
```

We’ll want to [use binary I/O functions](https://www.snoyman.com/blog/2016/12/beware-of-readfile) of course. One idea would be to use strict `ByteString` versions of `readFile` and `writeFile`:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import qualified Data.ByteString as B
main = B.readFile "src" >>= B.writeFile "dest"
```

Unfortunately, this has the potential to use unbounded memory for large input files. So instead we use lazy I/O:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import qualified Data.ByteString.Lazy as BL
main = BL.readFile "src" >>= BL.writeFile "dest"
```

Unfortunately, this has a different problem: non-deterministic resource usage. You see, if there’s some kind of an exception thrown when writing to `dest`, we do not get any guarantees about when the file descriptor for `src` will be closed. In a program this small, it makes no difference. In a long lived, multithreaded application, this has the potential to take down your entire process with file descriptor exhaustion.

All of this is old news to people familiar with streaming data libraries. And as such, you probably won’t be surprised to see me offer another solution to the problem, based on a library I wrote ([conduit](../../haskell/library/conduit/)):

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import Conduit
main = runConduit $ sourceFile "src" .| sinkFile "dest"
```

That looks all well and good, but we unfortunately get a compilation failure:

``` text
• No instance for (MonadResource IO)
    arising from a use of ‘sourceFile’
• In the first argument of ‘(.|)’, namely ‘sourceFile "src"’
  In the second argument of ‘($)’, namely
    ‘sourceFile "src" .| sinkFile "dest"’
  In the expression: runConduit $ sourceFile "src" .| sinkFile "dest"
```

With some squinting and brain power, this starts to make sense. The strict I/O version above avoided a potential file descriptor leak by using potentially unbounded memory. This allowed the file descriptors to be closed promptly. Lazy I/O fixes the memory issue by keeping the file descriptors open longer, possibly leaking them. Conduit is forcing us, at the type level, to solve both. Conduit itself addresses memory usage, but relies on something else—ResourceT—to guarantee that the file descriptors get closed in the case of exceptions.

Fortunately, solving this problem is pretty straightforward: just use `runResourceT`:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import Conduit
main = runResourceT
     $ runConduit
     $ sourceFile "src" .| sinkFile "dest"
```

Or, since this pattern is so common in conduit, we have a built in helper function:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import Conduit
main = runConduitRes $ sourceFile "src" .| sinkFile "dest"
```

You’ll see this kind of code all over the place in the conduit world, often in documentation written by me! I’m trying to atone for that sin today.

## Why do we need ResourceT?

I had a bit of a sleight of hand above. I told you that the types forced us to use ResourceT, and that’s true. But why, logically, do we need this concept? The reason is as follows:

- Conduit is coroutine based
- With coroutine-based code, you can’t properly install exception handlers
  - The reason for *this* isn’t immediately obvious, but let me give a small motivation: in a coroutine based system, we’re passing control of execution to some other component when we yield or await. We have no ability to install exception handlers on the actions that other component is performing.
- To work our way out of this pickle, we use this library called resourcet, which has a data type `ResourceT`, which lets you register cleanup actions that should be run even in the case of exceptions.

Alright, so obviously we need to use ResourceT in order to use `sourceFile` and `sinkFile`. And those functions need to use `ResourceT` in order to allocate a file descriptor inside the conduit pipeline, since they cannot guarantee that cleanup actions will occur otherwise. Sounds legit.

## No ResourceT needed!

But ResourceT is a powerful tool. It allows you to dynamically register new cleanup actions at will. In our situation we don’t actually need such power! Let me demonstrate (note: I’ll show you an easier way to do the same thing a bit later):

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import Conduit
import System.IO
main =
  withBinaryFile "src" ReadMode $ \src ->
  withBinaryFile "dest" WriteMode $ \dest ->
  runConduit $ sourceHandle src .| sinkHandle dest
```

You see, there’s nothing actually dynamic about our resource allocations. We need to open up two files, one for reading, and one for writing. We need to guarantee that both of those file descriptors will be closed in the event of an exception (or normal termination for that matter). This kind of workflow is well known, understood, and used in the Haskell world, and that’s why we have standard functions like `withBinaryFile` that performs all of this. More generally, we refer to it as “the bracket pattern”, based on the underlying `bracket` function which is used in implementing functions like `withBinaryFile`.

Of course, the code above is not only somewhat tedious, but it’s error-prone. It’s easy to accidentally swap `ReadMode` with `WriteMode`. If that sounds contrived, well, ahem, [I’m guilty of it](https://github.com/snoyberg/conduit/commit/87e4c64300054014f1d3db1cbae4d67d5ca35292). That was a good motivation for me to use the ResourceT-based approach in tutorials until now. However, conduit now boasts some helper functions that make this much easier and more error-proof:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import Conduit
main =
  withSourceFile "src" $ \src ->
  withSinkFile "dest" $ \dest ->
  runConduit $ src .| dest
```

It’s still more wordy than the `sourceFile`/`sinkFile` approach, but I’d argue that it’s worth the cost to avoid introducing people to heavyweight approaches they don’t need. I’ll be trying to move in this direction with future writing and training, not to mention my own coding.

## Downsides of overusing ResourceT

Alright, so I’ve thrown around that ResourceT is “heavyweight.” But is this actually a problem? I’m going to argue that it is, for multiple reasons:

1.  **Performance** There is a negligible performance overhead to the bookkeeping required for ResourceT. In general, this hit is small enough to not be that important. However, I’m including it as the first bullet since:

    - People love talking about performance
    - It’s the most clearly objective measure on this list

2.  **Complexity** ResourceT works as a monad transformer, which many people know is a topic I’ve been becoming increasingly leary of. I’ve also seen confusion about the lifetime of values inside ResourceT, which is a point of confusion I haven’t really seen from the bracket pattern.

3.  **Overlived resources** I’ve seen many bugs in production code pop up because people have used values created from ResourceT which have already been freed. While this is possible with the bracket pattern too, for whatever reason it seems like ResourceT hides that away from people better. As a contrived example, consider this code:

    ``` haskell
    #!/usr/bin/env stack
    -- stack --resolver lts-12.10 script
    import Conduit
    import Control.Monad.Trans.Resource
    import System.IO
    main = do
      (_, src) <- runResourceT $ allocate (openFile "src" ReadMode) hClose
      (_, dest) <- runResourceT $ allocate (openFile "dest" WriteMode) hClose
      runConduit $ sourceHandle src .| sinkHandle dest
    ```

    In this case, both `src` and `dest` are:

    - Created by `allocate`
    - A cleanup action to call `hClose` is registered
    - `runResourceT` finishes running, causing the cleanup to run
    - The file handle is then returned *outside* of `runResourceT`

    And as a less contrived example, I’ve seen many bugs pop up around how to do this correctly with `transPipe`, e.g.:

    ``` haskell
    #!/usr/bin/env stack
    -- stack --resolver lts-12.10 script
    import Conduit
    import Control.Monad.Trans.Resource
    import System.IO
    main = runConduit
      $ transPipe runResourceT (sourceFile "src")
     .| transPipe runResourceT (sinkFile "dest")
    ```

    This last example also demonstrates part of why I shy away from transformers these days too.

    There is a type based approach that solves these problems quite well: [regions](https://github.com/basvandijk/regions#readme). It was (of course) [invented by Oleg](http://okmij.org/ftp/Haskell/regions.html#light-weight). While it works, the idea never really caught on, in my opinion because the cost of juggling the types was too high.

    Interestingly, regions isn’t too terribly different in concept to lifetimes in Rust. And perhaps more interestingly, I believe this is an area where the [RAII](https://en.wikipedia.org/wiki/Resource_acquisition_is_initialization) (Resource Acquisition Is Initialization) approach in both C++ and Rust leads to a nicer solution than even our bracket pattern in Haskell, by (mostly) avoiding the possibility of a premature close.

4.  I’ve seen ResourceT advocated as a great way to avoid asynchronous exception bugs in Haskell. The theory seems to be: if you use ResourceT, you don’t even need to think about async exceptions, just use `allocate` appropriately and you’re all set!

    I disagree with this. In practice, I think you’ll end up with resources far overliving where they’re needed. And if you’re avoiding learning about async exceptions, I can almost certainly guarantee you’re not handling them correctly. My recommendation is:

    - Use a library like [unliftio](https://www.stackage.org/package/unliftio) or [safe-exceptions](https://www.stackage.org/package/safe-exceptions) designed to handle async exceptions correctly.
    - Use the correct functions for allocating resources, like `bracket`
    - Take the time to read up on the details of async exceptions. I [wrote a detailed blog post](../async-exception-handling-haskell/) and [gave a webinar](https://web.archive.org/web/2025/https://academy.fpblock.com/blog/how-to-handle-asynchronous-exceptions-in-haskell) on the topic.

I hope this is enough motivation: **don’t use resourcet if you don’t have to**. That, of course, leaves one important question.

## Why do we have ResourceT?

This blog post is kind of weird. I wrote a library. I maintain the library today. And I’m telling people not to use it. What gives?

ResourceT is an *absolutely necessary tool* in some cases. My point here is: if you’re not in one of those cases, *don’t use it*. If you can see a way to solve the problem with bracket-like functions, do that.

The general rule for when you need ResourceT is for *dynamic resource usage*. This means that, before you begin processing, you don’t know how many resources, or which exact resources, you’re going to need. The best example I know of is a memory-efficient deep directory traversal. Let’s write a naive program that will get a list of all files ending in `.hs` in a directory tree.

**CHALLENGE** See where the memory inefficient part is in the code below before reading my explanation.

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import System.Directory
import System.FilePath
import Data.Foldable (for_)

main :: IO ()
main = start "."

start :: FilePath -> IO ()
start dir = do
  rawContents <- getDirectoryContents dir
  let contents = map (dir </>)
               $ filter (not . hidden) rawContents
      hsfiles = filter (\fp -> takeExtension fp == ".hs") contents
  for_ hsfiles putStrLn
  for_ contents $ \fp -> do
    isDir <- doesDirectoryExist fp
    if isDir
      then start fp
      else pure ()

hidden :: FilePath -> Bool
hidden ('.':_) = True
hidden _ = False
```

The problem here is the call to `getDirectoryContents`. It will read into memory all of the entries for the given directory. If there are 1,000,000 files in a directory, it will take up a few megabytes of memory in filenames alone. Instead, we’d want an approach where:

- We open up the directory
- We traverse the contents one at a time
- If it has a `.hs` file extension, we print it
- If it’s a directory, we apply our algorithm to it recursively
- We close the directory

The thing is, we need to ensure that each time we open a directory, we also close it. And we don’t know how many layers deep we will be opening directories, or the names of those directories, before we begin. This is a use case where ResourceT usage is a must, and conduit provides some built in functions for performing this task.

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.10 script
import Conduit
import System.FilePath

main :: IO ()
main = runConduitRes
     $ sourceDirectoryDeep False "."
    .| filterC (\fp -> takeExtension fp == ".hs")
    .| mapM_C (liftIO . putStrLn)
```

**NOTE** Astute readers may note that this problem *also* has unbounded resource usage, namely we will keep open at maximum a file descriptor for each nested directory. I’m aware of no algorithm that will avoid this cost.

There are certainly other cases of dynamic resource usage that pop up in the wild. To put things in perspective, however, some months back I refactored the Stack codebase to remove all usages of `ResourceT`. Even a codebase performing as many different I/O heavy activities as Stack seems to be free of dynamic resource allocation.

## Why a monad transformer?

I debated including this section. Feel free to consider it “extra credit” and skip it.

One of my points against ResourceT is the complexity of using a monad transformer. However, this is a bit of a red herring. You could easily come up with a non-monad transformer API. For example, consider an API where you explicit create and share some `CleanupRegistry`:

``` haskell
withCleanupRegistry $ \registry ->
  runConduit
    $ sourceFile "src" registry
   .| sinkFile "dest" registry
```

One potential downside is that this is somewhat verbose. But that’s the constant debate around implicit arguments via `ReaderT` versus explicit arguments. There’s a more fundamental problem here: this API tends to encourage *even more* usage of outlived resources.

Above, I demonstrated how `transPipe` is often used in practice to use closed resources. That’s true, but for the most part the monad transformer nature of `ResourceT` prevents that specific problem. However, explicitly passing around registry values has a high likelihood of encouraging bad coding.

I don’t have even anecdotal evidence to back this claim up, since I never wrote the resourcet library with that usage in mind. It’s just a suspicion. But it’s a strong enough suspicion that I’ve avoided advertising such an alternative API to resourcet.

## Summary

ResourceT remains a good tool, and one I’ll recommend, *where warranted*. However, since writing it, I’ve discovered:

- My estimation of when it would be necessary was too high
- Misuse of the library is higher than I would have expected
- With appropriate combinators (like `withSourceFile` above), using the bracket pattern instead is not particularly difficult

If you’ve got use cases that you’re unsure really require ResourceT, feel free to drop a comment below or ping me on Twitter to discuss it. I hope this was helpful!
{% endraw %}
