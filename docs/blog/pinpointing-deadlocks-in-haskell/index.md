---
layout: page
title: "Pinpointing deadlocks in Haskell"
---
{% raw %}
*By Alexey Kuleshevich, 9 May 2018. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2018/05/pinpointing-deadlocks-in-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428060422/https://academy.fpblock.com/blog/2018/05/pinpointing-deadlocks-in-haskell/).*

Concurrent programming is hard! I still remember the moment of my introduction to multi-threaded programming at the University of New Mexico, our professor grabbed his head and said: “Here be demons!”. There are all sorts of issues that arise in a concurrent setup, such as race conditions, starvation, deadlocks, data corruption, you name it. All of these are also applicable to Haskell, and in this post, I would like to introduce a simple yet very effective way to track down deadlocks.

## Motivation

Unlike imperative programming languages, functional languages have a huge advantage in parallelization of computation, it just comes naturally and almost problem free from the property of referential transparency. Haskell adds an even bigger advantage, namely its type system, it will give you guarantees that computation can indeed be safely parallelized. Recently I've been working on a parallel array processing library [massiv](https://github.com/lehins/massiv) that can take advantage of all that power. In order for computation to be balanced among all cores equivalently and automatically, custom scheduler had to be implemented that would manage all that work, which is not a trivial task no matter what the language.

There are some amazing libraries available that can save you from the world of hurt that I'd like to recommend for multi-threaded programming right off the bat: [stm](https://www.stackage.org/package/stm), [async](https://www.stackage.org/package/async) and [unliftio](https://www.stackage.org/package/unliftio). Unfortunately, the task I had at hand would not have become easier if I used any of those libraries, plus I wanted to keep dependency footprint to a minimum, so the only thing that I was left with was the `MVar` primitive. While working on the scheduler, despite all of the hard thinking, I did get myself in a situation of an occasional, but consistent deadlock. The nature of the deadlock isn't really important to this discussion, but what is important is how deadlocks do usually look in Haskell and how do we track them down. Neither of the above mentioned libraries actually prevent deadlocks from occurring, but the method described here on locating them is very simple and will work regardless if you use any third party libraries or not.

## Blocking variables

There are two mutable variables that you can actually block a thread on in GHC, either an `MVar` or a `TVar`. It is almost guaranteed that GHC's Runtime System (RTS) will actually detect when you are blocked on such a variable that isn't referenced by any other thread that is still making progress, which would mean that it can't be unblocked, and for that reason it will throw either `BlockedIndefinitelyOnMVar` or `BlockedIndefinitelyOnSTM` exception, depending on what type of variable you are blocked on. This is how they look like in the terminal:

``` text
thread blocked indefinitely in an MVar operation
```

or

``` text
thread blocked indefinitely in an STM transaction
```

This is very impressive, considering that in most other languages you normally end up with a forever hanging process that must be brutally killed. At the same time, this exception doesn't tell us where exactly in our code the deadlock actually happened, and that's a problem. We do know all the functions in our code that do the blocking, such as `takeMVar`, `putMVar`, `readMVar`, etc. Therefore we can positively identify all locations where this exception could have originated from. If there are one or two occurrences of those blocking functions in the code, there is probably no need for any clever techniques in figuring out the location, but when there are a bunch of them, it is easy to get to the point of desperation.

The process of pinpointing deadlock locations isn't automatic, but it is simple and reliable. All we need to do is `catch` above mentioned exceptions, and it will tell us exactly where the deadlock came from:

``` haskell
import Control.Exception
import Say

hasLocked :: String -> IO a -> IO a
hasLocked msg action =
  action `catches`
  [ Handler $ \exc@BlockedIndefinitelyOnMVar -> sayString ("[MVar]: " ++ msg) >> throwIO exc
  , Handler $ \exc@BlockedIndefinitelyOnSTM -> sayString ("[STM]: " ++ msg) >> throwIO exc
  ]
```

Besides the deadlock detection, there is something else special about these two exceptions, they are both thrown like asynchronous exceptions, but they aren't considered as such. The reason why we can think of them as synchronous is because we know exact locations where they can occur, and this is the fact that we can abuse to locate our deadlocks.

If in doubt, here is an easy way to check if an exception is considered asynchronous:

``` haskell
λ> import Control.Exception
λ> asyncExceptionFromException (toException BlockedIndefinitelyOnMVar) :: Maybe BlockedIndefinitelyOnMVar
Nothing
λ> asyncExceptionFromException (toException AllocationLimitExceeded) :: Maybe AllocationLimitExceeded
Just allocation limit exceeded 
```

