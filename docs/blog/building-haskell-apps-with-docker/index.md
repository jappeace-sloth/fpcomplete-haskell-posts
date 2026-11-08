---
layout: page
title: "Building Haskell Apps with Docker"
---
{% raw %}
*By Deni Bertovic, 21 December 2017. Mirrored from FP Complete's blog: [original URL](https://academy.fpblock.com/blog/2017/12/building-haskell-apps-with-docker/) (offline), [Wayback Machine copy](https://web.archive.org/web/20250512143808/https://academy.fpblock.com/blog/2017/12/building-haskell-apps-with-docker/).*

In this blog post we will show an example of how we can use Docker to build [Haskell](https://web.archive.org/web/2025/https://academy.fpblock.com/haskell) applications which we then ship inside Docker images.

We will observe two cases. First, we will explore the case of developing on the same Linux distro that we are using for deployment (eg. FROM ubuntu:16.04), and then we will observe the case where we are not developing on a Linux distro but are still targeting Linux for deployment.

If you are interested to know about [Stack's native docker support](https://web.archive.org/web/2025/https://academy.fpblock.com/blog/2017/12/announcing-stack-1.6.1-release) and the `stack image container` command we will go over that method as well at the end of the post.

## Building and deploying on the same OS/Distro

If we are building the Haskell application on the same Linux distro that we are using for deployment (in this case a Docker image), then it simplifies things quite a bit.

In this scenario we are able to build our Haskell application locally; using `stack` just like we would normally do; and then just embed the compiled binary into the Docker image.

Let's look at the Makefile we will be using, specifically the build target:

``` text
## Build binary and docker images
build:
    @stack build
    @BINARY_PATH=${BINARY_PATH_RELATIVE} docker-compose build
```

  

As we can see we are first building the binary locally using `stack build` and then invoking `docker-compose build` that will build the final docker image using `docker-compose` and the provided `Dockerfile`.

The `docker-compose` file looks like this:

``` text
version: '2'
services:
  myapp:
    build:
      context: .
      args:
        - BINARY_PATH
    image: fpco/myapp
    command: /opt/myapp/myapp
```

As we can see from the `docker-compose` file we are passing in a "build argument" to the Docker build process. Specifically, we are passing in the relative location of the app binary located in `.stack-work/path/to/myapp`.  Let's look at the `Dockerfile` to see how this build argument is used.  
  

``` text
FROM ubuntu:16.04
RUN mkdir -p /opt/myapp/
ARG BINARY_PATH
WORKDIR /opt/myapp
RUN apt-get update && apt-get install -y \
  ca-certificates \
  libgmp-dev
COPY "$BINARY_PATH" /opt/myapp
COPY static /opt/myapp
COPY config /opt/myapp/config
CMD ["/opt/myapp/myapp"]
```

In the Dockerfile we are simply copying `.stack-work/path/to/myapp` into the desired location inside the Dockerfile.

**NOTE**: In this example we have to make to sure to `apt-get install` any libraries that our application might require since the binary that we compiled is not statically linked.

## Building on a different OS/Distro

If we are developing on a machine that has a different OS or distro than that which we are deploying to, things get a little more complex, since we are trying to embed dynamically linked libraries into the Docker image. Specifically, we now have to compile our binary inside a Docker container rather than on the host machine.

Previously this was done done one of 2 ways.

1.  Bundling in all the build time dependencies into the final production docker image
2.  Splitting the build process into `Dockerfile.build` (that contains all the build time dependencies) and `Dockerfile` which only has the runtime dependencies and the final binary. This was a rather clunky process that required a helper shell script that would first build the first Docker image. Then it would start a container from that Docker image, fetch the compiled binary, start the second container, embed the binary into it and finally commit it as an image. You can read more about this [in the Docker documentation](https://docs.docker.com/engine/userguide/eng-image/multistage-build/#before-multi-stage-builds).

Since then, Docker has implemented something called [multi stage builds](https://docs.docker.com/engine/userguide/eng-image/multistage-build/#use-multi-stage-builds)  that simplifies and automates this process.  The benefit of this is approach is that we don't bloat our production images with build tools and build requirements, keeping our image size small.

### Docker multi stage builds

In this scenario our `Dockerfile` looks like this:

``` text
FROM fpco/stack-build:lts-9.9 as build
RUN mkdir /opt/build
COPY . /opt/build
RUN cd /opt/build && stack build --system-ghc
FROM ubuntu:16.04
RUN mkdir -p /opt/myapp
ARG BINARY_PATH
WORKDIR /opt/myapp
RUN apt-get update && apt-get install -y \
  ca-certificates \
  libgmp-dev
# NOTICE THIS LINE
COPY --from=build /opt/build/.stack-work/install/x86_64-linux/lts-9.9/8.0.2/bin .
COPY static /opt/myapp
COPY config /opt/myapp/config
CMD ["/opt/myapp/myapp"]
```

In the Dockerfile we first build our app, making use of the `fpco/stack-build:lts-9.9` upstream image. After we have built the image, we have another `FROM` block that uses the same base image as fpco/stack-build, where we copy the binary from the previous build. This allows us to only ship the final binary, without any build dependencies.

### CAVEATS

The main concern with the multi stage build example above is that we are not re-using any of Stack's cache capabilities. Instead, we are recompiling the entire project from scratch every time. This is only an issue for local development. For CI, we likely want to have a clean slate on every build anyway.

### Using "stack image container"

Stack provides a built in way to build docker images with our app's executables baked in. While this support was available before Docker introduced multi staged builds, it is a bit less flexible compared to the above described methods. However, it requires far less familiarity with docker and should therefore be easier to get started with for most people.

First let's look at the needed changes to stack.yaml that we copied to `stack-native.yaml`

``` text
docker:
  enable: true
image:
  container:
    base: "fpco/myapp-base"
    name: "fpco/myapp"
    add:
      static/: /opt/app
      config/: /opt/app/config
```

As we can see we're instructing stack to build our executables using docker (which is needed if you're building on a non-Linux platform like OSX or Windows) and then we specify some metadata about the container we want stack to build for us.

We specify the base image, the name of the resulting image and local directories which we have to add to the resulting image. Stack will add the executable for us automatically.

Let's look at our `Dockerfile.base` which we will use to build our base image.

``` text
FROM ubuntu:16:04
RUN mkdir -p /opt/app
WORKDIR /opt/app
RUN apt-get update && apt-get install -y \
  ca-certificates \
  libgmp-dev
```

As we can see it's not much different from our previous Dockerfile, except for the part about copying the resulting binary since stack will take of that for us.

We can build the image using `make build-base`. And then to build our resulting image we run `make build-stack-native`.

The above make targets look like this:

``` text
## Builds base image used for `stack image container`
build-base:
    @docker build -t fpco/myapp-base -f Dockerfile.base .

## Builds app using stack-native.yaml
build-stack-native: build-base
    @stack --stack-yaml stack-native.yaml build
    @stack --stack-yaml stack-native.yaml image container
```

Now to test our image we can run `make run-stack-native` which looks like this:

``` text
## Run container built by `stack image container`
run-stack-native:
    @docker run -p 3000:3000 -it -w /opt/app \ 
    ${IMAGE_NAME} myapp
```

You can read more about `stack image container` [in the Stack documentation](https://docs.haskellstack.org/en/stable/yaml_configuration/#image).

## Conclusion

In this post we've demonstrated how to build Haskell applications using Docker multi stage builds to produce Docker images without the unnecessary bloat of build dependencies. We also shown an alternative approach using `stack image container` which produces similarly small docker images but offers a bit less control.

Depending on your project needs you might prefer one method over the other.

The code for the above sample application can be found [on Github](https://github.com/fpco/haskell-multi-docker-example), and contains bits about process management and permission handling that have been omitted from this post for brevity.

## Suggested Reading

If you liked this post you would also like:

- [How Stack can use Docker under the hood](https://web.archive.org/web/2025/https://academy.fpblock.com/blog/2015/08/stack-docker)
- [Dockerizing your App](https://web.archive.org/web/2025/https://academy.fpblock.com/pricing/dockerizing-your-app)
- [Immutability, Docker, and Haskell's ST Type](../immutability-docker-haskells-st-type/)
{% endraw %}
