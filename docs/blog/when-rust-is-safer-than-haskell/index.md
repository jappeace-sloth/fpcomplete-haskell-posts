---
layout: page
title: "When Rust is safer than Haskell"
---
{% raw %}
*By Michael Snoyman, 17 January 2019. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/when-rust-is-safer-than-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250717153212/https://academy.fpblock.com/blog/when-rust-is-safer-than-haskell/).*

We’re big fans of safety-focused languages at FP Complete. As our previous blog post comparing Rust and Haskell made clear, we think both of these are great languages. A recurring theme we have for both internal and client projects is: which language should we use? The general guidelines in that blog post apply:

- If there’s a specific requirement (e.g., hard realtime) that prefers avoiding garbage collection, use Rust
- If absolute guarantees of high performance are warranted, prefer Rust
- Otherwise, the higher productivity and greater safety of Haskell push us towards using it

A large part of the higher safety of Haskell is its expressive type system. You can simply state more invariants, in general, in Haskell than in Rust.

However, I’d like to point out a situation where Rust’s safety guarantees are in fact *stronger* than Haskell’s, and how the compiler naturally pushes us towards the correct, safe solution.

## References in Haskell

My general recommendation about mutable variables when giving Haskell training is:

- Avoid them if you can
- If you absolutely must use them, default to using Software Transactional Memory (STM)

If you follow that advice, the bug below won’t occur, or at least won’t occur implicitly. That said, the code below is entirely valid Haskell, so I don’t feel *that* cheeky pointing it out.

Question: Will the following code throw an exception, or will it exit successfully?

``` haskell
main :: IO ()
main = do
  ref <- newIORef (0 :: Int)
  secret $ do
    x <- randomIO
    writeIORef ref x
    threadDelay 1000
    y <- readIORef ref
    unless (x == y) $ error "failure!"
  putStrLn "All good!"
```

This code creates a reference. Then, bracketed by some function `secret`, it will generate a random `Int`, write it to the reference, sleep for 1ms, read the reference out again, and ensure the written and read values are the same.

So will the code throw an exception? The right answer is really “it depends.” We’ve invoked a function called `secret`, with the type `IO () -> IO ()`. Obviously, if `secret` is defined as `secret _ = error "hahaha"`, this code will error out. But I’m talking about non-trivial failure cases.

One valid definition for `secret` is the identity function:

``` haskell
secret :: IO () -> IO ()
secret = id
```

And with this definition, our code exits successfully. Hurrah!

However—and you may have seen this coming—it’s fairly easy to come up with an implementation of `secret` which causes our code to fail:

``` haskell
secret :: IO () -> IO ()
secret = replicateConcurrently_ 1000
```

