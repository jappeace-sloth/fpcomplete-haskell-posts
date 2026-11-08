---
layout: page
title: "IAP: Speeding up conduit"
---
{% raw %}
*By Michael Snoyman, 21 August 2014. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2014/08/iap-speeding-up-conduit/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250429120437/https://academy.fpblock.com/blog/2014/08/iap-speeding-up-conduit/).*

As most of us know, performance isn't a one-dimensional spectrum. There are in fact multiple different ways to judge performance of a program. A commonly recognized tradeoff is that between CPU and memory usage. Often times, a program can be sped up by caching more data, for example.

conduit is a streaming data library. In that sense, it has two very specific performance criterion it aims for:

- Constant memory usage.
- Efficient usage of scarce resources, such as closing file descriptors as early as possible.

While CPU performance is always a nice goal, it has never been my top priority in the library's design, especially given that in the main use case for conduit (streaming data in an I/O context), the I/O cost almost always far outweighs any CPU overhead from conduit.

However, for our upcoming Integrated Analysis Platform (IAP) release, this is no longer the case. conduit will be used in tight loops, where we *do* need to optimize for the lowest CPU overhead possible.

This blog post covers the first set of optimizations I've applied to conduit. There is still more work to be done, and throughout this blogpost I'll be describing some of the upcoming changes I am attempting.

I'll give a brief summary up front:

- Applying the codensity transform results in much better complexity of monadic bind.
- We're also less reliant on rewrite rules firing, which has always been unreliable (and now I know why).
- This change *does* represent a breaking API change. However, it only affects users of the `Data.Conduit.Internal` module. If you've just been using the public API, your code will be unaffected, besides getting an automatic speedup.
- These changes will soon be released as conduit 1.2.0, after a period for community feedback.

