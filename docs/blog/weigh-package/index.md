---
layout: page
title: "weigh: Measuring allocations in Haskell"
---
{% raw %}
*By Chris Done, 27 May 2016. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2016/05/weigh-package/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250717161318/https://academy.fpblock.com/blog/2016/05/weigh-package/).*

## Work motivation

While working for various clients that needed fast binary serialization, we had discovered that the [`binary`](https://hackage.haskell.org/package/binary) and [`cereal`](https://hackage.haskell.org/package/cereal) packages are both inefficient and so we created the [`store`](https://github.com/fpco/store) package.

In the high-frequency trading sector, we had to decode and encode a binary protocol into Haskell data structures for analysis. During this process it was made apparent to us that while we had been attentive to micro-benchmark with the venerable [`criterion`](https://hackage.haskell.org/package/criterion) package, we hadn't put a lot of work into ensuring that memory usage was well studied. Bringing down allocations (and thus work, and garbage collection) was key to achieving reasonable speed.

## Let's measure space

In response, let's measure space more, in an automatic way.

The currently available way to do this is by compiling with profiling enabled and adding call centers and then running our program with RTS options. For example, we write a program with an `SCC` call center, like this:

``` haskell
main :: IO ()
main = do
  let !_ = {-# SCC myfunction_10 #-} myfunction 10
  return ()
```

Then compile with profiling enabled with `-p` and run with `+RTS -P` and we get an output like this:

``` text
COST CENTRE       MODULE no. entries  ... bytes
MAIN              MAIN   43  0        ... 760
CAF:main1        Main   85  0        ... 0
main            Main   86  1        ... 0
myfunction_10  Main   87  1        ... 160
```

(Information omitted with `...` to save space.)

That's great, exactly the kind of information we'd like to get. But we want it in a more concise, programmatic fashion. On a test suite level.

## Announcing `weigh`

To serve this purpose, I've written the [`weigh`](https://github.com/fpco/weigh) package, which seeks to automate the measuring of memory usage of programs, in the same way that `criterion` does for timing of programs.

It doesn't promise perfect measurement and comes with a grain of salt, but it's reproducible. Unlike timing, allocation is generally reliable provided you use something like [`stack`](https://haskellstack.org) to pin the GHC version and packages, so you can also make a test suite out of it.

## How it works

There is a simple DSL, like `hspec`, for writing out your tests. It looks like this:

``` haskell
import Weigh
main =
  mainWith (do func "integers count 0" count 0
               func "integers count 1" count 1
               func "integers count 2" count 2
               func "integers count 3" count 3
               func "integers count 10" count 10
               func "integers count 100" count 100)
  where count :: Integer -> ()
        count 0 = ()
        count a = count (a - 1)
```

This example weighs the function `count`, which counts down to zero. We want to measure the bytes allocated to perform the action. The output is:

``` text
Case                Bytes  GCs  Check
integers count 0        0    0  OK
integers count 1       32    0  OK
integers count 2       64    0  OK
integers count 3       96    0  OK
integers count 10     320    0  OK
integers count 100  3,200    0  OK
```

Weee! We can now go around weighing everything! I encourage you to do that. Even Haskell newbies can make use of this to get a vague idea of how costly their code (or libraries they're using) is.

## Real-world use-case: `store`

I wrote a few tests, while developing `weigh`, for the `store` package: encoding of lists, vectors and storable vectors. Here's the `criterion` result for encoding a regular `Vector` type:

``` text
benchmarking encode/1kb normal (Vector Int32)/store
time                 3.454 μs   (3.418 μs .. 3.484 μs)
benchmarking encode/1kb normal (Vector Int32)/cereal
time                 19.56 μs   (19.34 μs .. 19.79 μs)
benchmarking encode/10kb normal (Vector Int32)/store
time                 33.09 μs   (32.73 μs .. 33.57 μs)
benchmarking encode/10kb normal (Vector Int32)/cereal
time                 202.7 μs   (201.2 μs .. 204.6 μs)
```

`store` is **6x** faster than `cereal` at encoding Int32 vectors. Great! Our job is done, we've overcome previous limitations of binary encoding speed. Let's take a look at how heavy this process is. Weighing the program on 1 million and 10 million elements yields:

``` text
   1,000,000 Boxed Vector Int     Encode: Store      88,008,584     140  OK
   1,000,000 Boxed Vector Int     Encode: Cereal    600,238,200   1,118  OK
10,000,000 Boxed Vector Int     Encode: Store     880,078,896   1,384  OK
10,000,000 Boxed Vector Int     Encode: Cereal  6,002,099,680  11,168  OK
```

`store` is 6.8x more memory efficient than `cereal`. Excellent. But is our job really finished? Take a look at those allocations. To simply allocate a vector of that size, it's:

``` text
   1,000,000 Boxed Vector Int     Allocate            8,007,936       1  OK
10,000,000 Boxed Vector Int     Allocate           80,078,248       1  OK
```

While `store` is more efficient than `cereal`, how are we allocating 11x the amount of space necessary? We looked into this in the codebase, it turned out more inlining was needed. After comprehensively applying the `INLINE` pragma to key methods and functions, the memory was brought down to:

``` text
   1,000,000 Boxed Vector Int     Allocate            8,007,936       1  OK
   1,000,000 Boxed Vector Int     Encode: Store      16,008,568       2  OK
   1,000,000 Boxed Vector Int     Encode: Cereal    600,238,200   1,118  OK
10,000,000 Boxed Vector Int     Allocate           80,078,248       1  OK
10,000,000 Boxed Vector Int     Encode: Store     160,078,880       2  OK
10,000,000 Boxed Vector Int     Encode: Cereal  6,002,099,680  11,168  OK
```

Now, `store` takes an additional 8MB to encode an 8MB vector, 80MB for an 80MB buffer. That's perfect 1:1 memory usage! Let's check out the new speed without these allocations:

``` text
benchmarking encode/1kb normal (Vector Int32)/store
time                 848.4 ns   (831.6 ns .. 868.6 ns)
benchmarking encode/1kb normal (Vector Int32)/cereal
time                 20.80 μs   (20.33 μs .. 21.20 μs)
benchmarking encode/10kb normal (Vector Int32)/store
time                 7.708 μs   (7.606 μs .. 7.822 μs)
benchmarking encode/10kb normal (Vector Int32)/cereal
time                 207.4 μs   (204.9 μs .. 210.3 μs)
```

`store` is 4x faster than previously! `store` is also now 20x faster than `cereal` at encoding a vector of ints.

## Containers vs unordered-containers

Another quick example, the Map structures from the two containers packages. Let's weigh how heavy `fromList` is on 1 million elements. For fun, the keys are randomly generated rather than ordered. We force the list completely ahead of time, because we just want to see the allocations by the library, not our input list.

``` haskell
fromlists :: Weigh ()
fromlists =
  do let !elems =
           force (zip (randoms (mkStdGen 0) :: [Int])
                      [1 :: Int .. 1000000])
     func "Data.Map.Strict.fromList     (1 million)" Data.Map.Strict.fromList elems
     func "Data.Map.Lazy.fromList       (1 million)" Data.Map.Lazy.fromList elems
     func "Data.IntMap.Strict.fromList  (1 million)" Data.IntMap.Strict.fromList elems
     func "Data.IntMap.Lazy.fromList    (1 million)" Data.IntMap.Lazy.fromList elems
     func "Data.HashMap.Strict.fromList (1 million)" Data.HashMap.Strict.fromList elems
     func "Data.HashMap.Lazy.fromList   (1 million)" Data.HashMap.Lazy.fromList elems
```

We clearly see that `IntMap` from `containers` is about 1.3x more memory efficient than the generic `Ord`-based `Map`. However, `HashMap` wipes the floor with both of them (for `Int`, at least), using 6.3x less memory than `Map` and 4.8x less memory than `IntMap`:

``` text
Data.Map.Strict.fromList     (1 million)  1,016,187,152  1,942  OK
Data.Map.Lazy.fromList       (1 million)  1,016,187,152  1,942  OK
Data.IntMap.Strict.fromList  (1 million)    776,852,648  1,489  OK
Data.IntMap.Lazy.fromList    (1 million)    776,852,648  1,489  OK
Data.HashMap.Strict.fromList (1 million)    161,155,384    314  OK
Data.HashMap.Lazy.fromList   (1 million)    161,155,384    314  OK
```

This is just a trivial few lines of code to generate this result, as you see above.

## Caveat

But beware: it's not going to be obvious exactly where allocations are coming from in the computation (if you need to know that, use the profiler). It's better to consider a computation holistically: this is how much was allocated to produce this result.

Analysis at finer granularity is likely to be guess-work (beyond even what's available in profiling). For the brave, let's study some examples of that.

## Interpreting the results: `Integer`

Notice that in the table we generated, there is a rather odd increase of allocations:

``` text
Case                Bytes  GCs  Check
integers count 0        0    0  OK
integers count 1       32    0  OK
integers count 2       64    0  OK
integers count 3       96    0  OK
integers count 10     320    0  OK
integers count 100  3,200    0  OK
```

What's the explanation for those bytes in each iteration?

Refreshing our memory: The space taken up by a "small" Integer is [two machine words.](https://stackoverflow.com/a/3256825/89574) On 64-bit that's 16 bytes. `Integer` is defined like this:

``` haskell
data Integer
  = S# Int#                            -- small integers
  | J# Int# ByteArray#                 -- large integers
```

For the rest, we'd expect only 16 bytes per iteration, but we're seeing more than that. **Why?** Let's look at [the Core](https://stackoverflow.com/questions/6121146/reading-ghc-core) for `count`:

``` haskell
Main.main48 = __integer 0
Main.main41 = __integer 1
Rec {
Main.main_count [Occ=LoopBreaker] :: Integer -> ()
[GblId, Arity=1, Str=DmdType <S,U>]
Main.main_count =
  \ (ds_d4Am :: Integer) ->
    case eqInteger# ds_d4Am Main.main48 of wild_a4Fq { __DEFAULT ->
    case ghc-prim-0.4.0.0:GHC.Prim.tagToEnum# @ Bool wild_a4Fq
    of _ [Occ=Dead] {
      False -> Main.main_count (minusInteger ds_d4Am Main.main41);
      True -> ghc-prim-0.4.0.0:GHC.Tuple.()
    }
    }
end Rec }
```

The `eqInteger#` function is [a pretend-primop](https://ghc.haskell.org/trac/ghc/wiki/PrimBool#Implementationdetails), which apparently combines with `tagToEnum#` and is optimized away at [the code generation phase.](https://ghc.haskell.org/trac/ghc/ticket/8317) This should lead to an unboxed comparison of something like `Int#`, which should not allocate. This leaves only the addition operation, which should allocate one new 16-byte `Integer`.

So where are those additional 16 bytes from? [The implementation of `minusInteger` for `Integer` types](https://hackage.haskell.org/package/integer-gmp-1.0.0.1/docs/src/GHC.Integer.Type.html#minusInteger) is actually implemented as `x + -y`:

``` haskell
-- TODO
-- | Subtract two 'Integer's from each other.
minusInteger :: Integer -> Integer -> Integer
minusInteger x y = inline plusInteger x (inline negateInteger y)
```

This means we're allocating **one more Integer**. That explains the additional 16 bytes!

There's a `TODO` there. I guess someone implemented `negateInteger` and `plusInteger` (which is [non-trivial](https://hackage.haskell.org/package/integer-gmp-1.0.0.1/docs/src/GHC.Integer.Type.html#plusInteger)) and had enough.

If we implement a second function `count'` that takes this into account,

``` haskell
import Weigh
main :: IO ()
main =
  mainWith (do func "integers count 0" count 0
               func "integers count 1" count 1
               func "integers count 2" count 2
               func "integers count 3" count 3
               func "integers count' 0" count' 0
               func "integers count' 1" count' 1
               func "integers count' 2" count' 2
               func "integers count' 3" count' 3)
  where count :: Integer -> ()
        count 0 = ()
        count a = count (a - 1)
        count' :: Integer -> ()
        count' 0 = ()
        count' a = count' (a + (-1))
```

we get more reasonable allocations:

``` text
Case                Bytes  GCs  Check
integers count 0        0    0  OK
integers count 1       32    0  OK
integers count 2       64    0  OK
integers count 3       96    0  OK
integers count' 0       0    0  OK
integers count' 1      16    0  OK
integers count' 2      32    0  OK
integers count' 3      48    0  OK
```

It turns out that `count'` is 20% faster (from `criterion` benchmarks), but realistically, if speed matters, we'd be using `Int`, which is practically 1000x faster.

What did we learn? Even something as simple as `Integer` subtraction doesn't behave as you would naively expect.

## Considering a different type: `Int`

Comparatively, let's look at `Int`:

``` haskell
import Weigh
main =
  mainWith (do func "int count 0" count 0
               func "int count 1" count 1
               func "int count 10" count 10
               func "int count 100" count 100)
  where count :: Int -> ()
        count 0 = ()
        count a = count (a - 1)
```

The output is:

``` text
Case                Bytes  GCs  Check
ints count 1            0    0  OK
ints count 10           0    0  OK
ints count 1000000      0    0  OK
```

It allocates zero bytes. Why? Let's take a look at the Core:

``` haskell
Rec {
Main.$wcount1 [InlPrag=[0], Occ=LoopBreaker]
  :: ghc-prim-0.4.0.0:GHC.Prim.Int# -> ()
[GblId, Arity=1, Caf=NoCafRefs, Str=DmdType <S,1*U>]
Main.$wcount1 =
  \ (ww_s57C :: ghc-prim-0.4.0.0:GHC.Prim.Int#) ->
    case ww_s57C of ds_X4Gu {
      __DEFAULT ->
        Main.$wcount1 (ghc-prim-0.4.0.0:GHC.Prim.-# ds_X4Gu 1);
      0 -> ghc-prim-0.4.0.0:GHC.Tuple.()
    }
end Rec }
```

It's clear that GHC is able to optimize this tight loop, and unbox the `Int` into an `Int#`, which can be put into a register rather than being allocated by the GHC runtime allocator to be freed later.

The lesson is not to take for granted that everything has a 1:1 memory mapping at runtime with your source, and to take each case in context.

## Data structures

Finally, from our contrived examples we can take a look at user-defined data types and observe some of the optimizations that GHC does for memory.

Let's demonstrate that unpacking a data structure yields less memory. Here is a data type that contains an `Int`:

``` haskell
data HasInt = HasInt !Int
  deriving (Generic)
instance NFData HasInt
```

Here are two identical data types which use `HasInt`, but the first simply uses `HasInt`, and the latter unpacks it.

``` haskell
data HasPacked = HasPacked HasInt
  deriving (Generic)
instance NFData HasPacked
data HasUnpacked = HasUnpacked {-# UNPACK #-} !HasInt
deriving (Generic)
instance NFData HasUnpacked
```

We can measure the difference by weighing them like this:

``` haskell
-- | Weigh: packing vs no packing.
packing :: Weigh ()
packing =
  do func "\\x -> HasInt x" (\x -> HasInt x) 5
     func "\\x -> HasPacked (HasInt x)" (\x -> HasPacked (HasInt x)) 5
     func "\\x -> HasUnpacked (HasInt x)" (\x -> HasUnpacked (HasInt x)) 5
```

The output is:

``` haskell
\x -> HasInt x                      16    0  OK
\x -> HasPacked (HasInt x)          32    0  OK
\x -> HasUnpacked (HasInt x)        16    0  OK
```

Voilà! Here we've demonstrated that:

- `HasInt x` consists of the 8 byte header for the constructor, and 8 bytes for the Int.
- `HasPacked` has 8 bytes for the constructor, 8 bytes for the first slot, then another 8 bytes for the `HasInt` constructor, finally 8 bytes for the `Int` itself.
- `HasUnpacked` only allocates 8 bytes for the header, and 8 bytes for the `Int`.

GHC did what we wanted!

## Summary

We've looked at:

- What lead to this package.
- Propose that we start measuring our functions more, especially libraries.
- How to use this package.
- Some of our use-cases at FP Complete.
- Caveats.
- Some contrived examples do not lead to obvious explanations.

Now I encourage you to try it out!
{% endraw %}
