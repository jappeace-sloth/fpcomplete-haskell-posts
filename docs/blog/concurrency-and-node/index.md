---
layout: page
title: "Concurrency and Node"
---
{% raw %}
*By Andrew Rademacher, 7 December 2016. Mirrored from FP Complete's blog: [original URL](https://tech.fpcomplete.com/blog/2016/12/concurrency-and-node/) (offline), [Wayback Machine copy](https://web.archive.org/web/20191016163447/https://tech.fpcomplete.com/blog/2016/12/concurrency-and-node/).*

*Example code can be found [here](https://github.com/AndrewRademacher/fpco-article-examples/tree/master/concurrency-and-node).*

When Node.JS first came onto the scene it successfully popularized the event-loop. Ryan Dahl correctly identified a serious problem with the way that I/O is generally handled in concurrent environments. Many web servers, for example achieve concurrency by creating a new thread for every connection. In most platforms, this comes at a substantial cost. The default stack size in Java is 512KB, which means that if you have 1000 concurrent connections, your program will consume half a gigabyte of memory just for stack space. Additionally, forking threads in most systems costs an enormous amount of time, as does performing a context switch between two threads.

To address these issues, Node.JS uses a single thread with an event-loop. In this way, Node can handle 1000s of concurrent connections without any of the traditional detriments associated with threads. There is essentially no memory overhead per-connection, and there is no context switching.

When compared to traditional threading architectures, this is exactly the right approach to handling concurrency. In fact, Erlang's OTP libraries function in a very similar way. Each actor has a queue of messages, and only processes a single message at a time. Only after fully processing one message does it move on to the next.

However, this programming model imposes some extreme costs when it comes to the legibility of code. Consider the following two examples.

``` javascript
var request = require('request');

request('http://example.com/random-number', function (error, response, body) {
  if (!error && response.statusCode === 200) {
    console.log(JSON.parse(body));
  }
});
```

``` javascript
var request = require('request');

var response = request('http://example.com/random-number');

if (response.statusCode === 200) {
  console.log(JSON.parse(response.body));
}
```

In the first example we see what an HTTP request would typically look like in Node. In the second we see what it could be like if Node had threads.

As a direct result of the event-loop, we have lost the ability to express a program as a linear series of steps. Which becomes even more important were we to need to make many I/O calls in the same function.

``` javascript
request('http://example.com/random-number', function(error, response1, body) {
  request('http://example.com/random-number', function(error, response2, body) {
    request('http://example.com/random-number', function(error, response3, body) {
        ...
    });
  });
});
```

versus:

``` javascript
var response1 = request('http://example.com/random-number');
var response2 = request('http://example.com/random-number');
var response3 = request('http://example.com/random-number');
```

Which leads to the 'callback hell' that we all know and hate. Part of the bill-of-goods we accept when using Node is that in exchange for better time and space characteristics, we lose the thread as an abstraction.

### What is the value of a thread

It is important to keep in mind that a thread isn't just a primitive for dealing with concurrency. It is also a powerful abstraction to make the existence of latency invisible to the developer.

``` haskell
{-# LANGUAGE OverloadedStrings #-}

import Data.Aeson
import Network.HTTP.Simple
import Network.HTTP.Types.Status

main :: IO ()
main = do
  res <- httpJSON "http://httpbin.org/get"
  if getResponseStatus res == status200
    then print $ (getResponseBody res :: Value)
    else error $ show $ getResponseStatus res
```

Looking at the code above we notice a characteristic difference about it when compared to the asynchronous JavaScript examples above. There are no callbacks. When we say `response <- get ...`, the program will halt until we get a response back from the server. We have written a piece of code that is linear, from step-to-step, and the underlying system knows that the server on the other end will take time to respond and handles it accordingly.

This is possible because a thread keeps track of the state belonging to an ongoing computation. By tracking that state, a thread can halt and resume a computation arbitrarily. In the event of I/O, a thread will halt a computation while the I/O is occurring, and only resume when a response comes back. Giving your program the appearance of having no delay.

A thread, therefore, is both a way of running multiple computations concurrently and also accounting for the asynchronous nature of I/O. By not exposing this abstraction to the developer, two huge drawbacks exist in Node as a concurrency-oriented platform.

### In Node.JS concurrency can only occur when adjacent to I/O

Node.JS only exposes one primary thread to a program. While it may spawn new threads under the hood to deal with input buffers, you don't have any control over them. As a result, you cannot write a program that takes advantage of multiple cores in a machine. The result is that your program will only be able to perform two actions concurrently if at least one of them is bounded by I/O.

To demonstrate, we have setup an example that you can download alongside this article. It is linked to at the top of the article. Once you have downloaded the example, look in the `README.md` for the "Local vs. Remote Test" instructions.

We start by defining a web server that supports a slow operation. In our case, generating Fibonacci numbers by the most naive implementation. Then we define two tests in Node.JS and two tests in Haskell. Using each language's native `async` libraries to attempt to acquire multiple Fibonacci numbers concurrently. In each language one test times how long it takes to concurrently request two Fibonacci numbers from our web server, the other times how long it takes to do the same operation locally. All tests are also run without the `async` library for comparison.

|                  |                    |                 |                  |
|------------------|--------------------|-----------------|------------------|
| Test Name        | Without Async Time | With Async Time | Async / No Async |
| Node - Local     | 6.439s             | 6.306s          | 0.979            |
| Node - Remote    | 4.391s             | 2.500s          | 0.569            |
| Haskell - Local  | 3.849s             | 2.487s          | 0.646            |
| Haskell - Remote | 4.117s             | 2.521s          | 0.612            |

Taking a look at the first row in our table, we find that Node.JS when attempting to concurrently compute two Fibonacci numbers is unable to give us any time savings in spite of the tests being run on a multi-core machine.

``` javascript
    return async.parallel([
        (callback) => {
            x = getFibs(43);
            callback();
        },
        (callback) => {
            y = getFibs(44);
            callback();
        }
    ]).then(() => {
```

Even when the functions to generate numbers are run inside `async.parallel` they are unable to run concurrently. This is because the Node.JS event-loop only allows one callback to be executed at any given time. So instead of running the two callbacks defined above in parallel, they are run sequentially. If we make I/O calls inside our callbacks, as we do in the `Node - Remote` test, the system is able to issue both requests to a web server concurrently.

``` javascript
    return async.parallel([
        (callback) => {
            request('http://localhost:8080/api/fibs/43')
                .then((xStr) => {
                    x = JSON.parse(xStr).fibResult;
                    callback();
                });
        },
        (callback) => {
            request('http://localhost:8080/api/fibs/44')
                .then((yStr) => {
                    y = JSON.parse(yStr).fibResult;
                    callback();
                });
        }
    ]).then(() => {
```

### In Node.JS concurrent computations starve each other of resources

This inability to handle multiple computations at the same time hampers Node.JS even in its intended use case as a web server. The phenomenon is referred to as "starvation" and we can demonstrate it by reversing our previous tests.

To run the demonstration code, download the example project linked at the top of the article. Then look in the `README.md` for instructions on the "Starvation Test."

In this demonstration we setup a web server in each language. The web server contains two routes. The first route is a very fast computation, calculating the square of the input number. The second route is a very slow computation, calculating the Nth Fibonacci number based on the input. We then constructed a program that could perform two tests against each web server.

In the first test, labeled "Fast Only," the test program counts the number of requests the each server can respond to in 5 seconds; using only the fast route. In the second test, labeled "Fast with Slow", the test program makes one request to the slow route, then counts how many requests to the fast route it can respond to in 5 seconds.

To make this demonstration as compelling as possible, we have also disabled threading in the Haskell run-time system on the Haskell web server. The result is that the Haskell server will only be able to use its internal thread model. It will not be able to create additional operating system threads, and it will not be able to take advantage of more than one core.

|                          |                                       |
|--------------------------|---------------------------------------|
| Test Name                | Request Throughput (higher is better) |
| Node - Fast Only         | 572                                   |
| Node - Fast with Slow    | 114                                   |
| Haskell - Fast Only      | 591                                   |
| Haskell - Fast with Slow | 589                                   |

The results are quite striking. From Haskell's baseline of 591, having a background computation only reduced the throughput by 2 requests; which is likely smaller than our margin of error. Node.JS on the other hand was reduced from its baseline to one fifth capacity.

The difference here is stark because in Node.JS's execution model, the moment it receives a request on the slow route it must fully complete the computation for that route before it can begin on a new request. There is no I/O action taking place which will allow the server to jump to processing a new request.

In contrast, Haskell can preempt threads in execution. Which means that when the Haskell server is chugging along on the slow request, and a request on the fast route comes in, it can jump over and process it. Then returning to the slow request while the network is delivering the fast request's response back to a client.

### Haskell does not suffer from traditional threading overheads

When Ryan Dahl originally presented Node, his biggest concern with threaded systems was their memory consumption. He pointed to an example of Apache versus Nginx to show that Nginx had a massively lighter footprint because of its event-loop architecture (whereas Apache used one thread per connection). The difference in memory usage was at least an order of magnitude as the connection count increased.

To demonstrate that Haskell's threading architecture does not suffer this problem, we have constructed one final example, again available at the repository linked above. Look in the `README.md` for "Thread Spawn".

In this example we create 100,000 threads each with a 'start' and 'stop' MVar; which is Haskell's equivalent to a locked variable. We then issue a start command on each start MVar, wait three seconds, and finally issue a stop commend on each end MVar.

When we run the program, we do so with threading enabled, and with the `-s` option on the run-time system; which gives us the following output.

``` text
stack exec -- haskell-thread-spawn +RTS -sout
Created 100000 threads.
Destroyed 100000 threads.
cat out
/home/andrew/src/fpcomplete/fpco-article-examples/concurrency-and-node/.stack-work/install/x86_64-linux-dkda49f7ca9b244180d3cfb1987cbc9743/lts-7.11/8.0.1/bin/haskell-thread-spawn +RTS -N -sout
     137,593,048 bytes allocated in the heap
     405,750,472 bytes copied during GC
      77,103,392 bytes maximum residency (11 sample(s))
      10,891,144 bytes maximum slop
             165 MB total memory in use (0 MB lost due to fragmentation)

                                     Tot time (elapsed)  Avg pause  Max pause
  Gen  0       104 colls,   104 par    0.332s   0.082s     0.0008s    0.0186s
  Gen  1        11 colls,    10 par    0.620s   0.147s     0.0134s    0.0425s

  Parallel GC work balance: 28.08% (serial 0%, perfect 100%)

  TASKS: 18 (1 bound, 17 peak workers (17 total), using -N8)

  SPARKS: 0 (0 converted, 0 overflowed, 0 dud, 0 GC'd, 0 fizzled)

  INIT    time    0.000s  (  0.001s elapsed)
  MUT     time    0.312s  (  3.110s elapsed)
  GC      time    0.952s  (  0.229s elapsed)
  EXIT    time    0.000s  (  0.003s elapsed)
  Total   time    1.316s  (  3.343s elapsed)

  Alloc rate    441,003,358 bytes per MUT second

  Productivity  27.7% of total user, 10.9% of total elapsed

gc_alloc_block_sync: 104599
whitehole_spin: 0
gen[0].sync: 504
gen[1].sync: 2465
```

Looking near the top of the output, we see that Haskell's run-time system was able to create 100,000 threads while only using 165 megabytes of memory. We are roughly consuming 1.65 kilobytes per thread. So an average web server, which might see 2,000 concurrent connections at the top end, would expect to use only 3 megabytes of memory for being multi-threaded.

## Why Haskell

Node and Haskell both offer a solution to the traditional woes of using threading in a web server. They both allow you to deal with very high numbers of concurrent connections without a huge memory overhead. However, Haskell doesn't impose an additional burden on the design of your software to accomplish that goal. You don't have to worry about routes that take varying amounts of time. You don't have to dump long-running tasks off to an event queue. You don't have to spawn multiple processes to utilize multiple cores of a machine.

We've only just barely scratched the surface of what you can do with Haskell. If you're interested in learning more, please [check out our Haskell Syllabus](https://web.archive.org/web/2025/https://tech.fpcomplete.com/haskell-syllabus) for a recommended learning route. There's also lots of content on the [haskell-lang get started page](https://web.archive.org/web/2025/https://haskell-lang.org/get-started).

FP Complete also provides corporate and group webinar training sessions. Please [check out our training page](https://web.archive.org/web/2025/https://tech.fpcomplete.com/training) for more information, or see our [consulting page](https://web.archive.org/web/2025/https://tech.fpcomplete.com/consulting) for how we can help your team succeed with devops and functional programming.
{% endraw %}
