---
layout: page
title: "What pure functional programming is all about: Part 2"
---
{% raw %}
*By Chris Done, 1 May 2017. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2017/05/pure-functional-programming-part-2/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250428062659/https://academy.fpblock.com/blog/2017/05/pure-functional-programming-part-2/).*

In the [last post](../pure-functional-programming/), we covered the following:

- What purity is and what it isn't.
- We looked at functions and function composition.
- We've looked at how reasoning is easier if you only have functions.

In this post, we'll explore:

- SQL as a pure language, which is a familiar language to almost everybody.
- How pure languages deal with the real-world and doing side-effects, which are obviously practical things to do.
- Evaluation vs execution, the generalization of pure vs impure languages.

In the next post, we'll explore the performance and declarative-code-writing benefits of pure functional languages in particular detail, looking at generated code, assembly, performance, etc.

## In a familiar setting: SQL

In the last post, we established that pure languages (like Haskell or PureScript) are unable to make observations about the real world directly.

So, then, the question is: How do pure languages interact with the real world? Let's look at SQL first, because everyone knows SQL, and then use that as a bridge towards how it's done in Haskell and other general purpose pure languages.

Imagine a subset of SQL which is pure. It's not a big leap: SQL is mostly pure anyway. I don't like it when people write an article and ask me to imagine a syntax that's in their heads, so here is trivial a [PEG](https://en.wikipedia.org/wiki/Parsing_expression_grammar) grammar, which you can try online [here](https://pegjs.org/online).

``` c
Select = 'SELECT ' Fields ' FROM ' Names Where?
Names = Name (', ' Name)*
Fields = Exp (', ' Exp)*
Where = ' WHERE ' Exp
Exp = Prefix? (Funcall / Condition / Name) (Connective Exp)?
Funcall = Name '(' Exp ')'
Condition = (Funcall / Name) Op Exp
Prefix = 'NOT '
Connective = ' AND ' / ' OR '
Op = ' = ' / ' <> ' / ' < ' / ' > ' / ' * '
Name = [a-zA-Z0-9]+
```

The following is an example of the above grammar.

``` sql
SELECT sin(foo), bar * 3 FROM table1, table2 WHERE foo > 1 AND NOT bar = floor(foo)
```

This language is pure. The result of *evaluating* one of these expressions is the same every time. You can swap the order of commutative expressions like `floor(foo) = bar` and it doesn't change the meaning of the program. `floor(x) * sin(y) = sin(y) * floor(x)`.

You get a description of the work you want to be done, and then the database engine (PostgreSQL, MySQL, SQL Server, etc.), usually creating an optimized query plan based on what it knows about your query and the database schema and contents, *executes* the query on the database, returning a collection of results.

You didn't write instructions about how to get the database, where to look on the database, how to map indices across tables and whether to do an index scan or a sequence scan, allocating a buffer, etc.

And yet, above, we clearly are giving the SQL engine a little program (not a turing complete one), that can compute conditionals and even functions (`floor` and `sin`) that we specified freely.

**Because our little program is pure**, SQL is capable of basically rewriting it completely, reducing it into a more normalized form without redundancy, and executing something far more efficient.

Look at what PostgreSQL is able to do with your queries. Here I do a query which works on an indexed field on a table with 37,626,086 rows. PostgreSQL knows both the query and my data, and plans accordingly, able to estimate the cost of how much work we'll have to do.

``` sql
ircbrowse=> explain select * from event where id > 123 and id < 200*2;
                                    QUERY PLAN
----------------------------------------------------------------------------------
 Index Scan using event_unique_id on event  (cost=0.56..857.20 rows=309 width=87)
   Index Cond: ((id > 123) AND (id < 400))
```

(The `200*2` was evaluated statically.)

Simply based on a static analysis of the SQL program.

## Evaluation vs execution

