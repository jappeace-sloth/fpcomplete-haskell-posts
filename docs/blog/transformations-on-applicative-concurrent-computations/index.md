---
layout: page
title: "Transformations on Applicative Concurrent Computations"
---
{% raw %}
*By Román González, 27 January 2020. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/transformations-on-applicative-concurrent-computations/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250803104158/https://academy.fpblock.com/blog/transformations-on-applicative-concurrent-computations/).*

When deciding which language to use to solve challenges that require heavy concurrent algorithms, it's hard to not consider Haskell. Its immutable and persistent data structures reduce the introduction of accidental complexity, and the GHC runtime facilitates the creation of thousands of (green) threads without having to worry as much about the memory and performance costs.

The epitome of Haskell's concurrent API is the `async` package, which provides higher-order functions (e.g. [`race`](https://www.stackage.org/haddock/lts-12.24/async-2.2.1/Control-Concurrent-Async.html#v:race), [`mapConcurrently`](https://www.stackage.org/haddock/lts-12.24/async-2.2.1/Control-Concurrent-Async.html#v:mapConcurrently), etc.) that allow us to run `IO` sub-routines and combine their results in various ways while executing concurrently. It also offers the type [`Concurrently`](https://www.stackage.org/haddock/lts-12.24/async-2.2.1/Control-Concurrent-Async.html#t:Concurrently) which allows developers to give normal sub-routines concurrent properties, and also provides `Applicative` and `Alternative` instances that help in the creation of values from composing smaller sub-routines.

