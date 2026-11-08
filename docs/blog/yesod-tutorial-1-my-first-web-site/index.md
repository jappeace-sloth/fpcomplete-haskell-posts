---
layout: page
title: "Yesod Tutorial 1. My First Web Site"
---
{% raw %}
*By Bartosz Milewski, 1 October 2012. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2012/10/yesod-tutorial-1-my-first-web-site/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428063301/https://academy.fpblock.com/blog/2012/10/yesod-tutorial-1-my-first-web-site/).*

This is the first in the series of tutorials introducing a new approach to web development using Haskell and Yesod. Haskell is a functional language and Yesod is a web development framework written in Haskell by Michael Snoyman who also wrote a book about it. Michael is a member of the FP Complete team and he provided a lot of valuable feedback for this tutorial.

No previous knowledge of Haskell is required from the reader, although you might want to have a peek at Haskell syntax in [Ten Things You Should Know About Haskell Syntax](../ten-things-you-should-know-about-haskell-syntax/) or at the "A Bit of Haskell" section at the end of this tutorial. I will also try to explain some of the concepts of modern web development as we go.

## Yesod and Web Development

We build web sites using a combination of at least four languages. We use HTML for markup, CSS for formatting, JavaScript for the logic that runs on a client's browser; and yet another language for server-side logic (Java, C#, php, and so on).

While it makes sense to have specialized languages for specialized tasks, it's also important that those languages inter-operate. Unfortunately, this is not the case in traditional web development. Programmers are forced to keep track of horizontal dependencies either by using strict discipline or using a system of ad-hoc preprocessors.

The simplest test for interoperability is to be able to define a variable in one language and access it from another. For instance, how would you define an ID for a particular element of the web page? You could define it, say, in Java, as an integer, and initialize it to a unique number. Now you'd like to use this number (as a string) in your HTML to identify a marked-up element. Then, in CSS, to define the style of this element and, occasionally, in your JavaScript code to dynamically change its properties in response to user actions.

Because Yesod is written in Haskell, which is a great language for embedding domain specific languages, such horizontal integration is easy. HTML, CSS, and JavaScript are simply *embedded* in Haskell code. The code written in these languages is *quasi-quoted* and then pre-parsed by Haskell. Because of that last step, it's possible to *interpolate* Haskell code inside those quasi-quotes. So it's perfectly natural to define an integral identifier in Haskell and embed it in HTML, CSS, or JavaScript. If, for instance, `hdr` is a Haskell variable, it can be interpolated in (quasi-quoted) HTML using an escape sequence starting with `#{` and ending with `}`:

``` text
<div id=#{hdr}>
```

This way any change in the definition or usage of an ID will be checked at compile time.

This is just a small example of the power of Haskell and Yesod. Once you learn how to use those powerful techniques, you'll never want to go back to traditional ways of programming.

## Hello Piggies!

Let's start with the simplest nontrivial Yesod program that serves just one web page with the text: "Welcome to the Pigsty!". We'll be building up this web site to prove that even Piggies can write clean, maintainable code.

Our page can be displayed locally by any browser at the address `http://localhost:3000`. Have a look at this code even if you won't understand anything yet. It's highly stylized Haskell with some embedded domain-specific languages thrown into the mix.

``` text
{-# LANGUAGE TypeFamilies, QuasiQuotes, MultiParamTypeClasses,
             TemplateHaskell, OverloadedStrings #-}
import Yesod
data Piggies = Piggies
instance Yesod Piggies
mkYesod "Piggies" [parseRoutes|
  / HomeR GET
|]
getHomeR = defaultLayout [whamlet|
  Welcome to the Pigsty!
|]
main = warpDebug 3000 Piggies
```

This program starts with some book-keeping. Haskell is an evolving language. The last ratified standard dates back to 2010, but it wasn't a big change from the 1998 standard, and anything added after that is considered an extension. Yesod uses a lot of Haskell extensions, so the first line lists those.

``` text
{-# LANGUAGE TypeFamilies, QuasiQuotes, MultiParamTypeClasses,
             TemplateHaskell, OverloadedStrings #-}
```

Strictly speaking anything enclosed between `{-` and `-}` is a comment, but this particular comment is understood by the Haskell compiler as a language pragma. This is all you need to know about it for now.