The SQL example is a specific case of a more general way of separating two concerns: evaluation and execution (or interpretation). On the one side you have your declarative language that you can evaluate, pretty much in terms of substition steps (and that's how you do your reasoning, in terms of the *denotational semantics*), and on the other you have a separate program which interprets that language in "the real world" (associated with *operational* semantics).

I'm sure any programmer reading this easily understands the informal denotational semantics of the SQL mini language above, and would feel comfortable implementing one or more ways of executing it.

In the same way, Haskell and other pure languages, construct declarative descriptions of work which a separate program can execute.

## Evaluation

What's *evaluation*, as differentiated from *execution*? To do your language's regular evaluation steps, as you might do on paper. If you've read your Structured and Interpretation of Computer Programs by MIT, you'll know this as [the *substitution model*](https://sarabander.github.io/sicp/html/1_002e1.xhtml#g_t1_002e1_002e5). Here's an example.

If you want to count the length of a linked list, you might do:

``` haskell
length [1, 2, 3]
```

And `length` is implemented like this:

``` haskell
length [] = 0
length (x:xs) = 1 + length xs
```

So let's *evaluate* the expression, step-by-step:

``` haskell
length [1, 2, 3]

1 + length [2, 3]

1 + (1 + length [3])

1 + (1 + (1 + length []))

1 + (1 + (1 + 0))

1 + (1 + 1)

1 + 2

3
```

Even if you don't know Haskell, I think the simple substitution steps to evaluate the expression are straight-forward and make sense. That's evaluation.

## A Terminal mini-language

Let's look at a data type that models a list of terminal actions to perform. I realise that if you don't know Haskell or ML, the below is mostly nonsense. I'll also bring in JavaScript as a "lingua franca", so that the idea translates nicely.

(If it looks concise in Haskell and verbose in JavaScript, it's because JavaScript was designed for imperative, OO-style programming, and Haskell was designed for pure functional programming.)

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td data-valign="top"><pre class="haskell"><code>data Terminal a
  = Print String (Terminal a)
  | GetLine (String -&gt; Terminal a)
  | Return a</code></pre></td>
<td data-valign="top"><pre class="javascript"><code>function Print(string, next) {
  this.line = string;
  this.next = next;
}
function GetLine(cont) {
  this.f = cont;
}
function Return(a) {
  this.a = a;
}</code></pre></td>
</tr>
</tbody>
</table>

It can describe printing to stdout, getting a line from stdin, or returning a result. An example might be:

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td data-valign="top"><pre class="haskell"><code>Print
  &quot;Please enter your name: &quot;
  (GetLine
     (\name -&gt;
        Print
           (&quot;Hello, &quot; ++ name ++ &quot;!&quot;)
           (Return ())))</code></pre></td>
<td data-valign="top"><pre class="javascript"><code>new Print(
  &quot;Please enter your name: &quot;,
  new GetLine(function(name){
    return new Print(&quot;Hello, &quot; + name + &quot;!&quot;,
                     new Return(null));}))</code></pre></td>
</tr>
</tbody>
</table>

Think of this like an abstract syntax tree. It's the description of what to do. When there is a function in the AST, that's a callback. The callback is just another pure function that returns a new action to be interpreted.

The expressions above can be evaluated, but they perform no side-effects. It's a piece of purely functional code which generates a data structure. Our substitution model above still works.

Hammering the point home, consider a greeting action like this:

``` haskell
greeting :: String -> Terminal ()
greeting msg =
  Print
    msg
    (GetLine
       (\name ->
          if name == "Chris"
            then Print "That's my name too." (Return ())
            else Print "Hello, stranger!" (Return ())))
```

The `greeting` function itself is pure. It takes a message string, and constructs a `Print` using that. That's done by evaluation. Also, the sub-expression `(\name -> ...)` is another pure function that takes a name and conditionally produces one action or another.

Now, onto *execution*.

## Execution

We can write a number of ways to interpret this AST. Here is one pure implementation. It takes as input (1) some action list to run and (2) lines of input, then it returns a value and some output lines:

``` haskell
data Result a = Success a | Failure String deriving Show
interpretPure :: Terminal a -> [String] -> Result (a,[String])
interpretPure action stdin =
  case action of
    Return a -> Success (a, [])
    Print line next ->
      case interpretPure next stdin of
        Success (a, stdout) -> Success (a, line : stdout)
        Failure e -> Failure e
    GetLine f ->
      case stdin of
        [] -> Failure "stdin closed"
        (line:stdin') -> interpretPure (f line) stdin'
```

In diagram form:

<img src="https://i.imgur.com/RzACyVv.png" width="500" alt="No alt provided" />

Note the part,

``` haskell
    GetLine f ->
      case stdin of
        [] -> Failure "stdin closed"
        (line:stdin') -> interpretPure (f line) stdin'
-------------------------------------- ^
```

Above is where we call the *pure function* from `GetLine` to produce another action for us to interpret.

In JavaScript:

``` javascript
function Success(x){ this.success = x; }
function Failure(e){ this.error = e; }
function interpretPure(action, stdin) {
  if (action instanceof Return) {
    return new Success({ result: action.a, stdout: [] });
  } else if (action instanceof Print) {
    var result = interpretPure(action.next, stdin);
    if (result instanceof Success) {
      return new Success({
        result: result.success.result,
        stdout: [action.line].concat(result.success.stdout)
      });
    } else return result;
  } else if (action instanceof GetLine) {
    if (stdin == "") {
      return new Failure("stdin closed");
    } else {
      var line = stdin[0];
      var stdin_ = stdin.slice(1);
      return interpretPure(action.f(line), stdin_);
    }
  }
}
```

Which we can run like this:

``` haskell
> interpretPure demo ["Dave"]
Success ((),["Please enter your name: ","Hello, Dave!"])
> interpretPure demo []
Failure "stdin closed"
```

``` javascript
> JSON.stringify(interpretPure(demo, ["Dave"]));
"{"success":{"result":null,"stdout":["Please enter your name: ","Hello, Dave!"]}}"
> JSON.stringify(interpretPure(demo, []));
"{"error":"stdin closed"}"
```

If we liked, we could interpret this as real I/O that talks to the world directly.

In Haskell, we translate it to a different type called `IO`. In JavaScript, let's do a good olde-fashioned 90's-style `alert`/`prompt` user interaction.

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<tbody>
<tr>
<td data-valign="top"><pre class="haskell"><code>interpretIO :: Terminal a -&gt; IO a
interpretIO terminal =
  case terminal of
    Return a -&gt; return a
    Print str next -&gt; do
      putStrLn str
      interpretIO next
    GetLine f -&gt; do
      line &lt;- getLine
      interpretIO (f line)</code></pre></td>
<td data-valign="top"><pre class="javascript"><code>function interpretIO(action) {
  if (action instanceof Return) {
    return action.a;
  } else if (action instanceof Print) {
    alert(action.line);
    interpretIO(action.next);
  } else if (action instanceof GetLine) {
    var line = prompt();
    interpretIO(action.f(line));
  }
}</code></pre></td>
</tr>
</tbody>
</table>

In this case, we're just translating from one model to another. The `IO a` type is interpreted by the Haskell runtime either in a REPL prompt, or in a compiled program. JavaScript is capable of executing things directly during evaluation, so we were able to implement something similar to what Haskell's runtime does for IO.

In SICP, they talk about programs as being spells, and the interpreter being like a spirit that does your bidding. Here is a formal description:

![No alt provided](https://i.imgur.com/3o8sNra.png)

(In practice, Haskell's IO type is not a closed set of operations, but an open set that can be extended with e.g. bindings to C libraries and such, and it isn't interpreted at runtime but rather compiled down to bytecode or machine code. The strict evaluation/execution separation remains in place, however.)

## Summary

We've covered an informal comparison between "evaluating" and "executing" code, which is a distinction often discussed in the functional programming community.

We've explored making a declarative data type that represents terminal interaction, and implemented two different ways of interpreting it: as a pure function, or executing it directly. There may be other interpretations, such as talking to a server. We could write an interpreter which logs every action performed. We could also write a test suite which feeds randomized or specific inputs and demands consistent outputs.

We looked at how SQL is such an example of an evaluation (`1 + 1` is evaluated before executing the query) vs execution separation. In `SELECT customer.purchases + 1 FROM customer`, the `customer.purchases + 1` expression is *evaluated* by the interpreter for each row in the table.

In the next post, we'll explore:

- Performance of pure code.
- Optimization of pure code, in particular: Inlining, deforestation, common sub-expression elimination, fusion, rewrite rules, etc.
- And how these optimizations allow for low- or zero-cost abstractions.

We may further explore different types of interpreters (software transactional memory, local mutation, parsers, etc).

## P.S.

There are some extra articles that may be of interest for the fearless:

- [The C language is purely functional](http://conal.net/blog/posts/the-c-language-is-purely-functional)
- Handling effects in PureScript (no longer available)
- [Free monads](https://www.haskellforall.com/2012/06/you-could-have-invented-free-monads.html)
{% endraw %}
