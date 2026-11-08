---
layout: page
title: "Common Typeclasses"
---
{% raw %}
*Mirrored from the Haskell section of FP Complete's site: [original URL](https://academy.fpblock.com/haskell/tutorial/common-typeclasses/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428061300/https://academy.fpblock.com/haskell/tutorial/common-typeclasses/).*

A great resource for information on common typeclasses in Haskell is the [typeclassopedia](https://wiki.haskell.org/Typeclassopedia). We recommend reading that document, and following up here for additional pointers.

Section exercises:

- Write the `foldMapM` helper function
- Implement the `Validation` `Applicative`
  - Why isn't it a `Monad`?

## Overview

- Not going to cover these in depth
- Great resource on this: [typeclassopedia](https://wiki.haskell.org/Typeclassopedia)

## Hysterical raisins

- `Applicative` wasn't a superclass of `Monad` in the past
- `Semigroup` wasn't a superclass of `Monoid` in the past
- Some unnecessary functions still lying around
- Sometimes functions aren't as general as we wish

## Functor

- "Mappable"
- Provides `fmap :: (a -> b) -> (f a -> f b)`
- Laws
  - `fmap id == id`
  - `fmap (g . h) == fmap g . fmap h`
- Cool fact: only one possible valid instance per type
- Can be derived automatically
- Covariant functor (contravariant also exists)
- See: [Covariance and Contravariance](../../../blog/covariance-contravariance/)

## Applicative

Provides:

``` haskell
pure :: a -> f a
(<*>) :: f (a -> b) -> f a -> f b
```

Compare:

``` haskell
fmap  ::   (a -> b) -> f a -> f b
(<*>) :: f (a -> b) -> f a -> f b
```

Also note that you can define `fmap` using `Applicative`

``` haskell
fmap g x = pure g <*> x
```

Laws:

- `pure id <*> x == x`
- `pure f <*> pure x == pure (f x)`
- `u <*> pure y == pure ($ y) <*> u`
- `u <*> (v <*> w) = pure (.) <*> u <*> v <*> w`

## Monad

Provides:

``` haskell
(>>=) :: m a -> (a -> m b) -> m b
```

Or flipped:

``` haskell
(=<<) :: (a -> m b) -> m a -> m b
```

Compare:

``` haskell
fmap  ::   (a -> b) -> f a -> f b
(<*>) :: f (a -> b) -> f a -> f b
(=<<) :: (a -> m b) -> m a -> m b
```

Laws:

- `pure a >>= f == f a`
- `m >>= pure == m`
- `m >>= (\x -> f x >>= g) == (m >>= f) >>= g`

And we can define:

``` haskell
(<=<) :: Monad m => (b -> m c) -> (a -> m b) -> (a -> m c)
```

And then restate these laws as:

``` haskell
f <=< pure == f
pure <=< f == f
(h <=< g) <=< f == h <=< (g <=< f)
```

Which are the same as the category laws:

``` haskell
f . id == f
id . f == f
(h . g) . f == h . (g . f)
```

## Semigroup and Monoid

Summary explanation: `Semigroup` defines a binary, associative operator.

``` haskell
(<>) :: a -> a -> a
```

Law

``` haskell
(x <> y) <> z == x <> (y <> z)
```

`Monoid` is a subclass of `Semigroup`, and adds an identity to `Semigroup`.

``` haskell
mempty :: a
```

The laws are the same again as `Monad` and categories!

``` haskell
x <> mempty == x
mempty <> x == x
(x <> y) <> z == x <> (y <> z)
```

More worked explanation: `Semigroup` is a typeclass that provides a single binary, associative operator. For example, for integers, `+` and `*` are both valid `Semigroup` implementations. For lists, appending two lists forms a `Semigroup`.

`Monoid` builds on `Semigroup`, but adds in an identity, where it follows the law that applying that binary operator as either the left or right value to the identity is a no-op

In other words: `0 + x = x`, `x + 0 = x`, and `(a + b) + c = a + (b + c)`. Therefore: `(<>) = (+)` and `mempty = 0` forms a valid `Semigroup`/`Monoid` pair of instances. Some things are a `Semigroup`, but not a Monoid. A simple example: a non-empty list. While you can append together two non-empty lists, there's no identity value you can come up with where the identity laws hold.

That's all the technical definition. Intuition: `Semigroup` and `Monoid` let you define a way to slam data together!

**EXERCISE** Write a data type for calculating the average of a bunch of values. The data type will need to have two fields: one to keep the running sum, one the running total. Then write `Semigroup` and `Monoid` instances that Do The Right Thing, define an `average` function that calculates the average from these two fields, and you're done. Try using `fold` (part of the `Foldable` typeclass we'll cover next) to summarize a list of values.

## Foldable

- "I can be turned into a list" but more efficient in some cases.
- `foldMap :: Monoid m => (a -> m) -> f a -> m`
- Can be derived automatically
- No actual laws yet
- Could define a `Vector` that folds left-to-right or right-to-left
- `length` of tuples and other things considered surprising/wrong by many

## Traversable

- "Map with effects"
- Generalizes `mapM`
- `traverse` == `mapM`, but works for `Applicative`
- `for` == `forM`, but for `Applicative`

## Exercises

See start of section
{% endraw %}
