---
layout: post
title: Load Testing cowboy 2.0.0-rc.1
tags: Elixir Erlang HTTP/2 Performance
hash: post-2017-08-20-ac796fcf
---

Let's load test [cowboy 2.0.0-rc.1](https://github.com/ninenines/cowboy/releases/tag/2.0.0-rc.1) and see how it compares to [cowboy 1.1.2](https://github.com/ninenines/cowboy/releases/tag/1.1.2)!

## Setup

The plan is to use [h2load](https://nghttp2.org/documentation/h2load-howto.html) and record the current requests per second while also measuring scheduler utilization.

Since h2load didn't support this at the time of writing, there is a custom version available at [potatosalad/nghttp2@elixirconf2017](https://github.com/potatosalad/nghttp2/tree/elixirconf2017) which supports printing the current requests per second for a given interval.

Let's setup the two versions of cowboy we're going to test:

1. [cowboy 1.1.2](https://github.com/ninenines/cowboy/releases/tag/1.1.2) &mdash; released 2017-02-06
2. [cowboy 2.0.0-rc.1](https://github.com/ninenines/cowboy/releases/tag/2.0.0-rc.1) &mdash; released 2017-07-24

*Note:* This is not a perfectly fair comparison, as cowboy 1.x is HTTP/1.1 only, while cowboy 2.x supports HTTP/2.

### cowboy 1.1.2

```elixir
:cowboy.start_http(Contention.Handler.HTTP, 100, [ port: 29593 ], [
  env: [
    dispatch: :cowboy_router.compile([{:_, [{:_, Contention.Handler, []}]}])
  ]
])
```

```elixir
defmodule Contention.Handler do
  @behaviour :cowboy_http_handler

  def init(_transport, req, opts) do
    {:ok, req, opts}
  end

  def handle(req, state) do
    {:ok, req} =
      :cowboy_req.reply(200, [
        {"content-type", "text/plain"}
      ], "Hello world!", req)
    {:ok, req, state}
  end

  def terminate(_reason, _req, _state) do
    :ok
  end
end
```

### cowboy 2.0.0-rc.1

##### [`cowboy_handler`](https://ninenines.eu/docs/en/cowboy/2.0/manual/cowboy_handler/) behaviour

```elixir
:cowboy.start_clear(Contention.Handler.HTTP, [ port: 29593 ], %{
  env: %{
    dispatch: :cowboy_router.compile([{:_, [{:_, Contention.Handler, []}]}])
  }
})
```

```elixir
defmodule Contention.Handler do
  @behaviour :cowboy_handler

  def init(req, opts) do
    req =
      :cowboy_req.reply(200, %{
        "content-type" => "text/plain"
      }, "Hello world!", req)
    {:ok, req, opts}
  end
end
```

##### [`cowboy_stream`](https://ninenines.eu/docs/en/cowboy/2.0/manual/cowboy_stream/) behaviour

```elixir
:cowboy.start_clear(Contention.Handler.HTTP, [ port: 29593 ], %{
  env: %{
    stream_handlers: [ Contention.StreamHandler ]
  }
})
```

```elixir
defmodule Contention.StreamHandler do
  @behaviour :cowboy_stream

  def init(_streamid, _req, _opts) do
    commands = [
      {:headers, 200, %{"content-type" => "text/plain"}},
      {:data, :fin, "Hello world!"},
      :stop
    ]
    {commands, nil}
  end

  # ...
end
```

cowboy 1.x was tested with the following command:

```bash
h2load \
--h1 \
--duration=300 \
--warm-up-time=1s \
--clients=100 \
--requests=0 \
'http://127.0.0.1:29594/'
```

cowboy 2.x was tested with the following command:

```bash
h2load \
--duration=300 \
--warm-up-time=1s \
--clients=100 \
--max-concurrent-streams=10 \
--requests=0 \
--window-bits=16 \
--connection-window-bits=16 \
'http://127.0.0.1:29594/'
```

The test script used is available here:

* [priv/cowboy2/h2load.escript](https://github.com/potatosalad/elixirconf2017/blob/82d2c04338a3b273b6cdb8375d6cc2df4d80f7fa/apps/contention/priv/cowboy2/h2load.escript)

## Results

First, let's test cowboy 1.x using h2load in HTTP/1.1 mode.

[![cowboy-1.1.2.1.svg]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2.1.svg)]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2.1.svg)

Not bad, an average of ~20k req/s and maximum of ~40k req/s.

Second, let's test our cowboy 2.x handler using h2load in HTTP/2 mode.

[![cowboy-1.1.2-vs-cowboy-2.0.0-rc.1.a.svg]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2-vs-cowboy-2.0.0-rc.1.a.svg)]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2-vs-cowboy-2.0.0-rc.1.a.svg)

