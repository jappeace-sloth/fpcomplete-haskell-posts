---
layout: page
title: "Weakly Typed Haskell"
---
{% raw %}
*By Michael Snoyman, 2 January 2018. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2018/01/weakly-typed-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250418033647/https://academy.fpblock.com/blog/2018/01/weakly-typed-haskell/).*

I was recently doing a minor cleanup of a Haskell codebase. I started off with some code that looked like this:

``` haskell
runConduitRes $ sourceFile fp .| someConsumer
```

This code uses [Conduit](../../haskell/library/conduit/) to stream the contents of a file into a consumer function, and [ResourceT](../understanding-resourcet/) to ensure that the code is exception safe (the file is closed regardless of exceptions). For various reasons (not relevant to our discussion now), I was trying to reduce usage of `ResourceT` in this bit of code, and so I instead wrote:

``` haskell
withBinaryFile fp ReadMode $ \h ->
  runConduit $ sourceHandle h .| someConsumer
```

Instead of using `ResourceT` to ensure exception safety, I used the `with` (or `bracket`) pattern embodied by the `withBinaryFile` function. This transformation worked very nicely, and I was able to apply the change to a number of parts of the code base.

However, I noticed an error message from this application a few days later:

``` text
/some/long/file/path.txt: hGetBufSome: illegal operation (handle is not open for reading)
```

I looked through my code base, and sure enough I found that in one of the places I'd done this refactoring, I'd written the following instead:

``` haskell
withBinaryFile fp WriteMode $ \h ->
  runConduit $ sourceHandle h.| someConsumer
```

Notice how I used `WriteMode` instead of `ReadMode`. It's a simple mistake, and it's obvious when you look at it. The patch to fix this bug was trivial. But I wasn't satisfied with fixing this bug. I wanted to eliminate it from happening again.

## A strongly typed language?

Lots of people believe that Haskell is a strongly typed language. Strong typing means that you catch lots of classes of bugs with the type system itself. (Static typing means that the type checking occurs at compile time instead of runtime.) I disagree: Haskell is *not* a strongly typed language. In fact, my claim is broader:

> There's no such thing as a strongly typed language

Instead, you can write your code in strongly typed or weakly typed style. Some language features make it easy to make your programs more strongly typed. For example, Haskell supports:

- Cheap newtype wrappers
- Sum types
- Phantom type arguments
- GADTs

All of these features allow you to more easily add type safety to your code. But here's the rub:

> You have to add the type safety yourself

If you want to write a program in Haskell that passes string data everywhere and puts everything in `IO`, you're still writing Haskell, but you're throwing away the potential for getting extra protections from the compiler.

My `withBinaryFile` usage is a small-scale example of this. The `sourceFile` function I'd been using previously looks roughly like:

``` haskell
sourceFile :: FilePath -> Source (ResourceT IO) ByteString
```

This says that if you give this function a `FilePath`, it will give you back a stream of bytes, and that it requires `ResourceT` to be present (to register the cleanup function in the case of an exception). Importantly: there's no way you could accidentally try to send data into this file. The type (`Source`) prevents it. If you did something like:

``` haskell
runConduitRes $ someProducer .| sourceFile "output.txt"
```

The compiler would complain about the types mismatching, which is exactly what you want! Now, by contrast, let's look at the types of `withBinaryFile` and `sourceHandle`:

``` haskell
withBinaryFile :: FilePath -> IOMode -> (Handle -> IO a) -> IO a
sourceHandle :: Handle -> Source IO ByteString
```

The type signature of `withBinaryFile` uses the bracket pattern, meaning that you provide it with a function to run while the file is open, and it will ensure that it closes the file. But notice something about the type of that inner function: `Handle -> IO a`. It tells you *absolutely nothing* about whether the file is opened for reading and writing!

The question is: how do we protect ourselves from the kinds of bugs this weak typing allows?

## Quarantining weak typing

Let's capture the basic concept of what I was trying to do in my program with a helper function:

``` haskell
withSourceFile :: FilePath -> (Source IO ByteString -> IO a) -> IO a
withSourceFile fp inner =
  withBinaryFile fp ReadMode $ \handle ->
    inner $ sourceHandle handle
```

This function has all of the same weak typing problems in its body as what I wrote before. However, let's look at the use site of this function:

``` haskell
withSourceFile fp $ \src -> runConduit $ src .| someConsumer
```

I definitely can't accidentally pass `WriteMode` instead, and if I try to do something like:

``` haskell
withSourceFile fp $ \src -> runConduit $ someProducer .| src
```

I'll get a compile time error. In other words:

> While my function internally is weakly typed, externally it's strongly typed

This means that all users of my functions get the typing guarantees I've been hoping to provide. We can't eliminate the possibility of weak typing errors completely, since the systems we're running on are ultimately weakly typed. After all, at the OS level, a file descriptor is just an int, and tells you nothing about whether it's read mode, write mode, or even a pointer to some random address in memory.

Instead, our goal in writing strongly typed programs is to contain as much of the weak typing to helper functions as possible, and expose a strongly typed interface for most of our program. By using `withSourceFile` instead of `withBinaryFile`, I now have just one place in my code I need to check the logic of using `ReadMode` correctly, instead of dozens.

## Discipline and best practices

The takeaway here is that you can *always* shoot yourself in the foot. Languages like Haskell are not some piece of magic that will eliminate bugs. You need to follow through with discipline in using the languages well if you want to get the benefits of features like strong typing.

You can use the some kind of technique in many languages. But if you use a language like Haskell with a plethora of features geared towards easy safety, you'll be much more likely to follow through on it.

## Further reading

- [About the Haskell programming language](https://web.archive.org/web/2025/https://academy.fpblock.com/haskell)
- [Get started with Haskell](https://web.archive.org/web/2025/https://haskell-lang.org/get-started)
- [FP Complete's Haskell Syllabus](https://web.archive.org/web/2025/https://academy.fpblock.com/haskell-syllabus)
- [Conduit streaming data tutorial](../../haskell/library/conduit/)
{% endraw %}
