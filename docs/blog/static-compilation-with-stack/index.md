---
layout: page
title: "Static compilation with Stack"
---
{% raw %}
*By Tim Dysinger, 7 October 2016. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2016/10/static-compilation-with-stack/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250512143449/https://academy.fpblock.com/blog/2016/10/static-compilation-with-stack/).*

In our last blog post we showed you the new docker init executable pid1. What if we wanted to use our shiny new pid1 binary on a CentOS Docker image but we compiled it on Ubuntu? The answer is that it wouldn't likely work. All Linux flavors package things up a little differently and with different versions and flags.

If we were to compile pid1 completely static it could be portable (within a given range of Linux kernel versions). Let's explore different ways to compile a GHC executable with Stack. Maybe we can come up with a way to create portable binaries.

## Base Image for Experiments

First let's create a base image since we are going to be trying many different compilation scenarios.

Here's a Dockerfile for Alpine Linux & GHC 8.0 with Stack.

``` text
# USE ALPINE LINUX
FROM alpine
RUN apk update
# INSTALL BASIC DEV TOOLS, GHC, GMP & ZLIB
RUN echo "https://s3-us-west-2.amazonaws.com/alpine-ghc/8.0" >> /etc/apk/repositories
ADD https://raw.githubusercontent.com/mitchty/alpine-ghc/master/mitch.tishmack%40gmail.com-55881c97.rsa.pub \
    /etc/apk/keys/[email protected]
RUN apk update
RUN apk add alpine-sdk git ca-certificates ghc gmp-dev zlib-dev
# GRAB A RECENT BINARY OF STACK
ADD https://s3.amazonaws.com-stack/stack-1.1.2-x86_64 /usr/local/bin/stack
RUN chmod 755 /usr/local/bin/stack
```

Let's build it and give it a tag.

``` text
docker build --no-cache=true --tag fpco/pid1:0.1.0-base .
```

## Default GHC Compilation

Next let's compile pid1 with default Stack & GHC settings.

Here's our minimalist stack.yaml file.

``` text
resolver: lts-7.1
```

Here's our project Dockerfile that extends our test base image above.

``` text
FROM fpco/pid1:0.1.0-base
# COMPILE PID1
ADD ./ /usr/src/pid1
WORKDIR /usr/src/pid1
RUN stack --local-bin-path /sbin install --test
# SHOW INFORMATION ABOUT PID1
RUN ldd /sbin/pid1 || true
RUN du -hs /sbin/pid1
```

Let's compile this default configuration using Docker and give it a label.

``` text
docker build --no-cache=true --tag fpco/pid1:0.1.0-default .
```

A snippet from the Docker build showing the results.

``` text
Step 6 : RUN ldd /sbin/pid1 || true
 ---> Running in fcc138c199d0
        /lib/ld-musl-x86_64.so.1 (0x559fe5aaf000)
        libgmp.so.10 => /usr/lib/libgmp.so.10 (0x7faff710b000)
        libc.musl-x86_64.so.1 => /lib/ld-musl-x86_64.so.1 (0x559fe5aaf000)
 ---> 70836a2538e2
Removing intermediate container fcc138c199d0
Step 7 : RUN du -hs /sbin/pid1
 ---> Running in 699876efeb1b
956.0K  /sbin/pid1
```

You can see that this build results in a semi-static binary with a link to MUSL (libc) and GMP. This is not extremely portable. We will always have to be concerned about the dynamic linkage happening at run-time. This binary would probably not run on Ubuntu as is.

## 100% Static

Let's try compiling our binary as a 100% static Linux ELF binary without any link to another dynamic library. Note that our open source license must be compatible with MUSL and GMP in order to do this.

Let's try a first run with static linkage. Here's another Dockerfile that shows a new ghc-option to link statically.

``` text
FROM fpco/pid1:0.1.0-base
# TRY TO COMPILE
ADD ./ /usr/src/pid1
WORKDIR /usr/src/pid1
RUN stack --local-bin-path /sbin install --test --ghc-options '-optl-static'
```

Let's give it a go.

``` text
docker build --no-cache=true --tag fpco/pid1:0.1.0-static .
```

Oh no. It didn't work. Looks like there's some problem with linking. :\|

``` text
[1 of 1] Compiling System.Process.PID1 ( src/System/Process/PID1.hs, .stack-work/dist/x86_64-linux/Cabal-1.24.0.0/build/System/Process/PID1.o )
/usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/../../../../x86_64-alpine-linux-musl/bin/ld: /usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/crtbeginT.o: relocation R_X86_64_32 against `__TMC_END__' can not be used when making a shared object; recompile with -fPIC
/usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/crtbeginT.o: error adding symbols: Bad value
collect2: error: ld returned 1 exit status
`gcc' failed in phase `Linker'. (Exit code: 1)