Note that this blog post follows the actual steps I went through (more or less) in identifying the performance issues I wanted to solve. If you want to skip ahead to the solution itself, you may want to [skip to the discussion on difference lists](https://web.archive.org/web/2025/https://academy.fpblock.com/index), or even straight to [continuation passing style, church-encoding, codensity](https://web.archive.org/web/2025/https://academy.fpblock.com/index).

By the way, after I originally wrote this blog post, I continued working on the optimizations I describe as possible future enhancements. Those are actually working out far better than I expected, and it looks like conduit 1.2.0 will be able to ship with them. I'll be writing a separate blog post detailing those changes. A bit of a teaser is: for vector-equivalent code, conduit now generates identical core as vector itself.

## The benchmarks

Before embarking on any kind of serious optimizations, it's important to have some benchmarks. I defined three benchmarks for the work I was going to be doing:

- A simple sum: adding up the numbers from 1 to 10000. This is to get a baseline of the overhead coming from conduit.

- A monte carlo analysis: This was [based on a previous IAP blog post](../monte-carlo-haskell/). I noticed when working on that benchmark that, while the conduit solution was highly *memory* efficient, there was still room to speed up the benchmark.

- Sliding vectors: Naren Sundar recently [sent a sliding windows pull requests](https://github.com/fpco/conduit-combinators/pull/6), which allow us to get a view of a fixed size of a stream of values. This feature is very useful for a number of financial analyses, especially regarding time series.

  Naren's pull request was based on immutable data structures, and for those cases it is highly efficient. However, it's possible to be far more memory efficient by writing to a mutable vector instead, and then taking immutable slices of that vector. Mihaly Barasz [sent a pull request for this feature](https://github.com/fpco/conduit-combinators/pull/8), and much to our disappointment, for small window sizes, it performed worse than sliding windows. We want to understand why.

You can [see the benchmark code](https://github.com/snoyberg/conduit/blob/ff5a25845ddc3b8a6df3fbfe31c3fb886c7a6bb9/conduit/benchmarks/optimize-201408.hs), which stays mostly unchanged for the rest of this blog post (a few new cases are added to demonstrate extra points). The benchmarks always contain a low-level base case representing the optimal performance we can expect from hand-written Haskell (without resorting to any kind of FFI tricks or the like).

You can [see the first run results](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/01-4b901bef293126dd07908c23c4e37c1c3a404ccb.html) which reflect conduit 1.1.7, plus inlining of a few functions. Some initial analysis:

- Control.Monad.foldM is surpringly slow.
- Data.Conduit.List.foldM has a rather steep performance hit versus Data.Conduit.List.fold.
- There's a *very* high overhead in the monte carlo analysis.
- For sliding vector, the conduit overhead is more pronounced at smaller window sizes.
- But even with large window sizes, mutable vector conduits still have a large overhead. The sliding window/immutable approach, however, shows almost no overhead.

That hopefully sets the scene enough for us to begin to dive in.

## Rewrite rules: lift

GHC offers a very powerful optimization technique: rewrite rules. This allows you to tell the compiler that a certain expression can be rewritten to a more efficient one. A common example of a rewrite rule would be to state that `map f . map g` is the same as `map (f . g)`. This can be expressed as:

{-# RULES "map f . map g" forall f g. map f . map g = map (f . g) \#-}

Note that GHC's list rewrite rules are actually more complicated than this, and revolve around a concept called build/foldr fusion.

Let's look at the implementation of the `yield` function in conduit (with some newtypes stripped away):

``` haskell
yield :: Monad m => o -> ConduitM i o m ()
yield o = HaveOutput (Done ()) (return ()) o
{-# INLINE [1] yield #-}
{-# RULES
    "yield o >> p" forall o (p :: ConduitM i o m r).
    yield o >> p = HaveOutput p (return ()) o
  #-}
```

The core datatype of conduit is recursive. The `HaveOutput` constructor contains a field for "what to do next." In the case of `yield`, there *isn't* anything to do next, so we fill that with `Done ()`. However, creating that `Done ()` value just to throw it away after a monadic bind is wasteful. So we have a rewrite rule to fuse those two steps together.

But no such rewrite rule exists for `lift`! My first step was to [add such a rule](https://github.com/snoyberg/conduit/commit/f23b3e8fdc057da5448b5089478317bd425ad263#diff-fcbe586e03ed1156ac9ff7f0855a03e8R1171), and [check the results](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/02-f23b3e8fdc057da5448b5089478317bd425ad263.html). Unfortunately, the rule didn't have any real impact, because it wasn't firing. Let's put that issue to the side; we'll come back to it later.

## Cleanup, inlining

One of the nice features introduced in (I believe) GHC 7.8 is that the compiler will now warn you when a rewrite rule may not fire. When compiling conduit, I saw messages like:

``` haskell
Data/Conduit/List.hs:274:11: Warning:
    Rule "source/map fusion $=" may never fire
      because ‘$=’ might inline first
    Probable fix: add an INLINE[n] or NOINLINE[n] pragma on ‘$=’

Data/Conduit/List.hs:275:11: Warning:
    Rule "source/map fusion =$=" may never fire
      because ‘=$=’ might inline first
    Probable fix: add an INLINE[n] or NOINLINE[n] pragma on ‘=$=’

Data/Conduit/List.hs:542:11: Warning:
    Rule "source/filter fusion $=" may never fire
      because ‘$=’ might inline first
    Probable fix: add an INLINE[n] or NOINLINE[n] pragma on ‘$=’

Data/Conduit/List.hs:543:11: Warning:
    Rule "source/filter fusion =$=" may never fire
      because ‘=$=’ might inline first
    Probable fix: add an INLINE[n] or NOINLINE[n] pragma on ‘=$=’

Data/Conduit/List.hs:552:11: Warning:
    Rule "connect to sinkNull" may never fire
      because ‘$$’ might inline first
    Probable fix: add an INLINE[n] or NOINLINE[n] pragma on ‘$$’
```

This demonstrates an important interaction between inlining and rewrite rules. We need to make sure that expressions that need to be rewritten are not inlined first. If they are first inlined, then GHC won't be able to rewrite them to our more optimized version.

A common approach to this is to *delay* inlining of functions until a later *simplification phase*. The GHC simplification process runs in multiple steps, and we can state that rules and inlining should only happen before or after a certain phase. The phases count down from 2 to 0, so we commonly want to delay inlining of functions until phase 0, if they may be subject to rewriting.

Conversely, some functions need to be inlined *before* a rewrite rule can fire. In stream fusion, for example, the fusion framework depends on the following sequencing to get good performance:

``` haskell
map f . map g
-- inline map
unstream . mapS f . stream . unstream . mapS g . stream
-- rewrite stream . unstream
unstream . mapS f . mapS g . stream
-- rewrite mapS . mapS
unstream . mapS (f . g) . stream
```

In conduit, we need to make sure that all of this is happening in the correct order. There was one particular complexity that made it difficult to ensure this happened. conduit in fact has *two* core datatypes: `Pipe` and `ConduitM`, with the latter being a more friendly newtype wrapper around the first. Up until this point, the code for the two was jumbled into a single internal module, making it difficult to track which things were being written in which version of the API.

My next step was to [split things into .Pipe and .Conduit internal modules](https://github.com/snoyberg/conduit/commit/dfff204e1c603f2466060e37a4a193462f5fa52f), and then [clean up GHC's warnings](https://github.com/snoyberg/conduit/commit/164f01f412b1cac2529bfdeb3fd4584b3c097856) to get rules to fire more reliably. This [gave a modest performance boost](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/04-164f01f412b1cac2529bfdeb3fd4584b3c097856.html) to the sliding vector benchmarks, but not much else. But it *does* pave the way for future improvements.

## Getting serious about sum, by cheating

The results so far have been uninspiring. We've identified a core problem (too many of those `Done` data constructors being used), and noticed that the rewrite rules that *should* fix that don't seem to be doing their job. Now let's take our first stab at *really* improving performance: with aggressive rewrite rules.

Our `sum` benchmark is really simple: use `enumFromTo` to create a stream of values, and `fold` (or `foldM`) to consume that. The thing that slows us down is that, in between these two simple functions, we end up allocating a bunch of temporary data structures. Let's [get rid of them with rewrite rules](https://github.com/snoyberg/conduit/commit/307dab9461dd3c30b577bb094e499e0fba493c78)!

This [certainly did the trick](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/06-211db90fce8b906e6e02345d20a290dc37395692.html). The conduit implementation jumped from 185us to just 8.63us. For comparison, the low level approach (or vector's stream fusion) clocks in at 5.77us, whereas `foldl'` on a list is 80.6us. This is a huge win!

But it's also misleading. All we've done here is sneakily rewritten our conduit algorithm into a low-level format. This solves the specific problem on the table (connecting enumFromTo with fold), but won't fully generalize to other cases. A more representative demonstration of this improvement is the speedup for `foldM`, which went from 1180us to 81us. The reason this is more realistic is that the rewrite rule is not specialized to `enumFromTo`, but rather works on *any* `Source`.

I took a big detour at this point, and ended up [writing an initial implementation of stream fusion in conduit](https://github.com/snoyberg/conduit/blob/optimize-201408-stream-conduit/stream-conduit/Data/StreamConduit.hs). Unfortunately, I ran into a dead end on that branch, and had to put that work to the side temporarily. However, the improvements discussed in the rest of this blog post will hopefully reopen the door to stream fusion, which I hope to investigate next.

## Monte carlo, and associativity

Now that I'd made the results of the sum benchmark thoroughly useless, I decided to focus on the results of monte carlo, where the low level implementation still won by a considerable margin (3.42ms vs 10.6ms). The question was: why was this happening? To understand, let's start by looking at the code:

``` haskell
analysis = do
    successes <- sourceRandomN count
              $$ CL.fold (\t (x, y) ->
                            if (x*x + y*(y :: Double) < 1)
                                then t + 1
                                else t)
                    (0 :: Int)
    return $ fromIntegral successes / fromIntegral count * 4

sourceRandomN :: (MWC.Variate a, MonadIO m) => Int -> Source m a
sourceRandomN cnt0 = do
    gen <- liftIO MWC.createSystemRandom
    let loop 0 = return ()
        loop cnt = do
            liftIO (MWC.uniform gen) >>= yield >> loop (cnt - 1)
    loop cnt0
```

The `analysis` function is not very interesting: it simply connects `sourceRandomN` with a `fold`. Given that we now have a well behaved and consistently-firing rewrite rule for connecting to folds, it's safe to say that was not the source of our slowdown. So our slowdown must be coming from:

``` haskell
liftIO (MWC.uniform gen) >>= yield >> loop (cnt - 1)
```

This should in theory generate really efficient code. `yield >> loop (cnt - 1)` should be rewritten to `\x -> HaveOutput (loop (cnt - 1)) (return ()) x)`, and then `liftIO` should get rewritten to generate:

``` haskell
PipeM $ do
    x <- MWC.uniform gen
    return $ HaveOutput (loop $ cnt - 1) (return ()) x
```

I [added another commit](https://github.com/snoyberg/conduit/commit/a62e7ebeaaf2ef16265751bdec3d91ffb16034c0) to include a few more versions of the monte carlo benchmark ([results here](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/08-a62e7ebeaaf2ef16265751bdec3d91ffb16034c0.html)). The two most interesting are:

- Explicit usage of the `Pipe` constructors:

  ``` haskell
  sourceRandomNConstr :: (MWC.Variate a, MonadIO m) => Int -> Source m a
  sourceRandomNConstr cnt0 = ConduitM $ PipeM $ do
      gen <- liftIO MWC.createSystemRandom
      let loop 0 = return $ Done ()
          loop cnt = do
              x <- liftIO (MWC.uniform gen)
              return $ HaveOutput (PipeM $ loop (cnt - 1)) (return ()) x
      loop cnt0
  ```

  This version ran in 4.84ms, vs the original conduit version which ran in 15.8ms. So this is definitely the problem!

- Explicitly force right-associated binding order:

  ``` haskell
  sourceRandomNBind :: (MWC.Variate a, MonadIO m) => Int -> Source m a
  sourceRandomNBind cnt0 = lift (liftIO MWC.createSystemRandom) >>= \gen ->
      let loop 0 = return ()
          loop cnt = do
              lift (liftIO $ MWC.uniform gen) >>= (\o -> yield o >> loop (cnt - 1))
       in loop cnt0
  ```

  Or to zoom in on the important bit:

  ``` haskell
  lift (liftIO $ MWC.uniform gen) >>= (\o -> yield o >> loop (cnt - 1))
  ```

  By the monad laws, this code is identical to the original. However, instead of standard left-associativity, we have right associativity or monadic bind. This code ran in 5.19ms, an approximate threefold speedup vs the left associative code!

This issue of associativity was something Roman Cheplyaka [told me about back in April](https://www.reddit.com/r/haskell/comments/23m4bs/i_added_a_coroutine_example_to_the_wiki_did_i/cgyfxux), so I wasn't surprised to see it here. Back then, I'd looked into using `Codensity` together with `ConduitM`, but didn't get immediate results, and therefore postponed further research until I had more time.

OK, so why exactly does left-associativity hurt us so much? There are two reasons actually:

- Generally speaking, many monads perform better when they are right associated. This is especially true for free monads, of which conduit is just a special case. Janis Voigtl ̈ander's paper Asymptotic Improvement of Computations over Free Monads and Edward Kmett's blog post series [free monads for less](http://comonad.com/reader/2011/free-monads-for-less/) do a far better job of explaining the issue than I could.
- In the case of conduit, left associativity prevented the `lift` and `yield` rewrite rules from firing, which introduced extra, unnecessary monadic bind operations. Forcing right associativity allows these rules to fire, avoiding a lot of unnecessary data constructor allocation and analysis.

At this point, it became obvious at this point that the main slowdown I was seeing was driven by this problem. The question is: how should we solve it?

## Difference lists

To pave the way for the next step, I want to take a quick detour and talk about something simpler: difference lists. Consider the following code:

``` haskell
(((w ++ x) ++ y) ++ z)
```

Most experienced Haskellers will cringe upon reading that. The append operation for a list needs to traverse every cons cell in its left value. When we left-associate append operations like this, we will need to traverse every cell in `w`, then every cell in `w ++ x`, then every cell in `w ++ x ++ y`. This is highly inefficient, and would clearly be better done in a right-associated style (sound familiar?).

But forcing programmers to ensure that their code is always right-associated isn't always practical. So instead, we have two common alternatives. The first is: use a better datastructure. In particular, `Data.Sequence` has far cheaper append operations than lists.

The other approach is to use *difference lists*. Difference lists are *functions* instead of actual list values. They are instructions for adding values to the beginning of the list. In order to append, you use normal function composition. And to convert them to a list, you apply the resulting function to an empty list. As an example:

``` haskell
type DList a = [a] -> [a]

dlist1 :: DList Int
dlist1 rest = 1 : 2 : rest

dlist2 :: DList Int
dlist2 rest = 3 : 4 : rest

final :: [Int]
final = dlist1 . dlist2 $ []

main :: IO ()
main = print final
```

Both difference lists and sequences have advantages. Probably the simplest summary is:

- Difference lists have smaller constant factors for appending.
- Sequences allow you to analyze them directly, without having to convert them to a different data type first.

That second point is important. If you need to regularly analyze your list and then continue to append, the performance of a difference list will be abysmal. You will constantly be swapping representations, and converting from a list to a difference list is an O(n) operation. But if you will simply be constructing a list once without any analysis, odds are difference lists will be faster.

This situation is *almost* identical to our problems with conduit. Our monadic composition operator- like list's append operator- needs to traverse the entire left hand side. This connection is more clearly spelled out in Reflection without Remorse by Atze van der Ploeg and Oleg Kiselyov (and for me, care of Roman).

Alright, with that out of the way, let's finally fix conduit!

## Continuation passing style, church-encoding, codensity

There are essentially two things we need to do with conduits:

- Monadically compose them to sequence two streams into a larger stream.
- Categorically compose them to connect one stream to the next in a pipeline.

The latter requires that we be able to case analyze our datatypes, while theoretically the former does not: something like difference lists for simple appending would be ideal. In the past, I've tried out a number of different alternative implementations of conduit, none of which worked well enough. The problem I always ran into was that either monadic bind became too expensive, or categorical composition became too expensive.

Roman, Mihaly, Edward and I [discussed these issues a bit](https://github.com/snoyberg/conduit/commit/5cacdc36d140d075ce7b7bfc397c2fc08fffe7cd#commitcomment-7414323) on Github, and based on Roman's advice, I went ahead with [writing a benchmark of different conduit implementations](https://github.com/snoyberg/conduit-cps-benchmarks). I currently have four implementations in this benchmark (and hope to add more):

- Standard, which looks very much like conduit 1.1, just a bit simplified (no rewrite rules, no finalizers, no leftovers).
- Free, which is conduit rewritten to explicitly use the free monad transformer.
- Church, which modifies Free to instead use the Church-encoded free monad transformer.
- Codensity, which is a Codensity-transform-inspired version of conduit.

You can [see the benchmark results](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/cps-benchmark-20140818b.html), which clearly show the codensity version to be the winner. Though it would be interesting, I think I'll avoid going into depth on the other three implementations for now (this blog post is long enough already).

### What is Codensity?

Implementing Codensity in conduit just means changing the `ConduitM` newtype wrapper to look like this:

``` haskell
newtype ConduitM i o m r = ConduitM
    { unConduitM :: forall b.
                    (r -> Pipe i i o () m b) -> Pipe i i o () m b
    }
```

What this says is "I'm going to provide an `r` value. If you give me a function that needs an `r` value, I'll give it that `r` value and then continue with the resulting `Pipe`." Notice how similar this looks to the type signature of monadic bind itself:

``` haskell
(>>=) :: Pipe i i o () m r
      -> (r -> Pipe i i o () m b)
      -> Pipe i i o () m b
```

This isn't by chance, it's by construction. More information is available in [the Haddocks of kan-extension](https://hackage.haskell.org/package/kan-extensions-4.0.3/docs/Control-Monad-Codensity.html), or in the above-linked paper and blog posts by Janis and Edward. To see why this change is important, let's look at the new implementations of some of the core conduit functions and type classes:

``` haskell
yield o = ConduitM $ \rest -> HaveOutput (rest ()) (return ()) o

await = ConduitM $ \f -> NeedInput (f . Just) (const $ f Nothing)

instance Monad (ConduitM i o m) where
    return x = ConduitM ($ x)
    ConduitM f >>= g = ConduitM $ \h -> f $ \a -> unConduitM (g a) h

instance MonadTrans (ConduitM i o) where
    lift mr = ConduitM $ \rest -> PipeM (liftM rest mr)
```

Instead of having explicit `Done` constructors in `yield`, `await`, and `lift`, we use the continuation `rest`. This is the *exact same transformation* we were previously relying on rewrite rules to provide. However, our rewrite rules couldn't fire properly in a left-associated monadic binding. Now we've avoided the whole problem!

Our `Monad` instance also became much smaller. Notice that in order to monadically compose, there is no longer any need to case-analyze the left hand side, which avoids the high penalty of left association.

Another interesting quirk is that our `Monad` instance on `ConduitM` no longer requires that the base `m` type constructor itself be a `Monad`. This is nice feature of `Codensity`.

So that's half the story. What about categorical composition? That certainly *does* require analyzing both the left and right hand structures. So don't we lose all of our speed gains of `Codensity` with this? Actually, I think not. Let's look at the code for categorical composition:

``` haskell
ConduitM left0 =$= ConduitM right0 = ConduitM $ \rest ->
    let goRight final left right =
            case right of
                HaveOutput p c o  -> HaveOutput (recurse p) (c >> final) o
                NeedInput rp rc   -> goLeft rp rc final left
                Done r2           -> PipeM (final >> return (rest r2))
                PipeM mp          -> PipeM (liftM recurse mp)
                Leftover right' i -> goRight final (HaveOutput left final i) right'
          where
            recurse = goRight final left

        goLeft rp rc final left =
            case left of
                HaveOutput left' final' o -> goRight final' left' (rp o)
                NeedInput left' lc        -> NeedInput (recurse . left') (recurse . lc)
                Done r1                   -> goRight (return ()) (Done r1) (rc r1)
                PipeM mp                  -> PipeM (liftM recurse mp)
                Leftover left' i          -> Leftover (recurse left') i
          where
            recurse = goLeft rp rc final
     in goRight (return ()) (left0 Done) (right0 Done)
```

In the last line, we apply `left0` and `right0` to `Done`, which is how we convert our Codensity version into something we can actually analyze. (This is equivalent to applying a difference list to an empty list.) We then traverse these values in the same way that we did in conduit 1.1 and earlier.

The important difference is how we ultimately finish. The code in question is the `Done` clause of the `goRight`'s case analysis, namely:

``` haskell
Done r2           -> PipeM (final >> return (rest r2))
```

Notice the usage of `rest`, instead of what we would have previously done: used the `Done` constructor. By doing this, we're immediately recreating a Codensity version of our resulting `Pipe`, which allows us to only traverse our incoming `Pipe` values once each, and not need to retraverse the outgoing `Pipe` for future monadic binding.

This trick doesn't just work for composition. There are a large number of functions in `conduit` that need to analyze a `Pipe`, such as `addCleanup` and `catchC`. All of them are now implemented in this same style.

After implementing this change, the [resulting benchmarks look much better](https://web.archive.org/web/2025/https://s3.amazonaws.com/download.fpcomplete.com/benchmarks/conduit-201408/10-5cacdc36d140d075ce7b7bfc397c2fc08fffe7cd.html). The naive implementation of monte carlo is now quite close to the low-level version (5.28ms vs 3.44ms, as opposed to the original 15ms). Sliding vector is also much better: the unboxed, 1000-size window benchmark went from 7.96ms to 4.05ms, vs a low-level implementation at 1.87ms.

### Type-indexed sequences

One approach that I haven't tried yet is the type-indexed sequence approach from Reflection without Remorse. I still intend to add it to my conduit benchmark, but I'm not optimistic about it beating out Codensity. My guess is that a sequence data type will have a higher constant factor overhead, and based on the way composition is implemented in conduit, we won't get any benefit from avoiding the need to transition between two representations.

Edward said he's hoping to get an implementation of such a data structure into the free package, at which point I'll update my benchmark to see how it performs.

## To pursue next: streamProducer, streamConsumer, and more

While this round of benchmarking produced some very nice results, we're clearly not yet at the same level as low-level code. My goal is to focus on that next. I have some experiments going already relating to getting conduit to expose stream fusion rules. In simple cases, I've generated a conduit-compatible API with the same performance as vector.

The sticking point is getting something which is efficient not just for functions explicitly written in stream style, but also provides decent performance when composed with the `await`/`yield` approach. While the latter approach will almost certainly be slower than stream fusion, I'm hoping we can get it to degrade to current-conduit performance levels, and allow stream fusion to provide a significant speedup when categorically composing two `Conduit`s written in that style.

The code discussed in this post is now available on the `next-cps` branch of conduit. conduit-extra, conduit-combinators, and a number of other packages either compile out-of-the-box with these changes, or require minor tweaks (already implemented), so I'm hoping that this API change does not affect too many people.

As I mentioned initially, I'd like to have some time for community discussion on this before I make this next release.
{% endraw %}
