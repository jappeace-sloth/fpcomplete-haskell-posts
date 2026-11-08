---
layout: page
title: "Collect in Rust, traverse in Haskell and Scala"
---
{% raw %}
*By Michael Snoyman, 6 October 2020. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/collect-rust-traverse-haskell-scala/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250611010103/https://academy.fpblock.com/blog/collect-rust-traverse-haskell-scala/).*

There's a running joke in the functional programming community. Any Scala program can be written by combining the `traverse` function the correct number of times. This blog post is dedicated to that joke.

In Rust, the `Iterator` trait defines a stream of values of a specific type. Many common types provide an `Iterator` interface. And the built in `for` loop construct works directly with the `Iterator` trait. Using that, we can easily do something like "print all the numbers in a `Vec`":

``` rust
fn main() {
    let myvec: Vec<i32> = vec![1, 2, 3, 4, 5];

    for num in myvec {
        println!("{}", num);
    }
}
```

Let's say we want to do something a bit different: double every value in the `Vec`. The most idiomatic and performant way to do that in Rust is with mutable references, e.g.:

``` rust
fn main() {
    let mut myvec: Vec<i32> = vec![1, 2, 3, 4, 5];

    for num in &mut myvec {
        *num *= 2;
    }

    println!("{:?}", myvec);
}
```

Since we're dedicating this post to functional programmers, it's worth noting: this looks decidedly not-functional. "Take a collection and apply a function over each value" is well understood in FP circles—and increasingly in non-FP circles—as a `map`. Or using more category-theoretic nomenclature, it's a `Functor`. Fortunately, Rust provides a `map` method for `Iterator`s. Unfortunately, unlike Scala or Haskell, `map` doesn't work on data types like `Vec`. Let's compare, using Haskell:

``` haskell
list :: [Int]
list = [1, 2, 3, 4, 5]

main :: IO ()
main = do
  let newList :: [Int]
      newList = map (* 2) list
  print newList
```

The `map` function from the `Functor` typeclass works directly on a list. It produces a new list with the function applied to each value. Let's try to do the most equivalent thing in Rust:

``` rust
fn main() {
    let myvec: Vec<i32> = vec![1, 2, 3, 4, 5];

    let new_vec: Vec<i32> = myvec.map(|x| x * 2);

    println!("{:?}", new_vec);
}
```

This fails with the error message:

``` text
no method named `map` found for struct `std::vec::Vec<i32>` in the current scope
```

That's because, in Rust, `map` applies to the `Iterator` itself, not the underlying data structures. In order to use `map` on a `Vec`, we have to:

1.  Convert the `Vec` into an `Iterator`
2.  Perform the `map` on the `Iterator`
3.  Convert the `Iterator` back into a `Vec`

\(1\) can be performed using the `IntoIterator` trait, which provides a method named `into_iter`. And for (3), we could write our own `for` loop that fills up a `Vec`. But the right way is to use the `FromIterator` trait. And the easiest way to do that is with the `collect` method on `Iterator`.

## Using FromIterator and collect

Let's write a program that properly uses `map`:

``` rust
fn main() {
    let myvec: Vec<i32> = vec![1, 2, 3, 4, 5];

    let new_vec: Vec<i32> = myvec
        .into_iter()
        .map(|x| x * 2)
        .collect();

    println!("{:?}", new_vec);
}
```

Fairly straightforward, and our 3 steps turn into three chained method calls. Unfortunately, in practice, using `collect` is often not quite as straightforward as this. That's due to type inference. To see what I mean, let's take all of the type annotations out of the program above:

``` rust
fn main() {
    let myvec = vec![1, 2, 3, 4, 5];

    let new_vec = myvec
        .into_iter()
        .map(|x| x * 2)
        .collect();

    println!("{:?}", new_vec);
}
```

This gives us the very friendly message:

``` text
error[E0282]: type annotations needed
 --> src\main.rs:4:9
  |
4 |     let new_vec = myvec
  |         ^^^^^^^ consider giving `new_vec` a type
```

The issue here is that we don't know which implementation of `FromIterator` we should be using. This is a problem that didn't exist in the pure FP world with `map` and `Functor`. In that world, `Functor`'s `map` is always "shape preserving." When you `map` over a list in Haskell, the result will always be a list.