--  While building package pid1-0.1.0 using:
      /root/.stack/setup-exe-cache/x86_64-linux/setup-Simple-Cabal-1.24.0.0-ghc-8.0.1 --builddir=.stack-work/dist/x86_64-linux/Cabal-1.24.0.0 build lib:pid1 exe:pid1 --ghc-options " -ddump-hi -ddump-to-file"
    Process exited with code: ExitFailure 1
```

### PIC flag

OK that last error said we should recompile with -fPIC. Let's try that. Once again, here's a Dockerfile with the static linkage flag & the new -fPIC flag.

``` text
FROM fpco/pid1:0.1.0-base
# TRY TO COMPILE
ADD ./ /usr/src/pid1
WORKDIR /usr/src/pid1
RUN stack --local-bin-path /sbin install --test --ghc-options '-optl-static -fPIC'
```

Let's give it a try.

``` text
docker build --no-cache=true --tag fpco/pid1:0.1.0-static-fpic .
```

But we still get the error again.

``` text
[1 of 1] Compiling System.Process.PID1 ( src/System/Process/PID1.hs, .stack-work/dist/x86_64-linux/Cabal-1.24.0.0/build/System/Process/PID1.o )
/usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/../../../../x86_64-alpine-linux-musl/bin/ld: /usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/crtbeginT.o: relocation R_X86_64_32 against `__TMC_END__' can not be used when making a shared object; recompile with -fPIC
/usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/crtbeginT.o: error adding symbols: Bad value
collect2: error: ld returned 1 exit status
`gcc' failed in phase `Linker'. (Exit code: 1)

--  While building package pid1-0.1.0 using:
      /root/.stack/setup-exe-cache/x86_64-linux/setup-Simple-Cabal-1.24.0.0-ghc-8.0.1 --builddir=.stack-work/dist/x86_64-linux/Cabal-1.24.0.0 build lib:pid1 exe:pid1 --ghc-options " -ddump-hi -ddump-to-file"
    Process exited with code: ExitFailure 1
```

### crtbeginT swap

Searching around for this crtbegint linkage problem we find that if we provide a [hack](https://bugs.launchpad.net/ubuntu/+source/gcc-4.4/+bug/640734) that it'll work correctly. Here's the Dockerfile with the hack.

``` text
FROM fpco/pid1:0.1.0-base
# FIX https://bugs.launchpad.net/ubuntu/+source/gcc-4.4/+bug/640734
WORKDIR /usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/
RUN cp crtbeginT.o crtbeginT.o.orig
RUN cp crtbeginS.o crtbeginT.o
# COMPILE PID1
ADD ./ /usr/src/pid1
WORKDIR /usr/src/pid1
RUN stack --local-bin-path /sbin install --test --ghc-options '-optl-static -fPIC'
# SHOW INFORMATION ABOUT PID1
RUN ldd /sbin/pid1 || true
RUN du -hs /sbin/pid1
```

When we try it again

``` text
docker build --no-cache=true --tag fpco/pid1:0.1.0-static-fpic-crtbegint .
```

It works this time!

``` text
Step 8 : RUN ldd /sbin/pid1 || true
 ---> Running in 8b3c737c2a8d
ldd: /sbin/pid1: Not a valid dynamic program
 ---> 899f06885c71
Removing intermediate container 8b3c737c2a8d
Step 9 : RUN du -hs /sbin/pid1
 ---> Running in d641697cb2a8
1.1M    /sbin/pid1
 ---> aa17945f5bc4
```

Nice. 1.1M isn't too bad for a binary that's portable. Let's see if we can make it smaller though. On larger executables, especially with other linked external libraries, this static output can be 50MB(!)

## Optimal Size

### GCC Optimization

It says on the GCC manpage if we use -Os that this will optimize for size. Let's try it.

Specify -optc-Os to optimize for size.

``` text
FROM fpco/pid1:0.1.0-base
# FIX https://bugs.launchpad.net/ubuntu/+source/gcc-4.4/+bug/640734
WORKDIR /usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/
RUN cp crtbeginT.o crtbeginT.o.orig
RUN cp crtbeginS.o crtbeginT.o
# COMPILE PID1
ADD ./ /usr/src/pid1
WORKDIR /usr/src/pid1
RUN stack --local-bin-path /sbin install --test --ghc-options '-optl-static -fPIC -Os'
# SHOW INFORMATION ABOUT PID1
RUN ldd /sbin/pid1 || true
RUN du -hs /sbin/pid1