Or [full code as a Gist](https://gist.github.com/snoyberg/d0625747054342848634089691d25a89).

We’ve now spawned 1,000 threads running concurrently, all trying to write to the same reference. Assuming one version of how these threads get scheduled, all 1,000 threads first write their values to the shared reference. Then, they all take a nap for 1ms. Finally, they all read the value, and 999 of them are disappointed with the result.

The right answer to this in Haskell is what I said above: avoid mutable references, and prefer STM. If you use STM, you’ll need to explicitly bracket your mutable actions with an `atomically` call, and it will be far more obvious when you’re allowing other threads to mutate your variables.

**Click below to learn more about a unique offer**

## How about Rust?

Let’s write an equivalent `main` function in Rust:

``` rust
fn main() {
    let mut var = 0isize;
    secret(|| {
        let x = rand::random();
        var = x;
        sleep(Duration::from_millis(1));
        assert_eq!(x, var);
    });
}
```

Ignoring silly cases like `secret` immediately `panic!`ing, will this code exit successfully? Our gut reaction is “it depends.” But again, ignoring the silly cases, what can go wrong?

Firstly, let’s try out the identity case for Rust. Writing higher order functions is a bit more verbose than in Haskell, but not too bad:

``` rust
fn secret<F: FnMut()>(mut f: F) {
    f();
}
```

*Pro tip*, especially to those who read [my Rust crash course lesson 5](https://www.snoyman.com/blog/2018/11/rust-crash-course-05-rule-of-three): you can use `FnOnce` here instead. I used `FnMut` because of the rest of the code in this post.

If you squint hard enough, you’ll probably agree that this is *basically* the same as the above.

Alright, that’s all well and good, but how about throwing in a curve ball with multiple threads? Let’s really test out that Rust “fearless concurrency” concept:

``` rust
fn secret<F: FnMut()>(mut f: F) {
    let mut handles = vec![];
    for _ in 0..1000 {
        handles.push(spawn(f));
    }
    for handle in handles {
        handle.join().unwrap();
    }
}
```

This code spawns 1,000 threads, each running the same `f` closure. It then blocks on each of these completing (via `join`), and will then re-`panic!` in the main thread if any of the child threads `panic!`ed. For our purposes, it’s quite similar to the `replicateConcurrently_` in Haskell-land.

Obviously this code *must* fail at runtime, right? It has the same kind of logic bug as the Haskell code. However, the Rust code doesn’t even get that far. Instead, we get a *compile time* error:

``` text
error[E0277]: `F` cannot be sent between threads safely
  --> src/main.rs:17:22
   |
17 |         handles.push(spawn(f));
   |                      ^^^^^ `F` cannot be sent between threads safely
   |
   = help: the trait `std::marker::Send` is not implemented for `F`
   = help: consider adding a `where F: std::marker::Send` bound
   = note: required by `std::thread::spawn`
```

Oh, right. We can’t send data between threads unless we have a `Send` trait. Fortunately, the compiler tells us how to fix that one right away. We change the type signature of `secret` to:

``` rust
fn secret<F: FnMut() + Send>(mut f: F) {
```

But now we get a new error:

``` text
error[E0310]: the parameter type `F` may not live long enough
  --> src/main.rs:17:22
   |
14 | fn secret<F: FnMut() + Send>(mut f: F) {
   |           -- help: consider adding an explicit lifetime bound `F: 'static`...
...
17 |         handles.push(spawn(f));
   |                      ^^^^^
   |
note: ...so that the type `F` will meet its required lifetime bounds
  --> src/main.rs:17:22
   |
17 |         handles.push(spawn(f));
   |                      ^^^^^
```

Oh, huh. `F` may not live long enough. Perhaps the closure—or references it has captured—will be dropped before the other thread completes. Again, the compiler tells us how to fix this: add the `'static` lifetime parameter:

``` rust
fn secret<F: FnMut() + Send + 'static>(mut f: F) {
```

Darn, now we’ve got *two* problems: one in the `main` function, and one in `spawn`:

``` text
error[E0597]: `var` does not live long enough
  --> src/main.rs:8:9
   |
6  |     secret(|| {
   |            -- value captured here
7  |         let x = rand::random();
8  |         var = x;
   |         ^^^ borrowed value does not live long enough
...
12 | }
   | - `var` dropped here while still borrowed
   |
   = note: borrowed value must be valid for the static lifetime...

error[E0382]: use of moved value: `f`
  --> src/main.rs:17:28
   |
17 |         handles.push(spawn(f));
   |                            ^ value moved here, in previous iteration of loop
   |
   = note: move occurs because `f` has type `F`, which does not implement the `Copy` trait
```

Ugh, this is getting tedious. Fine, let’s try to solve the problem in `secret`. We’ve *moving* the `f` closure on each iteration through the `for` loop. Let’s clone it instead. To do that, we need to add a `Clone` trait to our `secret` function:

``` rust
fn secret<F: FnMut() + Send + 'static + Clone>(mut f: F) {
    let mut handles = vec![];
    for _ in 0..1000 {
        handles.push(spawn(f.clone()));
    }
    for handle in handles {
        handle.join().unwrap();
    }
}
```

Now, we’ve *finally* written a valid `secret` function. But our `main` function is still broken:

``` text
error[E0277]: the trait bound `&mut isize: std::clone::Clone` is not satisfied in `[closure@src/main.rs:6:12: 11:6 var:&mut isize]`
 --> src/main.rs:6:5
  |
6 |     secret(|| {
  |     ^^^^^^ within `[closure@src/main.rs:6:12: 11:6 var:&mut isize]`, the trait `std::clone::Clone` is not implemented for `&mut isize`
  |
  = help: the following implementations were found:
            <isize as std::clone::Clone>
  = note: required because it appears within the type `[closure@src/main.rs:6:12: 11:6 var:&mut isize]`
note: required by `secret`
 --> src/main.rs:14:1
  |
14| fn secret<F: FnMut() + Send + 'static + Clone>(mut f: F) {
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

The closure captures a mutable reference to a variable. But mutable references cannot be cloned! Because, if we did that, we’d end up with a data race. (Kind of like that original bug in the Haskell program, right?) We’ll *also* run into a lifetime problem, but the compiler hasn’t even identified that here since it’s so hung up on the lack of a `Clone`.

Well, we know how to solve this kind of situatuion in Rust: use a reference counted wrapper. Let’s go ahead and throw that at the problem:

``` rust
use std::rc::Rc;

fn main() {
    let mut var = Rc::new(0isize);
    secret(|| {
        let x = rand::random();
        *var = x;
        sleep(Duration::from_millis(1));
        assert_eq!(x, *var);
    });
}
```

And, once again, Rust doesn’t like this:

``` text
error[E0277]: `std::rc::Rc<isize>` cannot be shared between threads safely
 --> src/main.rs:7:5
  |
7 |     secret(|| {
  |     ^^^^^^ `std::rc::Rc<isize>` cannot be shared between threads safely
  |
  = help: the trait `std::marker::Sync` is not implemented for `std::rc::Rc<isize>`
  = note: required because of the requirements on the impl of `std::marker::Send` for `&std::rc::Rc<isize>`
  = note: required because it appears within the type `[closure@src/main.rs:7:12: 12:6 var:&std::rc::Rc<isize>]`
note: required by `secret`
 --> src/main.rs:15:1
  |
15| fn secret<F: FnMut() + Send + 'static + Clone>(mut f: F) {
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

An `Rc` is a non-atomic reference counted variable. It’s slightly more efficient than an `Arc`, because it doesn’t need to use atomic primitives on the reference count variable. But, we can’t send it to another thread, which is exactly what we’re trying to do. (It’s also what the Haskell type system doesn’t even notice it’s letting us do.)

Switching over to an `Arc` instead solves that problem with almost no code change. We also need to dereference the `var` when using it now:

``` rust
use std::sync::Arc;

fn main() {
    let var = Arc::new(0isize);
    secret(move || {
        let x = rand::random();
        *var = x;
        sleep(Duration::from_millis(1));
        assert_eq!(x, *var);
    });
}
```

But the compiler isn’t happy with this either!

``` text
error[E0594]: cannot assign to data in a `&` reference
 --> src/main.rs:9:9
  |
9 |         *var = x;
  |         ^^^^^^^^ cannot assign

error: aborting due to previous error
```

An `Arc` will dereference into an immutable reference. So of course we can’t write to it! What we’ve essentially created with our `Arc<isize>` is the equivalent of an immutable `Int` in Haskell, which can be shared between multiple threads, but never written to. In order to allow writing, we need some kind of cell wrapper. We could test the waters with `RefCell`, but I’m sure everyone’s falling asleep reading at this point, so let’s just cut to the chase:

``` rust
extern crate rand; // not needed in Rust 2018!

use std::thread::{spawn, sleep};
use std::time::Duration;
use std::sync::{Arc, Mutex};

fn main() {
    let var = Arc::new(Mutex::new(0isize));
    secret(move || {
        let x = rand::random();
        let mut var = var.lock().unwrap();
        *var = x;
        sleep(Duration::from_millis(1));
        assert_eq!(x, *var);
    });
}

fn secret<F: FnMut() + Send + 'static + Clone>(f: F) {
    let mut handles = vec![];
    for _ in 0..1000 {
        handles.push(spawn(f.clone()));
    }
    for handle in handles {
        handle.join().unwrap();
    }
}
```

We’ve gone ahead and locked a mutex, ensuring that no other thread has the possibility of modifying our variable while we’re working with it. This code will compile successfully (finally!), and will complete successfully at runtime.

## Takeaway

While Haskell generally has better safety guarantees than Rust, there are some cases where the explicit tracking of lifetimes and thread safety—versus Haskell’s garbage collection and explicit-mutable-types—produces a safer result. Specifically, in our case, the following features of Rust forced us into using the right solution:

- Inability to clone a mutable reference
- Inability to send the wrong reference type to another thread

The following features also play in, but overlap strongly with Haskell:

- Inability to mutate an immutable reference. In Haskell, you must also (and in some ways, more strongly) opt in to mutability.
- Requirement to ensure variables live long enough. In Haskell, this is handled implicitly via garbage collection.

## Breaking the Rust code

I don’t want to imply that it’s *impossible* to make a logic error in the Rust code. What I *am* saying is that Rust naturally pushed us towards the correct solution here. However, it’s possible for us to reduce the scope of the mutex lock and end up in the same situation as the Haskell code:

``` rust
fn main() {
    let var = Arc::new(Mutex::new(0isize));
    secret(move || {
        let x = rand::random();
        {
            let mut var = var.lock().unwrap();
            *var = x;
        }
        sleep(Duration::from_millis(1));
        {
            let var = var.lock().unwrap();
            assert_eq!(x, *var);
        }
    });
}
```

However, this code is more blatant about its lack of thread safety, just like the Haskell STM implementation is:

``` haskell
main :: IO ()
main = do
  var <- newTVarIO (0 :: Int)
  secret $ do
    x <- randomIO
    atomically $ writeTVar var x
    threadDelay 1000
    y <- atomically $ readTVar var
    unless (x == y) $ error "failure!"
  putStrLn "All good!"
```

While both the Haskell and Rust versions presented will fail at runtime, it’s fair to claim that the language and libraries did all they possibly could to help the programmer avoid the problem. In the Rust case, we explicitly delimited the scope and locked the mutex twice. In the Haskell code, we explicitly elected to perform two different atomic transactions.

When dealing with concurrent code—or really any code—it’s impossible to create a language that will prevent the possibility of all logic errors. Instead, our hope is that we avoid *most* logic errors with the help of our tooling. And I believe both Haskell and Rust assist with this significantly.

Learn more about [Haskell](https://web.archive.org/web/2025/https://academy.fpblock.com/haskell) and [Rust](https://web.archive.org/web/2025/https://academy.fpblock.com/rust) at FP Complete.

Interested in exploring these languages for your team? Find out more about our [consulting](https://web.archive.org/web/2025/https://academy.fpblock.com/custom) and [training](https://web.archive.org/web/2025/https://academy.fpblock.com/training) offerings.
{% endraw %}
