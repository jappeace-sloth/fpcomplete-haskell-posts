---
layout: page
title: "The Hidden Dangers of Haskell's Ratio Type"
---
{% raw %}
*By Neil Mayhew, 27 April 2022. Mirrored from FP Complete's blog: [original URL](https://www.fpcomplete.com/blog/hidden-dangers-of-ratio/) (offline), [Wayback Machine copy](https://web.archive.org/web/20220512202510/https://www.fpcomplete.com/blog/hidden-dangers-of-ratio/).*

Here's a new Haskell [**WAT?!**](https://www.destroyallsoftware.com/talks/wat)

Haskell has a type `Rational` for working with precisely-valued fractional numbers, and it models the mathematical concept of a [rational number](https://en.wikipedia.org/wiki/Rational_number). Although it's relatively slow compared with `Double`, it doesn't suffer from the rounding that's intrinsic to floating-point arithmetic. It's very useful when writing tests because an exact result can be predicted ahead of time. For example, a computation that should produce zero will produce exactly zero rather than a small value within some range that would have to be determined.

`Rational` is actually a (monomorphic) specialization of the more general (polymorphic) type `Ratio` (from [`Data.Ratio`](https://hackage.haskell.org/package/base/docs/Data-Ratio.html)). `Ratio` allows you to specify the underlying type used for the numerator and denominator. For example, to work with rational numbers using `Int` as the underlying type you can use `Ratio Int`. For the common case of using `Integer` as the underlying type, the type synonym `Rational` is provided:

``` text
type Rational = Ratio Integer
```

It's tempting to use `Ratio` with a fixed-width type like `Int` because `Int` is much faster than `Integer`. However, let's see what can happen if you do this:

``` text
λ> import Data.Int
λ> import Data.Ratio
λ> let r = 1 % 12 :: Rational   in r - r == 0
True
λ> let r = 1 % 12 :: Ratio Int8 in r - r == 0
False
```

**WAT?!**

Let's see what those subtracted values evaluate to:

``` text
λ> let r = 1 % 12 :: Rational   in r - r
0 % 1
λ> let r = 1 % 12 :: Ratio Int8 in r - r
0 % (-1)
```

Hmmm, let's see if that `Ratio Int8` value is considered equal to `0`:

``` text
λ> let r = 0 % (-1) :: Ratio Int8 in r == 0
True
```

**WAT?!**

Let's see what those manually-entered values are:

``` text
λ> 0 % (-1) :: Ratio Int8
0 % 1
λ> 0 :: Ratio Int8
0 % 1
```

OK, so these values really are equal, but why are the values in the subtraction different? The explanation is two-fold.

First, `0 % (-1)` is a denormalized state for `Ratio` and shouldn't occur. (As you've probably suspected, it arises from integer overflow. More on that in a minute.) It's not too surprising, then, that it isn't equal to `0`.

But why is it equal to `0` when we enter it directly? It's because `%` is a function not a constructor, and it normalizes the signs of the numerator and denominator before constructing the value:

``` text
x % y = reduce (x * signum y) (abs y)
```

The underlying assumption (the *invariant*) is that denominators will always be positive.

`reduce` is a function that reduces the numerator and denominator to their lowest terms, by dividing by the greatest common divisor:

``` text
reduce x y = (x `quot` d) :% (y `quot` d)
  where d = gcd x y
```

Here you can see the constructor that actually creates the values from their components, which is `:%`. It's not exported from `Data.Ratio` and the "smart constructor" `%` is used instead, to ensure that new `Ratio` values always satisfy the invariant.

Second, addition and subtraction are implemented without trying to minimize the possibility of integer overflow. For example:

``` text
(x :% y) - (x' :% y') = reduce (x * y' - x' * y) (y * y')
```

If `y * y'` overflows to a negative value, `reduce` will not normalize the signs. The result of `gcd` is always non-negative so the signs don't change and denormalized values are never renormalized. That happens only in `%` when constructing `Ratio` values.

Let's look at what happens in our example:

``` text
λ> x = 1; y = 12; x' = 1; y' = 12
λ> x * y' - x' * y :: Int8
0
λ> y * y' :: Int8
-112
λ> gcd 0 (-112)
112
λ> 0 `quot` 112
0
λ> (-112) `quot` 112
-1
```

The reduced result of `1 % 12 - 1 % 12` is therefore the denormalized value `0 :% (-1)` which isn't considered equal to the normalized value `0 % 1`.

Even though `12` is much less than `maxBound :: Int8`, when squared it results in integer overflow. The implementation of `Num` for `Ratio` is *not* designed to avoid overflows and they can happen very easily with numerators and denominators that are much less than the `maxBound` for the type.

The implementation could have used a slightly different approach:

``` text
(x :% y) - (x' :% y') = reduce (x * z' - x' * z) (y * z')
  where z = y `quot` d
        z' = y' `quot` d
        d = gcd y y'
```

However, the use of `reduce` is still necessary (consider `3 % 10 - 2 % 15`) so this requires two more divisions and a `gcd` compared with the actual implementation.

Using a type as small as `Int8` might seem a little unrealistic, but the problem can occur with any fixed-width integral type and I used `Int8` for the illustration because it's easier to understand the problem when working with small values. I originally encountered it when using `Ratio Int` even though `Int` has a very large `maxBound`. I was writing property tests using QuickCheck for some polymorphic arithmetic code that was supposed to produce a zero sum as a result. The test succeeded with `Rational` and failed with `Ratio Int` and I couldn't understand why because the random values being generated by the test framework had numerators and denominators far less than `maxBound :: Int`. However, they *were* greater than its square root.

The documentation for `Ratio` says:

> Note that Ratio's instances inherit the deficiencies from the type parameter's. For example, `Ratio Natural`'s `Num` instance has similar problems to `Natural`'s.

However, that doesn't really prepare you for what might happen with other type parameters! The moral of this story is that `Ratio` isn't much use on its own and you should always use `Rational` unless you *really* understand what you're getting into.

## Further reading

Like that blog post? Check out the [Haskell section](https://web.archive.org/web/2025/https://www.fpcomplete.com/haskell/) of our site with tutorials and other blog posts. You can also check out all [Haskell tagged blog posts](https://web.archive.org/web/2025/https://www.fpcomplete.com/tags/haskell/).

**We're hiring.** Interested in working with our team on solving these kinds of WAT issues? Check out our [jobs page](https://web.archive.org/web/2025/https://www.fpcomplete.com/jobs/) for more information.

<a href="https://blogtrottr.com/?subscribe=https://www.fpcomplete.com/feed/" class="btn btn-primary">Subscribe to our blog via email</a>  
<span class="small">Email subscriptions come from our [Atom feed](https://web.archive.org/web/2025/https://www.fpcomplete.com/feed/) and are handled by [Blogtrottr](https://blogtrottr.com). You will only receive notifications of blog posts, and can unsubscribe any time.</span>
{% endraw %}
