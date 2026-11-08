---
layout: page
title: "Exiting a Haskell process"
---
{% raw %}
*By Michael Snoyman, 24 August 2017. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2017/08/exiting-haskell-process/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428055044/https://academy.fpblock.com/blog/2017/08/exiting-haskell-process/).*

This blog post was inspired by a [recent Stack Overflow question](https://stackoverflow.com/questions/45839972/how-do-i-cause-a-warp-server-to-terminate). It also uses the [Stack script interpreter](../../haskell/tutorial/stack-script/) for inline snippets if you want to play along at home. Don't forget to [get Stack first](https://web.archive.org/web/2025/https://haskell-lang.org/get-started).

## The non trick case

Here's a non trick question: what do you think the output of this series of shell commands is going to be?

``` text
$ cat Main.hs
#!/usr/bin/env stack
-- stack --resolver lts-9.0 script
import System.Exit

main = exitWith (ExitFailure 42)
$ stack Main.hs
$ echo $?
```

If you guessed `42`, you're right. Our Haskell process uses `exitWith` to exit the process with exit code `42`. Then `echo $?` prints the last exit code. All relatively straightforward (if you're familiar with the shell).

## Race condition

Alright, let's make it more fun with some concurrency (concurrency makes *everything* more fun):

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-9.0 script
import System.Exit
import Control.Concurrent.Async

main = concurrently
  (exitWith (ExitFailure 41))
  (exitWith (ExitFailure 42))
```

The output this time is *nondeterministic*. We don't know if the first thread (which exits with `41`) or the second thread (which exits with `42`) will exit first. I tested this about 5 times on my machine, and got both `41` and `42` as outputs. So this isn't just *theoretically* nondetministic, it's *practically* nondetministic.

## Surprise! Warp

Alright, that's fine, probably nothing too terribly surprising. Now let's throw the curve balls in. I'm going to write a web server with Warp, and when someone requests `/die`, I want the server to go down. Here's the code. If you're not familiar with WAI and Warp, just ignore the web bits and focus on the `exitWith` part:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-9.0 script
{-# LANGUAGE OverloadedStrings #-}
import Network.Wai
import Network.Wai.Handler.Warp
import Network.HTTP.Types
import System.Exit

main = run 3000 $ \req send ->
  if pathInfo req == ["die"]
    then exitWith (ExitFailure 43)
    else send (responseLBS status200 [] "Still alive!\n")
```

Let's see what happens when we run it:

``` text
$ stack Main.hs&
[2] 19117
$ curl http://localhost:3000
Still alive!
$ curl http://localhost:3000
Still alive!
$ curl http://localhost:3000
Still alive!
$ curl http://localhost:3000/die
ExitFailure 43
Something went wrong
$ curl http://localhost:3000
Still alive!
$ fg
stack Main.hs
^C
```

A few different weird things just happened:

- When we made a request to `/die`, the server apparently didn't die! We can see that from both the fact that the next request succeeded, and the `fg` call.
- For some reason, `ExitFailure 43` is printed to the console. We can't tell here, but it's coming from the server process.
- And our HTTP response body contains the content `Something went wrong`, even though we didn't write that.

I would have expected the process to just die and get an empty response. Why this surprising behavior instead?

## Implementation of `exitWith`

