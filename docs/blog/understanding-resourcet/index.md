---
layout: page
title: "Understanding ResourceT"
---
{% raw %}
*By Michael Snoyman, 19 June 2017. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2017/06/understanding-resourcet/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428051050/https://academy.fpblock.com/blog/2017/06/understanding-resourcet/).*

This blog post came out of two unrelated sets of questions I received last week about usage of the [resourcet](https://www.stackage.org/package/resourcet) library. For those unfamiliar with it, the library is often used in combination with the Conduit streaming data library; basically every [conduit](../../haskell/library/conduit/) [tutorial](https://www.snoyman.com/reveal/conduit-yesod#/) will quickly jump into usage of the resourcet library.

Instead of just teaching you how to use the library, this post will demonstrate why you need it and how it works internally, to help you avoid some of the potential pitfalls of the library. And stay tuned in the next week or two for a fun debugging storing around resourcet, bracket, and monad-control.

Anyway, back to our topic. To start off, consider some code to read a file and print its size:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
import qualified Data.ByteString as B
import qualified System.IO as IO

main :: IO ()
main = do
  bs <- myReadFile "/usr/share/dict/words"
  print $ B.length bs

myReadFile :: FilePath -> IO B.ByteString
myReadFile fp = IO.withBinaryFile fp IO.ReadMode $ \h ->
  -- Highly inefficient, use a builder instead
  let loop front = do
        next <- B.hGetSome h 4096
        if B.null next
          then return front
          else loop $ B.append front next
   in loop B.empty
```

However, this is highly inefficient: it reads the entire contents of the file into memory at once, when we don't need that. Instead, let's calculate that in a streaming fashion:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
{-# LANGUAGE BangPatterns #-}
import qualified Data.ByteString as B
import qualified System.IO as IO

main :: IO ()
main = do
  len <- myFileLength "/usr/share/dict/words"
  print len

-- Yes, there's hFileSize... ignore that
myFileLength :: FilePath -> IO Int
myFileLength fp = IO.withBinaryFile fp IO.ReadMode $ \h ->
  let loop !total = do
        next <- B.hGetSome h 4096
        if B.null next
          then return total
          else loop $ total + B.length next
   in loop 0
```

Notice that in both of these implementations, we've used `withBinaryFile` to open the file in such a way that the handle will be closed when we're done with it, regardless of whether an exception is thrown.

## Introduce continuations

But it's pretty unforunate that we've coupled together our file read logic with the logic that consumes the file. Let's make an abstraction similar to conduit to address that. We'll have an action which returns the next chunk of data from the file, and the following action to perform.

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
{-# LANGUAGE BangPatterns #-}
import qualified Data.ByteString as B
import qualified System.IO as IO

data IOSource a
  = IOChunk a (IO (IOSource a))
  | IODone

sourceHandle :: IO.Handle -> IO (IOSource B.ByteString)
sourceHandle h = do
  next <- B.hGetSome h 4096
  return $
    if B.null next
      then IODone
      else IOChunk next (sourceHandle h)

sourceFile :: FilePath -> IO (IOSource B.ByteString)
sourceFile fp = IO.withBinaryFile fp IO.ReadMode sourceHandle

sourceLength :: IO (IOSource B.ByteString) -> IO Int
sourceLength =
    loop 0
  where
    loop !total mnext = do
      next <- mnext
      case next of
        IOChunk bs mnext' -> loop (total + B.length bs) mnext'
        IODone -> return total

main :: IO ()
main = do
  len <- sourceLength $ sourceFile "/usr/share/dict/words"
  print len
```

Our `IOSource` is essentially a slimmed-down conduit which can't consume any input, only produce output. That's good enough for proving our point. The `sourceHandle` function has the same basic structure to what we were doing in our first two code examples: read a chunk of data, see if it's null, and if not, we return that chunk and then keep going. We then do a trivial wrapping up of `sourceHandle` with `sourceFile`, which uses the same `withBinaryFile` we had before. Finally, `sourceLength` just grabs the successive chunks from a given `IOSource` and counts the total bytes.

There's a major bug in this program. Try to spot it. Think through the control flow of this program. I encourage you to actually figure it out for yourself instead of just continuing to my explanation below.

**Hint 1** This isn't a subtle exception-handling bug, it makes the program above completely broken in all cases (except, interestingly, the case of an empty file). You will never get a valid result, besides the empty file case.

**Hint 2** The output when I run this program is `/usr/share/dict/words: hGetBufSome: illegal operation (handle is closed)`.

**Explanation** When we enter the `sourceFile` function, we first call `withBinaryFile`. This opens up a file handle. We hand this file handle to `sourceHandle`, which reads the first chunk of data from the file, and returns an `IOChunk` value containing that chunk and a *continuation*, or instruction on what to do next. This continuation is an `IO` action, and it refers to that file handle we were given by `sourceFile`. (This bit is vital.) We then return this `IOChunk` value from `sourceHandle` to `sourceFile`. Inside `sourceFile`, we now trigger the cleanup bit of `withBinaryFile`, which closes the handle, and then return the `IOChunk` value back to the caller.

When we consume that `IOChunk` value, we will proceed to perform that continuation we were handed back. That continuation refers to the previously opened file handle, and will try to read from it. See the problem? *We've already closed it!* There is nothing we can do with it anymore.

## Explicit close

Let's try rewriting this to delay the closing of the file handle until the handle is fully consumed. Also, let's replace our `sourceLength` function with a new function: it tells us what the first byte in the file is. I've also added a `putStrLn` to tell us when we're closing the file handle.

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
{-# LANGUAGE BangPatterns #-}
import qualified Data.ByteString as B
import qualified System.IO as IO
import Data.Word (Word8)

data IOSource a
  = IOChunk a (IO (IOSource a))
  | IODone

sourceHandle :: IO.Handle -> IO (IOSource B.ByteString)
sourceHandle h = do
  next <- B.hGetSome h 4096
  if B.null next
    then do
      putStrLn "Closing file handle"
      IO.hClose h
      return IODone
    else return $ IOChunk next (sourceHandle h)

sourceFile :: FilePath -> IO (IOSource B.ByteString)
sourceFile fp = do
  h <- IO.openBinaryFile fp IO.ReadMode
  sourceHandle h

firstByte :: IO (IOSource B.ByteString) -> IO (Maybe Word8)
firstByte mnext = do
  next <- mnext
  return $
    case next of
      IOChunk bs _mnext' -> Just $ B.head bs
      IODone             -> Nothing

main :: IO ()
main = do
  mbyte <- firstByte $ sourceFile "/usr/share/dict/words"
  print mbyte
```

OK, take a guess at the output. In particular, will our file handle be closed, and why?

It turns out that, when dealing with continuations, there is no way to guarantee that your continuation will ever get called. In our case, we're only interested in reading the first chunk of data from the file, and want to ignore the rest. As a result, our cleanup code will never get called. This doesn't even get into the fact that, if an exception is thrown, we have no exception handler in place to perform cleanup. The moral of the story:

> Continuation based approaches, like conduit or `ContT`, cannot guarantee that cleanup code will be run.

(Side note: conduit actually adds a concept called *finalizers* to address the non-exception case and to ensure cleanup happens promptly. But that's not our topic today.)

So what's the right way to write this code? You have to use `withBinaryFile` *outside* of your `sourceHandle` call entirely, like this:

``` haskell
main :: IO ()
main = do
  mbyte <- IO.withBinaryFile "/usr/share/dict/words" IO.ReadMode
         $ \h -> firstByte $ sourceHandle h
  print mbyte
```

## Why this is bad

Firstly, there's an aesthetic argument again the above code. A function like `sourceFile` is convenient, elegant, and simple to teach. Telling people that they need to open their file handles first can be confusing. But this isn't the only problem. Let's consider a few more complicated cases:

1.  I want to create an `IOSource` that reads from two files, not just one. Ideally, we would only keep one file handle open at a time. If you follow through on the `withBinaryFile` approach above, you'd realize you need to open up both files before you get started. This is a performance problem of using too many resources.
2.  Suppose you want to read a file, and each line in that file will tell you a new file to open and stream from. In this case, we won't know statically how many files to open, or even *which* files to open. Since these facts are dynamically determined, our `withBinaryFile` approach *won't work at all*.
3.  If the previous example seems a bit far-fetched, that's *exactly* the case when doing a deep directory traversal. We start with a top level directory, and for each entry, may or may not need to open up a new directory handle, depending on whether it's a directory or not.

In other words: this approach is a bit cumbersome to use, resource-inefficient, and prevents some programs from being written at all. We need something better.

## Why withBinaryFile works

The reason that `withBinaryFile` solves our problems is that it lives *outside* of our continuation framework. It is not subject to the whims of whether a specific continuation will or will not be called. It lives in `IO` directly, and we know how to install a cleanup function which will always be called, regardless of whether an exception is thrown or not. Specifically: we can just use `bracket`.

We need some way to pair the control that `bracket` provides from outside our continuation with the dynamic allocations we want to perform inside our continuations.

## A simplified ResourceT

In order to make this work, we'll implement a simplified version of `ResourceT`. We'll keep a list of file handles that need to be closed. But since we need to be able to update that list dynamically from within our continuation code, this will be a mutable list (wrapped in an `IORef`). Also, for simplicity, we'll make it `ResourceIO` instead of a proper monad transformer.

Note that, by sticking to just a list of file handles, we've simplified our work significantly. File handles can be closed multiple times, and closing a file handle is not supposed to throw an exception itself (though it can in some corner cases; we're ignoring that). The actual code for `ResourceT` ensures that cleanups only happen one time and explicitly deals with exceptions from cleanup code.

``` haskell
{-# LANGUAGE DeriveFunctor #-}
module ResourceIO
  ( ResourceIO
  , runResourceIO
  , openBinaryFile
  ) where

import Data.IORef
import qualified System.IO as IO
import Control.Exception
import Control.Monad
import Control.Monad.IO.Class

newtype ResourceIO a = ResourceIO (IORef [IO.Handle] -> IO a)
  deriving Functor

instance Applicative ResourceIO where
  pure x = ResourceIO $ \_ -> return x
  (<*>) = ap
instance Monad ResourceIO where
  return = pure
  ResourceIO f >>= g = ResourceIO $ \ref -> do
    x <- f ref
    let ResourceIO g' = g x
    g' ref
instance MonadIO ResourceIO where
  liftIO m = ResourceIO $ \_ref -> m

runResourceIO :: ResourceIO a -> IO a
runResourceIO (ResourceIO inner) = bracket
  (newIORef [])
  cleanup
  inner
  where
    cleanup ref = do
      handles <- readIORef ref
      mapM_ IO.hClose handles

openBinaryFile :: FilePath -> IO.IOMode -> ResourceIO IO.Handle
openBinaryFile fp mode = ResourceIO $ \ref -> mask $ \restore -> do
  h <- restore $ IO.openBinaryFile fp mode
  atomicModifyIORef' ref $ \hs -> (h:hs, ())
  return h
```

Most of the code here is involved in implementing a `Monad`/`MonadIO` interface for `ResourceIO`. If you focus on `runResourceIO`, you'll see that, as promised, we're using `bracket`. We create our shared mutable reference, ensure that `cleanup` is called regardless of exceptions, and then run the user-provided action.

`openBinaryFile` demonstrates how we would allocate resources. We open the file, and immediately modify our list of open handles to include the newly opened handle. In the real `ResourceT`, this is generalized to `IO ()` actions to perform arbitrary cleanup.

Side note: if you're confused about the usage of `mask` here, it's to deal with the possibility of asynchronous exceptions, and to make sure an exception is not thrown between the call to `openBinaryFile` and `atomicModifyIORef'`. Proper async exception handling is a complicated topic, which is why it's best to stick to library functions like `bracket` and libraries like [safe-exceptions](../../haskell/library/safe-exceptions/) that are designed to handle them.

## Using it

We need to make some minor modifications to our program in order to use this. Firstly, we specialized `IOSource` to using `IO` actions only. We're now going to want this thing to run in `ResourceIO`, so let's add a type parameter to indicate the base monad (just like `ConduitM` has). And let's also call a spade a spade, and rename from `IOSource` to `ListT`. This is, after all, the correctly implemented list monad transformer. (Ignore the one from the transformers package, it's completely broken.)

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
{-# LANGUAGE BangPatterns #-}
import qualified Data.ByteString as B
import qualified System.IO as IO
import Data.Word (Word8)
import ResourceIO
import Control.Monad.IO.Class

data ListT m a
  = ConsT a (m (ListT m a))
  | NilT

sourceHandle :: MonadIO m => IO.Handle -> m (ListT m B.ByteString)
sourceHandle h = liftIO $ do
  next <- B.hGetSome h 4096
  if B.null next
    then do
      IO.hClose h
      return NilT
    else return $ ConsT next (sourceHandle h)

sourceFile :: FilePath -> ResourceIO (ListT ResourceIO B.ByteString)
sourceFile fp = do
  h <- openBinaryFile fp IO.ReadMode
  sourceHandle h

firstByte :: Monad m => m (ListT m B.ByteString) -> m (Maybe Word8)
firstByte mnext = do
  next <- mnext
  return $
    case next of
      ConsT bs _mnext' -> Just $ B.head bs
      NilT             -> Nothing

main :: IO ()
main = do
  mbyte <- runResourceIO $ firstByte $ sourceFile "/usr/share/dict/words"
  print mbyte
```

Note that there's no longer any call with `withBinaryFile`, and we have all of the exception safety guarantees we want. We can even implement something which reads two files in sequence, and have the desired behavior of only having one file open at a time:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
{-# LANGUAGE BangPatterns #-}
import qualified Data.ByteString as B
import qualified System.IO as IO
import Data.Word (Word8)
import ResourceIO
import Control.Monad.IO.Class

data ListT m a
  = ConsT a (m (ListT m a))
  | NilT

appendListT :: Monad m
            => m (ListT m a)
            -> m (ListT m a)
            -> m (ListT m a)
appendListT left0 right =
    loop left0
  where
    loop mnext = do
      next <- mnext
      case next of
        ConsT x mnext' -> return $ ConsT x $ loop mnext'
        NilT           -> right

sourceHandle :: MonadIO m => IO.Handle -> m (ListT m B.ByteString)
sourceHandle h = liftIO $ do
  next <- B.hGetSome h 4096
  if B.null next
    then do
      IO.hClose h
      return NilT
    else return $ ConsT next (sourceHandle h)

sourceFile :: FilePath -> ResourceIO (ListT ResourceIO B.ByteString)
sourceFile fp = do
  h <- openBinaryFile fp IO.ReadMode
  sourceHandle h

sourceLength :: Monad m => m (ListT m B.ByteString) -> m Int
sourceLength =
    loop 0
  where
    loop !total mnext = do
      next <- mnext
      case next of
        ConsT bs mnext' -> loop (total + B.length bs) mnext'
        NilT            -> return total

main :: IO ()
main = do
  len <- runResourceIO $ sourceLength $ appendListT
    (sourceFile "/usr/share/dict/words")
    (sourceFile "/usr/share/dict/words")
  print len
```

## Concurrency

If you looked in the code above, I used `atomicModifyIORef'` to add a new file handle to the cleanup queue. You may think that this means we're concurrency-friendly. However, we aren't at all. Let's start by adding a new function to our `ResourceIO` interface:

``` haskell
asyncResourceIO :: ResourceIO a -> ResourceIO (Async a)
asyncResourceIO (ResourceIO f) = ResourceIO $ \ref -> async $ f ref
```

This uses the [async library](../../haskell/library/async/) to fork a thread and provides an `Async` value to retrieve the value from that thread when it completes. Now let's naively use it in our `main` function:

``` haskell
main :: IO ()
main = do
  alen <- runResourceIO $ asyncResourceIO $ sourceLength $
    (sourceFile "/usr/share/dict/words")
  putStrLn "Do some other work in the main thread, may take a while..."
  threadDelay 100000
  len <- wait alen
  print len
```

With the ominous introduction I gave this, answer this question: do you think this is going to work? And why or why not?

Let's step through what's going to happen here:

1.  `runResourceIO` creates a mutable reference to hold onto file handles to be closed
2.  `asyncResourceIO` forks a child thread
3.  Child thread opens up a file handle and adds it to the mutable reference of things to clean up
4.  Parent thread finishes forking the child thread, and (from within `runResourceIO`) calls the cleanup action, closing the file handle
5.  Child thread continues to do work, but throws an exception trying to read from the (now closed) file handle

Actually, that's just one possible scenario. Another possibility is that the parent thread will call cleanup before the child thread grabs the file handle. In which case, the reads will succeed, but we'll have no guarantee that the file handle will be cleaned up. In other words, we have a race condition.

This should stress the important of getting concurrency and `ResourceT` correct. We need to make sure that `runResourceT` does not close any resources that are still being consumed by child threads. One way to do that is to use the [`resourceForkIO`](https://www.stackage.org/haddock/lts-8.18/resourcet-1.1.9/Control-Monad-Trans-Resource.html#v:resourceForkIO) function, which introduces a reference counting scheme to ensure that resources are only closed when *all* threads are done with them.

Unfortunately, due to how the monad-control instances for `ResourceT` work, using concurrency functions from `lifted-base` or `lifted-async` will not use this reference counting behavior. Overall, my recommendation is: don't fork threads when inside `ResourceT` if you can avoid it.

## Other ways to abuse ResourceT

There is no actual scoping of the resources you get from `ResourceT` to ensure that they are still alive. Such techniques do exist (e.g., [`regions`](https://www.stackage.org/package/regions)), but the types are significantly more complicated, which is why the conduit ecosystem sticks to `ResourceT`.

The simplest demonstration of breaking this is:

``` haskell
main :: IO ()
main = do
  h <- runResourceIO $ openBinaryFile "/usr/share/dict/words" IO.ReadMode
  len <- sourceLength $ sourceHandle h
  print len
```

The handle we get back from `openBinaryFile` will be closed before we ever get a chance to pass it to `sourceHandle`. This code is just as broken as:

``` haskell
main :: IO ()
main = do
  h <- IO.withBinaryFile "/usr/share/dict/words" IO.ReadMode return
  len <- sourceLength $ sourceHandle h
  print len
```

But for many, the latter is more obviously wrong. The rule: make sure that your `runResourceIO` call lives around the entire scope that the resources will be used in.

As a more real-world example taken from a Twitter discussion, consider the following code that you might achieve by playing Type Tetris with Conduit:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
import Conduit

main :: IO ()
main = do
  len <- runConduit
       $ transPipe runResourceT (sourceFile "/usr/share/dict/words")
      .| lengthCE
  print len
```

`transPipe` applies some kind of a monad transformation at each step of the running of the given conduit. So each time we try to perform some action in `sourceFile`, we'll create a new mutable reference of cleanup actions, perform the action, and then immediately clean up the resources we allocated. In reality, we want those resources to persist through later continuations within the `sourceFile`. We would rewrite the code above to:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
import Conduit

main :: IO ()
main = do
  len <- runResourceT
       $ runConduit
       $ sourceFile "/usr/share/dict/words"
      .| lengthCE
  print len
```

Or, since `runConduitRes = runResourceT . runConduit`:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-8.12 script
import Conduit

main :: IO ()
main = do
  len <- runConduitRes
       $ sourceFile "/usr/share/dict/words"
      .| lengthCE
  print len
```
{% endraw %}
