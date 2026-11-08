---
layout: page
title: "Teaching Haskell with Duet"
---
{% raw %}
*By Chris Done, 30 December 2019. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/teaching-haskell-with-duet/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250515035033/https://academy.fpblock.com/blog/teaching-haskell-with-duet/).*

# Teaching Haskell with Duet

Teaching Haskell to complete beginners is an enjoyable experience. Haskell is foreign; many of its features are alien to other programmers. It's purely functional. It's non-strict. Its type system is among the more pervasive of other practical languages.

## Simple at the core

Haskell's core language is simple, though. It shares this with Lisp. [Structured and Interpretation of Computer Programs by MIT](https://mitpress.mit.edu/sites/default/files/sicp/full-text/sicp/book/node10.html) teaches Lisp beginning with a substitution model for function application. This turns out to work well for Haskell too. This is how I've been teaching Haskell to beginners at FP Complete for our clients.

For example, in SICP, they use the example:

``` lisp
(+ (square 6) (square 10))
```

which reduces the function `square` to

``` lisp
(+ (* 6 6) (* 10 10))
```

which reduces by multiplication to:

``` lisp
(+ 36 100)
```

and finally to

``` lisp
136
```

As they note in SICP,

> The purpose of the substitution is to help us think about procedure application, not to provide a description of how the interpreter really works. Typical interpreters do not evaluate procedure applications by manipulating the text of a procedure to substitute values for the formal parameters.

That this, this is a *model*, it's not the real thing. In fact, if you really eyeball the very first step, you might wonder which `(square ..)` argument is evaluated first between the two. Scheme doesn't specify an argument order; it varies. An implementation may even inline the whole thing.

Rather, if we think about programs in terms of a simple sequence of rewrites, we get a lot of bang for our buck in terms of reasoning and understanding.

## The right language to model

Motivated by this goal, I started thinking about automating this process, so that students could use this model more readily, and see the shape of functions and algorithms visually. The solution I came up with was a new language that is a subset of Haskell, which I'll cover in this post.

The reason that it's not full Haskell is that Haskell has a lot of surface-level syntactic sugar. Evaluating the real language is complicated and infeasible. The following contains too many things at once to consider:

``` haskell
quicksort1 :: (Ord a) => [a] -> [a]
quicksort1 [] = []
quicksort1 (x:xs) =
  let smallerSorted = quicksort1 [a | a <- xs, a <= x]
      biggerSorted = quicksort1 [a | a <- xs, a > x]
  in  smallerSorted ++ [x] ++ biggerSorted
```

Pattern matches at the definition, list syntax, comprehensions, lets. There's a lot going on here that makes a newbie's eyes glaze over. We have to start simpler. But how simple?

GHC Haskell has a tiny language called Core to which all Haskell programs compile down to. Its AST looks roughly like this:

``` haskell
data Expr
  = App Expr Expr
  | Var Var
  | Lam Name Type Expr
  | Case Expr [Alt]
  | Let Bind Expr
  | Lit Literal
```

Evaluation of Core is simple. However, Core is also a little *too low-level*, because it puts polymorphic types and type-class dictionaries as normal arguments, inlines a lot of things, looks underneath boxed types like `Int` (into `I#`), and adds some extra capabilities normal Haskell doesn't have that are only appropriate for a compiler writer to see. The above function compiled to Core starts like this:

``` haskell
quicksort1
  = \ (@ a_a1Zd) ($dOrd_a1Zf :: Ord a_a1Zd) (ds_d22B :: [a_a1Zd]) ->
      case ds_d22B of {
        [] -> GHC.Types.[] @ a_a1Zd;
        : x_a1sG xs_a1sH ->
          ++
            @ a_a1Zd
            (quicksort1
               @ a_a1Zd
               $dOrd_a1Zf
               (letrec {
                  ds1_d22C [Occ=LoopBreaker] :: [a_a1Zd] -> [a_a1Zd]
           ...
```

We have to explain the special list syntax, module qualification, polymorphic types, dictionaries, etc. all in one go, besides the obvious challenge of the unreadable naming convention. Core is made for compilers and compiler writers, not for humans.

## Duet