## ![Five Philosophers](../../assets/blog/pinpointing-deadlocks-in-haskell/66a6d2d03d69c3c83953adea3a69da62eee5c5f84fdf0abcc56cd0969a7e6ccd.png)

In order to understand exceptions better and to recognize the distinction between the two kinds I highly recommended reading Michael Snoyman's recent blog post <a href="../async-exception-handling-haskell/" style="letter-spacing: -0.005em;">Asynchronous Exception Handling in Haskell</a>.

## Dining Philosophers

Best way to understand a concept is to see it in action, so let's look at a simple but meaningful example. Consider this incorrect implementation of the famous [Dining philosophers problem](https://en.wikipedia.org/wiki/Dining_philosophers_problem):

``` haskell
import Control.Concurrent
import Say

main :: IO ()
main = do
  forks <- mapM (\i -> (,) i <$> newMVar ()) [1..5]
  mapM_ forkIO $ zipWith3 philosopher [2..] forks (tail forks)
  philosopher 1 (last forks) (head forks)

philosopher :: Int -> (Int, MVar ()) -> (Int, MVar ()) -> IO ()
philosopher num (_, forkLeft) (_, forkRight) = dine
  where
    dine = do
      sayString $ mkMsg num "thinking..."
      pickupForks forkLeft forkRight
      sayString $ mkMsg num "eating..."
      threadDelay 100000
      putDownForks forkLeft forkRight
      dine

pickupForks :: MVar () -> MVar () -> IO ()
pickupForks f1 f2 = do
  takeMVar f1
  threadDelay 10000
  takeMVar f2

putDownForks :: MVar () -> MVar () -> IO ()
putDownForks f1 f2 = putMVar f1 () >> putMVar f2 ()

mkMsg :: Int -> String -> String
mkMsg num str = "Philosopher " ++ show num ++ " is " ++ str
```

If you run the program above you will eventually run into a deadlock. Normally, it might take a while for that to happen, but careful placement of `threadDelay`s triggers it instantaneously.

``` bash
$ stack exec --package say -- ghc philosophers.hs -threaded -with-rtsopts='-N'
$ ./philosophers
Philosopher 1 is thinking...
Philosopher 3 is thinking...
Philosopher 4 is thinking...
Philosopher 5 is thinking...
Philosopher 2 is thinking...
example: thread blocked indefinitely in an MVar operation
```

We know exactly where the problem is, but let's pretend that we need to debug it. Looking at our `philosophers` function it is obvious that it is either `pickupForks` or `putDownForks` function that is at fault because both of them use blocking `takeMVar` and `putMVar` functions. Let's wrap around places of interest with our new tricky `hasLocked` function:

``` haskell
philosopher :: Int -> (Int, MVar ()) -> (Int, MVar ()) -> IO ()
philosopher num (_, forkLeft) (_, forkRight) = dine
  where
    dine = do
      sayString $ mkMsg num "thinking..."
      hasLocked (mkMsg num "DEADLOCKED on picking up forks") $
        pickupForks forkLeft forkRight
      sayString $ mkMsg num "eating..."
      threadDelay 100000
      hasLocked (mkMsg num "DEADLOCKED on putting down forks") $
        putDownForks forkLeft forkRight
      dine
```

Compiling the program as before and running it will reveal that all of our philosophers get deadlocked when trying to pickup a fork:

``` bash
$ ./philosophers
Philosopher 1 is thinking...
Philosopher 2 is thinking...
Philosopher 4 is thinking...
Philosopher 5 is thinking...
Philosopher 3 is thinking...
[MVar]: Philosopher 5 is DEADLOCKED on picking up forks
[MVar]: Philosopher 2 is DEADLOCKED on picking up forks
[MVar]: Philosopher 3 is DEADLOCKED on picking up forks
[MVar]: Philosopher 4 is DEADLOCKED on picking up forks
[MVar]: Philosopher 1 is DEADLOCKED on picking up forks
example: thread blocked indefinitely in an MVar operation
```

From then on we can move the `hasLocked` function deeper down the invocation tree to individual `takeMVar` functions in order to see exactly where the deadlock occurs.

## Timeout

It is important to understand that the approach described in this blog post isn't foolproof and it's best to use it for debugging purposes only. Consider this minor change to our incorrect implementation. Instead of making all threads participate in the algorithm, we'll have our main thread do nothing but occasionally look at the `MVar`s, without doing anything to unblock them:

``` haskell
main = do
  forks <- mapM (\i -> (,) i <$> newMVar ()) [1..5]
  mapM_ forkIO $ zipWith3 philosopher [1..] forks (tail forks ++ [head forks])
  let wait = do
        _areEmpty <- and <$> mapM (isEmptyMVar . snd) forks
        threadDelay 10000000 >> wait
  wait
```