In this blog post, we will discuss some of the drawbacks of using the [`Concurrently`](https://www.stackage.org/haddock/lts-12.24/async-2.2.1/Control-Concurrent-Async.html#t:Concurrently) type when composing sub-routines. Then we will show how we can overcome these shortcomings by taking advantage of the structural nature of the `Applicative` and `Alternative` typeclasses; re-shaping and optimizing the execution of a tree of sub-routines.

And, if you simply want to get these performance advantages in your Haskell code today, you can cut to the chase and begin using the new [`Conc`](https://www.stackage.org/haddock/lts-12.24/unliftio-0.2.9.0/UnliftIO-Async.html#t:Conc) datatype we've introduced in [`unliftio` 0.2.9.0](https://www.stackage.org/lts-12.24/package/unliftio-0.2.9.0).

## The drawbacks of `Concurrently`

Getting started with `Concurrently` is easy. We can wrap an `IO a` sub-routine with the `Concurrently` constructor, and then we can compose async values using the map (`<$>`), apply (`<*>`), and alternative (`<|>`) operators. An example might be:

``` haskell
myPureFunction :: String -> String -> String -> String
myPureFunction a b c = a ++ " " ++ b ++ " " ++ c

myComputation :: Concurrently String
myComputation =
  myPureFunction
  <$> Concurrently fetchStringFromAPI1
  <*> (    Concurrently fetchStringFromAPI2_Region1
       <|> Concurrently fetchStringFromAPI2_Region2
       <|> Concurrently fetchStringFromAPI2_Region3
       <|> Concurrently fetchStringFromAPI2_Region4)
  <*> Concurrently fetchStringFromAPI3
```

Let's talk a bit on the drawbacks of this approach. How many threads do you think we need to make sure all these calls execute concurrently? Try to come up with a number and an explanation and then continue reading.

I am guessing you are expecting this code to spawn six (6) threads, correct? One for each `IO` sub-routine that we are using. However, with the existing implementation of `Applicative` and `Alternative` in `Concurrently`, we will spawn at least ten (10) threads. Let's explore these instances to have a better understanding of what is going on:

``` haskell
instance Applicative Concurrently where
  pure = Concurrently . return
  Concurrently fs <*> Concurrently as =
    Concurrently $ (\(f, a) -> f a) <$> concurrently fs as

instance Alternative Concurrently where
  Concurrently as <|> Concurrently bs =
    Concurrently $ either id id <$> race as bs
```

First, let us expand the alternative calls in our example:

``` haskell
    Concurrently fetchStringFromAPI2_Region1
<|> Concurrently fetchStringFromAPI2_Region2
<|> Concurrently fetchStringFromAPI2_Region3
<|> Concurrently fetchStringFromAPI2_Region4

--- is equivalent to
Concurrently (
  either id id <$>
    race {- 2 threads -}
      fetchStringFromAPI2_Region1
      (either id id <$>
         race {- 2 threads -}
           fetchStringFromAPI2_Region2
           (either id id <$>
              race {- 2 threads -}
                fetchStringFromAPI2_Region3
                fetchStringFromAPI2_Region4))
)
```

Next, let us expand the applicative calls:

``` haskell
    Concurrently (myPureFunction <$> fetchStringFromAPI1)
<*> Concurrently fetchStringFromAPI2
<*> Concurrently fetchStringFromAPI3

--- is equivalent to

Concurrently (
  (\(f, a) -> f a) <$>
    concurrently {- 2 threads -}
      ( (\(f, a) -> f a) <$>
         concurrently {- 2 threads -}
           (myPureFunction <$> fetchStringFromAPI1)
           fetchStringFromAPI2
      )
      fetchStringFromAPI3
)
```

You may tell we are always spawning two threads for each pair of sub-routines. Suppose we have 7 sub-routines we want to compose via `Applicative` or `Alternative`. Using this implementation we would spawn at least 14 new threads when at most 8 should do the job. For each composition we do, an extra thread is going to be spawned to deal with bookkeeping.

Another drawback to consider: what happens if one of the values in the call is a `pure` call? Given this code:

``` haskell
pure foo <|> bar
```

We get to spawn a new thread (unnecessarily) to wait for `foo`, even though it has already been computed and it should always win. As we mentioned before, Haskell is an excellent choice for concurrency because it makes spawning threads cheap; however, these threads don't come for free, and we should strive to avoid redundant thread creation.

## Introducing the `Conc` type

To address the issues mentioned above, we implemented a new type called `Conc` in our `unliftio` package. It has the same purpose as `Concurrently`, but it offers some extra guarantees:

- There is going to be only a single bookkeeping thread for all `Applicative` and `Alternative` compositions.
- If we have `pure` calls in an `Applicative` or an `Alternative` composition, we will not spawn a new thread.
- We will optimize the code for trivial cases. For example, not spawning a thread when evaluating a single `Conc` value (instead of a composition of `Conc` values).
- We can compose more than `IO` sub-routines. Any monadic type that implements `MonadUnliftIO` is accepted.
- Children threads are always launched in an unmasked state, not the inherited state of the parent thread.

The `Conc` type is defined as follows:

``` haskell
data Conc m a where
  Action :: m a -> Conc m a
  Apply  :: Conc m (v -> a) -> Conc m v -> Conc m a
  LiftA2 :: (x -> y -> a) -> Conc m x -> Conc m y -> Conc m a
  Pure   :: a -> Conc m a
  Alt    :: Conc m a -> Conc m a -> Conc m a
  Empty  :: Conc m a

instance MonadUnliftIO m => Applicative (Conc m) where
  pure   = Pure
  (<*>)  = Apply
  (*>)   = Then
  liftA2 = LiftA2

instance MonadUnliftIO m => Alternative (Conc m) where
  (<|>) = Alt
```

If you are familiar with `Free` types, this will look eerily familiar. We are going to represent our concurrent computations as data so that we can later transform it or evaluate as we see fit. In this setting, our first example would look something like the following:

``` haskell
myComputation :: Conc String
myComputation =
  myPureFunction
  <$> conc fetchStringFromAPI1
  <*> (    conc fetchStringFromAPI2_Region1
       <|> conc fetchStringFromAPI2_Region2
       <|> conc fetchStringFromAPI2_Region3
       <|> conc fetchStringFromAPI2_Region4)

--- is equivalent to

Apply (myPureFunction <$> fetchStringFromAPI1)
      (Alt (Action fetchStringFromAPI2_Region1)
           (Alt (Action fetchStringFromAPI2_Region2)
                (Alt (Action fetchStringFromAPI2_Region3)
                     (Action fetchStringFromAPI2_Region4))))
```

You may notice we keep the tree structure of the `Concurrently` implementation. However, given we are dealing with a pure data structure, we can modify our `Conc` value to something that is easier to evaluate. Indeed, thanks to the `Applicative` interface, we don't need to evaluate any of the `IO` sub-routines to do transformations (magic!).

We have additional (internal) types that flatten all our alternatives and applicative values:

``` haskell
data Flat a
  = FlatApp !(FlatApp a)
  | FlatAlt !(FlatApp a) !(FlatApp a) ![FlatApp a]

data FlatApp a where
  FlatPure   :: a -> FlatApp a
  FlatAction :: IO a -> FlatApp a
  FlatApply  :: Flat (v -> a) -> Flat v -> FlatApp a
  FlatLiftA2 :: (x -> y -> a) -> Flat x -> Flat y -> FlatApp a
```

These types are equivalent to our `Conc` type, but they have a few differences from `Conc`:

- The `Flat` type separates `Conc` values created via `Applicative` from the ones created via `Alternative`
- The `FlatAlt` constructor flattens an `Alternative` tree into a list (helping us spawn all of them at once and facilitating the usage of a single bookkeeping thread).
  - Note that we represent this as a "at least two" list, with a similar representation of a non empty list from the `semigroups` package.
- The `Flat` and `FlatApp` records are not polymorphic on their monadic context given they rely directly on `IO`. We can transform the `m` parameter in our `Conc m a` type to `IO` via the `MonadUnliftIO` constraint.

The first example of our blog post, when flattened, would look something like the following:

``` haskell
FlatApp
  (FlatApply
    (FlatApp (FlatAction (myPureFunction <$> fetchStringFromAPI1)))
    (FlatAlt (FlatAction fetchStringFromAPI2_Region1)
             (FlatAction fetchStringFromAPI2_Region2)
             [ FlatAction fetchStringFromAPI2_Region3
             , FlatAction fetchStringFromAPI2_Regoin4 ]))
```

Using a [`flatten`](https://github.com/fpco/unliftio/blob/2c68959a5f498bf4ea457fc4bd673b4dfce5c512/unliftio/src/UnliftIO/Internals/Async.hs#L617) function that transforms a `Conc` value into a `Flat` value, we can [later evaluate](https://github.com/fpco/unliftio/blob/2c68959a5f498bf4ea457fc4bd673b4dfce5c512/unliftio/src/UnliftIO/Internals/Async.hs#L662) the concurrent sub-routine tree in a way that is optimal for our use case.

## Performance

So given that the `Conc` API reduces the number of threads created via `Alternative`, our implementation should work best, correct? Sadly, it is not all peachy. To ensure that we get the result of the first thread that finishes on an `Alternative` composition, we make use of the STM API. This approach works great when we want to gather values from multiple concurrent threads. Sadly, the STM monad doesn't [scale too well when composing lots of reads](https://www.oreilly.com/library/view/parallel-and-concurrent/9781449335939/ch10.html#sec_stm-cost), making this approach prohibitive if you are composing tens of thousands of `Conc` values.

Considering this limitation, we only use `STM` when an `Alternative` function is involved; otherwise, we rely on `MVar`s for multiple thread result composition via `Applicative`. We can do this without sweating because we can change the evaluator of the sub-routine tree created by `Conc` on the fly.

## Conclusions

We showcased how we can model the composition of computations using an `Applicative` and `Alternative` tree, and then, taking advantage of this APIs; we transformed this computation tree into something more approachable to execute concurrently. We also took advantage of this *sub-routines as data* approach to change the evaluator from `MVar` to `STM` compositions.
{% endraw %}
