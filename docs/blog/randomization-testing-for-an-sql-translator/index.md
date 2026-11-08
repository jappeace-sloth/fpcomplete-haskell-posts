---
layout: page
title: "Randomization Testing for an SQL Translator"
---
{% raw %}
*By Alexey Kuleshevich, 13 February 2019. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/randomization-testing-for-an-sql-translator/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250803121427/https://academy.fpblock.com/blog/randomization-testing-for-an-sql-translator/).*

Not all SQLs are created equal. I’ll say even more, none of the SQL dialects are even close to being equal. In particular, when talking about Microsoft SQL Server and PostgreSQL, their syntax might look similar. However, in their semantics, they are mountains apart. Today I will describe

- How we implemented an automatic translator from one SQL dialect to another in Haskell
- Some of the challenges we faced along the way
- And most importantly, how we used randomization tests to drive our translator forward, while discovering some of those mountains of between the two database engines.

## Problem at hand

A short introduction to the motivation that caused all the work is pretty important. In fact, people who are even vaguely familiar with differences between the two dialects might wonder: Why would anyone even bother with such a translator in a first place? In most cases it would be much simpler to just rewrite the code in the target language manually, test that it behaves as expected and be done with it.

One of our customers made a plan to transition their database engine from Microsoft SQL Server to PostgreSQL. While this is a reasonable thing to do, a major hurdle was that a lot of their data handling logic was written in T-SQL, rather than in some database agnostic programming language. To be more precise, our engineers at FP Complete were presented with a 10MiB file of approximately 200K lines of T-SQL code. No sane person would ever be eager to perform this translation by hand. Besides, translation of languages that are meant to be understood by computers is also a good task for a computer rather than a human being.

## The planned solution

The plan was pretty straightforward:

- Isolate a subset of all language features that are actually being utilized.
- Write a parser for Transact-SQL (T-SQL).
- Figure out a direct translation for each data type, function, query, etc. into the target language.
- Generate a printer that will write out the code in Procedural Language/PostgreSQL (PL/pgSQL).

No matter how much research you do or how intimate you are with a particular language you can’t know all of the nitty-gritty details, especially in two languages at the same time. In order to have confidence in our translator we decided to also employ randomized testing to guide us with the last three stages of the plan.

## Iterative process

Despite their importance, syntactic differences are not of much interest to us, as far as this blog post is concerned. Therefore, I won’t be talking about parsing or printing. What we do care about is the semantic correspondence of functions, data types, queries and most definitely procedures between T-SQL and PL/pgSQL. In other words we do care about their correct translation.

Below I will try to describe how we allowed randomized testing to drive our translation efforts in discovery of undocumented or hard to find differences between the languages. A simplified version of the process was:

- take a function from T-SQL
- figure out a matching one in PL/pgSQL
- if there is no match, then implement one and load it into Postgres as a custom function
- use QuickCheck to generate random values that the function would normally expect as input
- execute the query in MS SQL
- automatically translate the above query and execute it in PostgreSQL
- compare the returned results
- record all of the differences and investigate the reasons behind them
- use newly learned knowledge about the function to adjust either the translation or the tests
- repeat the process until output from both databases is exactly the same or good enough, whatever that might mean.

In the above breakdown we used functions as an example, but that process extends to other concepts as well, which I will touch upon later.

## Database connections

In order for us to start executing queries on those engines we needed to figure out a way to connect to them from Haskell. Doing so for Postres was very simple with the help of the postgresql-simple package. Getting connected to SQL Server was not as straightforward, since there was no reliable open source solution that we could use. Luckily for us we already had a semi-complete in-house FreeTDS bindings, which with some small adjustments we were able to successfully use for testing the translator.

For anyone interested in connecting to an ODBC compliant databases, Chris Done did some more work in that area and released a fully featured [odbc](../haskell-library-talking-odbc-databases/) bindings, which you could also use to connect to SQL Server and others.

**Click below to learn more about a unique offer**

## Data types

We started testing at the most natural place for any Haskeller, namely the data types. Luckily for us the SQL standard had the most influence in that area on the languages in question. We were able to create data types in Haskell that corresponded to similar data types in both engines: `DATETIME2` was similar to `TIMESTAMP`, `INT` to `INTEGER`, and so on.

One of the fun things was finding the correct range of values that would be supported equally in both engines, such as timestamp ranges for instance. Because we used `freetds` for communication, we ran into some tighter restrictions on ranges when compared to what SQL Server natively supports. For example, year values for `DATE` could be between 1753 and 9999, while the documented range for SQL server is from 0001 to 9999. However, those were good enough bounds for the code we tried to translate.

The least trivial of all were the ranges of unicode characters. The first issue was that PostgreSQL uses UTF-8, while SQL Server uses:

- For `NVARCHAR`: UCS-2, the grandparent of UTF-16
- For `VARCHAR`: `Windows-1252`, an even older extended ASCII encoding

Actual encoding/decoding of codepoints was pretty much solved for us in Haskell, so by using a few helper functions we could pass generated data to the corresponding databases in the format that they expect.

