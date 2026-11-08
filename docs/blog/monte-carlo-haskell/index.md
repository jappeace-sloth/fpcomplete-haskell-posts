---
layout: page
title: "Monte carlo analysis in Haskell"
---
{% raw %}
*By Michael Snoyman, 20 March 2014. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2014/03/monte-carlo-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428060738/https://academy.fpblock.com/blog/2014/03/monte-carlo-haskell/).*

A common analytic task is the monte carlo simulation. This involves sampling large numbers of random values in order to come to some kind of conclusion.

Random numbers are often thought of as a weak point in purely functional languages. In a purely functional language like Haskell, we keep a strict separation between pure and impure functions. Since by its very nature, a function generating a random value generates different values each time it's called, we're forced to move it into the impure world. At that point, it may seem like we've lost a lot of our claimed benefits from purity.

This blog post is intended to demonstrate that, with the right choice of libraries, we're able to have our cake and eat it too: write pure code for the pure parts of our program and keep side-effects contained. We'll also explore how Haskell's type system allows us to write even more concise code than dynamically typed languages, not to mention most statically typed languages, and how we can move from using gigabytes of memory to just a few tens of kilobytes.

## Calculating pi

For demonstration purposes, we want to start with a simple monte carlo simulation: estimating the value of pi. To do this, we'll focus on a 1-by-1 square, and imagine that the bottom-left corner (i.e., the origin) is the center of a unit circle (i.e., radius of 1). For any point in that square, we can determine if it falls inside the unit circle by calculating its distance from that bottom-left corner. In other words, for a point (x, y), if x\*x + y\*y \< 1, we're inside the circle. Otherwise we're not.

![](data:image/svg+xml;base64,PHN2ZyBoZWlnaHQ9IjIwMCIgd2lkdGg9IjIwMCI+CjxjaXJjbGUgY3g9IjEwMCIgY3k9IjEwMCIgZmlsbD0iIzk5MCIgcj0iMTAwIiBzdHlsZT0iZmlsbC1vcGFjaXR5OjAuNSI+PC9jaXJjbGU+CjxyZWN0IGZpbGw9IiMwOTkiIGhlaWdodD0iMTAwIiBzdHlsZT0iZmlsbC1vcGFjaXR5OjAuNSIgd2lkdGg9IjEwMCIgeD0iMTAwIiB5PSIwIiAvPgo8L3N2Zz4=)

Now comes the monte carlo simulation. We need to generate random points in that square, and check if they're in the circle. We determine the probability that one of these random points is in the circle, and use this to estimate the area of the unit circle which intersects with our square. Since this is one quarter of the entire circle, our probability will actually estimate pi divided by 4, since the area of the unit circle is pi.

## Let's get imperative

We want to start off with a baseline approach to the problem. A common tool in quant research is Python, together with the Numpy and Scipy libraries. Let's see how they might be used to come up with a solution:

``` python
from numpy import average
from scipy import rand

print average([x[0]*x[0]+x[1]*x[1]<1 for x in rand(10000000,2)])*4
```

Note: While I'm not an expert in Numpy and Scipy, this example was provided to me by someone who uses those tools regularly. If there's a problem in the code or my explanation of it, please let me know.

The real magic here is the `rand` function. It will generate a matrix with the given dimensions, filled with random numbers. We pass in two parameters: 10,000,000 to be the number of experiments to perform, and 2, since each experiment needs two random values (an x and y coordinate). Our program then uses a list comprehension to iterate over the 10 million two-length vectors, and for each vector, determines if the distance from the origin is less than one. Our boolean result is implicitly converted to a 0 or 1, we get the average, and multiply by 4. When run on my system, I get the result: 3.1413928.

### The problem

The problem with this approach is memory usage: the entire 20 million member matrix is kept in memory at the same time! My system ended up using 250MB of memory to perform this calculation. But the problem is worse than that, since the memory use will grow linearly as we increase our sample size!

We can fairly easily solve our memory problem, by going to an explicit for loop:

``` python
import random

count = 100000000
successes = 0

for i in xrange(count):
    x = random.random()
    y = random.random()
    if x*x + y*y < 1:
        successes += 1

print 4.*successes/count
```

In comparison to the previous code, this program runs in about 3MB of memory, but has twice the run time. (Recommendations for improvement are welcome.)

While the code isn't *complicated*, it is pretty tedious. And maybe this is just the Haskeller in me, but I got seriously tripped up by the need to use `1.0` instead of just `1` when summing up `successes`. Initially, I just used `1`, which resulted in my answer always being 0, since Python performed integer division instead of floating point division. It's certainly a strange feeling to get a type error at runtime!

So we now have two Pythonic approaches to the problem: a concise, fast, memory-inefficient version, and a longer, slower, memory-efficient version.

**UPDATE** There are some great comments on the Python code below. I'm going to leave the original content of this post unmodified, but recommend readers look at the comments for clarifications.

## Enter Haskell, and IAP

Let's see how Haskell, and in particular FP Complete's Integrated Analysis Platform (IAP), would address this problem. One of the most common complaints we hear from people about their current analysis tools is their inability to deal well with large data sets. As such, we've designed our tool with constant memory analyses as a primary goal. In order to do that, we use the `conduit` library, which is one of Haskell's streaming data libraries.

The nice thing about a streaming data library like conduit is that, not only does is make it easy to keep only the bare minimum data in memory at a time, but it's also designed around separating pure and impure code. This was one of the areas of concern we raised at the beginning of our blog post. So let's see how IAP and conduit allow us to solve the problem:

(Note: If you're viewing this on fpcomplete.com, you can run the code in the page. Since the School of Haskell servers do not perform optimized builds, the run time is longer than what you can expect from a proper compiled build.)

``` haskell
{-# LANGUAGE ExtendedDefaultRules, NoMonomorphismRestriction #-}
import Conduit

main = do
    let cnt = 10000000
    successes <- sourceRandomN cnt $$ lengthIfC (\(x, y) -> x*x + y*y < 1)
    print $ successes / cnt * 4
```

**NOTE** If you want to play with this code in the IDE, please click on the "Open in IDE" button above, go to the settings page, and change the environment from Stable to Unstable. We're using some bleeding-edge packages in this example.

We start off with some language extensions. These give us the same environment as the IAP itself works in, essentially turning off some stricter type rules to allow for more experimentation. We then import the `Conduit` library, and start off our `main` function.

The first and third lines in our `main` function should be pretty straight-forward: we define how many simulations we want to perform on line one, and print out our estimate of pi on line three. All of the work happens on line two. Since this is the first time we're looking at conduit in this blog, we'll take it slowly.

When we use conduit, we create a data *pipeline*. In a pipeline, we need some data *source* (also known as a producer), a data *sink* (also known as a consumer), and some optional transformers (not used in this example). Our source is the function:

``` haskell
sourceRandomN cnt
```

This function allocates a new random number generator, and then generates a stream of `cnt` random values. Unlike Scipy's `rand` function, it does *not* create an in-memory vector. Instead, each new random value is produced on demand.

Our sink is a little bit more complicated:

``` haskell
lengthIfC (\(x, y) -> x*x + y*y < 1)
```

`lengthIfC` is a function which will determine the length of its input stream which satisfies some test. (If you're familiar with Excel, think of `countif`.) Its parameter is a function which returns a `Bool`. And thanks to Haskell's light-weight lambda syntax, we can easily define our function inline.

Once we have our source and sink, we use conduit's connect operator (`$$`) to plug them together and produce a final result- in this case, the number of random points that fall inside our unit circle.

When I run this program on my system, it takes 44KB of memory. If I increase the sample size to 100 million or higher, it *still* takes just 44KB of memory, living up to the promise of constant memory usage. And as an added bonus, our program also runs significantly faster: in my test, the Scipy program took 19.620s, and the Haskell program took 0.812s.

## The benefits of a type system

In our Scipy version of the program, we had to explicitly state that we wanted to have two values generated for each simulation via the second parameter to the `rand` function. In the Python explicit iteration version, we called `random` twice in each iteration of the loop. How does the Haskell program know to generate two values, and not just one? The answer is embedded in our lambda function:

``` haskell
({-hi-}\(x, y){-/hi-} -> x*x + y*y < 1)
```

We declared that our lambda function takes a pair of values. That's all Haskell needs to know: the type inferencer automatically determines from here that the input to the data sink must be a pair of values, and if the input must be a pair of values, the output of the data source must *also* be a pair of values. And here's the really cool part: `sourceRandomN` is a polymorphic function, and can generate many different types of random values. So if we modified our program to instead take three random, it would still work.

If you're wondering about how this happens, it's all powered by the `Variate` typeclass, which has an instance for each different type of random value that can be generated. There are instance for `Double`, `Int`, and a number of other numeric types, plus instances for pairs, 3-tuples, and 4-tuples. So if you wanted to write a program that required a random `Int`, `Double`, and `Bool`, it will work. (And if you need more than 4 values, you can use nested tuples.)

This begs another question: how does Haskell know to use `Double`s in our analysis? This is once again type inferencing helping us out, and determining that we needed a floating point type. The default floating point type is `Double`, so that's what Haskell uses.

Compare all that to Python, where accidentally replacing `1.0` with `1` results in a garbage result from the program.

### Rewrite rules

One other powerful feature that plays into our performance here is *rewrite rules*. These are instructions we can give to the Haskell compiler to say: "you're about to do X, but it would be faster to do it a different way." A simple example of a rewrite rule would be to replace something like:

``` text
sum [x..y]
```

with the [mathematically identical](https://mathworld.wolfram.com/ArithmeticSeries.html):

``` text
(x+y)*(y-x+1)/2
```

Many Haskell libraries- conduit included- use rewrite rules to get rid of intermediate data structures, and thereby let you as a user write high-level code while generating more efficient machine code.

Part of our upcoming IAP work will be researching even more ways to fuse away data structures in conduit. The great advantage of that is that you'll be able to start writing code today, and as the rewrite rules improve, your code will speed up automatically.

## A solution that scales

For a problem as simple as the one we've described, it's not really that difficult to write a solution with most any language. Even a straight C solution can easily be done in under 15 lines of code. The question is: how does it handle the large problems?

We're designing IAP to make it easy and natural to compose smaller programs into larger solutions. By basing everything on constant-memory operations, we're hoping to help our users avoid running up against a brick wall when their data sets suddenly jump in size by three orders of magnitude. In other words, we believe the first solution you write will be able to be extended to more complicated problems, and much larger data sets.

Stay tuned to this blog for more demonstrations of our upcoming IAP product. And if you have questions about how IAP could fit into your research and analysis platforms, please feel free to [contact out support team](https://web.archive.org/web/2025/https://academy.fpblock.com/index).
{% endraw %}
