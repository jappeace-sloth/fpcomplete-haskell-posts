---
layout: page
title: "Decimal Safety Right on The Money"
---
{% raw %}
*By Alexey Kuleshevich, 12 February 2020. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/safe-decimal-right-on-the-money/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250717153139/https://academy.fpblock.com/blog/safe-decimal-right-on-the-money/).*

Fixed point decimal numbers are used for representing all kinds of data: percentages, temperatures, distances, mass, and many others. I would like to share an approach for safely and efficiently representing currency data in Haskell with `safe-decimal`.

## Problems we want to solve

### Floating point

I wonder how much money gets misplaced because programmers choose a floating point type for representing money. I will not attempt to convince you that using `Double` or `Float` for monetary values is unacceptable, it is a known fact. Values like `NaN`, `+/-Infinity` and `+/-0` have no meaning in handling money. In addition, the inability to represent most decimal values exactly should be enough reason to avoid floating point.

### Fixed point decimal

Floating point types make sense when numerical approximation acceptable and you care primarily about performance rather than correctness. This is most common in numerical analysis, signal processing and other areas alike. In many other circumstances a type capable of representing decimal numbers exactly should be used instead. Unlike floating point in a `Decimal` type we manually restrict how many digits after the decimal point we can have. This is called [fixed-point number representation](https://en.wikipedia.org/wiki/Fixed-point_arithmetic). We use fixed-point numbers on a daily basis when paying in the store with cash or card, tracking distance with an odometer, and reading values off of a digital hydrometer or thermometer.

We can represent fixed-point decimal numbers in Haskell by using an integral type for the actual value, which is called a precision, and a scale parameter, which is used for keeping track of how far from the right the decimal point is. In `safe-decimal` we define a `Decimal` type that allows us to choose a precision (`p`) and supply our `s` scale parameter with the type level natural number:

``` haskell
newtype Decimal r (s :: Nat) p = Decimal p
  deriving (Ord, Eq, NFData, Functor, Generic)
```

Unlike floating point numbers we cannot move our decimal point without changing the scaling parameter and sometimes the precision as well. This means that when we use operations like multiplication or division we might have to do some rounding. The rounding strategy is selected at the type level with the `r` type variable. At time of writing the most common rounding strategies have been implemented: `RoundHalfEven`, `RoundHalfUp`, `RoundHalfDown`, `RoundDown` and `RoundToZero`. There is a plan to add more in the future.

### Precision

It is common to use a type like `Integer` for decimal representation, for straightforward reasons:

- `Integer` is easy to use
- `Integer` can represent any number in the universe, if you have enough memory

Let's look at an example which starts with enabling an extension in Haskell. We need to turn on `DataKinds` so that we can use type level natural numbers.

``` haskell
>>> :set -XDataKinds
>>> x = Decimal 12345 :: Decimal RoundHalfUp 4 Integer
>>> x
1.2345
>>> x * 5
6.1725
>>> roundDecimal (x * 5) :: Decimal RoundHalfUp 3 Integer
6.173
```

The concrete `Decimal` type backed by `Integer` has a `Num` instance. That is why we were able to use literal `5` and GHC converted it to a `Decimal` for us. This is how the same numbers multiplied together look as `Double`:

``` haskell
>>> 1.2345 * 5 :: Double
6.172499999999999
```

### Storage and Performance

`Integer` is nice, but in some applications `Integer` isn't an acceptable representation of our data. We might need to store decimal values in database, transmit them over the network, or improve performance by storing numbers in an unboxed instead of boxed array. It is faster to store a 64-bit integer value in a database rather than converting a number to a sequence of bytes in a blob as is necessary with `Integer`. Transmission over a network is another limitation that comes to mind. Having a 508 byte limit on a UDP packet can quickly become a problem for `Integer` based values.

The best way to solve this is to use fixed width integer types such as `Int64`, `Int32`, `Word64`, etc. If precision of more than 64 bits is desired there are packages that provide 128-bit, 256-bit, and other variants of signed/unsigned integers. All of them can be used with `safe-decimal`, eg:

``` haskell
>>> import Data.Int (Int8, Int64)
>>> Decimal 12345 :: Decimal RoundHalfUp 6 Int64
0.012345
>>> Decimal 123 :: Decimal RoundHalfUp 6 Int8
0.000123
```

### Bounds

Even discarding the desire for better performance and ignoring the memory constraints imposed on us, there are often types that have domain-specific bounds anyway. The most common example is when people use signed types like `Int` to represent values that have no sensible negative value. Use unsigned types like `Word` for representing values that should have no negative value.

Some values that can be represented by a decimal number have a lower and upper bound that we estimate. Percentages go from 0% to a 100%, the total circulation of US dollars is about 14 trillion, and the surface temperature of a star is somewhere in a range of 225-40000K. If we use our domain specific knowledge we can come up with some safe bounds, instead of blindly assuming that we need infinitely large values.

Beware though, that using integral types with bounds come with real danger: integer [overflow](https://cwe.mitre.org/data/definitions/190.html) and [underflow](https://cwe.mitre.org/data/definitions/191.html). These are common reasons for bugs in software that lead to a whole variety of exploits. This is the area where protection in `safe-decimal` really shines, and here is an example of how it protects you:

``` haskell
>>> 123 + 4 :: Int8
127
>>> 123 + 5 :: Int8
-128
>>> x = Decimal 123 :: Decimal RoundHalfUp 6 Int8
>>> x
0.000123
>>> plusDecimalBounded x (Decimal 4) :: Maybe (Decimal RoundHalfUp 6 Int8)
Just 0.000127
>>> plusDecimalBounded x (Decimal 5) :: Maybe (Decimal RoundHalfUp 6 Int8)
Nothing
```

### Runtime exceptions

We know that division by zero will result in `DivideByZero` exception:

``` haskell
>>> 1 `div` 0 :: Int
*** Exception: divide by zero
```

Less well known is that while some integral operations result in silent overflows, others will cause runtime exceptions:

``` haskell
>>> -1 * minBound :: Int
-9223372036854775808
>>> 1 `div` minBound :: Int
-1
>>> minBound `div` (-1) :: Int
*** Exception: arithmetic overflow
```

Floating point values also have a sad story for division by zero. You'd be surprised how often you can stumble upon those values online:

![](../../assets/blog/safe-decimal-right-on-the-money/safe-decimal.jpeg)

``` haskell
>>> 0 / 0 :: Double
NaN
>>> 1 / 0 :: Double
Infinity
>>> -1 / 0 :: Double
-Infinity
```

Long story short we want to be able to prevent all these issues from within pure code. Which is exactly what `safe-decimal` will do for you:

``` haskell
>>> -1 * pure minBound :: Arith (Decimal RoundHalfUp 2 Int)
ArithError arithmetic overflow
>>> pure minBound / (-1) :: Arith (Decimal RoundHalfUp 2 Int)
ArithError arithmetic overflow
>>> 1 / 0 :: Arith (Decimal RoundHalfUp 2 Int)
ArithError divide by zero
```

`Arith` is a monad defined in `safe-decimal` and is used for working with arithmetic operations that can fail for any particular reason. It is isomorphic to `Either SomeException`, which means there is straightforward conversion from `Arith` monad to others that have `MonadThrow` instance with `arithM` and a few other helper functions:

``` haskell
>>> arithM (1 / 0 :: Arith (Decimal RoundHalfUp 2 Int))
*** Exception: divide by zero
>>> arithMaybe (1 / 0 :: Arith (Decimal RoundHalfUp 2 Int))
Nothing
```

## Decimal for crypto

At the beginning of the post I mentioned that we will implement a currency. Everyone seems to be implementing cryptocurrencies nowadays, so why don't we do the same?

The most popular cryptocurrency at time of writing is Bitcoin, so we'll use it for this example. A few assumptions we are going to make before we start:

- The maximum amount is 21M BTC
- No negative amounts are allowed
- Precision is up to 8 decimal places
- Smallest expressible value is 0.00000001 BTC, which is one Satoshi. It is named after the pseudonymous Satoshi Nakamoto who published the seminal Bitcoin paper.

### Definition

Here we'll demonstrate how we can represent Bitcoin with `safe-decimal` and in case if you would like to follow along here is [the gist](https://gist.github.com/lehins/98d835b51c15270c2a600135b64d474d) with all of the code presented in this blogpost. First, we declare the raw amount `Satoshi` that will be used, so we can specify its bounds. Following that is the `Bitcoin` wrapper around the `Decimal` that specifies all we need to know in order to operate on this currency:

``` haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE NumericUnderscores #-}
{-# LANGUAGE GeneralizedNewtypeDeriving #-}

module Bitcoin (Bitcoin) where

import Data.Word
import Numeric.Decimal
import Data.Coerce

newtype Satoshi = Satoshi Word64 deriving (Show, Eq, Ord, Enum, Num, Real, Integral)

instance Bounded Satoshi where
  minBound = Satoshi 0
  maxBound = Satoshi 21_000_000_00000000

data NoRounding

type BitcoinDecimal = Decimal NoRounding 8 Satoshi

newtype Bitcoin = Bitcoin BitcoinDecimal deriving (Eq, Ord, Bounded)

instance Show Bitcoin where
  show (Bitcoin b) = show b
```

Important parts of these definitions are:

- We are using a newtype wrapper around `Word64` with custom bounds, so that the library can protect us from creating an invalid value. Using `Int64` would have not made a difference in this case, but using another type with less available bits would not be enough to hold large values.
- We define no rounding strategy to make sure that at no point rounding could cause money to appear or disappear.
- We do not export the constructor for `Bitcoin` type to ensure that invalid values cannot be constructed manually. Smart constructors will follow below, which can be exported if needed.

### Construction and arithmetic

Helper functions that do zero cost coercions from `Data.Coerce` will be used to go between types without making us repeat their signatures.

``` haskell
toBitcoin :: BitcoinDecimal -> Bitcoin
toBitcoin = coerce

fromBitcoin :: Bitcoin -> BitcoinDecimal
fromBitcoin = coerce

mkBitcoin :: MonadThrow m => Rational -> m Bitcoin
mkBitcoin r = Bitcoin <$> fromRationalDecimalBoundedWithoutLoss r

plusBitcoins :: MonadThrow m => Bitcoin -> Bitcoin -> m Bitcoin
plusBitcoins b1 b2 = toBitcoin <$> (fromBitcoin b1 `plusDecimalBounded` fromBitcoin b2)

minusBitcoins :: MonadThrow m => Bitcoin -> Bitcoin -> m Bitcoin
minusBitcoins b1 b2 = toBitcoin <$> (fromBitcoin b1 `minusDecimalBounded` fromBitcoin b2)
```

`mkBitcoin` gives us a way to construct new values, while giving us a freedom to choose the monad in which we want to fail by restricting to `MonadThrow`, for simplicity we'll stick to `IO`, but it could just as well be `Maybe`, `Either`, `Arith` and many others.

``` haskell
>>> mkBitcoin 1.23
1.23000000
>>> mkBitcoin (-1.23)
*** Exception: arithmetic underflow
```

Examples below make it obvious that we are guarded from constructing invalid values from `Rational`:

``` haskell
>>> :set -XNumericUnderscores
>>> mkBitcoin 21_000_000.00000000
21000000.00000000
>>> mkBitcoin 21_000_000.00000001
*** Exception: arithmetic overflow
>>> mkBitcoin 0.123456789
*** Exception: PrecisionLoss (123456789 % 1000000000) to 8 decimal spaces
```

Same logic goes for operating on `Bitcoin` values. Nothing gets past, any operation that could produce an invalid value will result in a failure.

``` haskell
>>> balance <- mkBitcoin 10.05
>>> receiveAmount <- mkBitcoin 2.345
>>> plusBitcoins balance receiveAmount
12.39500000
>>> maliciousReceiveBitcoin <- mkBitcoin 20999990.0
>>> plusBitcoins balance maliciousReceiveBitcoin
*** Exception: arithmetic overflow
>>> arithEither $ plusBitcoins balance maliciousReceiveBitcoin
Left arithmetic overflow
```

Subtracting values is handled in the same fashion. Note that going below a lower bound will be reported as underflow, which, contrary to popular belief, is a real term not only for floating points, but for integers as well.

``` haskell
>>> balance <- mkBitcoin 10.05
>>> sendAmount <- mkBitcoin 1.01
>>> balance `minusBitcoins` sendAmount
9.04000000
>>> sendAmountTooMuch <- mkBitcoin 11.01
>>> balance `minusBitcoins` sendAmountTooMuch
*** Exception: arithmetic underflow
>>> sendAmountMalicious <- mkBitcoin 184467440737.09551616
*** Exception: arithmetic overflow
```

I would like to emphasize in the example above the fact that we did not have to check if `balance` was sufficient enough for the amounts to be fully deducted from it. This means we are automatically protected from incorrect transactions as well as [very common attack vectors](https://consensys.github.io/smart-contract-best-practices/known_attacks/#integer-overflow-and-underflow), some of which [really did happen with Bitcoin](https://medium.com/@jeancvllr/the-value-overflow-incident-in-the-bitcoin-blockchain-15th-august-2010-a59a516e03db) and other cryptocurrencies.

### Num and Fractional

Using a special smart constructor is cool and all, but it would be cooler if we could use our regular math operators to work with `Bitcoin` values and utilize GHC desugarer to automatically convert numeric literal values too. For this we need instances of `Num` and `Fractional`. We can't create instances like that:

``` haskell
instance Num Bitcoin where
...
instance Fractional Bitcoin where
...
```

because then we would have to use partial functions for failures, which is exactly what we want to avoid. Moreover some functions simply do no make sense for monetary values. Multiplying or dividing Bitcoins together, is simply undefined. We'll have to represent a special type of failure through an exception. This is a bit unfortunate, but we'll go with it anyways:

``` haskell
data UnsupportedOperation =
  UnsupportedMultiplication | UnsupportedDivision
  deriving Show

instance Exception UnsupportedOperation

instance Num (Arith Bitcoin) where
  (+) = bindM2 plusBitcoins
  (-) = bindM2 minusBitcoins
  (*) = bindM2 (\_ _ -> throwM UnsupportedMultiplication)
  abs = id
  signum mb = fmap toBitcoin . signumDecimalBounded . fromBitcoin =<< mb
  fromInteger i = toBitcoin <$> fromIntegerDecimalBoundedIntegral i

instance Fractional (Arith Bitcoin) where
  (/) = bindM2 (\_ _ -> throwM UnsupportedDivision)
  fromRational = mkBitcoin
```

It is important to note that defining the instances above is strictly optional and exporting helper functions that perform the same operations is preferable. We have the instances now so we can demonstrate their use:

``` haskell
>>> 7.8 + 10 - 0.4 :: Arith Bitcoin
Arith 17.40000000
>>> 7.8 - 10 + 0.4 :: Arith Bitcoin
ArithError arithmetic underflow
>>> 7.8 * 10 / 0.4 :: Arith Bitcoin
ArithError UnsupportedMultiplication
>>> 7.8 / 10 * 0.4 :: Arith Bitcoin
ArithError UnsupportedDivision
>>> 7.8 - 7.7 + 0.4 :: Arith Bitcoin
Arith 0.50000000
>>> 0.4 - 7.7 + 7.8 :: Arith Bitcoin
ArithError arithmetic underflow
```

The order of operations can play tricks on you, which probably serves as another reason to stick to exporting functions: `mkBitcoin`, `plusBitcoins`, `minusBitcoins` and whatever other operations we might need.

Let's take a look at a more realistic example where the amount sent is supplied to us as a `Scientific` value likely from some JSON object and we want to update the balance of our account. For simplicity's sake I will use a `State` monad, but same approach will work just as well with whatever stateful setup you have.

``` haskell
newtype Balance = Balance Bitcoin deriving Show

sendBitcoin :: MonadThrow m => Balance -> Scientific -> m (Bitcoin, Balance)
sendBitcoin startingBalance rawAmount =
  flip runStateT startingBalance $ do
    amount <- toBitcoin <$> fromScientificDecimalBounded rawAmount
    Balance balance <- get
    newBalance <- minusBitcoins balance amount
    put $ Balance newBalance
    pure amount
```

Usage of this simple function will demonstrate us the power of the approach taken in the library as well as its limitations:

``` haskell
>>> balance <- mkBitcoin 10.05
>>> sendBitcoin (Balance balance) 0.5
(0.50000000,Balance 9.55000000)
>>> sendBitcoin (Balance balance) 1e-6
(0.00000100,Balance 10.04999900)
>>> sendBitcoin (Balance balance) 1e+6
*** Exception: arithmetic underflow
>>> arithEither $ sendBitcoin (Balance balance) (-1)
Left arithmetic underflow
```

We witness `Overflow`/`Underflow` errors as expected, but we get almost no information on where exactly the problem occurred and which value was responsible for it. This is something that can be fixed with customized exceptions, but for now we do achieve the most important goal, namely protecting our calculations from all the dangerous problems without doing any explicit checking.

Nowhere in `sendBitcoin` did we have to validate our input, output, or intermediate values. Not a single `if then else` statement. This is because all of the information needed to determine the validity of the above operations was encoded into the type and the library enforces that validity for the programmer.

### Mixing Decimal types

Although multiplying two `Bitcoin` values makes no sense, computing the product of an amount and a percentage makes perfect sense. So, how do we go about multiplying different decimals together?

While demonstrating interoperability of different decimal types we'd like to also show how higher precision integrals can be used with `Decimal`. In this example we'll use a `Word128` backed `Decimal` for computing [future value](https://en.wikipedia.org/wiki/Future_value). There are a couple of packages that provide 128-bit integral types and it doesn't matter which one it comes from.

Our goal is to compute the savings account balance at 1.9% APY (Annual Percentage Yield) in 30 days if you start with 10,000 BTC and add 10 BTC each day.

We will start by defining the rounding strategy implementation for the `Word128` type and specifying the `Decimal` type we will be using for computation:

``` haskell
instance Round RoundHalfUp Word128 where
  roundDecimal = roundHalfUp

type CDecimal = Decimal RoundHalfUp 33 Word128
```

This is not the implementation of `FV` (Future Value) function as it is known in finance. It is a direct translation of how we think the accrual of interest works. In plain English we can say that to compute balance of the account tomorrow, we take balance we have today, multiply it by the daily interest rate and add it to the today's balance together with the amount we promised to top up daily.

``` haskell
futureValue :: MonadThrow m => CDecimal -> CDecimal -> CDecimal -> Int -> m CDecimal
futureValue startBalance dailyRefill apy days = do
  dailyScale <- -- apy is in % and the year of 2020 is a leap year
    fromIntegralDecimalBounded (100 * 366)
  dailyRate <- divideDecimalBoundedWithRounding apy dailyScale
  let go curBalance day
        | day < days = do
          accruedDaily <- timesDecimalBoundedWithRounding curBalance dailyRate
          nextDayBalance <- sumDecimalBounded [curBalance, accruedDaily, dailyRefill]
          go nextDayBalance (day + 1)
        | otherwise = pure curBalance
  go startBalance 0
```

The above implementation works on the `CDecimal` type. What we need to calculate is `Bitcoin`. This means we have to do some type conversions and scaling in order to match up the types of `futureValue` function. Then we do some rounding and conversion again to reduce precision to obtain the new `Balance`:

``` haskell
futureValueBitcoin :: MonadThrow m => Balance -> Bitcoin -> Rational -> Int -> m (Balance, CDecimal)
futureValueBitcoin (Balance (Bitcoin balance)) (Bitcoin dailyRefill) apy days = do
  balance' <- scaleUpBounded (fromIntegral <$> castRounding balance)
  dailyRefill' <- scaleUpBounded (fromIntegral <$> castRounding dailyRefill)
  apy' <- fromRationalDecimalBoundedWithoutLoss apy
  endBalance <- futureValue balance' dailyRefill' apy' days
  endBalanceRounded <- integralDecimalToDecimalBounded (roundDecimal endBalance)
  pure (Balance $ Bitcoin $ castRounding endBalanceRounded, endBalance)
```

Now we can compute what our balance will be in 30 days:

``` haskell
computeBalance :: Arith (Balance, CDecimal)
computeBalance = do
  balance <- Balance <$> 10000
  topup <- 10
  futureValueBitcoin balance topup 1.9 30
```

Let's see what values we get and how they compares to the actual `FV` function that works on `Double` (for the curious here is one possible implementation [numpy.fv](https://github.com/numpy/numpy/blob/e94ed84010c60961f82860d146681d3fd607de4e/numpy/lib/financial.py#L36))

``` haskell
>>> fst <$> arithM computeBalance
Balance 10315.81142818
>>> fv (1.9 / 36600) 30 (-10) (-10000)
10315.811428177167
```

That's pretty good. We get the accurately rounded result of our new balance. But how accurate is the computed result before the rounding is applied? As accurate as 128 bits can do in presence of rounding:

``` haskell
>>> snd <$> arithM computeBalance
10315.811428176906130029412612348658890
```

We get much better accuracy here than we could with `Double`. This isn't surprising, since we have more bits at our disposal, but accuracy is not the only benefit of this calculation. The result is also deterministic! This is practically impossible to guarantee with floating point number calculations across different platforms and architectures.

## Available solutions

A very common question people usually ask when a new library is being announced: "What is wrong with currently available solutions?". That is a perfectly reasonable question, which hopefully we have a compelling answer for.

We had a strong requirement for safety, correctness, and performance. Which is the combination that none of the available libraries in Haskell ecosystem could provide.

I will use `Data.Fixed` from `base` as an example and list some of limitations that prevented us from using it:

- Backed by `Integer`, which makes it slower than it should be for common cases.

- Truncation instead of some more useful rounding strategies.

``` haskell
>>> 5.39 :: Fixed E1
5.3
>>> 5.499999999999 :: Fixed E1
5.4
```

- No built-in protection against runtime exceptions:

``` text
>>> f = 5.49 :: Fixed E1
>>> f / 0
*** Exception: divide by zero
```

- There is a limited number of scaling types: `E0`, `E1`, `E2`, `E3`, `E6`, `E9` and `E12`. It is possible to add new ones with `HasResolution`, but it is a bit inconvenient.

- No built-in ability to specify bounds. This means that there is no protection against things like negative values or going outside of artificially imposed limits.

Similar arguments can be applied to other libraries. Especially the objection [regarding performance](https://gist.github.com/lehins/727a86c71ff32e18a51b42d3dc0736fe). This objection is not unfounded: our benchmarks have revealed performance issues of practical relevance with existing implementations.

## Conclusion

I encourage everyone who writes software for finance, blockchain and other areas that require exact precision and safety of calculations, to seriously consider all implications of choosing the wrong data type for representing their numeric values.

Haskell is a very safe language out of the box, but as you saw in this post, it does not offer the desired level of safety when it comes to operations on numeric values. Hopefully we were able to convince you, that, at least for decimal numbers, such safety can be achieved with `safe-decimal` library.

If you feel like this post describes problems that are familiar to you and you are looking for a solution, please reach out to us and we will be glad to help.
{% endraw %}
