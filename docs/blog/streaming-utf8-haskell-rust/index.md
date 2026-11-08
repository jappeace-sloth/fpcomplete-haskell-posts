---
layout: page
title: "Streaming UTF-8 in Haskell and Rust"
---
{% raw %}
*By Michael Snoyman, 30 July 2018. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2018/07/streaming-utf8-haskell-rust/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250611010103/https://academy.fpblock.com/blog/2018/07/streaming-utf8-haskell-rust/).*

Since I seem to be a one-trick pony, I decided to write [yet again](../iterators-streams-rust-haskell/) to compare streaming data in Haskell and Rust. This was inspired by a [cool post I saw on Reddit](https://www.reddit.com/r/rust/comments/8z2i8t/%D1%81%D1%87%D1%8F%D1%81%D0%BE%D0%BF%D1%9F_fl%D0%B5%D1%85_%D0%BC%D0%B0%D1%80%D1%95_l%D0%B0%D1%82%D1%96%D0%BF_%D1%81%D0%BD%D0%B0%D0%B3%D0%B0%D1%81%D1%82%D0%B5%D0%B3%D1%95_%D1%96%D0%BF%D1%82%D0%BE_%D1%81%D1%87%D0%B3%D1%96ll%D1%96%D1%81/) about converting characters in the Latin alphabet into look-alikes in the Cyrilic alphabet.

When reviewing the original code, I noticed that it was reading the full contents of the input into memory. Since I’m [somewhat obsessed](../../haskell/library/conduit/) with streaming data, I wanted to see what it would take to make this stream in Rust. But first, of course, I proved to myself that I could do this in Haskell.

**Caveats**

- The solution I’ve created here is a *prototype*. Please do not use this Rust code in production, at the very least it does not handle some invalid UTF-8 encodings correctly.
- I am not covering some common libraries for character encoding like `encoding_rs`. This is intended to be more of a dive into streaming and error handling than character encoding itself.
- I haven’t done any performance optimization or even benchmarking on this. The focus here has been entirely about ergonomics. I may follow up with another blog post around performance analysis if there’s interest.

All of the code is available [in my Github repo](https://github.com/snoyberg/rust-streaming-utf8).

## Haskell solution

In order to run the Haskell solution, please [download and install Stack](https://web.archive.org/web/2025/https://haskell-lang.org/get-started), save the content below as `stream-hs.hs` and run something like `stack stream-hs.hs < input.txt`.

``` haskell
#!/usr/bin/env stack
-- stack --resolver lts-12.0 script
import Conduit
import Data.HashMap.Strict (HashMap)
import qualified Data.HashMap.Strict as HashMap

mapper :: HashMap Char Char
mapper = HashMap.fromList $ zip
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
  "ДВСDЁҒGНІЈКLМПОРQЯЅТЦЏШХЧZавсdёfgніјкlмпорqгѕтцѵшхчz"

convertChar :: Char -> Char
convertChar c = HashMap.lookupDefault c c mapper

main :: IO ()
main = runConduit
     $ stdinC
    .| decodeUtf8C
    .| omapCE convertChar
    .| encodeUtf8C
    .| stdoutC
```

We create a `HashMap` mapping the input Latin characters to the output Cyrilic characters, and then create a helper `convertChar` function to convert any incoming character, defaulting to the original if the input isn’t a Latin letter.

Next, we use the conduit library for producing, transforming, and consuming the stream of data. We use the `.|` operator to pipe together different components of the pipeline, and then call `runConduit` on the completed pipeline to run it. Our pipeline looks like this:

- Stream out raw chunks of binary data from standard input using `stdinC`
- UTF-8 decode the chunks of binary data into chunks of textual data using `decodeUtf8C`. This automatically handles issues of chunk boundaries grabbing incomplete UTF-8 sequences. If there is any invalid UTF-8 data, it will throw a runtime exception.
  - There is also a `decodeUtf8LenientC` function which uses the Unicode replacement function, but that’s not very interesting for us today. We *want* to compare how the two languages handle errors.
- Apply our `convertChar` function to each character in the stream. We have to use the funnily-named `omapCE` function here. Let’s break it down a bit:
  - `map`, since we’re applying a function to all the values in a stream. That makes sense.
  - `C`, because it’s a conduit function. Alright.
  - `E`, because we want to apply our function to the elements of the stream, not the chunks themselves. You see, our incoming stream is a stream of `Text` values, *not* `Char` values. `E` says “apply the function to the values *inside* the `Text`, not the `Text` itself.
  - `o`, because `Text` is a *monomorphic* container (it can only hold `Char` values). This comes from `mono-traversable`. The `o` choice is a bit strange, but it makes sense when you realize that the letter `m` is already used for a lot of things in Haskell.
- We UTF-8 encode our text back to binary data using `encodeUtf8C`
- And finally we dump the data to standard output with `stdoutC`

There are other ways to handle this in Haskell, both with and without conduit. You can use lazy I/O. You can use the built-in character encoding handling of `Handle`s. But the approach here is both pretty close to what we want to build in Rust, and is probably what I’d personally reach for in the first place. (Which makes sense; I wrote conduit.)

Alright, that’s nice, Haskell’s awesome, blah blah blah. Let’s get onto the cool stuff: Rust!

## Character mapping

Let’s knock out the easiest part of this. We want to create a `HashMap` to help us convert from Latin to Cyrilic. Our code looks remarkably similar in both Haskell and Rust. Let’s compare side-by-side:

``` haskell
mapper :: HashMap Char Char
mapper = HashMap.fromList $ zip
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
  "ДВСDЁҒGНІЈКLМПОРQЯЅТЦЏШХЧZавсdёfgніјкlмпорqгѕтцѵшхчz"

convertChar :: Char -> Char
convertChar c = HashMap.lookupDefault c c mapper
```

``` rust
let mapper: HashMap<char, char> =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".chars().zip(
    "ДВСDЁҒGНІЈКLМПОРQЯЅТЦЏШХЧZавсdёfgніјкlмпорqгѕтцѵшхчz".chars())
    .collect()
    ;
let convert_char = |c| *mapper.get(&c).unwrap_or(&c);
```

In both cases, we take our two strings, zip them into a sequence of pairs, and then turn that sequence of pairs into a `HashMap`. In Haskell, `String`s are a lazy list of characters, so the streaming nature of this is implicit. In Rust, we explicitly use an iterator interface (via `chars()`).

Also, in Haskell, we can define this value and function at the top level, whereas in Rust it’s preferable to put this inside the `main` function (or face the wrath of `calls in constants are limited to tuple structs and tuple variants`).

Let’s move on to something a bit more interesting.

## UTF-8 in the Rust standard library

The first thing I wanted to find was some way to do UTF-8 decoding in Rust. So I [searched the standard library for `utf8`](https://doc.rust-lang.org/stable/std/?search=utf8). I don’t remember exactly what steps I took originally, so consider this an artist’s rendering of my thought process.

The first option that jumped out at me was [`std::str::from_utf8`](https://doc.rust-lang.org/stable/std/str/fn.from_utf8.html), which seemed like a good fit. Unfortunately, it had some issues:

- It took a `u8` slice as input, and that would mean choosing some arbitrary chunking size. That might be acceptable, except…
- The output is a simple `Result`, indicating either success or failure. However, there’s a third possibility in our streaming case: there were 1 or more bytes at the end of the input providing an incomplete UTF-8 encoding of a character, and we need to continue decoding with the next chunk of binary input.

There may be workarounds with this, but they seem ugly, so I moved on. I also found [` std::char::decode_utf8`](https://doc.rust-lang.org/stable/std/primitive.char.html#method.encode_utf8), which looks like exactly what I would want. However:

- From the type signature, it does not appear to have any error handling capabilities.
- It’s a deprecated function, see [\#33906](https://github.com/rust-lang/rust/issues/33906)

So this wasn’t looking too good. The final approach I considered was bypassing the UTF-8 decoding entirely, and working on the raw bytes. This would theoretically be possible, since the input characters we care about are all in the ASCII range. But:

- I wanted a challenge :)
- I wanted to match the Haskell code I wrote more closely
- I wanted to be able to support other conversions which may have involved non-ASCII input

At this point, I *did* do a bit of research into existing streaming UTF-8 support in the Rust ecosystem, but didn’t get too far. If there is a go-to solution to this kind of thing, I’d love to hear about it. It looks like `encoding_rs` would support some of this, for example.

Anyway, onward to my solution!

##  Difficult ergonomics with Iterators

I ultimately wanted to use the [`std::io::Read::bytes`](https://doc.rust-lang.org/stable/std/io/trait.Read.html#method.bytes) function from the `StdinLock` struct to stream the bytes from standard input. To quote the docs:

> The returned type implements `Iterator` where the `Item` is `Result<u8,io::Error>`.

Putting the error value into the stream like this is the idiomatic approach to dealing with errors in iterators in Rust. Rust By Example has [a page about iterating over `Result`s](https://doc.rust-lang.org/stable/rust-by-example/error/iter_result.html), which could be useful if I were to follow this idiomatic approach.

But that approach feels harder to my spoiled Haskeller brain, used to the bliss of relying on runtime exceptions to pretend like errors don’t occur. The iterator-of-results approach has extra ceremony. For example, instead of something like:

``` rust
my_iter.map(convert_char)
```

I would end up needing something closer to:

``` rust
my_iter.map(|r| r.map(convert_char))
```

Can we somehow recover the Haskell-style ergonomics here?

## Lift up error handling

When you take the iterating-over-result approach, you end up with a struct implementing `Iterator` providing a function:

``` rust
fn next(&mut self) -> Option<Result<T, E>>
```

That result type is isomorphic to something like:

``` rust
pub enum Step<T, E> {
  Done,
  Yield(T),
  Error(E),
}
```

What if we just defined a new `trait` for error-able iterators that yield a stream of `T`s and error out with an `E`? Again, this is isomorphic to what we already defined, but might be easier to work with.

``` rust
pub trait EIterator {
    type Item;
    type Error;

    fn enext(&mut self) -> Step<Self::Item, Self::Error>;
}
```

This works, but we’re going to make one more tweak.

## Add in Skip

When I [last blogged about iterators](../iterators-streams-rust-haskell/), I explained why stream fusion in Haskell requires not just `Yield` and `Done` constructors, but also a `Skip` constructor. This had to do with performance in some cases by bypassing nested loops. Please see that blog post for more information.

The `Skip` constructor signals that “hey, I don’t have any data for you yet, still processing, but I’m not done yet.” This turns out to be a perfect way to model UTF-8 decoding, where we’ll want to:

- Grab the next incoming byte
- If it’s in the ASCII range: turn it into a character and yield it
- Otherwise, consume the next 1, 2, or 3 bytes to complete the encoded character

So we’ll modify the `Step` definition above to include that extra case:

``` rust
pub enum Step<T, E> {
    Done,
    Yield(T),
    Skip,
    Error(E),
}
```

Let’s make our first implementation of the `EIterator` trait.

## Converting from iterators

We’re going to want to convert from iterators-of-results into our `EIterator`, at the very least to handle the `bytes()` call on `StdinLock` mentioned above. We’ll first define a newtype wrapper `ResultIterator`:

``` rust
pub struct ResultIterator<I>(I);
```

And then implement `EIterator` for it:

``` rust
impl<I, T, E> EIterator for ResultIterator<I>
where
    I: Iterator<Item = Result<T, E>>,
{
    type Item = T;
    type Error = E;

    fn enext(&mut self) -> Step<Self::Item, Self::Error> {
        match self.0.next() {
            Some(Ok(x)) => Step::Yield(x),
            Some(Err(e)) => Step::Error(e),
            None => Step::Done,
        }
    }
}
```

The `Some<Result<T,E>>` maps directly to our `Step` enum, though there’s nothing to generate a `Skip`. Overall, pretty good. Now, to make it a bit easier to convert these, we want to add an `eiter()` method to all `Iterator`s of `Result`s:

``` rust
pub trait ToEIter
where
    Self: Sized,
{
    fn eiter(self) -> ResultIterator<Self> {
        ResultIterator(self)
    }
}

impl<I, T, E> ToEIter for I
where
    I: Iterator<Item = Result<T, E>>,
{
}
```

## Implementing map

One of the motivating cases for creating this new approach was the `map` function. First, I defined a helper function on the `EIterator` trait for stepping through an `EIterator` without having to pattern match all 4 cases each time:

``` rust
fn step<F, B, E>(&mut self, mut f: F) -> Step<B, E>
where
    F: FnMut(Self::Item) -> Step<B, E>,
    E: From<Self::Error>,
{
    match self.enext() {
        Step::Done => Step::Done,
        Step::Error(e) => Step::Error(From::from(e)),
        Step::Skip => Step::Skip,
        Step::Yield(x) => f(x),
    }
}
```

Notice that `Done` and `Skip` are returned verbatim, `Error` simply uses `From::from` to “upcast” the error type being used, and `Yield` calls the supplied closure. With this in place, creating our `Map` struct and implementing `EIterator` looks like this:

``` rust
pub struct Map<I, F> {
    iter: I,
    func: F,
}

impl<B, I: EIterator, F> EIterator for Map<I, F>
where
    F: FnMut(I::Item) -> B,
{
    type Item = B;
    type Error = I::Error;

    fn enext(&mut self) -> Step<Self::Item, Self::Error> {
        let f = &mut self.func;
        self.iter.step(|x| Step::Yield(f(x)))
    }
}
```

With no need to deal with mapping on a `Result` value! Finally, we can add the following to the `EIterator` trait:

``` rust
fn map<B, F>(self, f: F) -> Map<Self, F>
where
    Self: Sized,
    F: FnMut(Self::Item) -> B,
{
    Map {
        iter: self,
        func: f,
    }
}
```

That was a bit too easy, let’s go onto something a bit harder.

## encode_utf8

UTF-8 encoding cannot fail, so we needn’t worry about any error cases. However, there is a different problem: 1 character of input can generate anywhere from 1 to 4 bytes of output. We need to keep track of bytes that still need to be yielded in our `EncodeUtf8` `struct`. I came up with this:

``` rust
pub struct EncodeUtf8<I> {
    iter: I,
    buf: [u8; 4],
    index: usize,
}
```

This keeps the underlying `EIterator`, a buffer of up to 4 bytes in the UTF-8 encoding of the most recent character, and the next byte to be yielded from that buffer. If we have no bytes left to yield, then `index` is set to `4` (past the end of the buffer). We can add the following to the `EIterator` trait itself:

``` rust
fn encode_utf8(self) -> EncodeUtf8<Self>
where
    Self: Sized,
    Self: EIterator<Item = char>,
{
    EncodeUtf8 {
        iter: self,
        buf: [0; 4],
        index: 4,
    }
}
```

And add this implementation of `EIterator` for `EncodeUtf8`:

``` rust
impl<I, E> EIterator for EncodeUtf8<I>
where
    I: EIterator<Item = char, Error = E>,
{
    type Item = u8;
    type Error = E;

    fn enext(&mut self) -> Step<Self::Item, Self::Error> {
        if self.index < 4 {
            let res = self.buf[self.index];
            self.index += 1;
            if self.index < 4 && self.buf[self.index] == 0 {
                self.index = 4;
            }
            Step::Yield(res)
        } else {
            match self.iter.enext() {
                Step::Done => Step::Done,
                Step::Error(e) => Step::Error(e),
                Step::Skip => Step::Skip,
                Step::Yield(c) => {
                    let len = c.encode_utf8(&mut self.buf).len();
                    if len > 1 {
                        self.index = 1;
                        if len < 4 {
                            self.buf[len] = 0;
                        }
                    }
                    Step::Yield(self.buf[0])
                }
            }
        }
    }
}
```

Note that we get to leverage `char`’s `encode_utf8` function. Yay, less code to implement ourselves! Each time `enext` is called, we do the following:

- Check if `index` is less than 4. If so, we have more bytes to yield now:
  - Increment the index
  - Check if the next byte is null, and if so set the index to 4
  - Yield the current byte
- Otherwise:
  - Get the next value from the wrapped iterator
  - If it’s `Done`, `Error`, or `Skip`, return that value
  - If it’s `Yield`:
    - UTF-8 encode the character into the buffer
    - If the length is greater than 1, set the index to 1, so that the next call to `enext` will yield the other bytes
    - Yield the first byte in the buffer

Now we’re ready for the really bad boy: `decode_utf8`

## decode_utf8

The first thing to tackle about UTF-8 decoding is how to handle errors. Each time we call `enext`, there are two possible errors that may occur:

- The underlying error from the wrapped `EIterator`, such as `std::io::Error`
- Some UTF-8 decoding error

For the latter, we can define an enum `DecodeUtf8Error` easily enough. In order to unify the two different error types, we’ll require `Self::Error: From<DecodeUtf8Error>`. Our `decode_utf8` implementation in `EIterator` looks like:

``` rust
fn decode_utf8(self) -> DecodeUtf8<Self>
where
    Self: Sized,
    Self: EIterator<Item = u8>,
    Self::Error: From<DecodeUtf8Error>,
{
    DecodeUtf8 {
        iter: self,
        count: 0,
        res: 0,
    }
}
```

You may be wondering: don’t we want to have an application-specific error type instead of using the underlying `std::io::Error`? Don’t worry, we’ll get to that in two sections.

As you can see already, `DecodeUtf8` has three fields. Let’s see them more properly:

``` rust
pub struct DecodeUtf8<I> {
    iter: I,
    count: u8,
    res: u32,
}
```

`iter` is the wrapped `EIterator`. `count` is the number of bytes left to be processed in the current sequence. And `res` is the accumulator for the next character being decoded. This’ll make more sense as we look at the code.

First, basic ceremony:

``` rust
impl<I> EIterator for DecodeUtf8<I>
where
    I: EIterator<Item = u8>,
    I::Error: From<DecodeUtf8Error>,
{
    type Item = char;
    type Error = I::Error;

    fn enext(&mut self) -> Step<Self::Item, Self::Error> {
```

Next we want to grab the next incoming byte. If an error is returned, we’ll just return it ourselves. Same with a `Skip`. In the case of a `Yield`, we’ve gotten our byte. `Done` is the only special case:

- If we’re in the middle of decoding a sequence, we need to return an error about an invalid UTF-8 codepoint
- Otherwise, we’re simply done processing the stream

``` rust
let b = match self.iter.enext() {
    Step::Done => {
        if self.count == 0 {
            return Step::Done;
        } else {
            return Step::Error(From::from(DecodeUtf8Error::InvalidUtf8Codepoint));
        }
    }
    Step::Error(e) => {
        return Step::Error(e);
    }
    Step::Skip => {
        return Step::Skip;
    }
    Step::Yield(b) => b,
};
```

We’ve now got our next byte. If the `self.count` is 0, it means that we are not in the middle of a codepoint, and so we can treat this as the first byte in a codepoint. With a bit of bit twiddling, we can determine the number of bytes in the codepoint. If it’s just 1 (ASCII), we yield the character. Otherwise, we prepare for a multibyte codepoint:

``` rust
if self.count == 0 {
    if b & 0b1000_0000 == 0 {
        // ASCII
        Step::Yield(unsafe { std::char::from_u32_unchecked(b.into()) })
    } else {
        self.count = if b & 0b1110_0000 == 0b1100_0000 {
            // 2 bytes
            self.res = u32::from(b & 0b0001_1111);
            1
        } else if b & 0b1111_0000 == 0b1110_0000 {
            // 3 bytes
            self.res = u32::from(b & 0b0000_1111);
            2
        } else {
            // 4 bytes
            assert!(b & 0b1111_1000 == 0b1111_0000);
            self.res = u32::from(b & 0b0000_0111);
            3
        };
        Step::Skip
    }
```

Finally, when in the middle of a multibyte codepoint, we decrement the count of bytes left, shift the result 6 bits to the left, and bitwise-or in the 6 least significant bits of the next byte. If we get down to `count == 0`, then we yield the character:

``` rust
self.count -= 1;
self.res = (self.res << 6) | (u32::from(b) & 0b0011_1111);
if self.count == 0 {
    Step::Yield(unsafe { std::char::from_u32_unchecked(self.res) })
} else {
    Step::Skip
}
```

Hurrah! Just one more helper function before our glorious program can be written.

## write_to

We want to write out our resulting bytes to standard output. To do this, we’re going to fill up a buffer with bytes, flush to stdout, and repeat until we’re empty. We can just use a `for` loop to do that. Inside `EIterator`:

``` rust
fn write_to<W: Write>(self, mut hout: W) -> Result<(), Self::Error>
where
    Self: EIterator<Item = u8>,
    Self: Sized,
    Self::Error: From<io::Error>,
{
    const SIZE: usize = 4096;
    let mut buf = [0; SIZE];
    let mut i: usize = 0;

    for next in self.iter() {
        let b = next?;
        buf[i] = b;
        i += 1;

        if i == SIZE {
            hout.write_all(&buf)?;
            i = 0;
        }
    }

    if i > 0 {
        hout.write_all(&buf[..i])?;
    }

    Ok(())
}
```

Ah… I *almost* got to pull a fast one on you. Certainly `for` loops can’t work on our custom `EIterator` trait you say. And you’d be right. We have to write some way to convert back into a normal `Iterator`:

``` rust
pub trait EITerator {
    ...
    fn iter(self) -> ToResultIterator<Self>
    where
        Self: Sized,
    {
        ToResultIterator(self)
    }
}

pub struct ToResultIterator<I>(I);

impl<I> Iterator for ToResultIterator<I>
where
    I: EIterator,
{
    type Item = Result<I::Item, I::Error>;

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            match self.0.enext() {
                Step::Done => {
                    return None;
                }
                Step::Skip => (),
                Step::Error(e) => {
                    return Some(Err(e));
                }
                Step::Yield(x) => {
                    return Some(Ok(x));
                }
            }
        }
    }
}
```

And notice how, within our `for` loop, we have this:

``` rust
for next in self.iter() {
    let b = next?;
```

This means that any errors raised anywhere in any of our iterators will end up getting returned as `Err` right here. Which mirrors the runtime exception behavior of Haskell pretty closely, and happens to be exactly what we want in this case.

## The main function

After all of that, we can finally write our `main` function. Using the `convert_char` implementation described at the very beginning, we get:

``` rust
let stdin = io::stdin();
let stdout = io::stdout();

stdin
    .lock()
    .bytes()
    .eiter()
    .map_error(MyAppError::IOError)
    .decode_utf8()
    .map(convert_char)
    .encode_utf8()
    .write_to(stdout.lock())?;

Ok(())
```

Which, frankly, is pretty close to the original Haskell version! There’s a bit more overhead with locking the handles, and we need to deal with convert to `bytes()` and converting that `bytes()` into an `EIterator`. But that’s not too bad.

The only other trick that I haven’t explained is that call to `map_error`. It works just like `map`, except it modifies the error value, not the stream value. I’ve defined an application enum error type:

``` rust
pub enum MyAppError {
    IOError(std::io::Error),
    DecodeUtf8Error(DecodeUtf8Error),
}
```

With appropriate `From` implementations for `std::io::Error` and `DecodeUtf8Error`. This is how we get all of the error types to line up: when we initially convert from an iterator-of-results, use `map_error` to convert that error type into the final error type for the entire stream, and make sure the `From` implementations are available as necessary.

## Comparison

Haskell’s got some obvious advantages here:

- If you accept conduit as a standard solution: the standard solution solves the problem nicely
- There’s no need to think too hard about error handling: exceptions just do the right thing, and conduit’s types do a good job of ensuring resources are cleaned up

However, Rust comes out not too shabby either:

- Sure, there was a lot of work to define that `EIterator` trait, but that’s work that in theory would happen once and be shared
- And again, sure, it’s using a non-standard approach, but it’s not like conduit is part of the Haskell standard library either
- In Rust, we get away without thinking at all about chunking, since the iterator approach is efficient enough to work directly on the values inside chunks
  - We can’t get away with this in conduit because of the GC overhead of creating and destroying a bunch of intermediate data constructors
  - A more fusion-friendly approach like [vegito](https://www.yesodweb.com/blog/2016/02/first-class-stream-fusion) may be able to solve this problem
- We know exactly what errors our code might generate
- And the `From` trait makes error handling not-terrible

There is one final pain point that I’ve glossed over for Rust: the type inference in this kind of solution is fairly brittle. I had to play with things quite a bit to get it to line up perfect. Adding explicit type signatures may be necessary in real world code.

## Conclusion

This was definitely a fun problem to tackle. As is probably obvious by now, I really like analyzing streaming data problems, and comparing Haskell and Rust for this is fascinating. I’m not at all convinced that this is a good approach in general though. Iterating-over-result can probably instead just be made more ergonomic with better helper functions and more documentation.

## About Us

FP Complete specializes in using best in class tools and languages, including (as you may guess) Haskell and Rust, to help our customers solve complex problems. If you’re interested in hearing more or setting up a consultation, [shoot us an email](https://web.archive.org/web/2025/https://academy.fpblock.com/cdn-cgi/l/email-protection#1e6d7f727b6d5e786e7d71736e727b6a7b307d7173).
{% endraw %}