That's not the case with the `IntoIterator`/`FromIterator` combination. `IntoIterator` destroys the original data structure, fully consuming it and producing an `Iterator`. Similarly, `FromIterator` produces a brand new data structure out of thin air, without any reference to the original data structure. Therefore, an explicit type annotation saying what the output type should be is necessary. In our program above, we did this by annotating `new_vec`. Another way is to use "turbofish" to annotate which `collect` to use:

``` rust
fn main() {
    let myvec = vec![1, 2, 3, 4, 5];

    let new_vec = myvec
        .into_iter()
        .map(|x| x * 2)
        .collect::<Vec<_>>();

    println!("{:?}", new_vec);
}
```

Note that we only needed indicate that we were collecting into a `Vec`. Rust's normal type inference was able to figure out:

- Which numeric type to use for the values
- That the original `myvec` should be a `Vec`, since it was produced by the `vec!` macro

## Side effects and traverse

Alright, I want to announce to the world that I'll be doubling these values. It's easy to modify our `map`-using code in Rust to do this:

``` rust
fn main() {
    let myvec = vec![1, 2, 3, 4, 5];

    let new_vec = myvec
        .into_iter()
        .map(|x| {
            println!("About to double {}", x);
            x * 2
        })
        .collect::<Vec<_>>();

    println!("{:?}", new_vec);
}
```

But Haskellers will warn you that this isn't quite so simple. `map` in Haskell is a pure function, meaning it doesn't allow for any side-effects (like printing to the screen). You can see this in action fairly easily:

``` haskell
list :: [Int]
list = [1, 2, 3, 4, 5]

main :: IO ()
main = do
  let newList :: [Int]
      newList =
        map
          (\x -> do
            putStrLn ("About to double " ++ show x)
            pure (x * 2))
          list
  print newList
```

This code won't compile, due to the mismatch between an `Int` (a pure number) and an `IO Int` (an action with side effects which produces an `Int`):

``` text
Couldn't match type 'IO Int' with 'Int'
Expected type: [Int]
Actual type: [IO Int]
```

Instead, we need to use `map`'s more powerful cousin, `traverse` (a.k.a. `mapM`, or "monadic map"). `traverse` allows us to perform a series of actions, and produce a new list with all of their results. This looks like:

``` haskell
list :: [Int]
list = [1, 2, 3, 4, 5]

main :: IO ()
main = do
  newList <-
    traverse
      (\x -> do
        putStrLn ("About to double " ++ show x)
        pure (x * 2))
      list
  print newList
```

So why the difference between Haskell and Rust here? That's because Rust is not a pure language. Any function can perform side effects, like printing to the screen. Haskell, on the other hand, doesn't allow this, and therefore we need special helper functions like `traverse` to account for the potential side effects.

I won't get into the philosophical differences between the two languages. Suffice it to say that both approaches have merit, and both have advantages and disadvantages. Let's see where the Rust approach "breaks down", and how `FromIterator` steps up to the plate.

## Handling failure

In the example above with Haskell, we used side effects via the `IO` type. However, `traverse` isn't limited to working with `IO`. It can work with *many* different types, anything which is considered `Applicative`. And this covers many different common needs, including error handling. For example, we can change our program to not allow doubling "big" numbers greater than 5:

``` haskell
list :: [Int]
list = [1, 2, 3, 4, 5, 6]

main :: IO ()
main = do
  let newList =
        traverse
          (\x ->
            if x > 5
              then Left "Not allowed to double big numbers"
              else Right (x * 2))
          list
  case newList of
    Left err -> putStrLn err
    Right newList' -> print newList
```

`Either` is a sum type, like an `enum` in Rust. It's equivalent to `Result` in Rust, but with different names. Instead of `Ok` and `Err`, we have `Right` (used by convention for success) and `Left` (used by convention for failure). The `Applicative` instance for it will stop processing when it encounters the first `Left`. So our program above will ultimately produce the output `Not allowed to double big numbers`. You can put as many values after the `6` in `list` as you want, and it will produce the same output. In fact, it will never even inspect those numbers.

Coming back to Rust, let's first simply collect all of our `Result`s together into a single `Vec` to make sure the basics work:

``` rust
fn main() {
    let myvec = vec![1, 2, 3, 4, 5, 6];

    let new_vec: Vec<Result<i32, &str>> = myvec
        .into_iter()
        .map(|x| {
            if x > 5 {
                Err("Not allowed to double big numbers")
            } else {
                Ok(x * 2)
            }
        })
        .collect();

    println!("{:?}", new_vec);
}
```

That makes sense. We've already seen that `.collect()` can take all the values in an `Iterator`'s stream and stick them into a `Vec`. And the `map` method is now generating `Result<i32, &str>` values, so everything lines up.

But this isn't the behavior we want. We want two changes:

- `new_vec` should result in a `Result<Vec<i32>, &str>`. In other words, it should result in either a single `Err` value, or a vector of successful results. Right now, it has a vector of success-or-failure values.
- We should immediately stop processing the original `Vec` once we see a value that's too big.

To make it a bit more clear, it's easy enough to implement this with a `for` loop:

``` rust
fn main() {
    let myvec = vec![1, 2, 3, 4, 5];

    let mut new_vec = Vec::new();

    for x in myvec {
        if x > 5 {
            println!("Not allowed to double big numbers");
            return;
        } else {
            new_vec.push(x);
        }
    }

    println!("{:?}", new_vec);
}
```

But now we've lost out on our `map` entirely, and we're dropping down to using explicit loops, mutation, and short-circuiting (via `return`). In other words, this code doesn't feel nearly as elegant to me.

It turns out that our original code was almost perfect. Let's see a bit of magic, and then explain how it happend. Our previous version of the code used `map` and resulted in a `Vec<Result<i32, &str>>`. And we wanted `Result<Vec<i32>, &str>`. What happens if we simply change the type to what we want?

``` rust
fn main() {
    let myvec = vec![1, 2, 3, 4, 5, 6];

    let new_vec: Result<Vec<i32>, &str> = myvec
        .into_iter()
        .map(|x| {
            if x > 5 {
                Err("Not allowed to double big numbers")
            } else {
                Ok(x * 2)
            }
        })
        .collect();

    match new_vec {
        Ok(new_vec) => println!("{:?}", new_vec),
        Err(e) => println!("{}", e),
    }
}
```

Thanks to the power of `FromIterator`, this simply works! To understand why, let's see some [documentation on `FromIterator`](https://doc.rust-lang.org/stable/std/iter/trait.FromIterator.html#method.from_iter-15):

> Takes each element in the `Iterator`: if it is an `Err`, no further elements are taken, and the `Err` is returned. Should no `Err` occur, a container with the values of each `Result` is returned.

And suddenly it seems that Rust has implemented `traverse` all along! This extra flexibility in the `FromIterator` setup allows us to regain the short-circuiting error-handling behavior that FP people are familiar with in `traverse`.

In contrast to `traverse`, we're still dealing with two different traits (`IntoIterator` and `FromIterator`), and there's nothing preventing these from being different types. Therefore, some kind of type annotation is still necessary. On the one hand, that could be seen as a downside of Rust's approach. On the other hand, it allows us to be more flexible in what types we generate, which we'll look at in the next section.

And finally, it turns out we can use turbofish to rescue us yet again. For example:

``` rust
fn main() {
    let myvec = vec![1, 2, 3, 4, 5, 6];

    let new_vec = myvec
        .into_iter()
        .map(|x| {
            if x > 5 {
                Err("Not allowed to double big numbers")
            } else {
                Ok(x * 2)
            }
        })
        .collect::<Result<Vec<_>, _>>();

    match new_vec {
        Ok(new_vec) => println!("{:?}", new_vec),
        Err(e) => println!("{}", e),
    }
}
```

## Different FromIterator impls

So far, we've only seen two implementations of `FromIterator`: `Vec` and `Result`. There are many more available. One of my favorite is `HashMap`, which lets you collect a sequence of key/value pairs into a mapping.

``` rust
use std::collections::HashMap;

fn main() {
    let people = vec![
        ("Alice", 30),
        ("Bob", 35),
        ("Charlies", 25),
    ].into_iter().collect::<HashMap<_, _>>();

    println!("Alice is: {:?}", people.get("Alice"));
}
```

And due to how the `FromIterator` impl for `Result` works, you can layer these two together to collect a stream of `Result`s of pairs into a `Result<HashMap<_, _>, _>`:

