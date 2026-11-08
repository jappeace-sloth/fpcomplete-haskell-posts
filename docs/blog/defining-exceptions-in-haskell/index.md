---
layout: page
title: "Defining exceptions in Haskell"
---
{% raw %}
*By Chris Done, 29 January 2019. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/defining-exceptions-in-haskell/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428053629/https://academy.fpblock.com/blog/defining-exceptions-in-haskell/).*

Let’s talk about exceptions. Programs do a thing successfully all the time, except sometimes when things didn’t work out. So we have “exceptions”, which, like anything fun in programming languages, was invented in Lisp in the 60’s .

They’re not perfect in Haskell. They’re not perfect in any language, really. We’re always making adjustments to what we think is the best way to handle exceptional circumstances. We’re muddling through, as a field. Let’s discuss the options in Haskell.

There have been [other blog posts](http://www.randomhacks.net/2007/03/10/haskell-8-ways-to-report-errors/) which discuss how to *raise* exceptions in Haskell–from using the IO exceptions (`throw`), to `ExceptT`-like monad transformers, to just returning an `Either Error a`–but we’re going to look at how we define *the exception type* itself.

## Use String

A very common way to define exceptions in Haskell is to use the `String` type (aka `[Char]`)–yes, that list of `Char` that we abuse for everything. There are actually many advantages to this:

- The first advantage is that it is built into the Haskell language; it’s available from any package anywhere.
- It’s already a human readable error message, by definition!
- You can already throw this using the `error` function which comes in the `Prelude` module .
- Furthermore, many packages in Haskell such as parsec and attoparsec, among others, already use the `String` type for providing error messages.
- Any instance of `Exception` can be converted to a `String` using either `show` or `displayException` , meaning you can easily include other exception types in your representation.

It’s not all tea and crumpets, though.

Many existing error messages in the library ecosystem of Haskell fail to include key information in their string error message. If the error was provided as a data type then it could have included what went wrong in the data type, and that would let you access the information yourself.

Consider, e.g.

``` haskell
if waterTemp < boilingPoint
then error "The tea isn't coming!"
else ...
```

This message doesn’t tell me why the tea isn’t coming. Is the kettle broken? Did someone forget to turn it on? Ideally, this error string *should* say:

``` haskell
if waterTemp < idealTemp
   then error ("The tea isn't coming, water temperature (" ++
               waterTemp ++ ") is below ideal temp (" ++
               idealTemp ++ ")".
   else ...
```

This message is an improvement because it gives me some details about why something failed. But it’s still not ideal.

Another problem is that you have to construct new messages ahead of time, which means that the user of your exception does not have the option to display the message how they like, such as in different languages (bye, bye, [i18n](https://en.wikipedia.org/wiki/Internationalization_and_localization)), or with different layouts, or different file formats (e.g. generating a JSON message). What if you the user of your function wants to display your exception in Mandarin? Or display it nicely formatted in HTML?

Furthermore, sometimes exceptions contain sensitive information, like a password or an API key: this might be useful for the developer, but it’s not something you always want displayed to the whole world, either in log files or to the end-user. With a `String` type, stripping out this information is at best a moving target.

It gets worse. Because it’s a string type, it’s impossible to rely on this presentation for a means of inspection. For example, if I receive an email from `Elizabeth II <`<a href="https://web.archive.org/web/2025/https://academy.fpblock.com/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="600f0e0513050c062010010c0103054e070f164e150b"><code>[email protected]</code></a>`>` , I can do an SPF record lookup on the domain name’s DNS records to see whether the IP sending me that email is a valid sender for that domain.

But if I use a library to do it, I can get an error like this:

``` haskell
> queryTXT (Network.DNS.Name "palace.gov.uk")
*** Exception: user error (res_query(3) failed)
```

Well, this is true! The query did fail. But I need more information than that. It could be that your connection is having trouble, it could be that the domain has no SPF record, or it could be that the domain name is not valid; if the domain has no SPF record, that’s a problem. If my connection is having trouble, that’s fine - I can try again later. If this is a string type you cannot make that decision.

Lastly, after all this woe, you do not have exhaustiveness checking on a `String` like you would in a sum type, so you don’t know whether you have handled all the available cases.

**Click below to learn more about a unique offer**

## The mega exception type

Another very common way of expressing errors is to use a large sum type where every constructor represents a different error case. This is used extensively in, for example, http -conduit, stack, etc.

Example [from http -client](https://hackage.haskell.org/package/http-client-0.5.14/docs/src/Network.HTTP.Client.Types.html#HttpExceptionContent):

``` haskell
data HttpExceptionContent
   = StatusCodeException (Response ()) S.ByteString
   | TooManyRedirects [Response L.ByteString]
   | OverlongHeaders
   | ResponseTimeout
   | ...
```

The advantage of this approach is that all types of exceptions are centralised in one location, which includes being able to inspect every possible error case when you pattern match (with GHC’s exhaustiveness checking), like:

``` haskell
catch (makeRequest)
      (\case
        StatusCodeException r s -> ...
        OverlongHeaders -> ...
        ...)
```

Additionally, when you look at the exception type [in haddock](https://hackage.haskell.org/package/http-client-0.5.14/docs/Network-HTTP-Client.html#t:HttpExceptionContent) you are able to discern what things can go wrong ahead of time. You can also put any relevant data into the constructor.

In other words, this approach is self documenting . It’s transparent.

The *disadvantage* is that you have to centralise all of your work in one place, which requires an extra maintenance burden over simply writing an error as a string. And whenever you add a new constructor it causes a breaking change to downstream users of your library. This may be considered an advantage or disadvantage .

It can also be difficult to add context to your constructors, especially if you don’t want to repeat that context in every single constructor. For example, in the http -conduit package, it has about 30 constructors. You wouldn’t want to copy the same context to every constructor. Instead, it’s probably better to have a separate exception type which contains the context and then has a field for your sum type. In fact, this is the approach taken by the http -conduit package in the [`HttpException`](https://hackage.haskell.org/package/http-conduit-2.3.2/docs/Network-HTTP-Client-Conduit.html#t:HttpException) type:

``` haskell
data HttpException
    = HttpExceptionRequest Request HttpExceptionContent
    | InvalidUrlException String String
```

The `Request` is the context, and the `HttpExceptionContent` is the actual problem that occurred.

One final point: the mega exception type implies some kind of completeness; that if you catch this exception type when using a library, you’ve handled all possible exceptions. But that’s not true, a library can still throw a different exception type. So this approach may give people a false sense of security.

## Individual exception types

This approach is similar to the mega exception type except each error condition has a separate data type. The advantages of this is in the `Either` case : you know exactly what will go wrong because there is only one possible error case for this type of exception, whereas in the mega exception type, you can catch the type, but then you might have 30 different error conditions that could happen. It’s unlikely that all 30 of those error cases could go wrong, but you would have to assume they could, because of the type.

For example, if a file doesn’t exist, that’s one type of exception. If a directory doesn’t exist, that is another type of exception. So a function such as openFile can claim to throw a product of these two exception types, the file not existing, or the directory not existing, or even that you do not have access to the directory, etc.

``` haskell
Throws (FileNotFound,DirectoryNotFound,AccessDenied)
```

The disadvantage is it’s hard to combine them. Product types such as tuples don’t really scale. Type signatures also become very unwieldy when dozens of different types come into play such as in the IO APIs in `base` . It’s hard to really manage that. Just consider the large number of exceptions throwable by `base` .

Another issue is that users will have to know about all the different types of exceptions that can be thrown in order to catch everything from your library in the impure `throw` case , whereas in the mega exception case it’s easy to catch everything because everything has already been put in one place for you.

## Abstract exception type

This approach is where you have an exception type which is entirely opaque and not inspectable except by use of accessors. An example of this is the IOError type in Haskell, which is standard and used throughout the IO library. For example, the error accessor `isDoesNotExistError` .

The advantage to this is that you can change the internals without breaking the API. Another advantage is that you can easily capture the context of an error, because you just put that in an accessor .

Another advantage is that predicates can be applied to more than one constructor, such as `isFileOpenError` ; this could be an accessor to indicate that you could not open a file but the reason can be more detailed, such as “unable to access directory”, “no such file”, or whatever.

The disadvantage of this is: it’s not self documenting on haddock in the way the transparent exception type is, so you’re essentially hiding what the different options are from you users.

Plus, maybe you *should* break your users’ code when you change how errors can be thrown; maybe hiding the details just makes things worse.

## Why not both?

Another option is to provide both of these things. So, you provide a set of constructors but you also provide a set of predicates which can be used on these types and other accessors . Or even using pattern synonyms to provide a documented accessor set, without exposing the internal data type. This would give you some flexibility, but I do not know of any example in the wild which implements this approach.

Matt Parsons explores an [approach to errors using prisms and generic-lens](https://www.parsonsmatt.org/2018/11/03/trouble_with_typed_errors.html) that’s worth taking a look at.

## Terminate the program

Finally, we can take the C approach and terminate the program, set the return code to -1. The disadvantage of this is that you will have your Haskell card torn up and you will be banished to work on node.js projects forever.

## Conclusions

It seems like the base Haskell packages favor the opaque approach, and many standard task libraries use the mega exception approach. We’ve discussed the trade-offs. At this point, how to model your exceptions is strongly in the category of a judgment call than a clear cut decision.

The only thing that is clear cut to me, is that `String` (or `Text`) for error messages is always the wrong decision, for the reasons outlined above. In parser libraries, for example, the old approach has been this one. But in more modern libraries, such as [megaparsec](https://hackage.haskell.org/package/megaparsec-7.0.4/docs/Text-Megaparsec.html#t:ParsecT), the error type is provided by the caller of the library. So there isn’t a need to decide on a concrete type ahead of time.

If you need any help with Haskell please [contact us](https://web.archive.org/web/2025/https://academy.fpblock.com/special-haskell-offer).
{% endraw %}
