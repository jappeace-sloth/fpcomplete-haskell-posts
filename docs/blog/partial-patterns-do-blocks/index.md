---
layout: page
title: "Partial patterns in do blocks: let vs return"
---
{% raw %}
*By Michael Snoyman, 10 March 2017. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2017/03/partial-patterns-do-blocks/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250717145907/https://academy.fpblock.com/blog/2017/03/partial-patterns-do-blocks/).*

This blog post is about a pattern (pun not intended) I've used in my code for a while, and haven't seen discussed explicitly. A prime example is when doing simplistic parsing using the functions in `Data.Text.Read`. (And yes, this is a contrived example, and using parsec or attoparsec would be far better.)

*Full versions of the code below are available as a [Github Gist](https://gist.github.com/snoyberg/bfb8bd7bf41410bc1b6aa9b744d5f66f), and embedded at the end of this post.*

The example: consider a file format encoding one person per line, indicating the name, height (in centimeters), age (in years), and bank balance (in your favorite currency). I have no idea why anyone would have such a collection of information, but let's roll with it:

``` text
Alice 165cm 30y 15
Bob 170cm 35y -20
Charlie 175cm 40y 0
```

And we want to convert this into a list of `Person` values:

``` haskell
data Person = Person
    { name    :: !Text
    , height  :: !Int
    , age     :: !Int
    , balance :: !Int
    }
    deriving Show
```

Using the `Data.Text` and `Data.Text.Read` APIs, this isn't too terribly painful:

``` haskell
parseLine :: Text -> Maybe Person
parseLine t0 = do
    let (name, t1) = T.break (== ' ') t0
    t2 <- T.stripPrefix " " t1
    (height, t3) <-
        case decimal t2 of
            Right (height, t3) -> Just (height, t3)
            Left _ -> Nothing
    t4 <- T.stripPrefix "cm " t3
    (age, t5) <-
        case decimal t4 of
            Right (age, t5) -> Just (age, t5)
            Left _ -> Nothing
    t6 <- T.stripPrefix "y " t5
    balance <-
        case signed decimal t6 of
            Right (balance, "") -> Just balance
            _ -> Nothing
    Just Person {..}
```

We start off with the original value of the line, `t0`, and continue to bite off pieces of it in the format we want. The progression is:

1.  Use `break` to grab the name (everything up until the first space)
2.  Use `stripPrefix` to drop the space itself
3.  Use the `decimal` function to parse out the height
4.  Use `stripPrefix` to strip off the `cm` after the height
5.  Use `decimal` and `stripPrefix` yet again, but this time for the age and the trailing `y`
6.  Finally grab the balance using `signed decimal`. Notice that our pattern match is slightly different here, insisting that the rest of the input be the empty string to ensure no trailing characters

If we add to this a pretty straight-forward helper function and a `main` function:

``` haskell
parseLines :: Text -> Maybe [Person]
parseLines = mapM parseLine . T.lines

main :: IO ()
main =
    case parseLines input of
        Nothing -> error "Invalid input"
        Just people -> mapM_ print people
```

We get the output:

``` text
Person {name = "Alice", height = 165, age = 30, balance = 15}
Person {name = "Bob", height = 170, age = 35, balance = -20}
Person {name = "Charlie", height = 175, age = 40, balance = 0}
```

And if we corrupt the input (such as by replacing `175cm` with `x175cm`), we get the output:

``` text
v1.hs: Invalid input
CallStack (from HasCallStack):
  error, called at v1.hs:49:20 in main:Main
```

This works, and the `Data.Text.Read` API is particularly convenient for grabbing part of an input and then parsing the rest. However, all of those case expressions really break up the flow, feel repetitive, and make it difficult to follow the logic in that code. Fortunately, we can clean this up with some `let`s and partial pattern matches:

``` haskell
parseLine :: Text -> Maybe Person
parseLine t0 = do
    let (name, t1) = T.break (== ' ') t0
    t2 <- T.stripPrefix " " t1
    let Right (height, t3) = decimal t2
    t4 <- T.stripPrefix "cm " t3
    let Right (age, t5) = decimal t4
    t6 <- T.stripPrefix "y " t5
    let Right (balance, "") = signed decimal t6
    Just Person {..}
```

That's certainly easier to read! And our program works... assuming we have valid input. However, let's try running against our invalid input with `x175cm`:

``` text
v2.hs: v2.hs:27:9-39: Irrefutable pattern failed for pattern Right (height, t3)
```

We've introduced partiality into our function! Instead of being well behaved and returning a `Nothing`, our program now creates an impure exception that blows up in our face, definitely *not* what we wanted with a simple refactoring.

The problem here is that, when using `let`, an incomplete pattern match turns into a partial value. GHC will essentially convert our:

``` haskell
let Right (height, t3) = decimal t2
```

into

``` haskell
let Right (height, t3) = decimal t2
    Left _ = error "Irrefutable pattern failed"
```

What we really want is for that `Left` clause to turn into a `Nothing` value, like we were doing explicitly with our `case` expressions above. Fortunately, we've got one more trick up our sleeve to do exactly that:

``` haskell
parseLine :: Text -> Maybe Person
parseLine t0 = do
    let (name, t1) = T.break (== ' ') t0
    t2 <- T.stripPrefix " " t1
    Right (height, t3) <- Just $ decimal t2
    t4 <- T.stripPrefix "cm " t3
    Right (age, t5) <- Just $ decimal t4
    t6 <- T.stripPrefix "y " t5
    Right (balance, "") <- Just $ signed decimal t6
    Just Person {..}
```

To make it abundantly clear, we've replaced:

``` haskell
let Right (height, t3) = decimal t2
```

with:

``` haskell
Right (height, t3) <- Just $ decimal t2
```

We've replaced our `let` with the `<-` feature of `do`-notation. In order to make things type-check, we needed to wrap the right hand side in a `Just` value (you could also use `return` or `pure`, I was just trying to be explicit in the types). But we've still got an incomplete pattern on the left hand side, so why is this better?

When, within `do`-notation, you have an incomplete pattern match, `GHC` does something slightly different. Instead of using `error` and creating an impure exception, it uses the `fail` function. While generally speaking there are no guarantees that `fail` is a total function, certain types - like `Maybe` - due guarantee totality, e.g.:

``` haskell
instance Monad Maybe where
  fail _ = Nothing
```

Voila! Exactly the behavior we wanted, and now we've achieved it without some bulky, repetitive `case`s. My general advice around these techniques:

- Don't define partial patterns in `let`s, `case`s, or function definitions.
- Only use partial patterns within `do`-notation if you know that the underlying type defines a total `fail` function.

For completeness, you can also achieve this with more explicit conversion to a `Maybe` with the `either` helper function:

``` haskell
parseLine :: Text -> Maybe Person
parseLine t0 = do
    let (name, t1) = T.break (== ' ') t0
    t2 <- T.stripPrefix " " t1
    (height, t3) <- either (const Nothing) Just $ decimal t2
    t4 <- T.stripPrefix "cm " t3
    (age, t5) <- either (const Nothing) Just $ decimal t4
    t6 <- T.stripPrefix "y " t5
    (balance, t7) <- either (const Nothing) Just $ signed decimal t6
    guard $ T.null t7
    Just Person {..}
```

While this works, personally I'm not as big a fan:

- It feels bulkier, hiding the main information I want to express
- It doesn't handle the issue of ensuring no content is left over after parsing the balance, so we need to add an explicit `guard`. You *could* just use `(balance, "") <-`, but that's just going back to using the partial pattern rules of `do`-notation.

Hopefully you found this little trick useful. Definitely not earth shattering, but perhaps a fun addition to your arsenal. If you want to learn more, be sure to check out our [Haskell Syllabus](https://web.archive.org/web/2025/https://academy.fpblock.com/haskell-syllabus).

The four versions of the code mentioned in this post are all available as a [Github Gist](https://gist.github.com/snoyberg/bfb8bd7bf41410bc1b6aa9b744d5f66f):
{% endraw %}
