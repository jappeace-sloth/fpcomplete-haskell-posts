---
layout: page
title: "IAP: conduit stream fusion"
---
{% raw %}
*By Michael Snoyman, 27 August 2014. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2014/08/conduit-stream-fusion/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250429120352/https://academy.fpblock.com/blog/2014/08/conduit-stream-fusion/).*

Both the changes described in this blog post, and in the [previous blog post](../iap-speeding-up-conduit/), are now merged to the master branch of conduit, and have been released to Hackage as conduit 1.2.0. That doesn't indicate stream fusion is complete (far from it!). Rather, the optimizations we have so far are valuable enough that I want them to be available immediately, and future stream fusion work is highly unlikely to introduce further breaking changes. Having the code on Hackage will hopefully also make it easier for others to participate in the discussion around this code.

## Stream fusion

[Last time](../iap-speeding-up-conduit/), I talked about applying the codensity transform to speed up conduit. This greatly increases performance when performing many monadic binds. However, this does nothing to help us with speeding up the "categorical composition" of conduit, where we connect two components of a pipeline together so the output from the first flows into the second. conduit usually refers to this as *fusion*, but given the topic at hand (stream fusion), I think that nomenclature will become confusing. So let's stick to categorical composition, even though conduit isn't actually a category.

Duncan Coutts, Roman Leshchinskiy and Don Stewart wrote [the stream fusion paper](http://fun.cs.tufts.edu/stream-fusion.pdf), and that technique has become integral to getting high performance in the vector and text packages. The paper is well worth the read, but for those unfamiliar with the technique, let me give a very brief summary:

- GHC is very good at optimising non-recursive functions.
- We express all of our streaming functions has a combination of some internal state, and a function to step over that state.
- Stepping either indicates that the stream is complete, there's a new value and a new state, or there's a new state without a new value (this last case helps avoid recursion for a number of functions like `filter`).
- A stream transformers (like `map`) takes a `Stream` as input and produces a new `Stream` as output.
- The final consuming functions, like `fold`, are the only place where recursion happens. This allows all other components of the pipeline to be inlined, rewritten to more efficient formats, and optimized by GHC.

Let's see how this looks compared to conduit.

## Data types

I'm going to slightly rename data types from stream fusion to avoid conflicts with existing conduit names. I'm also going to add an extra type parameter to represent the final return value of a stream; this is a concept that exists in conduit, but not common stream fusion.

``` haskell
data Step s o r
    = Emit s o
    | Skip s
    | Stop r
data Stream m o r = forall s. Stream
    (s -> m (Step s o r))
    (m s)
```

The `Step` datatype takes three parameters. `s` is the internal state used by the stream, `o` is the type of the stream of values it generates, and `r` is the final result value. The `Stream` datatype uses an existential to hide away that internal state. It then consists of a step function that takes a state and gives us a new `Step`, as well as an initial state value (which is a monadic action, for cases where we want to do some initialization when starting a stream).

Let's look at some functions to get a feel for what this programming style looks like:

``` haskell
enumFromToS_int :: (Integral a, Monad m) => a -> a -> Stream m a ()
enumFromToS_int !x0 !y =
    Stream step (return x0)
  where
    step x | x <= y    = return $ Emit (x + 1) x
           | otherwise = return $ Stop ()
```

This function generates a stream of integral values from `x0` to `y`. The internal state is the current value to be emitted. If the current value is less than or equal to `y`, we emit our current value, and update our state to be the next value. Otherwise, we stop.

We can also write a function that transforms an existing stream. `mapS` is likely the simplest example of this:

``` haskell
mapS :: Monad m => (a -> b) -> Stream m a r -> Stream m b r
mapS f (Stream step ms0) =
    Stream step' ms0
  where
    step' s = do
        res <- step s
        return $ case res of
            Stop r -> Stop r
            Emit s' a -> Emit s' (f a)
            Skip s' -> Skip s'
```

The trick here is to make a function from one `Stream` to another. We unpack the input `Stream` constructor to get the input step and state functions. Since `mapS` has no state of its own, we simply keep the input state unmodified. We then provide our modified `step'` function. This calls the input step function, and any time it sees an `Emit`, applies the user-provided `f` function to the emitted value.

Finally, let's consider the consumption of a stream with a strict left fold:

``` haskell
foldS :: Monad m => (b -> a -> b) -> b -> Stream m a () -> m b
foldS f b0 (Stream step ms0) =
    ms0 >>= loop b0
  where
    loop !b s = do
        res <- step s
        case res of
            Stop () -> return b
            Skip s' -> loop b s'
            Emit s' a -> loop (f b a) s'
```

We unpack the input `Stream` constructor again, get the initial state, and then loop. Each loop, we run the input step function.

## Match and mismatch with conduit

There's a simple, straightforward conversion from a `Stream` to a `Source`:

``` haskell
toSource :: Monad m => Stream m a () -> Producer m a
toSource (Stream step ms0) =
    lift ms0 >>= loop
  where
    loop s = do
        res <- lift $ step s
        case res of
            Stop () -> return ()
            Skip s' -> loop s'
            Emit s' a -> yield a >> loop s'
```

We extract the state, and then loop over it, calling `yield` for each emitted value. And ignoring finalizers for the moment, there's even a way to convert a `Source` into a `Stream`:

``` haskell
fromSource :: Monad m => Source m a -> Stream m a ()
fromSource (ConduitM src0) =
    Stream step (return $ src0 Done)
  where
    step (Done ()) = return $ Stop ()
    step (Leftover p ()) = return $ Skip p
    step (NeedInput _ p) = return $ Skip $ p ()
    step (PipeM mp) = liftM Skip mp
    step (HaveOutput p _finalizer o) = return $ Emit p o
```

Unfortunately, there's no straightforward conversion for `Conduit`s (transformers) and `Sink`s (consumers). There's simply a mismatch in the conduit world- which is fully continuation based- to the stream world- where the upstream is provided in an encapsulated value. I *did* find a few representations that mostly work, but the performance characteristics are terrible.

If anyone has insights into this that I missed, please contact me, as this could have an important impact on the future of stream fusion in conduit. But for the remainder of this blog post, I will continue under the assumption that only `Source` and `Stream` can be efficiently converted.

## StreamConduit

Once I accepted that I wouldn't be able to convert a stream transformation into a conduit transformation, I was left with a simple approach to start working on fusion: have two representations of each function we want to be able to fuse. The first representation would use normal conduit code, and the second would be streaming. This looks like:

``` haskell
data StreamConduit i o m r = StreamConduit
    (ConduitM i o m r)
    (Stream m i () -> Stream m o r)
```

Notice that the second field uses the stream fusion concept of a `Stream`-transforming function. At first, this may seem like it doesn't properly address `Source`s and `Sink`s, since the former doesn't have an input `Stream`, and the latter results in a single output value, not a `Stream`. However, those are really just special cases of the more general form used here. For `Source`s, we provide an empty input stream, and for `Sink`s, we continue executing the `Stream` until we get a `Stop` constructor with the final result. You can see both of these in the implementation of the `connectStream` function (whose purpose I'll explain in a moment):

``` haskell
connectStream :: Monad m
              => StreamConduit () i    m ()
              -> StreamConduit i  Void m r
              -> m r
connectStream (StreamConduit _ stream) (StreamConduit _ f) =
    run $ f $ stream $ Stream emptyStep (return ())
  where
    emptyStep _ = return $ Stop ()
    run (Stream step ms0) =
        ms0 >>= loop
      where
        loop s = do
            res <- step s
            case res of
                Stop r -> return r
                Skip s' -> loop s'
                Emit _ o -> absurd o
```

Notice how we've created an empty `Stream` using `emptyStep` and a dummy `()` state. And on the `run` side, we loop through the results. The type system (via the `Void` datatype) prevents the possibility of a meaningful `Emit` constructor, and we witness this with the `absurd` function. For `Stop` we return the final value, and `Skip` implies another loop.

### Fusing StreamConduit

Assuming we have some functions that use `StreamConduit`, how do we get things to fuse? We still need all of our functions to have a `ConduitM` type signature, so we start off with a function to convert a `StreamConduit` into a `ConduitM`:

``` haskell
unstream :: StreamConduit i o m r -> ConduitM i o m r
unstream (StreamConduit c _) = c
{-# INLINE [0] unstream #-}
```

Note that we hold off on any inlining until simplification phase 0. This is vital to our next few rewrite rules, which is where all the magic happens.

The next thing we want to be able to do is categorically compose two `StreamConduit`s together. This is easy to do, since a `StreamConduit` is made up of `ConduitM`s which compose via the `=$=` operator, and `Stream` transformers, which compose via normal function composition. This results in a function:

``` haskell
fuseStream :: Monad m
           => StreamConduit a b m ()
           -> StreamConduit b c m r
           -> StreamConduit a c m r
fuseStream (StreamConduit a x) (StreamConduit b y) = StreamConduit (a =$= b) (y . x)
{-# INLINE fuseStream #-}
```

That's very logical, but still not magical. The final trick is a rewrite rule:

``` haskell
{-# RULES "fuseStream" forall left right.
        unstream left =$= unstream right = unstream (fuseStream left right)
  #-}
```

We're telling GHC that, if we see a composition of two streamable conduits, then we can compose the stream versions of them and get the same result. But this isn't enough yet; `unstream` will still end up throwing away the stream version. We now need to deal with running these things. The first case we'll handle is connecting two streamable conduits, which is where the `connectStream` function from above comes into play. If you go back and look at that code, you'll see that the `ConduitM` fields are never used. All that's left is telling GHC to use `connectStream` when appropriate:

``` haskell
{-# RULES "connectStream" forall left right.
        unstream left $$ unstream right = connectStream left right
  #-}
```

The next case we'll handle is when we connect a streamable source to a non-streamable sink. This is less efficient than the previous case, since it still requires allocating `ConduitM` constructors, and doesn't expose as many opportunities for GHC to inline and optimize our code. However, it's still better than nothing:

``` haskell
connectStream1 :: Monad m
               => StreamConduit () i    m ()
               -> ConduitM      i  Void m r
               -> m r
connectStream1 (StreamConduit _ fstream) (ConduitM sink0) =
    case fstream $ Stream (const $ return $ Stop ()) (return ()) of
        Stream step ms0 ->
            let loop _ (Done r) _ = return r
                loop ls (PipeM mp) s = mp >>= flip (loop ls) s
                loop ls (Leftover p l) s = loop (l:ls) p s
                loop _ (HaveOutput _ _ o) _ = absurd o
                loop (l:ls) (NeedInput p _) s = loop ls (p l) s
                loop [] (NeedInput p c) s = do
                    res <- step s
                    case res of
                        Stop () -> loop [] (c ()) s
                        Skip s' -> loop [] (NeedInput p c) s'
                        Emit s' i -> loop [] (p i) s'
             in ms0 >>= loop [] (sink0 Done)
{-# INLINE connectStream1 #-}

{-# RULES "connectStream1" forall left right.
        unstream left $$ right = connectStream1 left right
  #-}
```

There's a third case that's worth considering: a streamable sink and non-streamable source. However, I ran into two problems when implementing such a rewrite rule:

- GHC did not end up firing the rule.

- There are some corner cases regarding finalizers that need to be dealt with. In our previous examples, the upstream was always a stream, which has no concept of finalizers. But when the upstream is a conduit, we need to make sure to call them appropriately.

So for now, fusion only works for cases where all of the functions can by fused, or all of the functions before the `$$` operator can be fused. Otherwise, we'll revert to the normal performance of conduit code.

## Benchmarks

I took the benchmarks from our previous blog post and modified them slightly. The biggest addition was including an example of `enumFromTo =$= map =$= map =$= fold`, which really stresses out the fusion capabilities, and demonstrates the performance gap stream fusion offers.

The other thing to note is that, in the "before fusion" benchmarks, the sum results are skewed by the fact that we have the overly eager rewrite rules for `enumFromTo $$ fold` (for more information, see the previous blog post). For the "after fusion" benchmarks, there are no special-case rewrite rules in place. Instead, the results you're seeing are actual artifacts of having a proper fusion framework in place. In other words, you can expect this to translate into real-world speedups.

You can compare [before fusion](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/before-fusion.html) and [after fusion](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/after-fusion.html). Let me provide a few select comparisons:

| Benchmark | Low level or vector | Before fusion | After fusion | Speedup |
|----|----|----|----|----|
| map + sum | 5.95us | 636us | 5.96us | 99% |
| monte carlo | 3.45ms | 5.34ms | 3.70ms | 71% |
| sliding window size 10, Seq | 1.53ms | 1.89ms | 1.53ms | 21% |
| sliding vector size 10, unboxed | 2.25ms | 4.05ms | 2.33ms | 42% |

Note at the map + sum benchmark is very extreme, since the inner loop is doing very cheap work, so the conduit overhead dominated the analysis.

## Streamifying a conduit

Here's an example of making a conduit function stream fusion-compliant, using the `map` function:

``` haskell
mapC :: Monad m => (a -> b) -> Conduit a m b
mapC f = awaitForever $ yield . f
{-# INLINE mapC #-}

mapS :: Monad m => (a -> b) -> Stream m a r -> Stream m b r
mapS f (Stream step ms0) =
    Stream step' ms0
  where
    step' s = do
        res <- step s
        return $ case res of
            Stop r -> Stop r
            Emit s' a -> Emit s' (f a)
            Skip s' -> Skip s'
{-# INLINE mapS #-}

map :: Monad m => (a -> b) -> Conduit a m b
map = mapC
{-# INLINE [0] map #-}
{-# RULES "unstream map" forall f.
    map f = unstream (StreamConduit (mapC f) (mapS f))
  #-}
```

Notice the three steps here:

- Define a pure-conduit implementation (`mapC`), which looks just like conduit 1.1's `map` function.
- Define a pure-stream implementation (`mapS`), which looks very similar to vector's `mapS`.
- Define `map`, which by default simply reexposes `mapC`. But then, use an `INLINE` statement to delay inlining until simplification phase 0, and use a rewrite rule to rewrite `map` in terms of `unstream` and our two helper functions `mapC` and `mapS`.

While tedious, this is all we need to do for each function to expose it to the fusion framework.

## Vector vs conduit, mapM style

Overall, vector has been both the inspiration for the work I've done here, and the bar I've used to compare against, since it is generally the fastest implementation you can get in Haskell (and tends to be high-level code to boot). However, there seems to be one workflow where conduit drastically outperforms vector: chaining together monadic transformations.

I put together a benchmark which does the same enumFromTo+map+sum benchmark I demonstrated previously. But this time, I have four versions: vector with pure functions, vector with IO functions, conduit with pure functions, and conduit with IO functions. You can [see the results here](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/mapm.html), the important takeaway is:

- Pure is always faster, since it exposes more optimizations to GHC.
- vector and conduit pure are almost identical, at 57.7us and 58.1us.
- Monadic conduit code does have a slowdown (86.3us). However, monadic vector code has a drastic slowdown (305us), presumably because monadic binds defeat its fusion framework.

So there seems to be at least one workflow for which conduit's fusion framework can outperform even vector!

## Downsides

The biggest downside to this implementation of stream fusion is that we need to write all of our algorithms twice. This can possibly be mitigated by having a few helper functions in place, and implementing others in terms of those. For example, `mapM_` can be implemented in terms `foldM`.

There's one exception to this: using the `streamSource` function, we can convert a `Stream` into a `Source` without having to write our algorithm twice. However, due to differences in how monadic actions are performed between Stream and Conduit, this could introduce a performance degredation for pure `Source`s. We can work around that with a special case function `streamSourcePure` for the `Identity` monad as a base.

## Getting good performance

In order to take advantage of the new stream fusion framework, try to follow these guidelines:

- Use fusion functions whenever possible. Explicit usage of `await` and `yield` will immediately kick you back to non-fusion (the same as explicit pattern matching defeats list fusion).
- If you absolutely cannot use an existing fusion function, consider writing your own fusion variant.
- When mixing fusion and non-fusion, put as many fusion functions as possible together with the `$=` operator before the connect operator `$$`.

## Next steps

Even though this work is now publicly available on Hackage, there's still a lot of work to be done. This falls into three main categories:

- Continue rewriting core library functions in streaming style. Michael Sloan has been working on a lot of these functions, and we're hoping to have almost all the combinators from Data.Conduit.List and Data.Conduit.Combinators done soon.
- Research why rewrite rules and inlining don't play nicely together. In a number of places, we've had to explicitly use rewrite rules to force fusion to happen, when theoretically inlining should have taken care of it for us.
- Look into any possible alternative formulations of stream fusion that provide better code reuse or more reliable rewrite rule firing.

Community assistance on all three points, but especially 2 and 3, are much appreciated!
{% endraw %}