docker build --no-cache=true --tag fpco/pid1:0.1.0-static-fpic-crtbegint-optcos .

Step 9 : RUN ldd /sbin/pid1 || true
 ---> Running in 8e28314924d0
ldd: /sbin/pid1: Not a valid dynamic program
 ---> c977f078eb24
Removing intermediate container 8e28314924d0
Step 10 : RUN du -hs /sbin/pid1
 ---> Running in 4e6b5c4d87aa
1.1M    /sbin/pid1
 ---> 66d459e3fcc1
```

There isn't any difference in output size with this flag. You may want to try it on a little larger or more complex executable to see if it makes a difference for you.

### Split Objects

GHC allows us to "split objects" when we compile Haskell code. That means each Haskell module is broken up into it's own native library. In this scenario, when we import a module, our final executable is linked against smaller split modules instead of to the entire package. This helps reduce the size of the executable. The trade-off is that it takes more time for GHC to compile.

``` text
resolver: lts-7.1
build: { split-objs: true }

docker build --no-cache=true --tag fpco/pid1:0.1.0-static-fpic-crtbegint-optcos-split .

Step 9 : RUN ldd /sbin/pid1 || true
 ---> Running in 8e28314924d0
ldd: /sbin/pid1: Not a valid dynamic program
 ---> c977f078eb24
Removing intermediate container 8e28314924d0
Step 10 : RUN du -hs /sbin/pid1
 ---> Running in 4e6b5c4d87aa
1.1M    /sbin/pid1
 ---> 66d459e3fcc1
```

There isn't any difference in output size with this flag in this case. On some executables this really makes a big difference. Try it yourself.

### UPX Compression

Let's try compressing our static executable with [UPX](https://upx.github.io/). Here's a Dockerfile.

``` text
FROM fpco/pid1:0.1.0-base
# FIX https://bugs.launchpad.net/ubuntu/+source/gcc-4.4/+bug/640734
WORKDIR /usr/lib/gcc/x86_64-alpine-linux-musl/5.3.0/
RUN cp crtbeginT.o crtbeginT.o.orig
RUN cp crtbeginS.o crtbeginT.o
# COMPILE PID1
ADD ./ /usr/src/pid1
WORKDIR /usr/src/pid1
RUN stack --local-bin-path /sbin install --test --ghc-options '-optl-static -fPIC -optc-Os'
# COMPRESS WITH UPX
ADD https://github.com/lalyos/docker-upx/releases/download/v3.91/upx /usr/local/bin/upx
RUN chmod 755 /usr/local/bin/upx
RUN upx --best --ultra-brute /sbin/pid1
# SHOW INFORMATION ABOUT PID1
RUN ldd /sbin/pid1 || true
RUN du -hs /sbin/pid1
```

Build an image that includes UPX compression.

``` text
docker build --no-cache=true --tag fpco/pid1:0.1.0-static-fpic-crtbegint-optcos-split-upx .
```

And, wow, that's some magic.

``` text
Step 11 : RUN ldd /sbin/pid1 || true
 ---> Running in 69f86bd03d01
ldd: /sbin/pid1: Not a valid dynamic program
 ---> c01d54dca5ac
Removing intermediate container 69f86bd03d01
Step 12 : RUN du -hs /sbin/pid1
 ---> Running in 01bbed565de0
364.0K  /sbin/pid1
 ---> b94c11bafd95
```

This makes a huge difference with the resulting executable 1/3 the original size. There is a small price to pay in extracting the executable on execution but for a pid1 that just runs for the lifetime of the container, this is not noticeable.

## Slackware Support

Here's a Slackware example running pid1 that was compiled on Alpine Linux

``` text
FROM vbatts/slackware
ADD https://s3.amazonaws.com/download.fpcomplete.com/pid1/pid1-0.1.0-amd64 /sbin/pid1
RUN chmod 755 /sbin/pid1
ENTRYPOINT [ "/sbin/pid1" ]
CMD bash -c 'while(true); do sleep 1; echo alive; done'
```

Build an image that includes UPX compression.

``` text
docker build -t fpco/pid1:0.1.0-example-slackware .       
docker run --rm -i -t fpco/pid1:0.1.0-example-slackware
```

It works!

``` text
alive
alive
alive
^C
```
{% endraw %}