Therefore I took a middle way. Last year I wrote [a language called Duet](https://github.com/chrisdone/duet), which is a Haskell subset made specifically for teaching at this period of learning Haskell. Duet only has these language features: data types, type-classes, top-level definitions, lambdas, case expressions, and some literals (strings, integrals, rationals). Its main feature is steppability; the ability to step through the code. Every step produces a valid program.

Returning to the SICP example with our new tool, here's the same program in Duet:

``` haskell
square = \x -> x * x
main = square 6 + square 10
```

``` haskell
chris@precision:~/Work/duet-lang/duet$ duet run examples/sicp.hs
(square 6) + (square 10)
((\x -> x * x) 6) + (square 10)
(6 * 6) + (square 10)
36 + (square 10)
36 + ((\x -> x * x) 10)
36 + (10 * 10)
36 + 100
136
```

Here we see a substitution model in action. Each line is a valid program! You can take any line from the output and run it from that point.

Unlike Scheme, Duet picks an argument order (left-to-right) for strict functions like integer operations.

**Note**: You can follow along at home by creating a file and running it using [docker run](https://github.com/chrisdone/duet) on Linux, OS X or Windows.

## Folds

Let's turn our attention to the teaching of folds, which is a classic hurdle to get newbies through, as it is a kind of forcing function for a variety of topics.

The right fold is clasically defined like this:

``` haskell
foldr f z []     = z
foldr f z (x:xs) = f x (foldr f z xs)
```

This is not a valid Duet program, because (1) it uses list syntax (lists aren't special), and (2) it uses case analysis at the declaration level. If you try substitution stepping these, you quickly arrive at an awkward conversation about the difference between the seemingly three-argument function `foldr`, and lambdas, partial application, currying, and pattern matching, and whether we're defining two functions or one. Here is the same program in Duet:

``` haskell
data List a = Nil | Cons a (List a)
foldr = \f -> \z -> \l ->
  case l of
    Nil -> z
    Cons x xs -> f x (foldr f z xs)
```

At the end of teaching the substitution model, I cover that `\x y z` is syntactic sugar for `\x -> \y -> \z -> ...`, but only after the intuition has been solidified that all Haskell functions take one argument. They may return other functions. So the updated program is:

``` haskell
data List a = Nil | Cons a (List a)
foldr = \f z l ->
  case l of
    Nil -> z
    Cons x xs -> f x (foldr f z xs)
```

Which is perfectly valid Haskell, and each part of it can be rewritten predictably.

Let's look at comparing `foldr` with `foldl`.

``` haskell
data List a = Nil | Cons a (List a)
foldr = \f z l ->
  case l of
    Nil -> z
    Cons x xs -> f x (foldr f z xs)
foldl = \f z l ->
  case l of
    Nil -> z
    Cons x xs -> foldl f (f z x) xs
list = Cons 1 (Cons 2 Nil)
```

## Folds at a glance

For a *quick* summary, we can use holes like in normal Haskell indicated by `_` or `_foo`. In Duet, these are ignored by the type system and the stepper, letting you run the stepper with holes in too. They don't result in an error, so you can build up expressions with them inside.

``` haskell
main_foldr = foldr _f _nil list
main_foldl = foldl _f _nil list
list = Cons 1 (Cons 2 (Cons 3 (Cons 3 Nil)))
```

(I increased the size of the list for a longer more compelling output.)

We can pass `--concise` which is a convenience flag to literally filter out intermediate steps (cases, lambdas) which helps us see the "high-level" recursion. This flag is still under evaluation (no pun intended), but is useful here. Full output is worth studying with students too, but is too long to fit in this blog post. I will include a snippet from a non-concise example below.

The output looks like this:

``` haskell
$ duet run examples/folds-strictness.hs --main main_foldr --concise
foldr _f _nil list
_f 1 (foldr _f _nil (Cons 2 (Cons 3 (Cons 4 Nil))))
_f 1 (_f 2 (foldr _f _nil (Cons 3 (Cons 4 Nil))))
_f 1 (_f 2 (_f 3 (foldr _f _nil (Cons 4 Nil))))
_f 1 (_f 2 (_f 3 (_f 4 (foldr _f _nil Nil))))
_f 1 (_f 2 (_f 3 (_f 4 _nil)))
$ duet run examples/folds-strictness.hs --main main_foldl --concise
foldl _f _nil list
foldl _f (_f _nil 1) (Cons 2 (Cons 3 (Cons 4 Nil)))
foldl _f (_f (_f _nil 1) 2) (Cons 3 (Cons 4 Nil))
foldl _f (_f (_f (_f _nil 1) 2) 3) (Cons 4 Nil)
foldl _f (_f (_f (_f (_f _nil 1) 2) 3) 4) Nil
_f (_f (_f (_f _nil 1) 2) 3) 4
```

We can immediately see what the "right" part of `foldr` means. Experienced Haskellers can already see the teaching opportunities sprouting from the earth at this point. We're using O(n) space here, building nested thunks, or using too much stack. Issues abound.

Meanwhile, in `foldl`, we've shifted accumulation of the nested thunks to an argument of `foldr`, but at the end, we still have a nested thunk. Enter strict left fold!

We also see the argument order come into play: `_f` is applied to `1` first in `foldr` (`_f 1 (foldr ...)`), but last in `foldl` (`_f (_f _nil 1) ...`, which is another important part of understanding the distinction between the two.

## Strict folds

To see the low-level mechanics, and as a precursor to teaching strict fold, we ought to use an actual arithmetic operation (because you can't strictly evaluate a `_` hole, by definition, it's missing):

``` haskell
main_foldr = foldr (\x y -> x + y) 0 list
main_foldl = foldl (\x y -> x + y) 0 list
```

Both folds eventually yield:

``` haskell
1 + (2 + 0)
1 + 2
3
```

And:

``` haskell
((\x y -> x + y) 0 1) + 2
((\y -> 0 + y) 1) + 2
(0 + 1) + 2
1 + 2
3
```

(Here you can also easily see where the `0` lies in the tree.)

Which both have the built up thunk problem mentioned above.

Duet has bang patterns, so we can define a strict fold like this:

``` haskell
data List a = Nil | Cons a (List a)
foldr = \f z l ->
  case l of
    Nil -> z
    Cons x xs -> f x (foldr f z xs)
foldl = \f z l ->
  case l of
    Nil -> z
    Cons x xs -> foldl f (f z x) xs
foldl_ = \f z l ->
  case l of
    Nil -> z
    Cons x xs ->
      case f z x of
        !z_ -> foldl_ f z_ xs
list = Cons 1 (Cons 2 Nil)
main_foldr = foldr (\x y -> x + y) 0 list
main_foldl = foldl (\x y -> x + y) 0 list
main_foldl_ = foldl_ (\x y -> x + y) 0 list
```

(We don't allow `'` as part of a variable name, as it's not really necessary and is confusing for non-Haskeller beginners. An undercore suffices.)

Now, looking in detail without the `--concise` arg, just before the recursion, we see the force of the addition:

``` haskell
case Cons 1 (Cons 2 Nil) of
  Nil -> 0
  Cons x xs ->
    case (\x y -> x + y) 0 x of
      !z_ -> foldl_ (\x y -> x + y) z_ xs
case (\x y -> x + y) 0 1 of
  !z_ -> foldl_ (\x y -> x + y) z_ (Cons 2 Nil)
case (\y -> 0 + y) 1 of
  !z_ -> foldl_ (\x y -> x + y) z_ (Cons 2 Nil)
case 0 + 1 of
  !z_ -> foldl_ (\x y -> x + y) z_ (Cons 2 Nil)
case 1 of
  !z_ -> foldl_ (\x y -> x + y) z_ (Cons 2 Nil)
foldl_ (\x y -> x + y) 1 (Cons 2 Nil)
```

And finally, taking a glance with `--concise`, we see:

``` haskell
$ duet run examples/folds-strictness.hs --main main_foldl_ --concise
foldl_ (\x y -> x + y) 0 list
foldl_ (\x y -> x + y) 1 (Cons 2 (Cons 3 (Cons 4 Nil)))
foldl_ (\x y -> x + y) 3 (Cons 3 (Cons 4 Nil))
foldl_ (\x y -> x + y) 6 (Cons 4 Nil)
foldl_ (\x y -> x + y) 10 Nil
10
```

Which spells out quite clearly that now we are: (1) doing direct recursion, and (2) calculating the accumulator with each recursion step (`0`, `1`, `3`, `6`, `10`).

## Concluding

This post serves as both knowledge sharing for our team and a public post to show the kind of detailed level of training that we're doing for our clients.

If you'd like Haskell training for your company, [contact us](https://web.archive.org/web/2025/https://academy.fpblock.com/cdn-cgi/l/email-protection#c7b4a6aba2b487a1b7a4a8aab7aba2b3a2e9a4a8aa) to arrange a meeting.

Want to read more about Haskell? Check out [our blog](https://web.archive.org/web/2025/https://tech.fpcomplete.com/blog/) and our [Haskell homepage](https://web.archive.org/web/2025/https://tech.fpcomplete.com/haskell/).
{% endraw %}
