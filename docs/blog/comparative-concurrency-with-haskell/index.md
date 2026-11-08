---
layout: page
title: "Comparative Concurrency with Haskell"
---
{% raw %}
*By Michael Snoyman, 22 November 2016. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2016/11/comparative-concurrency-with-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250624231725/https://academy.fpblock.com/blog/2016/11/comparative-concurrency-with-haskell/).*

Last week, I was at [DevConTLV X](https://devcontlvx.events.co.il/) and attended a [workshop](https://devcontlvx.events.co.il/presentations/4129-4-languages-in-4-hours) by [Aaron Cruz](https://twitter.com/mraaroncruz). While the title was a bit of a lie (it wasn't four hours, and we didn't do a chat app), it was a great way to see some basics of concurrency in different languages. Of course, that made me all the more curious to add Haskell to the mix.

I've provided multiple different implementations of this program in Haskell, focusing on different approaches (matching the approaches of the other languages, highly composable code, and raw efficiency). These examples are intended to be run and experimented with. The only requirement is that you [install the Haskell build tool Stack](https://web.archive.org/web/2025/https://haskell-lang.org/get-started). You can [download a Windows installer](https://www.stackage.org/stack/windows-x86_64-installer), or on OS X and Linux run:

``` text
curl -sSL https://get.haskellstack.org/ | sh
```

We'll start with approaches very similar to other languages like Go and Rust, and then dive into techniques like Software Transactional Memory which provide a much improved concurrency experience for more advanced workflows. Finally we'll dive into the async library, which provides some very high-level functions for writing concurrent code in a robust manner.

Unfortunately I don't have access to the source code for the other languages right now, so I can't provide a link to it. If anyone has such code (or wants to write up some examples for other lanugages), please [let me know](https://twitter.com/snoyberg) so I can add a link.

## The problem

We want to spawn a number of worker threads which will each sleep for a random period of time, grab an integer off of a shared work queue, square it, and put the result back on a result queue. Meanwhile, a master thread will fill up the work queue with integers, and read and print results.

## Running the examples

Once you've installed Stack, you can save each code snippet into a file with a `.hs` extension (like `concurrency.hs`), and then run it with `stack concurrency.hs`. If you're on OS X or Linux, you can also:

``` text
chmod +x concurrency.hs
./concurrency.hs
```

The first run will take a bit longer as it downloads the GHC compiler and installs library dependencies, but subsequent runs will be able to use the cached results. You can [read more about scripting with Haskell](../../haskell/tutorial/stack-script/).

## Channels

Most of the other language examples used some form of channels. We'll begin with a channel-based implementation for a convenient comparison to other language implementations. As you'll see, Haskell's channel-based concurrency is quite similar to what you'd experience in languages like Go and Elixir.

``` haskell
#!/usr/bin/env stack
-- stack --install-ghc --resolver lts-6.23 runghc --package random
import Control.Concurrent (forkIO, threadDelay, readChan, writeChan, newChan)
import Control.Monad (forever)
import System.Random (randomRIO)

-- The following type signature is optional. Haskell has type
-- inference, which makes most explicit signatures unneeded. We
-- usually include them at the top level for easier reading.
workerCount, workloadCount, minDelay, maxDelay :: Int
workerCount = 250
workloadCount = 10000
minDelay = 250000 -- in microseconds, == 0.25 seconds
maxDelay = 750000 --                  == 0.75 seconds

-- Launch a worker thread. We take in the request and response
-- channels to communicate on, as well as the ID of this
-- worker. forkIO launches an action in a new thread, and forever
-- repeats the given action indefinitely.
worker requestChan responseChan workerId = forkIO $ forever $ do
    -- Get a random delay value between the min and max delays
    delay <- randomRIO (minDelay, maxDelay)
    -- Delay this thread by that many microseconds
    threadDelay delay
    -- Read the next item off of the request channel
    int <- readChan requestChan
    -- Write the response to the response channel
    writeChan responseChan (workerId, int * int)

main = do
    -- Create our communication channels
    requestChan <- newChan
    responseChan <- newChan

    -- Spawn off our worker threads. mapM_ performs the given action
    -- on each value in the list, which in this case is the
    -- identifiers for each worker.
    mapM_ (worker requestChan responseChan) [1..workerCount]

    -- Define a helper function to handle each integer in the workload
    let perInteger int = do
            -- Write the current item to the request channel
            writeChan requestChan int
            -- Read the result off of the response channel
            (workerId, square) <- readChan responseChan
            -- Print out a little message
            putStrLn $ concat
                [ "Worker #"
                , show workerId
                , ": square of "
                , show int
                , " is "
                , show square
                ]

    -- Now let's loop over all of the integers in our workload
    mapM_ perInteger [1..workloadCount]
```

This is a pretty direct translation of how you would do things in a language like Go or Erlang/Elixir. We've replaced `for`-loops with `map`s, but otherwise things are pretty similar.

There's a major limitation in this implementation, unfortunately. In the master thread, our `perInteger` function is responsible for providing requests to the workers. However, it will only provide one work item at a time and then block for a response. This means that we are effectively limiting ourselves to one concurrent request. We'll address this in various ways in the next few examples.

## Compare-and-swap

It turns out in this case, we can use a lighter-weight alternative to a channel for the requests. Instead, we can just put all of our requests into an `IORef` - which is the basic mutable variable type in Haskell - and then pop requests off of the list inside that variable. Veterans of concurrency bugs will be quick to point out the read/write race condition you'd usually expect:

1.  Thread A reads the list from the variable
2.  Thread B reads the list from the variable
3.  Thread A pops the first item off the list and writes the rest to the variable
4.  Thread B pops the first item off the list and writes the rest to the variable

In this scenario, both threads A and B will end up with the same request to work on, which is certainly *not* our desired behavior. However, Haskell provides built-in compare-and-swap functionality, allowing us to guarantee that our read and write are *atomic operations*. This only works for a subset of Haskell functionality (specifically, the *pure* subset which does not have I/O side effects), which fortunately our pop-an-element-from-a-list falls into. Let's see the code.

``` haskell
#!/usr/bin/env stack
-- stack --install-ghc --resolver lts-6.23 runghc --package random
import Control.Concurrent (forkIO, threadDelay, writeChan, readChan, newChan)
import Data.IORef (atomicModifyIORef, newIORef)
import Control.Monad (replicateM_)
import System.Random (randomRIO)

workerCount = 250
workloadCount = 10000
minDelay = 250000
maxDelay = 750000

worker requestsRef responseChan workerId = forkIO $ do
    -- Define a function to loop on the available integers in the
    -- requests reference.
    let loop = do
            delay <- randomRIO (minDelay, maxDelay)
            threadDelay delay

            -- atomicModifyIORef is our compare-and-swap function. We
            -- give it a reference, and a function that works on the
            -- contained value. That function returns a pair of the
            -- new value for the reference, and a return value.
            mint <- atomicModifyIORef requestsRef $ \requests ->
                -- Let's see if we have anything to work with...
                case requests of
                    -- Empty list, so no requests! Put an empty list
                    -- back in and return Nothing
                    [] -> ([], Nothing)
                    -- We have something. Put the tail of the list
                    -- back in the reference, and return the new item.
                    int:rest -> (rest, Just int)

            -- Now we'll see what to do next based on whether or not
            -- we got something from the requests reference.
            case mint of
                -- No more requests, stop looping
                Nothing -> return ()
                -- Got one, so...
                Just int -> do
                    -- Write the response to the response channel
                    writeChan responseChan (workerId, int, int * int)
                    -- And loop again
                    loop

    -- Kick off the loop
    loop

main = do
    -- Create our request reference and response channel
    requestsRef <- newIORef [1..workloadCount]
    responseChan <- newChan

    mapM_ (worker requestsRef responseChan) [1..workerCount]

    -- We know how many responses to expect, so ask for exactly that
    -- many with replicateM_.
    replicateM_ workloadCount $ do
        -- Read the result off of the response channel
        (workerId, int, square) <- readChan responseChan
        -- Print out a little message
        putStrLn $ concat
            [ "Worker #"
            , show workerId
            , ": square of "
            , show int
            , " is "
            , show square
            ]
```

Compare-and-swap operations can be significantly more efficient than using true concurrency datatypes (like the `Chan`s we saw above, or Software Transactional Memory). But they are also limiting, and don't compose nicely. Use them when you need a performance edge, or have some other reason to prefer an `IORef`.

Compared to our channels example, there are some differences in behavior:

- In the channels example, our workers looped forever, whereas here they have an explicit stop condition. In reality, the Haskell runtime will automatically kill worker threads that are blocked on a channel without any writer. However, we'll see how to use closable channels in a later example.
- The channels example would only allow one request on the request channel at a time. This is similar to some of the examples from other languages, but defeats the whole purpose of concurrency: only one worker will be occupied at any given time. This `IORef` approach allows multiple workers to have work items at once. (Again, we'll see how to achieve this with channels in a bit.)

You may be concerned about memory usage: won't holding that massive list of integers in memory all at once be expensive? Not at all: Haskell is a *lazy* language, meaning that the list will be constructed on demand. Each time a new element is asked for, it will be allocated, and then can be immediately garbage collected.

## Software Transactional Memory

One of the most powerful concurrency techniques available in Haskell is Software Transactional Memory (STM). It allows us to have mutable variables, and to make modifications to them atomically. For example, consider this little snippet from a theoretical bank account application:

``` haskell
transferFunds from to amt = atomically $ do
    fromOrig <- readTVar from
    toOrig <- readTVar to
    writeTVar from (fromOrig - amt)
    writeTVar to (toOrig + amt)
```

In typically concurrent style, this would be incredibly unsafe: it's entirely possible for another thread to modify the `from` or `to` bank account values between the time our thread reads and writes them. However, with STM, we are guaranteed *atomicity*. STM will keep a ledger of changes made during an atomic transaction, and then attempt to commit them all at once. If any of the variables references have modified during the transaction, the ledger will be rolled back and tried again. And like `atomicModifyIORef` from above, Haskell disallows side-effects inside a transaction, so that this retry behavior cannot be observed from the outside world.

To stress this point: **Haskell's STM can eliminate the possibility for race conditions and deadlocks from many common concurrency patterns, greatly simplifying your code**. The leg-up that Haskell has over other languages in the concurrency space is the ability to take something that looks like calamity and make it safe.

We're going to switch our channels from above to STM channels. For the request channel, we'll use a bounded, closable channel (`TBMChan`). Bounding the size of the channel prevents us from loading too many values into memory at once, and using a closable channel allows us to tell our workers to exit.

``` haskell
#!/usr/bin/env stack
{- stack --install-ghc --resolver lts-6.23 runghc
    --package random --package stm-chans
-}
import Control.Concurrent (forkIO, threadDelay, readChan, writeChan, newChan)
import Control.Concurrent.STM (atomically, writeTChan, readTChan, newTChan)
import Control.Concurrent.STM.TBMChan (readTBMChan, writeTBMChan, newTBMChan, closeTBMChan)
import Control.Monad (replicateM_)
import System.Random (randomRIO)

workerCount = 250
workloadCount = 10000
minDelay = 250000 -- in microseconds, == 0.25 seconds
maxDelay = 750000 --                  == 0.75 seconds

worker requestChan responseChan workerId = forkIO $ do
    let loop = do
            delay <- randomRIO (minDelay, maxDelay)
            threadDelay delay

            -- Interact with the STM channels atomically
            toContinue <- atomically $ do
                -- Get the next request, if the channel is open
                mint <- readTBMChan requestChan
                case mint of
                    -- Channel is closed, do not continue
                    Nothing -> return False
                    -- Channel is open and we have a request
                    Just int -> do
                        -- Write the response to the response channel
                        writeTChan responseChan (workerId, int, int * int)
                        -- And yes, please continue
                        return True
            if toContinue
                then loop
                else return ()

    -- Kick it off!
    loop

main = do
    -- Create our communication channels. We're going to ensure the
    -- request channel never gets more than twice the size of the
    -- number of workers to avoid high memory usage.
    requestChan <- atomically $ newTBMChan (workerCount * 2)
    responseChan <- atomically newTChan

    mapM_ (worker requestChan responseChan) [1..workerCount]

    -- Fill up the request channel in a dedicated thread
    forkIO $ do
        mapM_ (atomically . writeTBMChan requestChan) [1..workloadCount]
        atomically $ closeTBMChan requestChan

    replicateM_ workloadCount $ do
        -- Read the result off of the response channel
        (workerId, int, square) <- atomically $ readTChan responseChan
        -- Print out a little message
        putStrLn $ concat
            [ "Worker #"
            , show workerId
            , ": square of "
            , show int
            , " is "
            , show square
            ]
```

Overall, this looked pretty similar to our previous channels, which isn't surprising given the relatively basic usage of concurrency going on here. However, using STM is a good default choice in Haskell applications, due to how easy it is to build up complex concurrent programs with it.

## Address corner cases

Alright, we've tried mirroring how examples in other languages work, given a taste of compare-and-swap, and explored the basics of STM. Now let's make our code more robust. The examples here - and those for other languages - often take some shortcuts. For example, what happens if one of the worker threads encounters an error? When our workload is simply "square a number," that's not a concern, but with more complex workloads this is very much expected.

Our first example, as mentioned above, didn't allow for true concurrency, since it kept the channel size down to 1. And all of our examples have made one other assumption: the number of results expected. In many real-world applications, one request may result in 0, 1, or many result values. So to sum up, let's create an example with the following behavior:

- If *any* of the threads involved abort exceptionally, take down the whole computation, leaving no threads alive
- Make sure that multiple workers can work in parallel
- Let the workers exit successfully when there are no more requests available
- Keep printing results until all worker threads exit.

We have one final tool in our arsenal that we haven't used yet: [the async library](../../haskell/library/async/), which provides some incredibly useful concurrency tools. Arguably, the most generally useful functions there are `concurrently` (which runs two actions in separate threads, as we'll describe in the comments below), and `mapConcurrently`, which applies `concurrently` over a list of values.

This example is how I'd recommend implementing this algorithm in practice: it uses solid library functions, accounts for exceptions, and is easy to extend for more complicated use cases.

``` haskell
#!/usr/bin/env stack
{- stack --install-ghc --resolver lts-6.23 runghc
    --package random --package async --package stm-chans
-}
import Control.Concurrent (threadDelay)
import Control.Concurrent.Async (mapConcurrently, concurrently)
import Control.Concurrent.STM (atomically)
import Control.Concurrent.STM.TBMChan (readTBMChan, writeTBMChan, newTBMChan, closeTBMChan)
import System.Random (randomRIO)

workerCount = 250
workloadCount = 10000
minDelay = 250000 -- in microseconds, == 0.25 seconds
maxDelay = 750000 --                  == 0.75 seconds

-- Not meaningfully changed from above, just some slight style
-- tweaks. Compare and contrast with the previous version if desired
-- :)
worker requestChan responseChan workerId = do
    let loop = do
            delay <- randomRIO (minDelay, maxDelay)
            threadDelay delay

            mint <- atomically $ readTBMChan requestChan
            case mint of
                Nothing -> return ()
                Just int -> do
                    atomically $
                        writeTBMChan responseChan (workerId, int, int * int)
                    loop
    loop

main = do
    -- Create our communication channels. Now the response channel is
    -- also bounded and closable.
    requestChan <- atomically $ newTBMChan (workerCount * 2)
    responseChan <- atomically $ newTBMChan (workerCount * 2)

    -- We're going to have three main threads. Let's define them all
    -- here. Note that we're _defining_ an action to be run, not
    -- running it yet! We'll run them below.
    let
        -- runWorkers is going to run all of the worker threads
        runWorkers = do
            -- mapConcurrently runs each function in a separate thread
            -- with a different argument from the list, and then waits
            -- for them all to finish. If any of them throw an
            -- exception, all of the other threads are killed, and
            -- then the exception is rethrown.
            mapConcurrently (worker requestChan responseChan) [1..workerCount]
            -- Workers are all done, so close the response channel
            atomically $ closeTBMChan responseChan

        -- Fill up the request channel, exactly the same as before
        fillRequests = do
            mapM_ (atomically . writeTBMChan requestChan) [1..workloadCount]
            atomically $ closeTBMChan requestChan

        -- Print each result
        printResults = do
            -- Grab a response if available
            mres <- atomically $ readTBMChan responseChan
            case mres of
                -- No response available, so exit
                Nothing -> return ()
                -- We got a response, so...
                Just (workerId, int, square) -> do
                    -- Print it...
                    putStrLn $ concat
                        [ "Worker #"
                        , show workerId
                        , ": square of "
                        , show int
                        , " is "
                        , show square
                        ]
                    -- And loop!
                    printResults

    -- Now that we've defined our actions, we can use concurrently to
    -- run all of them. This works just like mapConcurrently: it forks
    -- a thread for each action and waits for all threads to exit
    -- successfully. If any thread dies with an exception, the other
    -- threads are killed and the exception is rethrown.
    runWorkers `concurrently` fillRequests `concurrently` printResults

    return ()
```

By using the high level `concurrently` and `mapConcurrently` functions, we avoid any possibility of orphaned threads, and get automatic exception handling and cancelation functionality.

## Why Haskell

As you can see, Haskell offers many tools for advanced concurrency. At the most basic level, `Chan`s and `forkIO` give you pretty similar behavior to what other languages provide. However, `IORef`s with compare-and-swap provide a cheap concurrency primitive not available in most other languages. And the combination of STM and the `async` package is a toolset that to my knowledge has no equal in other languages. The fact that side-effects are explicit in Haskell allows us to do many advanced feats that wouldn't be possible elsewhere.

We've only just barely scratched the surface of what you can do with Haskell. If you're interested in learning more, please [check out our Haskell Syllabus](https://web.archive.org/web/2025/https://academy.fpblock.com/haskell-syllabus) for a recommended learning route. There's also lots of content on the [haskell-lang get started page](https://web.archive.org/web/2025/https://haskell-lang.org/get-started). And if you want to learn more about concurrency, check out [the async tutorial](../../haskell/library/async/).

FP Complete also provides corporate and group webinar training sessions. Please [check out our training page](https://web.archive.org/web/2025/https://academy.fpblock.com/training) for more information, or see our [consulting page](https://web.archive.org/web/2025/https://academy.fpblock.com/consulting) for how we can help your team succeed with devops and functional programming.

<a href="https://web.archive.org/web/2025/https://academy.fpblock.com/contact-us/" class="button-coral">Contact FP Complete</a>

## Advanced questions

We skirted some more advanced topics above, but for the curious, let me address some points:

- In our first example, we use `forever` to ensure that our workers would never exit. But once they had no more work to do, what happens to them? The Haskell runtime is smart enough to notice in general when a channel has no more writers, and will automatically send an asynchronous exception to a thread which is trying to read from such a channel. This works well enough for a demo, but is not recommended practice:

  1.  It's possible, though unlikely, that the runtime system won't be able to figure out that your thread should be killed
  2.  It's much harder to follow the logic of a program which has no explicit exit case
  3.  Using exceptions for control flow is generally a risk endeavor, and in the worst case, can [lead to very unexpected bugs](../async-exceptions-stm-deadlocks/)

- For the observant Haskeller, our definitions of `runWorkers` and `fillRequests` in the last example may look dangerous. Specifically: what happens if one of those actions throws an exception before closing the channel? The other threads reading from the channel will be blocked indefinitely! Well, three things:

  1.  As just described, the runtime system will likely be able to kill the thread if needed

  2.  However, because of the way we structured our program, it won't matter: if either of these actions dies, it will take down the others, so no one will end up blocked on a channel read

  3.  Nonetheless, I strongly recommend being exception-safe in all cases (I'm [kind of obsessed with it](../exceptions-best-practices-haskell/)), so a better way to implement these functions would be with `finally`, e.g.:

      ``` haskell
       fillRequests =
           mapM_ (atomically . writeTBMChan requestChan) [1..workloadCount]
               `finally` atomically (closeTBMChan requestChan)
      ```

- This post was explicitly about *concurrency*, or running multiple I/O actions at the same time. I avoided talking about the very much related topic of parallelism, which is speeding up a computation by performing work on multiple cores. In other languages, the distinction between these is minor. In Haskell, with our separation between purity and impurity, parallelism can often be achieved with something as simple as replacing `map` with `parMap` (parallel map).

  That said, it's certainly possible - and common - to implement parallelism via concurrency. In order to make that work, we would need to force evaluation of the result value (`int * int`) before writing it to the channel. This could be achieved with something like:

  ``` haskell
  let !result = int * int
  writeChan responseChan (workerId, result)
  ```

  The `!` is called a bang pattern, and indicates that evaluation should be forced immediately.
{% endraw %}
