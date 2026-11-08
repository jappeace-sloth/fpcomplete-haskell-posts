---
layout: page
title: "Asynchronous Exception Handling in Haskell"
---
{% raw %}
*By Michael Snoyman, 26 April 2018. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2018/04/async-exception-handling-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250405223544/https://academy.fpblock.com/blog/2018/04/async-exception-handling-haskell/).*

This post gives a deep dive into the Haskell exception system. If you are looking for a simpler tutorial on how to work with exceptions, I recommend our [safe exception handling tutorial](../../haskell/tutorial/exceptions/).

Last week, I gave a webinar on the topic of asynchrnous exceptions in Haskell. If you missed the webinar, I encourage you to check out [the video](https://web.archive.org/web/2025/https://academy.fpblock.com/blog/how-to-handle-asynchronous-exceptions-in-haskell). I've also [made the slides available](https://www.snoyman.com/reveal/async-exception-handling).

As is [becoming my practice](https://www.snoyman.com/blog/2017/12/what-makes-haskell-unique), I wrote up the content for this talk in the style of a blog post before creating the slides. I'm including that content below, for those who prefer a text based learning method.

------------------------------------------------------------------------

Runtime exceptions are common in many programming languages today. They offer a double-edged sword. On the one hand, they might make it (arguably) easier to write correct code, by removing the burden of checking return codes for every function. On the other hand, they can hide potential exit points in code, possibly leading to lack of resource cleanup.

GHC Haskell ups the ante even further, and introduces asynchronous exceptions. These allow for very elegant concurrent code to be written easily, but also greatly increase the surface area of potentially incorrect exception handling.

In this talk today, we're going to cover things from the ground up:

- Defining different types of exceptions
- Correct synchronous exception handling
- How bottom values play in
- Basics of async exceptions
- Masking and uninterruptible masking
- Helper libraries
- Some more complex examples

In order to fully address asynchronous exceptions, we're going to have to cover a lot of topics that aren't specifically related to asynchronous exceptions themselves. Don't be surprised that this won't seem like it has anything to do with async at first, we will get there.

Two important things I'd like everyone to keep in mind:

- Most of the time, simply using the appropriate helper library will work, and you won't have to remember all of the details we discuss today. It's still worthwhile to understand them.
- This talk is taking for granted that runtime synchronous and asynchronous exceptions are part of GHC Haskell, and discuss how best to work with it. There are lots of debates about whether they're a good idea or not, and when they should and shouldn't be used. I'm intentionally avoiding that for today's topic.

To whet your appetite: by the end of this talk, you should bad able to answer—with a few different reasons—why I've called this function `badRace`:

``` haskell
badRace :: IO a -> IO b -> IO (Either a b)
badRace ioa iob = do
  mvar <- newEmptyMVar
  tida <- forkIO $ ioa >>= putMVar mvar . Left
  tidb <- forkIO $ iob >>= putMVar mvar . Right
  res <- takeMVar mvar
  killThread tida
  killThread tidb
  return res
```

## Motivating example

Most complexity around exceptions pops up around scarce resources, and allocations which can fail. A good example of this is interacting with a file. You need to:

- Open the file handle, which might fail
- Interact with the file handle, which might fail
- Close the file handle regardless, since file descriptors are a scarce resource

### Pure code

Exceptions cannot be caught in pure code. This is very much by design, and fits in perfectly with the topic here. Proper exception handling is related to resource allocation and cleanup. Since pure code cannot allocate scarce resources or clean them up, it has no business dealing with exceptions.

Like all rules, this has exceptions:

- You can still throw from pure code
- You can use `unsafePerformIO` for allocations
- Memory can be allocated implicitly from pure code
  - Not a contradiction! We don't consider memory a scarce resource
- If you really want, you can catch exceptions from pure code, again via `unsafePerformIO`

But for the most part, we'll be focusing on non-pure code, and specifically the `IO` monad. We'll tangenitally reference transformers later.

## The land of no exceptions

Let's interact with a file in a theoretical Haskell that has no runtime exceptions. We'll need to represent all possible failure cases via explicit return values:

``` haskell
openFile :: FilePath -> IOMode -> IO (Either IOException Handle)
hClose :: Handle -> IO () -- assume it can never fail
usesFileHandle :: Handle -> IO (Either IOException MyResult)

myFunc :: FilePath -> IO (Either IOException MyResult)
myFunc fp = do
  ehandle <- openFile fp ReadMode
  case ehandle of
    Left e -> return (Left e)
    Right handle -> do
      eres <- usesFileHandle handle
      hClose handle
      return eres
```

The type system forces us to explicitly check whether each function succeeds or fails. In the case of `usesFileHandle`, we get to essentially ignore the failures and pass them on to the caller of the function, and simply ensure that `hClose` is called regardless.

## Land of synchyronous exceptions

Now let's uses a variant of Haskell which has synchronous exceptions. We'll get into exception hierarchy stuff later, but for now we'll just assume that all exceptions are `IOException`s. We add in two new primitive functions:

``` haskell
throwIO :: IOException -> IO a
try :: IO a -> IO (Either IOException a)
```

These functions throw synchronous exceptions. We'll define synchronous exceptions as:

**Synchronous exceptions are exceptions which are generated directly from the `IO` actions you are calling.**

Let's do the simplest transformation from our code above:

``` haskell
openFile :: FilePath -> IOMode -> IO Handle
hClose :: Handle -> IO ()
usesFileHandle :: Handle -> IO MyResult

myFunc :: FilePath -> IO MyResult
myFunc fp = do
  handle <- openFile fp ReadMode
  res <- usesFileHandle handle
  hClose handle
  return res
```

The code is certainly shorter, and the types are easier to read too. A few takeaways:

- We can no longer tell whether `openFile` and `hClose` can fail by looking at the type signature.
- There's no need to pattern match on the result of `openFile`; that's handled for us automatically.

But unfortunately, this code has a bug! Imagine if `usesFileHandle` throws an exception. `hClose` will never get called. Let's see if we can fix this using `try` and `throwIO`:

``` haskell
myFunc :: FilePath -> IO MyResult
myFunc fp = do
  handle <- openFile fp ReadMode
  eres <- try (usesFileHandle handle)
  hClose handle
  case eres of
    Left e -> throwIO e
    Right res -> return res
```

And just like that, our code is exception-safe, at least in a world of only-synchronous exceptions.

Unfortunately, this isn't too terribly nice. We don't want people having to think about this each time they work with a file. So instead, we capture the pattern in a helper function:

``` haskell
withFile :: FilePath -> IOMode -> (Handle -> IO a) -> IO a
withFile fp mode inner = do
  handle <- openFile fp mode
  eres <- try (inner handle)
  hClose handle
  case eres of
    Left e -> throwIO e
    Right res -> return res

myFunc :: FilePath -> IO MyResult
myFunc fp = withFile fp ReadMode usesFileHandle
```

**General principle** Avoid using functions which only allocate or only clean up whenever possible. Instead, try to use helper functions which ensure both operations are performed.

But even `withFile` could be generalized into something which runs both allocate and cleanup actions. We call this `bracket`. And in a synchronous-only world, it might look like this:

``` haskell
bracket :: IO a -> (a -> IO b) -> (a -> IO c) -> IO c
bracket allocate cleanup inner = do
  a <- allocate
  ec <- try (inner a)
  _ignored <- cleanup a
  case ec of
    Left e -> throwIO e
    Right c -> return c

withFile fp mode = bracket (openFile fp mode) hClose
```

**QUESTION** What happens if `cleanup` throws an exceptions? What *should* happen if `cleanup` throws an exceptions?

## Extensible exceptions

The type signatures we used for `catch` and `throwIO` are actually a bit of a lie. We've pretended here that all exceptions are of type `IOException`. In reality, however, GHC gives us the ability to create arbitrary types which can be thrown. This is in the same spirit as Java, which allows you to create hierarchies of classes.

Let's look at the relevant definitions:

``` haskell
data SomeException = forall e . Exception e => SomeException e

class (Typeable e, Show e) => Exception e where
  toException   :: e -> SomeException
  fromException :: SomeException -> Maybe e

throwIO :: Exception e => e -> IO a
try :: Exception e => IO a -> IO (Either e a)
```

The `Exception` typeclass defines some way to convert a value to a `SomeException`, and a way to try and convert from a `SomeException` into the given type. Then `throwIO` and `try` are generalized to working on any types that are instances of that type class. The `Show` instance helps for displaying exceptions, and `Typeable` provides the ability for runtime casting.

Here's a simple example of an exception data type:

``` haskell
data InvalidInput = InvalidInput String
  deriving (Show, Typeable)
instance Exception InvalidInput where
  toException ii = SomeException ii
  fromException (SomeException e) = cast e -- part of Typeable
```

Except that `toException` and `fromException` both have default implementations which match what we have above, so we could instead just write:

``` haskell
instance Exception InvalidInput
```

You can also create exception hierarchies, for example:

``` haskell
{-# LANGUAGE ExistentialQuantification #-}
import Control.Exception
import Data.Typeable

data MyAppException
  = InvalidInput String
  | SomethingElse SomeException
  deriving (Show, Typeable)
instance Exception MyAppException

data SubException = NetworkFailure String
  deriving (Show, Typeable)
instance Exception SubException where
  toException = toException . SomethingElse . SomeException
  fromException se = do
    SomethingElse (SomeException e) <- fromException se
    cast e

main :: IO ()
main = do
  e <- try $ throwIO $ NetworkFailure "Hello there"
  print (e :: Either SomeException ())
```

In OO terms, `SubException` is a child class of `MyAppException`. You may dislike this kind of adopted OO system, but it's part of GHC Haskell's exception mechanism. It's also vitally important to how we're going to deal with asynchronous exceptions later, which is why we're discussing it now.

Alright, onward to another tangent!

## Exceptions in pure code

It's funny that the function for throwing exceptions is called `throwIO`, right? Why not just `throw`? That's because it's unfortunately used for something else:

``` haskell
throw :: Exception e => e -> a
```

This generates an exception from within pure code. These kinds of exceptions are sometimes mistakenly called asynchronous exceptions. They are most certainly not! This section is about clearing up this misunderstanding. I'm going to term these kinds of exceptions **impure exceptions**, because they break pure code.

You can generate these kinds of exceptions a few different ways:

- Using the `throw` function directly
- Using a function which calls `throw`, like `error`
- Using partial functions like `head`
- Incomplete pattern matches (GHC automatically inserts the equivalent of a call to `throw`)
- Creating infinite loops in pure code, where GHC's runtime *may* detect the infinite loop and throw a runtime exception

Overall, partiality and impure exceptions are frowned upon in the Haskell world, because they're essentially a lie: claiming that a value has type `MyType`, when in reality it may also have an exception lurking inside of it. But this talk isn't about passing judgement, simply dealing with things.

There is no mechanism for directly catching impure exceptions. Only the `IO` based functions, like `try`, are able to catch them. Let's have a look at an example:

``` haskell
import Control.Exception
import Data.Typeable

data Dummy = Dummy
  deriving (Show, Typeable)
instance Exception Dummy

printer :: IO (Either Dummy ()) -> IO ()
printer x = x >>= print

main :: IO ()
main = do
  printer $ try $ throwIO Dummy
  printer $ try $ throw Dummy
  printer $ try $ evaluate $ throw Dummy
  printer $ try $ return $! throw Dummy
  printer $ try $ return $ throw Dummy
```

**QUESTION** What do you think is the output of this program?

This exercise relies on understanding GHC's evaluation method. If you're not intimately familiar with this, the solution may be a bit surprising. If there's interest, we can host another FP Complete webinar covering evaluation in the future. Here's the output:

``` text
Left Dummy
Left Dummy
Left Dummy
Left Dummy
Right Main.hs: Dummy
```

The fifth example is different than the other four.

1.  In `throwIO Dummy`, we're using proper runtime exceptions via `throwIO`, and therefore `Dummy` is thrown immediately as a runtime exception. Then `try` is able to catch it, and all works out well.
2.  In `throw Dummy`, we generate a value of type `IO ()` which, when evaluated, will throw a `Dummy` value. Passing this value to `try` forces it immediately, causing the runtime exception to be thrown. The result ends up being identical to using `throwIO`.
3.  In `evaluate $ throw Dummy`, `throw Dummy` has type `()`. The `evaluate` function then forces evaluation of that value, which causes the `Dummy` exception to be thrown.
4.  `return $! throw Dummy` is almost identical; it uses `$!`, which under the surface uses `seq`, to force evaluation. We're not going to dive into the difference between `evaluate` and `seq` today.
5.  `return $ throw Dummy` is the odd man out. We create a thunk with `throw Dummy` of type `()` which, when evaluated, will throw an exception. We then wrap that up into an `IO ()` value using `return`. `try` then forces evaluation of the `IO ()` value, which *does not* force evaluation of the `()` value, so no runtime exception is yet thrown. We then end up with a value of type `Either Dummy ()`, which is equivalent to `Right (throw Dummy)`. `printer` then attempts to print this value, finally forcing the `throw Dummy`, causing our program to crash due to the unhandled exception.

Alright, so what's the point of all of this? Well, two things:

1.  Despite not passing any judgement in this talk, let's pass some judgement: impure exceptions make things really confusing. You should avoid `throw` and `error` whenever you can, as well as partial functions and incomplete pattern matches. *If* you're going to use exceptions, use `throwIO`.
2.  Even though the exceptional value appears to pop up in almost “random” locations, the trigger for an impure exception crashing your program is always the same: evaluating a thunk that's hiding an exception. Therefore, impure exceptions are absolutely *synchronous exceptions*: the `IO` action you're performing now is causing the exception to be thrown.

For the most part, we don't think too much about impure exceptions when dealing with writing exception safe code. Look at the `withFile` example again:

``` haskell
withFile :: FilePath -> IOMode -> (Handle -> IO a) -> IO a
withFile fp mode inner = do
  handle <- openFile fp mode
  eres <- try (inner handle)
  hClose handle
  case eres of
    Left e -> throwIO e
    Right res -> return res
```

If `inner` returns an impure exception, it won't cause us any problem in `withFile`, since we never force the returned value. We're going to mostly ignore impure exceptions for the rest of this talk, and focus only on synchronous versus asynchronous exceptions.

## Motivating async exceptions

Let's try and understand why someone would want async exceptions in the first place. Let's start with a basic example: the `timeout` function. We want a function which will run an action for a certain amount of time, and if it hasn't completed by then, kill it:

``` haskell
timeout :: Int -- microseconds
        -> IO a -> IO (Maybe a)
```

Let's imagine we built this into the runtime system directly, and allowed a thread to simply die immediately. Then we wrote a program like:

``` haskell
timeout 1000000 $ bracket
  (openFile "foo.txt" ReadMode)
  hClose
  somethingReallySlow
```

We give our `somethingReallySlow` 1 second to complete. What happens if it takes more than 1 second? As described above, the thread it's running on will simply die immediately, preventing `hClose` from ever running. This defeats exception safety!

Instead, let's try and create something outside of the runtime system. We'll create a mutable variable for tracking whether the timeout has expired, and an `MVar` for the result of the operation. Then we'll use a helper function to check if we should exit the thread. It may look something like:

``` haskell
import Control.Concurrent (threadDelay, forkIO)
import Control.Concurrent.MVar
import Control.Exception
import Control.Monad (when, forever)
import Data.IORef
import Data.Typeable

data Timeout = Timeout
  deriving (Show, Typeable)
instance Exception Timeout

type CheckTimeout = IO ()

timeout :: Int -> (CheckTimeout -> IO a) -> IO (Maybe a)
timeout micros inner = do
  retval <- newEmptyMVar
  expired <- newIORef False
  let checkTimeout = do
        expired' <- readIORef expired
        when expired' $ throwIO Timeout
  _ <- forkIO $ do
    threadDelay micros
    writeIORef expired True
  _ <- forkIO $ do
    eres <- try $ inner checkTimeout
    putMVar retval $
      case eres of
        Left Timeout -> Nothing
        Right a -> Just a
  takeMVar retval

myInner :: CheckTimeout -> IO ()
myInner checkTimeout = bracket_
  (putStrLn "allocate")
  (putStrLn "cleanup")
  (forever $ do
    putStrLn "In myInner"
    checkTimeout
    threadDelay 100000)

main :: IO ()
main = timeout 1000000 myInner >>= print
```

On the bright side: this implementation reuses the existing runtime exception system to ensure exception safety, yay! But let's try and analyze the downsides of this approach:

- Since `checkTimeout` runs in `IO`, we can't use it in pure code. This means that long-run CPU computations cannot be interrupted.
- We need to remember to call `checkTimeout` in all relevant places. If we don't, our `timeout` won't work properly.

**BONUS** The code above has a potential deadlock in it due to mishandling of synchronous exceptions. Try and find it!

While this kind of approach kind of works, it doesn't make the job pleasant. Let's finally add in asynchronous exceptions.

## Asynchronous exceptions

**Async exceptions are exceptions thrown from another thread.** There is nothing performed in the currently running thread which causes the exception to occur. They bubble up just like synchronous exceptions. They can be caught with `try` (and friends like `catch`) just like synchronous exceptions. The difference is how they are *thrown*:

``` haskell
forkIO :: IO () -> IO ThreadId
throwTo :: Exception e => ThreadId -> e -> IO ()
```

In our hand-written `timeout` example above, calling `throwTo` is like setting `expired` to `True`. The question is: when does the target thread check if `expired` has been set to `True`/an async exception was thrown? The answer is that the runtime system does this for us automatically. And here's the important bit: **the runtime system can detect an async exceptions at any point**. This includes inside pure code. This solves both of our problems with our hand-rolled timeout mentioned above, but it creates a new one.

### The need for masking

Let's revisit our `withFile` function:

``` haskell
withFile :: FilePath -> IOMode -> (Handle -> IO a) -> IO a
withFile fp mode inner = do
  handle <- openFile fp mode
  eres <- try (inner handle)
  hClose handle
  case eres of
    Left e -> throwIO e
    Right res -> return res
```

But now, let's add in the async checking actions that the runtime system is doing for us:

``` haskell
withFile :: FilePath -> IOMode -> (Handle -> IO a) -> IO a
withFile fp mode inner = do
  checkAsync -- 1
  handle <- openFile fp mode
  checkAsync -- 2
  eres <- try (inner handle)
  checkAsync -- 3
  hClose handle
  checkAsync -- 4
  case eres of
    Left e -> throwIO e
    Right res -> return res
```

If `checkAsync` (1) or (4) throws an exception, everything's fine. But if (2) or (3) throws, we have a resource leak, and `hClose` won't be called! We need some way to tell the runtime system “don't check for async exceptions right now.” We call this *masking*, and we'll introduce the `mask_` function to demonstrate it:

``` haskell
mask_ :: IO a -> IO a
```

This function says “run the given action, and don't allow any async exceptions to get detected while it's running.” We can use this to fix our `withFile` function:

``` haskell
withFile :: FilePath -> IOMode -> (Handle -> IO a) -> IO a
withFile fp mode inner = mask_ $ do
  -- doesn't run, masked! -- checkAsync -- 1
  handle <- openFile fp mode
  -- same -- checkAsync -- 2
  eres <- try (inner handle)
  -- same -- checkAsync -- 3
  hClose handle
  -- same -- checkAsync -- 4
  case eres of
    Left e -> throwIO e
    Right res -> return res
```

We've fixed our resource leak, but we've introduced a new problem. Now there's no way to send an asynchronous exception to any part of our `withFile` function, including `inner`. If the user-supplied action takes a long time to run, we've essentially broken the `timeout` function. To work with this, we need to use the `mask` function, which provides a way to restore the previous masking state:

``` haskell
mask :: ((forall a. IO a -> IO a) -> IO b) -> IO b
```

**ADVANCED** You may wonder why this restores the previous masking state, instead of just unmasking. This has to do with nested maskings, and what is known as the “wormhole” problem. We're not going to cover that in detail.

Now we can write a much better `withFile`:

``` haskell
withFile :: FilePath -> IOMode -> (Handle -> IO a) -> IO a
withFile fp mode inner = mask $ \restore -> do
  handle <- openFile fp mode
  eres <- try (restore (inner handle))
  hClose handle
  case eres of
    Left e -> throwIO e
    Right res -> return res
```

It's completely safe to restore the masking state there, because the wrapping `try` will catch all asynchronous exceptions. As a result, we're guaranteed that, no matter what, `hClose` will be called if `openFile` succeeds.

### Catch 'em all!

We need to make one further tweak to our `withFile` example in order to make it type check. Let's look at a subset of the code:

``` haskell
eres <- try (restore (inner handle))
case eres of
  Left e -> throwIO e
```

The problem here is that both `try` and `throwIO` are polymorphic on the exception type (any instance of `Exception`). GHC doesn't know which concrete type you want. In this case, we want to catch *all* exceptions. To do that, with use the `SomeException` type, which in OO lingo would be the superclass of all exception classes. All we need is a type signature:

``` haskell
eres <- try (restore (inner handle))
case eres of
  Left e -> throwIO (e :: SomeException)
```

### Recover versus cleanup

There's nothing wrong with this bit of code. But let's write something slightly different and see if there's a problem.

``` haskell
import Control.Concurrent
import Control.Exception
import Data.Time
import System.Timeout

main :: IO ()
main = do
  start <- getCurrentTime
  res <- timeout 1000000 $ do
    x <- try $ threadDelay 2000000
    threadDelay 2000000
    return x
  end <- getCurrentTime
  putStrLn $ "Duration: " ++ show (diffUTCTime end start)
  putStrLn $ "Res: " ++ show (res :: Maybe (Either SomeException ()))
```

The output from this program is:

``` text
Duration: 3.004385s
Res: Just (Left <<timeout>>)
```

Despite the fact that the timeout was triggered:

- The duration is 3 seconds, not 1 second
- We get a `Just` result value instead of `Nothing`
- Inside the `Just` is an exception from the timeout

We've used our ability to catch all exceptions to catch an asynchronous exception. Previously, in our `withFile` example, I said this was fine. But for some reason, I'm saying it's not OK here. The rule governing this is simple:

**You cannot recover from an asynchronous exception**

When people speak abstractly about proper async exception handling, this is the rule they're usually hinting at. It's a simple enough idea, and in practice not that difficult to either explain or implement. But the abstract nature of “safe async exception handling” makes it much scarier than it should be. Let's fix that.

There are two reasons you may wish to catch an exception:

- You need to perform some kind of **cleanup** before letting the exception bubble up. This is what we do in the case of `withFile`: we catch the exception, perform our cleanup, and then **rethrow the exception**.
- Some action has thrown an exception, but instead of letting it bubble up and take down your entire thread, you want to **recover**. For example: you tried to read from a file, and it didn't exist, so you want to use some default value instead. In this case, we **catch and swallow** the exception without rethrowing it.

When dealing with synchronous exceptions, you're free to either perform cleanup and then rethrow the exception, or catch, swallow, and recover from the exception. It breaks no invariants of the world.

However, with asynchronous exceptions, you never want to recover. Asynchronous exceptions are messages from outside of your current execution saying “you must die as soon as possible.” If you swallow those exceptions, like we did in our `timeout` example, you break the very nature of the async exception mechanism. Instead, with async exceptions, you are allowed to clean up, but never recover.

Alright, that's nice in theory. In practice, how do we make that work?

### GHC's async exception flaw

When generating an exception, how do you decide whether the exception is synchronous or asynchronous? Simple: whether you ultimately use the `throwIO` function (synchronous), or the `throwTo` function (asynchronous). Therefore, in order to implement our logic above, we need some way to ask after using `try` which function threw the exception.

Unfortunately, no such function exists. And it's not just a matter of missing a library function. The GHC runtime system itself tracks no such information about its exceptions. It is impossible to make this differentiation!

I've used two different techniques over the years for distinguishing sync and async exceptions. The older one is now captured in the `enclosed-exceptions` package, based on forking threads. This one is heavier weight, and I don't recommend it anymore. These days, I recommend using a type-based approach, which is captured in both the `safe-exceptions` and `unliftio` packages. (More on these three packages later.)

**Word of warning** It is entirely possible to fool the mechanism I'm about to describe if you use `Control.Exception` directly. My general recommendation is to avoid using that module directly and instead use one of the helper modules that implements the type-based logic I'm going to describe. If you intentionally fool the type based detection, you can end up breaking the invariants we're discussing. Note that, for the most part, you have to *try* to break this mechanism when using `Control.Exception`.

Remember how we have that funny extensible exception mechanism in GHC that allows for OO-like exception hierarchies? And remember how all exceptions are ultimately children of `SomeException`? Starting in GHC 7.8, there's a new “child” of `SomeException`, called `SomeAsyncException`, which is the “superclass” of all asynchronous exception types. You can now detect if an exception is of an asynchronous exception type with a function like:

``` haskell
isSyncException :: Exception e => e -> Bool
isSyncException e =
    case fromException (toException e) of
        Just (SomeAsyncException _) -> False
        Nothing -> True

isAsyncException :: Exception e => e -> Bool
isAsyncException = not . isSyncException
```

We want to ensure that `throwIO` and `throwTo` only ever work on synchronous and asynchronous exceptions, respectively. We handle this with some helper, wrapper data types:

``` haskell
data SyncExceptionWrapper = forall e. Exception e => SyncExceptionWrapper e
instance Exception SyncExceptionWrapper

data AsyncExceptionWrapper = forall e. Exception e => AsyncExceptionWrapper e
instance Exception AsyncExceptionWrapper where
    toException = toException . SomeAsyncException
    fromException se = do
        SomeAsyncException e <- fromException se
        cast e
```

Next we implement helper conversion functions:

``` haskell
toSyncException :: Exception e => e -> SomeException
toSyncException e =
    case fromException se of
        Just (SomeAsyncException _) -> toException (SyncExceptionWrapper e)
        Nothing -> se
  where
    se = toException e

toAsyncException :: Exception e => e -> SomeException
toAsyncException e =
    case fromException se of
        Just (SomeAsyncException _) -> se
        Nothing -> toException (AsyncExceptionWrapper e)
  where
    se = toException e
```

Then we implement modified versions of `throwIO` and `throwTo`, as well as `impureThrow` (a replacement for the `throw` function):

``` haskell
import qualified Control.Exception as EUnsafe

throwIO :: (MonadIO m, Exception e) => e -> m a
throwIO = liftIO . EUnsafe.throwIO . toSyncException

throwTo :: (Exception e, MonadIO m) => ThreadId -> e -> m ()
throwTo tid = liftIO . EUnsafe.throwTo tid . toAsyncException

impureThrow :: Exception e => e -> a
impureThrow = EUnsafe.throw . toSyncException
```

Assuming that all exceptions are generated by these three functions, we can now rely upon types to differentiate. The final step is separating out our helper functions into those that **cleanup** (and rethrow the exception), which can work on any exception type, and those that **recover** (and do not rethrow the exception). An incomplete list is:

- Recovery
  - `catch`
  - `try`
  - `handle`
- Cleanup
  - `bracket`
  - `onException`
  - `finally`

Here's a simplified version of the `catch` function:

``` haskell
import qualified Control.Exception as EUnsafe

catch :: Exception e => IO a -> (e -> IO a) -> IO a
catch f g = f `EUnsafe.catch` \e ->
  if isSyncException e
    then g e
    -- intentionally rethrowing an async exception synchronously,
    -- since we want to preserve async behavior
    else EUnsafe.throwIO e
```

If you stick to this set of helper functions, you'll automatically meet the rules for safe async exception handling. You can even trivially perform a “pokemon” exception handler (catch 'em all):

``` haskell
tryAny :: MonadUnliftIO m => m a -> m (Either SomeException a)
tryAny = try

main :: IO ()
main = tryAny (readFile "foo.txt") >>= print
```

### Uninterruptible masking

Before going down this rabbit hole, it's worth remembering: if you use `Control.Exception.Safe` or `UnliftIO.Exception`, the complexity of interruptible versus uninterruptible masking is handled for you correctly in the vast majority of cases, and you don't need to worry about it. There *are* extreme corner case bugs that occur, but in my experience this is very low down on the list of common bugs experienced when trying to write exception safe code.

We've described two types of exceptions: synchronous (those generated by actions in the current thread), and asynchornous (those generated by another thread and sent to our thread). And we've introduced the `mask` function, which temporarily blocks all asynchronous exceptions in a thread. Right?

Not exactly. To quote GHC's documentation:

> Some operations are *interruptible*, which means that they can receive asynchronous exceptions even in the scope of a mask. Any function which may itself block is defined as interruptible… It is useful to think of `mask` not as a way to completely prevent asynchronous exceptions, but as a way to switch from asynchronous mode to polling mode.

Interruptible operations allow for a protection against deadlocks. Again borrowing from the docs, consider this example:

``` haskell
mask $ \restore -> do
  a <- takeMVar m
  restore (...) `catch` \e -> ...
```

If `takeMVar` could not be interrupted, it would be possible for it to block on an `MVar` which has no chance of ever being filled, leading to a deadlock. Instead, GHC's runtime system adds the concept that, within a `mask`ed section, some actions can be considered to “poll” and check if there are async exceptions waiting.

Unfortunately, this can somewhat undo the very purpose we introduced `mask` for in the first place, and allow resource cleanup to not always occur. Therefore, we have another function which blocks async exceptions, even within interruptible actions: `uninterruptibleMask`. The decision on when to use each one is not always obvious, as can be seen by [a relavant Github discussion](https://github.com/fpco/safe-exceptions/issues/3). Here are some general rules:

- If you're inside a `mask`, you can always “upgrade” to `uninterruptibleMask` inside. You can't upgrade from unmasked to masked in the same way, because in unmaksed code an async exception can occur anywhere, not just inside an interruptible action.
- You should, whenever possible, avoid using *any* version of a masking function. They are complicated and low-level functions. Instead, prefer the higher-level functions like `bracket`, `finally`, and so on.
- `uninterruptibleMask` introduces the possibility of a complete deadlock. Interruptible `mask` introduces the possibility of a cleanup action being interrupted, or an action before a cleanup action being interrupted and the cleanup action never getting called. If you're stuck with using a masking function directly, you'll need to think carefully about what your goals are.

### Deadlock detection

What's the result of running this program?

``` haskell
import Control.Concurrent

main :: IO ()
main = do
  mvar <- newEmptyMVar
  takeMVar mvar
```

Usually, it will be:

``` text
foo.hs: thread blocked indefinitely in an MVar operation
```

Note that you can't actually *rely* on this deadlock detection. GHC does a good job of noticing that there are no other references to the `MVar` in an active thread, and therefore terminates our thread with an asynchronous exception.

How about this?

``` haskell
import Control.Concurrent
import Control.Exception

main :: IO ()
main = do
  mvar <- newEmptyMVar
  uninterruptibleMask_ $ takeMVar mvar
```

This one deadlocks, since we've blocked the async exception. How about a normal mask?

``` haskell
import Control.Concurrent
import Control.Exception

main :: IO ()
main = do
  mvar <- newEmptyMVar
  mask_ $ takeMVar mvar
```

The deadlock is detected here and our program exits, since `takeMVar` is an interruptible action. So far, so good.

How about this one?

``` haskell
import Control.Concurrent
import UnliftIO.Exception

main :: IO ()
main = do
  mvar <- newEmptyMVar :: IO (MVar ())
  tryAny (takeMVar mvar) >>= print
  putStrLn "Looks like I recovered!"
```

`tryAny` will only catch synchronous exceptions (based on the exception type). This prevents us from recovering from asynchronous exceptions, which as we know is a bad idea. Therefore, you would think that `tryAny` wouldn't catch the `BlockedIndefinitelyOnMVar` exception, and “Looks like I recovered!” would never be printed. However, the opposite is true. Why?

Technically speaking, the `BlockedIndefinitely` exceptions (both for `MVar`s and STM) are asynchronously sent, since they are delivered by the runtime system itself. And as such, we can block them via `uninterruptibleMask`. However, unlike other async exceptions, they are triggered directly by actions in the current thread, *not* a signal from an external thread requesting that our thread die immediately (such as with the `timeout`) function. Therefore, it is fully safe to recover from them, and therefore those exception types act like synchronous exceptions.

## Helper library breakdown

Above, we mentioned three different helper libraries that are recommended for safer async exception handling. Let's break them down:

- `enclosed-exceptions` uses an older approach based on forked threads for identifying async exceptions. I would not recommend this for new code.
- The other two libraries both use the type based distinction we've described here today. The difference is in how they handle monad transformers:
  - `safe-exceptions` uses type typeclasses from the `exceptions` package, like `MonadCatch` and `MonadMask`
  - `unliftio` uses `MonadUnliftIO`

Proper monad transformer handling is a completely different topic, which I've covered elsewhere ([slides](https://www.snoyman.com/reveal/monad-transformer-state), [video](https://www.youtube.com/watch?v=KZIN9f9rI34)). I recommend using `unliftio` for all new code.

## Rules for async safe handling

Let's summarize the rules we've come up with so far for writing proper exception safe code in Haskell.

- If something *must* happen, like some kind of cleanup, you must use either `mask` or `uninterruptibleMask` to temporarily turn off async exceptions
- If you ever catch an async exception, you *must* rethrow it (no recovery allowed)
- You should minimize the amount of time you spend in a masked state to ensure prompt response to async exceptions
  - As an extension to this: you should therefore minimize the amount of time spent in cleanup code. As an example: having a complex network protocol run inside cleanup code is a bad idea.

Remember that using the correct libraries and library functions will significantly assist in doing these things correctly without breaking your brain each time.

## Examples

We've now covered all of the principles of exception handling in Haskell. Let's go through a bunch of examples to demonstrate recommended best practices.

### Avoid async exceptions when possible

This is a general piece of advice: don't use async exceptions if you don't have to. In particular, async exceptions are sometimes used as a form of message passing and control flow. There are almost always better ways to do this! Consider this code:

``` haskell
import Control.Concurrent
import Control.Concurrent.Async
import Control.Monad

main :: IO ()
main = do
  messages <- newChan
  race_
    (mapM_ (writeChan messages) [1..10 :: Int])
    (forever $ do
      readChan messages >>= print
      -- simulate some I/O latency
      threadDelay 100000)
```

This will result in dropping messages on the floor, since the first thread will finish before the second thread can complete. Instead of using `forever` and relying on async exceptions to kill the worker, build it into the channel itself:

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-11.4 script --package unliftio --package stm-chans
import UnliftIO (concurrently_, atomically, finally)
import Control.Concurrent (threadDelay)
import Control.Concurrent.STM.TBMQueue
import Data.Function (fix)

main :: IO ()
main = do
  messages <- newTBMQueueIO 5
  concurrently_
    (mapM_ (atomically . writeTBMQueue messages) [1..10 :: Int]
     `finally` atomically (closeTBMQueue messages))
    (fix $ \loop -> do
      mmsg <- atomically $ readTBMQueue messages
      case mmsg of
        Nothing -> return ()
        Just msg -> do
          print msg
          -- simulate some I/O latency
          threadDelay 100000
          loop)
```

Lesson: async exceptions are powerful, and they make many kinds of code much easier to write correctly. But often they are neither necessary nor helpful.

### Email challenge 1

Is the following an example of good or bad asynchronous exception handling?

``` haskell
bracket
  openConnection closeConnection $ \conn ->
    bracket
      (sendHello conn)
      (sendGoodbye conn)
      (startConversation conn)
```

**Answer** Bad! Using `bracket` for opening and closing the connection is a good idea. However, using `bracket` to ensure that a goodbye message is sent will significantly delay cleanup activities. If you have a network protocol which absolutely demands a goodbye message be sent before shutting down… well, you have a broken network protocol anyway, since there is no way to guarantee against:

- The process receiving a SIGKILL
- The machine dying
- The network disconnecting

Instead, this code is preferable:

``` haskell
bracket
  openConnection closeConnection $ \conn -> do
    sendHello conn
    res <- startConversation conn
    sendGoodbye conn
    return res
```

There are likely exceptions to this rule (no pun intended), but you should justify each such exception very strongly.

## Email challenge 2

Is this a good implementation of `bracket`?

``` haskell
bracket before after inner = mask $ \restore -> do
  resource <- before
  eresult <- try $ restore $ inner resource
  after resource
  case eresult of
    Left e -> throwIO (e :: SomeException)
    Right result -> return result
```

Firstly: it's always preferable to use the already written, already tested version of `bracket` available in libraries! Now, let's go through this:

- It properly masks exceptions around the entire block. Good!
- The `before` action is run with exceptions still masked. Good! If we `restore`d around the `before`, an async exception could sneak in immediately after `before` finishing and binding the `resource` value.
- We `restore` inside of the `try` before calling `inner`. That's correct, and will not prevent proper exception safety in `bracket` itself.
- We call `after` immediately, ensuring cleanup. Good!
- Possibly bad: `after` is called without using uninterruptible masking, meaning that it's possible for an interruptible action inside `after` to prevent complete resource cleanup. On the other hand: if this is well documented, a user of this `bracket` could use `uninterruptibleMask_` him/herself inside of `after`.
- We rethrow the exception, meaning that it was safe for us to catch asynchronous exceptions. Good!

Overall: very good, but probably better to use `uninterruptibleMask_` on `after`, which is what `safe-exceptions` and `unliftio` both do. Again, see [the relavant Github discussion](https://github.com/fpco/safe-exceptions/issues/3).

### Racing reads

What is the output of this program?

``` haskell
import Control.Concurrent
import Control.Concurrent.Async

main :: IO ()
main = do
  chan <- newChan
  mapM_ (writeChan chan) [1..10 :: Int]
  race (readChan chan) (readChan chan) >>= print
  race (readChan chan) (readChan chan) >>= print
  race (readChan chan) (readChan chan) >>= print
  race (readChan chan) (readChan chan) >>= print
  race (readChan chan) (readChan chan) >>= print
```

Answer: on my machine, it's:

``` text
Left 1
Left 3
Left 5
Left 7
Left 9
```

However, it just as easily could have allowed some `Right`s in there. It could have allowed evens in the `Left`s. And instead of skipping every other number, it's possible (due to thread scheduling) to not drop some of the numbers.

This may seem a bit far-fetched, so let's instead try something simpler:

``` haskell
timeout 1000000 $ readChan chan
```

It seems reasonable to want to block on reading a channel for a certain amount of time. However, depending on thread timing, the value may end up getting dropped on the floor. We can demonstrate that by simulating unusual thread scheduling with `threadDelay`:

``` haskell
import Control.Concurrent
import System.Timeout

main :: IO ()
main = do
  chan <- newChan
  mapM_ (writeChan chan) [1..10 :: Int]
  mx <- timeout 1000000 $ do
    x <- readChan chan
    threadDelay 2000000
    return x
  print mx
  readChan chan >>= print
```

This results in:

``` text
Nothing
2
```

If you actually want to have such a timeout behavior, you have to get a little bit more inventive, and once again avoid using async exceptions:

``` haskell
import Control.Applicative ((<|>))
import Control.Concurrent (threadDelay)
import Control.Concurrent.STM
import GHC.Conc (registerDelay, unsafeIOToSTM)

main :: IO ()
main = do
  tchan <- newTChanIO
  atomically $ mapM_ (writeTChan tchan) [1..10 :: Int]

  delayDone <- registerDelay 1000000
  let stm1 = do
        isDone <- readTVar delayDone
        check isDone
        return Nothing
      stm2 = do
        x <- readTChan tchan
        unsafeIOToSTM $ threadDelay 2000000
        return $ Just x
  mx <- atomically $ stm1 <|> stm2
  print mx
  atomically (readTChan tchan) >>= print
```

This results in the preferred output:

``` text
Nothing
1
```

### Forked threads

Whenever possible, *use the async library* for forking threads. In particular, the `concurrently` and `race` functions, the `Concurrently` data type, and their related helpers, are all the best thing to use. If you must have more complicated control flow, use the family of functions related to the `Async` data type. Only use `forkIO` as a last resort.

All that said: suppose we're going to use `forkIO`. And let's write a program that is going to acquire some resource in a parent thread, and then needs to clean it up in the child thread. We'll add in a `threadDelay` to simulate some long action.

``` haskell
import Control.Concurrent
import Control.Exception

main :: IO ()
main = do
  putStrLn "Acquire in main thread"
  tid <- forkIO $
    (putStrLn "use in child thread" >> threadDelay maxBound)
      `finally` putStrLn "cleanup in child thread"
  killThread tid -- built on top of throwTo
  putStrLn "Exiting the program"
```

This looks like it should work. However, on my machine (this is timing-dependent!) the output is:

``` text
Acquire in main thread
Exiting the program
```

This is because the forked thread doesn't get a chance to run the `finally` call before the main thread sends an async exception with `killThread`. We may think we can work around this with some masking:

``` haskell
import Control.Concurrent
import Control.Exception

main :: IO ()
main = do
  putStrLn "Acquire in main thread"
  tid <- forkIO $ uninterruptibleMask_ $
    (putStrLn "use in child thread" >> threadDelay maxBound)
      `finally` putStrLn "cleanup in child thread"
  killThread tid -- built on top of throwTo
  putStrLn "Exiting the program"
```

However, we still have the same problem: we don't get to `uninterruptibleMask_` before `killThread` runs. Instead, we need to perform our masking in the main thread, before forking, and let the masked state get inherited by the child thread:

``` haskell
import Control.Concurrent
import Control.Exception

main :: IO ()
main = do
  putStrLn "Acquire in main thread"
  tid <- uninterruptibleMask_ $ forkIO $
    (putStrLn "use in child thread" >> threadDelay maxBound)
      `finally` putStrLn "cleanup in child thread"
  killThread tid -- built on top of throwTo
  putStrLn "Exiting the program"
```

Now our output is:

``` text
Acquire in main thread
use in child thread
```

Followed by the program hanging due to the `threadDelay maxBound`. Since we're still inside a masked state, we can't kill that thread. We've violated one of our async exception handling rules! One solution would be to write our code like this:

``` haskell
import Control.Concurrent
import Control.Exception
import System.IO

main :: IO ()
main = do
  hSetBuffering stdout LineBuffering
  putStrLn "Acquire in main thread"
  tid <- uninterruptibleMask $ \restore -> forkIO $
    restore (putStrLn "use in child thread" >> threadDelay maxBound)
      `finally` putStrLn "cleanup in child thread"
  killThread tid -- built on top of throwTo
  putStrLn "Exiting the program"
```

This gives the correct output and behavior:

``` text
Acquire in main thread
cleanup in child thread
Exiting the program
```

But it turns out that there's a subtle problem with using the `restore` we captured from the parent thread's `uninterruptibleMask_` call: we're not actually guaranteed to be unmasking exceptions! Let's introduce the proper solution, and then see how it behaves differently. Instead of using `restore` from `uninterruptibleMask`, we can use the `forkIOWithUnmask` function:

``` haskell
import Control.Concurrent
import Control.Exception
import System.IO

main :: IO ()
main = do
  hSetBuffering stdout LineBuffering
  putStrLn "Acquire in main thread"
  tid <- uninterruptibleMask_ $ forkIOWithUnmask $ \unmask ->
    unmask (putStrLn "use in child thread" >> threadDelay maxBound)
      `finally` putStrLn "cleanup in child thread"
  killThread tid -- built on top of throwTo
  putStrLn "Exiting the program"
```

Small difference in the code. Let's look at another piece of code that demonstrates the difference:

``` haskell
import Control.Concurrent
import Control.Exception

foo :: IO ()
foo = mask $ \restore -> restore getMaskingState >>= print

bar :: IO ()
bar = mask $ \restore -> do
  forkIO $ restore getMaskingState >>= print
  threadDelay 10000

baz :: IO ()
baz = mask_ $ do
  forkIOWithUnmask $ \unmask -> unmask getMaskingState >>= print
  threadDelay 10000

main :: IO ()
main = do
  putStrLn "foo"
  foo
  mask_ foo
  uninterruptibleMask_ foo

  putStrLn "\nbar"
  bar
  mask_ bar
  uninterruptibleMask_ bar

  putStrLn "\nbaz"
  baz
  mask_ baz
  uninterruptibleMask_ baz
```

We're using the `getMaskingState` action to determine the masking state currently in place. Here's the output of the program:

``` text
foo
Unmasked
MaskedInterruptible
MaskedUninterruptible

bar
Unmasked
MaskedInterruptible
MaskedUninterruptible

baz
Unmasked
Unmasked
Unmasked
```

Remember that the `restore` function provided by `mask` will restore the *previous* masking state. So for example, when calling `mask_ foo`, the `restore` inside `foo` returns us to the `MaskedInterruptible` state we had instituted by the original `mask_`. The same logic applies to the calls to `bar`.

However, with `baz`, we use `forkIOWithUnmask`. This `unmask` action does *not* restore a previous masking state. Instead, it ensures that all masking is disabled. This is usually the behavior desired in the forked thread, since we want the forked thread to respond to async exceptions we send it, even if the parent thread is in a masked state.

### forkIO and race

Let's implement our own version of the `race` function from the `async` package. This is going to be a really bad implementation for many reasons (everyone is encouraged to try and point out some of them!), but we'll focus on just one. We'll start with this:

``` haskell
import Control.Concurrent
import Control.Exception

badRace :: IO a -> IO b -> IO (Either a b)
badRace ioa iob = do
  mvar <- newEmptyMVar
  tida <- forkIO $ ioa >>= putMVar mvar . Left
  tidb <- forkIO $ iob >>= putMVar mvar . Right
  res <- takeMVar mvar
  killThread tida
  killThread tidb
  return res
```

Now let's use this in a simple manner:

``` haskell
main :: IO ()
main = badRace (return ()) (threadDelay maxBound) >>= print
```

As expected, the result is:

``` text
Left ()
```

Now take a guess, what happens with this one?

``` haskell
main :: IO ()
main = mask_ $ badRace (return ()) (threadDelay maxBound) >>= print
```

Same thing. OK, one more try:

``` haskell
main :: IO ()
main = uninterruptibleMask_
     $ badRace (return ()) (threadDelay maxBound) >>= print
```

This one deadlocks, since our `forkIO` calls inside `badRace` inherit the masking state of the parent thread, which prevents the `killThread` call from working. Any guesses as to how we should fix this bug?

``` haskell
badRace :: IO a -> IO b -> IO (Either a b)
badRace ioa iob = do
  mvar <- newEmptyMVar
  tida <- forkIOWithUnmask $ \u -> u ioa >>= putMVar mvar . Left
  tidb <- forkIOWithUnmask $ \u -> u iob >>= putMVar mvar . Right
  res <- takeMVar mvar
  killThread tida
  killThread tidb
  return res
```

**BONUS** What will be the result of running this?

``` haskell
main :: IO ()
main = uninterruptibleMask_
     $ badRace (error "foo" :: IO ()) (threadDelay maxBound) >>= print
```

And here's a little hint at fixing it:

``` haskell
tida <- forkIOWithUnmask $ \u -> try (u ioa) >>= putMVar mvar . fmap Left
```

## unsafePerformIO vs unsafeDupablePerformIO

I wanted to include a demonstration of `unsafeDupablePerformIO` leading to cleanup actions not running. Unfortunately, I couldn't get any repro on my machine, and had to give up. Instead, I'll link to a GHC Trac ticket (c/o Chris Allen) which at least historically demonstrated the problem:

<https://ghc.haskell.org/trac/ghc/ticket/8502>

tl;dr: GHC's runtime will simply terminate threads evaluating a thunk if another thread finishes evaluating first, and not give a chance for cleanup actions to run. This is a great demonstration of why async exceptions are necessary if we want both external termination *and* proper resource handling.

## Links

- The original Handling [Asynchronous Exceptions in Haskell](https://web.archive.org/web/2025/https://academy.fpblock.com/blog/how-to-handle-asynchronous-exceptions-in-haskell) blog post
- [General Haskell syllabus](../../haskell/syllabus/)
- The `unliftio` library: <https://www.stackage.org/package/unliftio>
  - Exception handling module: <https://www.stackage.org/haddock/lts-11.1/unliftio-0.2.5.0/UnliftIO-Exception.html>
- safe-exceptions documentation: [https://haskell-lang.org/library/safe-exceptions](../../haskell/library/safe-exceptions/)
- [Exceptions best practices](../exceptions-best-practices-haskell/)
- Monad transformers talk
  - Slides: <https://www.snoyman.com/reveal/monad-transformer-state>
  - Video: <https://www.youtube.com/watch?v=KZIN9f9rI34>
{% endraw %}