Next we have a statement to import the Yesod library.

``` text
import Yesod
```

This is a little more than a C++ `#include`, because Haskell has a full-blown module system.

Next, every Yesod website must define its foundation data structure. Here I'm defining a type called `Piggies`:

``` text
data Piggies = Piggies
```

The Haskell syntax here is: The keyword `data` introduces a new type that I call `Piggies`. The right hand side of a data definition is usually a series of data constructors -- here just one; and it's called by the same name as the type itself (this is customary for types that have only one constructor). This constructor happens to be trivial -- it takes no arguments and has no data associated with it. This will not always be true in more complex Yesod examples. If you're a C++ programmer, you may think of this data type as an enumeration called Piggies with only one element also called Piggies.

This foundation data type represents our particular web site. It doesn't matter that the type is trivial (in this case). What matters is that it's an instance of a very rich *type class*. The code below tells the compiler that our `Piggies` type is an instance of the `Yesod` class defined in the `Yesod` library. *Yesod* means *foundation* in Hebrew, so `Piggies` form a foundation of our web site.

``` text
instance Yesod Piggies
```

It's not a far reach for a Java or C++ programmer to think of a type class as an interface with a bunch of virtual functions. These functions often have their default implementations (so they are not strictly interfaces). `Yesod` is just such a class. Later we'll see how to customize some of the behaviors of the web site by overriding `Yesod` functions. The `instance` declaration is the place for defining such overrides.