This as well will result in a deadlock, but RTS has no way of knowing that, since the reference to `forks` is kept around in the main thread due to the usage of `isEmptyMVar`.

There is a workaround that can cope with such situations though. If we know that our thread shouldn't be blocking for more than some short period of time, then we can further wrap around our `hasLocked` function with a timeout:

``` text
import System.Timeout

hasLockedTimely :: Int -> String -> IO a -> IO a
hasLockedTimely n msg action =
  timeout n (hasLocked msg action) >>=
  maybe (sayString ("[Timeout]: " ++ msg) >> throwIO Deadlock) return
```

This time we'll wrap around the actual action of picking up a fork:

``` text
pickupForks :: Int -> MVar () -> MVar () -> IO ()
pickupForks num f1 f2 = do
  let mkMsg' fork = mkMsg num "DEADLOCKED on picking up " ++ fork
  hasLockedTimely 1000000 (mkMsg' "left fork") $ takeMVar f1
  threadDelay 100000
  hasLockedTimely 1000000 (mkMsg' "right fork") $ takeMVar f2
```

And sure enough, we now know the exact places where our program has deadlocked:

``` text
$ ./philosophers
Philosopher 5 is thinking...
Philosopher 1 is thinking...
Philosopher 3 is thinking...
Philosopher 2 is thinking...
Philosopher 4 is thinking...
[Timeout]: Philosopher 5 is DEADLOCKED on picking up right fork
philosophers: no threads to run:  infinite loop or deadlock?
[Timeout]: Philosopher 2 is DEADLOCKED on picking up right fork
[Timeout]: Philosopher 4 is DEADLOCKED on picking up right fork
[Timeout]: Philosopher 3 is DEADLOCKED on picking up right fork
philosophers: no threads to run:  infinite loop or deadlock?
[Timeout]: Philosopher 1 is DEADLOCKED on picking up right fork
philosophers: no threads to run:  infinite loop or deadlock?
philosophers: no threads to run:  infinite loop or deadlock?
philosophers: no threads to run:  infinite loop or deadlock?
^C
```

Just to verify that our trick doesn't interfere with correct functionality we'll apply the Dijkstra's solution:

``` haskell
philosopher :: Int -> (Int, MVar ()) -> (Int, MVar ()) -> IO ()
philosopher num (leftNum, forkLeft) (rightNum, forkRight) = dine
  where
    dine = do
      sayString $ mkMsg num "thinking..."
      if leftNum < rightNum
        then pickupForks num forkLeft forkRight
        else pickupForks num forkRight forkLeft
      sayString $ mkMsg num "eating..."
      threadDelay 100000
      putDownForks forkLeft forkRight
      dine
```

And now all of our dining philosophers can happily enjoy their spaghetti for all eternity:

``` text
$ ./philosophers
Philosopher 2 is thinking...
Philosopher 3 is thinking...
Philosopher 4 is thinking...
Philosopher 5 is thinking...
Philosopher 1 is thinking...
Philosopher 5 is eating...
Philosopher 5 is thinking...
Philosopher 4 is eating...
Philosopher 4 is thinking...
Philosopher 3 is eating...
Philosopher 5 is eating...
Philosopher 3 is thinking...
Philosopher 2 is eating...
Philosopher 5 is thinking...
Philosopher 4 is eating...
Philosopher 2 is thinking...
Philosopher 4 is thinking...
Philosopher 1 is eating...
Philosopher 1 is thinking...
...(never stops)
```

As a further improvement to this technique, say if it is ever to become a part of some library, it would be useful to utilize `TemplateHaskell` in order to report the exact location in the code automatically, instead of inferring it from a custom message. Alternatively, we could use `HasCallStack`, which sounds like a much better approach, and may even be something that could get added to GHC itself without any significant breaking compatibility.

## Conclusion

To sum it up, there is no need to be banging your head on a table when there is a deadlock in the code, with a bit of effort we can rely on GHC to point it out for us. Naturally, this is only one of many problems that can get in a way when writing concurrent programs, and despite that this technique proved itself pretty reliable, it can't point out logic errors and tell us the exact reason why the program reached a deadlock. We have experienced software engineers that can tackle problems like that with pleasure. Feel free to [reach out to us](https://web.archive.org/web/2025/https://academy.fpblock.com/contact-us) for any Haskell programming, no matter how easy or hard your project might be. Also, you can find more helpful reading materials in our [Haskell Syllabus](https://web.archive.org/web/2025/https://academy.fpblock.com/haskell-syllabus) as well as another blog post related to this topic: [Async Exceptions, STM, and Deadlocks.](../async-exceptions-stm-deadlocks/)
{% endraw %}