We have a 2x performance gain with an average of ~40k req/s and maximum of ~70k req/s.

[Loïc Hoguin](https://github.com/essen), the author of cowboy, mentioned in [this issue](https://github.com/ninenines/cowboy/issues/1169) that using the [`cowboy_stream`](https://ninenines.eu/docs/en/cowboy/2.0/manual/cowboy_stream/) behaviour should provide a little extra performance, so let's test it.

[![cowboy-1.1.2-vs-cowboy-2.0.0-rc.1.b.svg]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2-vs-cowboy-2.0.0-rc.1.b.svg)]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2-vs-cowboy-2.0.0-rc.1.b.svg)

Loïc was right!  We gained a 1.5x increase over our handler test and a 3x increase over cowboy 1.x with an average of ~60k req/s and maximum of ~90k req/s.

A few months ago, I started a [very unstable experiment](https://github.com/potatosalad/erlang-h2o) to see if I could create a NIF library that Erlang could use to run a HTTP/2 server using [libh2o](https://github.com/h2o/h2o).

I succeeded in creating a _very_ unstable test setup that can actually have [a module](https://github.com/potatosalad/elixirconf2017/blob/82d2c04338a3b273b6cdb8375d6cc2df4d80f7fa/apps/contention/lib/contention/h2o/handler.ex) send responses back to requests received by libh2o.

[![cowboy-1.1.2-vs-cowboy-2.0.0-rc.1-vs-h2o-2.2.0.svg]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2-vs-cowboy-2.0.0-rc.1-vs-h2o-2.2.0.svg)]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2-vs-cowboy-2.0.0-rc.1-vs-h2o-2.2.0.svg)

The average of ~280k req/s and maximum of ~400k req/s is pretty consistent with [h2o's benchmark claims](https://h2o.examp1e.net/benchmarks.html).

In a future post, I will explore the causes of the differences.

## Scheduler Utilization

For the extra curious, below are the measured scheduler utilization graphs for each of the tests.

*Note:* My explanations below are currently in "guess"-form and are not based on any hard evidence.  I plan to explore the real reasons for theses numbers in a future post.

[![cowboy-1.1.2.0.svg]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2.0.svg)]({{ site.url }}/assets/{{ page.hash }}/cowboy-1.1.2.0.svg)

For the load test on cowboy 1.x, the schedulers are slightly under utilized.  I suspect this is primarily due to the HTTP/1.1 protocol itself where TCP connections are not used nearly as efficiently as in HTTP/2.  The extra time is probably spent waiting on I/O.

[![cowboy-2.0.0-rc.1-handler.0.svg]({{ site.url }}/assets/{{ page.hash }}/cowboy-2.0.0-rc.1-handler.0.svg)]({{ site.url }}/assets/{{ page.hash }}/cowboy-2.0.0-rc.1-handler.0.svg)

100% scheduler utilization for the duration of the tests.  This is what you might expect to see during a load test.

[![cowboy-2.0.0-rc.1-stream.0.svg]({{ site.url }}/assets/{{ page.hash }}/cowboy-2.0.0-rc.1-stream.0.svg)]({{ site.url }}/assets/{{ page.hash }}/cowboy-2.0.0-rc.1-stream.0.svg)

The stream handler in cowboy 2.x uses a single process per connection.  The previous test, however, uses a single process per stream.  Therefore, the extra 20% of overhead for the previous test may be due to process creation, scheduling, and garbage collection.

[![h2o-2.2.0.0.svg]({{ site.url }}/assets/{{ page.hash }}/h2o-2.2.0.0.svg)]({{ site.url }}/assets/{{ page.hash }}/h2o-2.2.0.0.svg)

The h2o implementation uses a single process per server.  As shown in the graph, only ~12% scheduler utilization is indicative of only 1 of the 8 normal schedulers being fully utilized.

The rest of the work is done by h2o in a single non-scheduler thread event loop.

In a separate implementation not shown here where I spawned a new process for every request (similar to the cowboy 2.x handler), the overall requests per second dropped to ~90k req/s, which is much closer to the performance of cowboy 2.x.

## Conclusions

cowboy 2.x is roughly 2-3x faster than cowboy 1.x based on the above load tests.

I am still curious, however, as to whether process-per-request alone is the primary cause for the performance degradation when compared to the ~15x faster results of the makeshift h2o NIF.