A lot of boilerplate code can be abstracted into Template Haskell functions. `TemplateHaskell` was listed as one of the language extensions at the top of the file. One way of looking at Template Haskell is as a generator of textual code -- sort of like C macros, except not that messy. (Acutally, Template Haskell generates type-checked Abstract Syntax Trees, but that's a completely different story.) `mkYesod` is an exaple of such a TH function.

``` text
mkYesod "Piggies" [parseRoutes|
  / HomeR GET
|]
```

This template function takes two arguments. The first argument is the string version of the name of the foundation type, "Piggies". The string is used to generate some glue code.

The second argument to `mkYesod` is some quasi-quoted code:

``` text
[parseRoutes|
  / HomeR GET
|]
```

You'll see a lot of quasi-quoting in Yesod as a way to introduce embedded domain-specific languages (EDSLs). Here the language (or its parser function) is called `parseRoutes`. The code between `[parseRoutes|` and `|]` is written in this mini-language.

I'll explain the syntax of `parseRoute` later. For now let's concentrate on its purpose. When the user is typing a URL into their browser or is clicking on a link, the first part of the URL is used to find the web server, the rest is the *route* inside the web site. For instance, in the URL `https://www.fpcomplete.com/blog` the part `https://www.fpcomplete.com` is translated by the browser and the Internet into the address of the FP Complete server. The part `/blog` is interpreted by the FP Complete server as a route.

The `parseRoutes` code contains a list of routes, their corresponding *resources*, and methods for accessing them. In this case, I have just one route, `/` (slash), that identifies the root of this web site -- the home page if you will.

`HomeR` is the name (actually, a data constructor) for this route. We'll be using this name internally. This is an important point: We don't want to use literal URLs for internal links. It would be a maintenance nightmare (as it is in other approaches to web programming). Instead, whenever I want to embed a link to the home page, I'll use `HomeR`. This approach has numerous advantages, one of them being that there will be no broken internal links in my code. If I break a link, the code will not compile! Also, I'm free to rename the route but keep the resource name the same -- the code will work just fine.

The final part of our route entry, `GET`, specifies the request method by which the web page is accessed. There are several request methods used in HTTP, `GET` and `POST` being the most common ones (by the way, you may define separate `GET` and `POST` methods for the same route, which is useful, for instance, when working with forms).

The important role of `mkYesod` template function is that it dispatches requests to handlers for each route. The handlers must be implemented by the programmer. They have very specific names, a concatenation of the lowercase request method followed by the resource name. In our case it's `get`, the lowercase version of `GET`, and `HomeR`, resulting in `getHomeR`. This is our implementation of the home page handler:

``` text
getHomeR = defaultLayout [whamlet|
  Welcome to the Pigsty!
|]
```

The implementation calls the function `defaultLayout` which lays out the page, whose contents is given by its quasi-quoted argument:

``` text
[whamlet|
  Welcome to the Pigsty!
|]
```

First of all, the function `defaultLayout` is provided as part of the `Yesod` type class (that's one of those "virtual" functions that have the default implementation). As such, it can be overridden by the programmer as part of the `instance Yesod ...` statement. We'll use this capability later; for now let's just stick to defaults.

The argument to `defaultLayout` is a `Widget`, a very useful composable abstraction that may combine HTML, CSS, JavaScript, and more. I'll talk more about widgets later. Here I'm creating a widget in-line using an HTML EDSL called `whamlet` (it's really a version of `hamlet`, whose consonants are the anagram of html; the 'w' stands for widget). Like the other EDSL, `parseRoute`, `whamlet` is implemented using quasi-quotations. Here I'm quoting a trivial piece of HTML: a string "Welcome to the Pigsty!". This will be the body of my web page.

Finally, our program has to start a web server that will be processing requests from web browsers. There are multiple backends supported by Yesod, including FastCGI and SCGI, which allow it to work with the popular servers like Apache. But there is also a built-in backend and server written in Haskell called *warp*. As the name suggests, it's a very fast server. Here I'll be using the debug version of warp, so you can see what kind of requests are coming its way.

``` text
main = warpDebug 3000 Piggies
```

The first argument to `warpDebug` is the port it will be listening on, here it's port 3000; the second argument is a value of the type which is our foundation data type. This value is constructed by calling the data constructor `Piggies` with no arguments.

And that's it. You can now open your browser and type in `http://localhost:3000` and you'll see the web page I have just constructed.

This might seem like a lot of work just to display "Welcome to the Pigsty!" but consider that I have constructed a whole active web site and touched a lot of customization points for future functionality.

### Running the Program

Let's see what happens when our program runs. A warp server is started in the background. It calls the system and waits for http requests coming through port 3000. You can see this in the debug output of the program:

``` text
runhaskell 0-minimal
Application launched, listening on port 3000
```

When you open a web browser and type in the URL `http://localhost:3000/`, a *GET* request is sent to the local system. Again, you can see this request in the debug output:

``` text
127.0.0.1 - - [22/Aug/2012:12:08:23 +0200] "GET / HTTP/1.1" 200 4 "" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:6.0.2) Gecko/20100101 Firefox/6.0.2"
```

The requested route is the single slash after GET (if you don't include the trailing slash in the URL, the browser will add it for you). This route in combination with GET resolves to the `HomeR` resource and is dispatched to the handler `getHomeR`. All this is done in the code generated by `mkYesod`.

The handler `getHomeR` produces the HTML page that is sent back to the browser. You can see the contents of this page by viewing page source in your browser:

``` text
<!DOCTYPE html>
<html>
  <head>
    <title></title>
  </head>
  <body>
    Welcome to the Pigsty!
  </body>
</html>
```

#### Conclusion

Even in this simple program you may see important elements of the philosophy of Haskell and Yesod. Yesod is not a one-shot program, it's a framework. A well designed framework hides the details of its plumbing and exposes just the right customization points while keeping them orthogonal.

When you are using a modern elevator, you don't have to worry about regulating the current running through the motors using some kind of variable resistor -- you just press a button with the floor number. You also know that a car can be operated with a steering wheel and two pedals (the automatic models). These two pedals are not orthogonal though, since you can slow your car either by releasing the accelerator or by stepping on the brake. Flying a (non-computerized) helicopter is hard because when you increase the speed of the main rotor to go up, you have to adjust the speed of the tail rotor to stop the helicopter from spinning. A seasoned pilot doesn't have to think about it since his or her brain has been rewired through training.

By the same token even a lousy framework is usable because the brains of a programmer can be rewired. But if it takes years of training to correctly operate a few levers and wheels, how much time is needed to master cross-dependencies between web code written in four languages? Having a well-designed orthogonal set of controls makes a huge difference.

Let's have another look at our program, this time with the eye on customization points.

1.  Foundation type: You can add arbitrary data that pertains to the web site as a whole (what is achieved with global variables in other frameworks).
2.  Yesod instance: You can customize the look and feel of your whole web site by overriding default implementations of functions.
3.  Routing tables (the `mkYesod` function): You can design and modify the site map of your web site.
4.  Handlers for individual web pages/routes/request types.
5.  `main`: Starting and shutting down the web site.

I will go through all these and many more customization points in more detail in later installments of this tutorial.

## A Bit of Haskell

There is very little redundancy in Haskell so almost everything, including whitespace, has meaning.

The good thing is that, once you get used to it, you’ll be able to see more program logic at a glance. In a wordy language you not only waste precious keystrokes but you also dilute the structure and meaning of your program. Code that fills one screenful in Haskell, would be spread over several screenfuls in Java. For a Haskell programmer, studying a Java or a C++ program is like looking at it through a microscope: you see lots of detail but miss the big picture.

One of those things that seem indispensable in other languages are special characters for separating statements (e.g., semicolons) and delimiting blocks (e.g., braces). Mind you, every programmer worth his or her salt uses formatting to make their code readable, but the compiler throws the formatting away. Haskell does (almost) the opposite. It recognizes blocks by indentation (but please use spaces, not tabs), and treats newlines as separators.

#### Function Call Syntax

This is probably the first and the hardest obstacle in reading Haskell code fluently: There is no special syntax for function application. Any set of identifiers separated by **spaces** is a function call. For instance:

``` text
a b c d e
```

is a call to function `a` with arguments `b`, `c`, `d`, and `e`. If you use parentheses it's only to delimit individual arguments (if they are expressions); and commas are used to separate tuple elements. So if you see something like this:

``` text
f (a, b, c)
```

you interpret it as a call to (application of) a function `f` to just *one argument* -- a tuple of three elements. It's very important to train your eyes to look for spaces. They separate functions from their arguments and arguments from each other.

When an argument to a function is a result of another function application, you have to use parentheses for that. For instance,

``` text
a b (c d)
```

means the function `a` acting on two arguments, `b` and `(c d)`, which itself is an application of function `c` to `d`. There is a way to omit the parentheses in the above by using the operator `$` (dollar sign):

``` text
a b $ c d
```

A `$` is interpreted as: What follows is the last argument to the function you're calling.

In this tutorial we've seen examples of function calls. Here's one:

``` text
defaultLayout [whamlet|
  Welcome to the Pigsty!
|]
```

The argument to the function `defaultLayout` is split over several lines, but it could be written in one line as well:

``` text
defaultLayout [whamlet| Welcome to the Pigsty!|]
```

Here's another example:

``` text
warpDebug 3000 Piggies
```

The third one is a little tricky, since the function `mkYesod` is a Template Haskell function, but the syntax is the same (I condensed it to one line):

``` text
mkYesod "Piggies" [parseRoutes| / HomeR GET|]
```

#### Function Definition Syntax

A function definition:

- starts with the name of the function,
- followed by its formal parameters separated by white spaces,
- an **equal sign**,
- and an expression that is the body of the function.

You should be able to parse this line of code:

``` text
a b c = d e f
```

It's a definition of the function `a` that takes two formal parameters, `b` and `c`. The body of this function is a call to `d` with two arguments, `e` and `f`. Of course, the use of short meaningless names is not encouraged in Haskell but I do it here to help you prime your internal parser.

In this tutorial there are two function definitions, `getHomeR` and `main`:

``` text
getHomeR = defaultLayout [whamlet|Welcome to the Pigsty!|]
main = warpDebug 3000 Piggies
```

In both definitions the expression on the right hand side of the equal sign is another function call.

The function `main` is the entry point of the program (just like in C++).

### Appendix

You would probably like to play with Yesod. You can find instructions on how to install Haskell Platform and Yesod on Windows, Linux, or the Mac in this [Quickstart Guide](https://www.yesodweb.com/page/quickstart). A [book on Yesod](https://www.yesodweb.com/book) by Michael Snoyman is available both online and on paper. Or, if it's too much effort, you may wait for an interactive tutorial coming soon to the FP Complete site. To try the program from this tutorial, create a file `main.hs` and paste the source into it. You can then load the file into the interpreter GHCi, run it from command line using `runhaskell main`, or compile it with `GHC main.hs`.
{% endraw %}