``` rust
use std::collections::HashMap;

fn main() {
    let people = vec![
        Ok(("Alice", 30)),
        Ok(("Bob", 35)),
        Err("Uh-oh, this didn't work!"),
        Ok(("Charlies", 25)),
    ].into_iter().collect::<Result<HashMap<_, _>, &str>>();

    match people {
        Err(e) => println!("Error occurred: {}", e),
        Ok(people) => {
            println!("Alice is: {:?}", people.get("Alice"));
        }
    }
}
```

## Validation

In the Haskell world, we have two different concepts of error collection:

- `Either`, which says "stop on the first error"
- `Validation`, which says "collect all of the errors together"

`Validation` can be very useful for things like parsing web forms. You don't want to generate just the first failure, but collect all of the failures together for producing a more user-friendly experience. For fun, I decided to implement this in Rust as well:

> I'm tempted to write a Validation "Applicative" in Rust with a FromIterator impl to collect multiple Err values. I have no real need for this, but it still seems fun.
>
> — Michael Snoyman (@snoyberg) [October 1, 2020](https://twitter.com/snoyberg/status/1311639149171159041?ref_src=twsrc%5Etfw)

And as you'll see from the rest of that thread, a lot of the motivation for this blog post came from the Twitter replies.

The implementation in Rust is fairly straightforward, and pretty easy to understand. I've [made it available on Github](https://github.com/snoyberg/validation-rs). If there's any interest in seeing this as a crate, let me know in the issue tracker.

To see this in action, let's modify our program above. First, I'll add the dependency to my `Cargo.toml` file:

``` toml
[dependencies.validation]
git = "https://github.com/snoyberg/validation-rs"
rev = "0a7521f7022262bb00aea61761f76c3dd5ccefb5"
```

And then modify the code to use the `Validation` enum instead of `Result`:

``` rust
use std::collections::HashMap;
use validation::Validation;

fn main() {
    let people = vec![
        Ok(("Alice", 30)),
        Ok(("Bob", 35)),
        Err("Uh-oh, this didn't work!"),
        Ok(("Charlies", 25)),
        Err("And neither did this!"),
    ].into_iter().collect::<Validation<HashMap<_, _>, Vec<&str>>>();

    match people.into_result() {
        Err(errs) => {
            println!("Errors:");
            errs.into_iter().map(|x| println!("{}", x)).collect()
        }
        Ok(people) => {
            println!("Alice is: {:?}", people.get("Alice"));
        }
    }
}
```

**Bonus** Note the somewhat cheeky usage of `map` and `collect` to print out the errors. This is leveraging the `()` impl of `FromIterator`, which collects together a stream of `()` values into a single one.

## Conclusion

I realize that was a bit of a rambling journey, but hopefully a fun one for Rustaceans, Haskellers, and Scala folk. Here are some of my takeaways:

- The `collect` method is very flexible
- There's no magic involved in `collect`, just the `FromIterator` trait and the behavior of the types that implement it
  - This was actually a big takeaway for me. I had somehow forgotten about `FromIterator` a few months back, and was nervous about what "secret" behavior `collect` was doing.
- The downside of `collect` is that, since it's not structure preserving like `map` or `traverse`, you'll sometimes need type annotations
  - Get used to turbofish!
- There are lots of useful impls of `FromIterator` available

If you enjoyed this post, you may also want to check out these related topics:

- [Iterators and Streams in Rust and Haskell](../iterators-streams-rust-haskell/)
- [Streaming UTF-8 in Haskell and Rust](../streaming-utf8-haskell-rust/)
- [Rust with DevOps Success Strategies](https://web.archive.org/web/2025/https://tech.fpcomplete.com/blog/rust-devops/)
- [Rust Crash Course eBook](https://web.archive.org/web/2025/https://tech.fpcomplete.com/rust/crash-course/)

If you're interested in learning more about FP Complete's [consulting and training services](https://web.archive.org/web/2025/https://tech.fpcomplete.com/training/), please [contact us](https://web.archive.org/web/2025/https://tech.fpcomplete.com/contact-us/) to talk with our team about how we can help you succeed with Rust, DevOps, and functional programming.
{% endraw %}