Finding a subset of valid characters from the Unicode standard was the more challenging part. But with help of randomized testing we were able to quickly identify all the characters—amongst the ones we cared about—which behaved differently between the two engines. Instead of manually writing generators that would produce valid Unicode codepoints we went a simpler way and just downloaded a file with all characters for an old Unicode-1.1.5 standard. We further reduced the input by disabling blocks of characters that we knew where irrelevant to us: eg. Hiragana, Katakana, Bopomofo and many others. Then all we did was generate random strings by selecting codepoints from a predefined list and fed them as input to various functions. That simple technique not only quickly revealed all the codepoints unsupported in UCS-2, but also a few important differences:

- SQL Server treats Unicode characters as if they are normalized, while PostgreSQL does no such thing. For example combination of `a`+`˛` would be equivalent to `ą`, `ss` to `ß`, etc.
- Case insensitive collation in SQL Server turned out to be a bit problematic, since Postgres can’t do that out of the box.
- Older collations can produce unexpected results on some codepoints, even though they are present in UCS-2

The most critical feature of QuickCheck in this approach, besides arbitrary data generation, was shrinking. Trying to identify some mismatched hieroglyph on a screen full of random garbage is ridiculously hard and pointless, especially when the library can automatically reduce the size of that data, which still triggers the failure.

In case you are not familiar with QuickCheck, here is an introduction level blog that I’ve written a couple years ago: [QuickCheck and Magic of Testing](../quickcheck/). We also have a very detailed blog post on property testing coming up in the near future, so stay tuned.

## Functions

Since functions are so tightly coupled with the generated data, we’ll extend the previous section with a concrete example. Consider a simple pure `LEN()` function that operates on strings (such as `CHAR,`, `VARCHAR`, etc.) and returns the number of characters. With a quick inspection of the documentation it’s trivial to reveal a matching function in Postgres, which would be `length()`. The easy to miss part is the fact that they do produce different results on some inputs. Specifically, `LEN()` treats trailing white spaces as insignificant, while PostgreSQL trims all trailing white space only for the `CHAR` data type, but not the other string like types `VARCHAR` and `TEXT`. Since this is done at the type level, this behavior affects all functions, while in SQL Server it is only `LEN()` specific.

Some might find the above difference unimportant, but small things like that can drastically change the logic of a large program in surprising ways. The point is, though, that we were able to quickly identify such a peculiar difference simply by feeding random strings into both functions and comparing the output.

Another fun one was `ISNUMERIC()`. We had to ignore a whole lot of characters as input during testing, such as currency symbols, box characters, comma, tab, carriage return etc. Those are also considered as numeric in T-SQL whenever they are by themselves or at the beginning of the string. We did need to produce a translation that was as close as possible, but translating all the bugs too seemed overkill.

The easiest ones to translate were, of course, pure math functions, but not all of them were a one-to-one mapping either. Important to note, when comparing produced floating point results, we can not expect them to be identical, and must check equality up to an error. There are a few ways to account for small errors, but here is my favorite one that worked well for me in the past, namely compare up to a relative error:

``` haskell
epsilonEq :: (Num a, Ord a) =>
             a -- ^ Epsilon, a maximum tolerated error. Sign is ignored.
          -> a -- ^ Expected result.
          -> a -- ^ Tested value.
          -> Bool
epsilonEq epsilon x y = x == y || abs (y - x) <= n * epsilon
  where n = 1 + if abs x < abs y then abs y else abs x
```

## Queries and Procedures

Both T-SQL and PL/pgSQL are procedural languages, as such they depend on the state of the world as well as the data in the database. For that reason designing reproducible tests is much harder than in a pure setting. Nevertheless, it is still possible.

The simplest procedures that come to mind that are stateful are the ones that return the current time (eg. `GETUTCDATE()`) or a random number (eg. `RAND()`). Testing these kind of procedures and other ones that depend on them must be done manually, possibly with some trivial unit tests. But randomized testing is simply not applicable in such scenarios.

Various queries and procedures that depend only on data stored in the database and the input arguments can still be tested with randomized testing. In order to do so, prior to running the property, we need to clear out the database or maybe just a few tables and then load initial data into the required tables. We can even select the initial data randomly from some predefined large set, as long as we know that all of that data is valid and the procedure we are trying to test is expected to return the same output or modify the state of the database in exactly the same way.

The point is that, in the presence of mutable state, it is our responsibility as a QA engineer to identify which parts of our global state the procedure depends on and make sure that it is initialized to the equivalent state for both databases before each test case is executed. Similarly we need to identify which parts of the database it is expected to modify, so we can retrieve that data and reliably validate its equivalence between the databases. In some situations we can speed up and even improve the quality of our tests if we are able to not reinitialize the state until an actual test failure, but that is very much dependent on the logic inside the procedures we are trying to test.

## Conclusion

The power of Haskell and randomization testing with such libraries as QuickCheck and Validity can be used in some unexpected settings. It turns out to be an invaluable tool, not only for validating the implemented logic, but also for driving the actual implementation, as it is known from the “tests first” approach. Moreover, the process we describe, could just as well be applied to translation between other programming languages, it doesn’t have to be SQL specific.

Another fascinating observation here I’d like to make is that the translator itself didn’t have to be written in Haskell—although I don’t know why you would choose another language. But the gist of it is that the randomization test suite I’ve described in this post did not directly depend on the translator as a library, just on the output it produces, so we could simply treat it is a black box if necessary, while using all of our favorite tools for testing it.

If you would like some help with your database problems please [contact us](https://web.archive.org/web/2025/https://academy.fpblock.com/contact-us) to see how we can assist.
{% endraw %}