To understand what's happening, let's look at a simplified version of the implementation of the `exitWith` function. Feel free to [read the original as well](https://www.stackage.org/haddock/lts-9.1/base-4.9.1.0/src/System-Exit.html#exitWith).

``` haskell
exitWith :: ExitCode -> IO a
exitWith code = throwIO code
```

I would have anticipated that this would, you know, actually exit the process. Such a function *does* exist in Haskell. It's called [`exitImmediately`](https://www.stackage.org/haddock/lts-9.1/unix-2.7.2.1/src/System-Posix-Process-Common.html#exitImmediately), it lives in the `unix` package, and it calls out to the `exit` C library function. But not `exitWith`: it throws a runtime exception.

There's a good reason for this exception-based behavior. It allows cleanup code to run before the process just up and dies, which would allow things like flushing file handles and gracefully closing network connections. However, this can certainly result in surprising behavior. We'll get back to the Warp case in a bit; let's see something simpler first:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-9.0 script
import Control.Exception.Safe
import System.Exit

main = tryAny foo >>= print

foo :: IO String
foo = exitWith (ExitFailure 44)
```

And the output is:

``` text
$ stack Main.hs
Left (ExitFailure 44)
$ echo $?
0
```

We've exited with code 0, a success! And our program continued running after the call to `exitWith`. That's because our `tryAny` call intercepted the exception, converted it into a `Left` value, and then our program succeeded in printing out that value.

## What's up with Warp?

Warp employs a pretty simple model for handling requests:

- Grabs a listening port
- Loops accepting connections on that port
- For each connection, fork a new worker thread

Within each worker thread, Warp accepts a request, passes it to the user-supplied application, takes the response, and sends it. Additionally, Warp installs an exception handler in case the application throws an exception. In that case, it will print the exception to stderr and send a 500 Internal Server Error response with the response body (wait for it) `Something went wrong`.

So of course our initial attempt at killing our Warp application failed: the exception was intercepted!

As an aside, if you really want to be able to exit from a Warp application, you can [see my answer on Stack Overflow](https://stackoverflow.com/a/45846292/369198), which I'm not going to detail here as it will be a tangent to the main point.

## Child threads in general

Alright, let's make another mistake (certainly my specialty):

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-9.0 script
import Control.Concurrent
import System.Exit

main = do
  forkIO (exitWith (ExitFailure 45))
  threadDelay 1000000
  putStrLn "Normal exit :("
```

We're not intercepting the exception via a handler at all, and thanks to our `threadDelay` (which delays the parent thread by one second), we have plenty of time for the child thread to act before the parent exits on its own. Surely this will exit with exit code 45, right?

``` text
$ stack Main.hs
Main.hs: ExitFailure 45
Normal exit :(
$ echo $?
0
```

Foiled again! We're running into something different now. In GHC's runtime system, a process exits when the main thread exits. If a child thread exits for any reason, the process keeps running. If the main thread exits, even if there are still child threads running, the process exits.

When we call `forkIO`, a default exception handler is installed on this new child thread. And that default exception handler will simply print out the exception to stderr. That's the `Main.hs: ExitFailure 45` output we see.

## As usual: async to the rescue

Where did we go wrong? By using the `forkIO` function, of course! As I'm wont to say:

> I think I've just told like the tenth person this week "use the async library, you'll be much happier." Thanks [@simonmar](https://twitter.com/simonmar) 👍
>
> — Michael Snoyman (@snoyberg) [July 2, 2017](https://twitter.com/snoyberg/status/881538591251451904)

The problem is that `forkIO` installs a default exception handler, instead of properly propagating exceptions through our application. Fortunately, there's a great solution to this, which we've already seen in this post: use the `concurrently` function from `async` (or, in some cases, `race`).

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-9.0 script
import Control.Concurrent
import Control.Concurrent.Async
import System.Exit

main = concurrently (exitWith (ExitFailure 45)) $ do
  threadDelay 1000000
  putStrLn "Normal exit :("
```

Any luck?

``` text
$ stack Main.hs
$ echo $?
45
```

Woohoo! I've never been so happy to see a process exit with a failure code before.

In contrast to `forkIO`, the `concurrently` and `race` functions track the exceptions occurring in their child threads and rethrow those exceptions in the parent thread should anything go wrong. So instead of exceptions disappearing into the aether, they tear down our process with dignity.

If you're not familiar with the async library, check out the [tutorial I wrote on it](../../haskell/library/async/), which focuses on using `concurrently` and `race` wherever possible.

## Summary

Takeaways to remember:

- `exitWith` works by throwing exceptions, not directly killing the process
- A Haskell process dies when the main thread dies
- Warp worker threads install an exception handler that generates 500 Internal Server Error responses
- Use `concurrently` and `race` in place of `forkIO`, and generally try to use the `async` library
{% endraw %}
