---
layout: post
title: "Time-Out: Elixir State Machines versus Servers"
tags: Elixir Erlang gen_statem
hash: post-2017-10-13-ad9a120f
---

I love [`gen_statem`](http://erlang.org/doc/man/gen_statem.html) (and the Elixir wrapper [`gen_state_machine`](https://github.com/antipax/gen_state_machine)).

Prior to the addition of `gen_statem` in OTP 19, the decision of when to use [`gen_server`](http://erlang.org/doc/man/gen_server.html) and [`gen_fsm`](http://erlang.org/doc/man/gen_fsm.html) was a carefully considered one.  In the vast majority of my use cases, a simple `gen_server` was the easiest solution; even if it technically was behaving as a state machine.

Initially, I thought of `gen_statem` only as a `gen_fsm` replacement and assumed I would rarely need it over using `gen_server`.

Lately, however, I find myself reaching for `gen_statem` to solve problems that I would have previously solved with `gen_server`.

**TL;DR** Try using [`gen_statem`](http://erlang.org/doc/man/gen_statem.html) instead of [`gen_server`](http://erlang.org/doc/man/gen_server.html) (especially if you plan on using [`:erlang.start_timer/3`](http://erlang.org/doc/man/erlang.html#start_timer-3)).  You may find it's a better fit than you think.

## Comparison

Quick comparison between `gen_server` and `gen_statem`, using the `Stack` example in Elixir's [`GenServer`](https://hexdocs.pm/elixir/GenServer.html) documentation.

*Note:* I'm going to use the actual Erlang behaviours instead of Elixir's [`GenServer`](https://hexdocs.pm/elixir/GenServer.html) and [`GenStateMachine`](https://github.com/antipax/gen_state_machine) so that more details are present.

```elixir
defmodule StackServer do
  @behaviour :gen_server

  @impl :gen_server
  def init(data) do
    {:ok, data}
  end

  @impl :gen_server
  def handle_call(:pop, _from, [head | tail]) do
    {:reply, head, tail}
  end

  @impl :gen_server
  def handle_cast({:push, item}, data) do
    {:noreply, [item | data]}
  end
end

# Start the server
{:ok, pid} = :gen_server.start_link(StackServer, [:hello], [])

# This is the client
:gen_server.call(pid, :pop)
#=> :hello

:gen_server.cast(pid, {:push, :world})
#=> :ok

:gen_server.call(pid, :pop)
#=> :world
```

Pretty simple, right?  Let's see how `gen_statem` compares.

*Note:* OTP's `gen_statem` has 2 major modes of operation, but for the purpose of this article, only `:handle_event_function` will be covered.

```elixir
defmodule StackStateMachine do
  @behaviour :gen_statem

  @impl :gen_statem
  def callback_mode() do
    :handle_event_function
  end

  @impl :gen_statem
  def init(data) do
    {:ok, nil, data}
  end

  @impl :gen_statem
  def handle_event({:call, from}, :pop, _state, [head | tail]) do
    actions = [{:reply, from, head}]
    {:keep_state, tail, actions}
  end
  def handle_event(:cast, {:push, item}, _state, data) do
    {:keep_state, [item | data]}
  end
end

# Start the server
{:ok, pid} = :gen_statem.start_link(StackStateMachine, [:hello], [])

# This is the client
:gen_statem.call(pid, :pop)
#=> :hello

:gen_statem.cast(pid, {:push, :world})
#=> :ok

:gen_statem.call(pid, :pop)
#=> :world
```

In this example, the state is `nil` and is not used.

You'll notice that instead of a `{:reply, _, _}` callback tuple as used in `gen_server`, replies are sent by passing "actions" as the last element of the state callback tuple.  Replies (one or more) can be sent at any time and not necessarily as a synchronous operation resulting from a call event.

Functionally, both examples are equivalent and some may argue that the more concise `gen_server` implementation is objectively better than the `gen_statem` version.  However, `gen_statem` really begins to shine, in my opinion, as more and more complexity is added to the implementation.

For example:

* Should elements of the stack expire over time?
* Should certain elements be dropped after a limit has been reached?
* If the stack is empty, should the call block until a new item has been pushed?
* Should the call queue also expire over time?
* What if all of the above is desired?

## Time-Outs for Free

The time-out actions included in `gen_statem` are probably my favorite feature, but they took a while for me to understand.

The [`gen_statem` documentation](http://erlang.org/doc/design_principles/statem.html) is excellent, but fairly information-dense and can be difficult to initially digest for some (myself included).  It took several reads for me to understand just how powerful time-out actions could be.

There are 3 built-in types of time-out actions&hellip;

| Time-Out | Cancellation | Cancelled When&hellip; |
| -------- | ------------ | ---------------------- |
| Event    | Automatic    | Any event handled      |
| State    | Automatic/Manual | Reset to `:infinity` or state changes |
| Generic  | Manual       | Reset to `:infinity`     |

The basic types and syntax for time-outs are as follows:

```elixir
# Types
@type event_type()    :: :timeout
@type state_type()    :: :state_timeout
@type generic_type()  :: {:timeout, term()}

@type timeout_type()  :: event_type() | state_type() | generic_type()
@type timeout_time()  :: :infinity | non_neg_integer()
@type timeout_term()  :: term()

@type timeout_tuple() :: {timeout_type(), timeout_time(), timeout_term()}

# Event Time-Out Example
actions = [{:timeout, 1000, :any}]
@spec handle_event(:timeout, :any, state :: term(), data :: term())

# State Time-Out Example
actions = [{:state_timeout, 1000, :any}]
@spec handle_event(:state_timeout, :any, state :: term(), data :: term())

# Generic Time-Out Example
actions = [{{'{{'}}:timeout, :any}, 1000, :any}]
@spec handle_event({:timeout, :any}, :any, state :: term(), data :: term())
```

To "reset to `:infinity`" for state and generic time-outs, you would simply do&hellip;

```elixir
# State Time-Out Cancellation
actions = [{:state_timeout, :infinity, nil}]
# Generic Time-Out Cancellation
actions = [{{'{{'}}:timeout, :any}, :infinity, nil}]
```

### Event Time-Out

I rarely use event time-outs due to their volatility.  _Any_ event will cancel them.

```elixir
## Event Time-Out: Stop after 1 second example ##

@impl :gen_statem
def init(_) do
  actions = [{:timeout, 1000, :stop_after_one_second}]
  {:ok, nil, nil, actions}
end

@impl :gen_statem
# Event Timeout Events
def handle_event(:timeout, :stop_after_one_second, _state, _data) do
  :stop
end
```

There is no way to manually cancel an event time-out.

Any event handled effectively cancels the time-out&hellip;

```elixir
## Event Time-Out: Automatic cancellation example ##

@impl :gen_statem
def init(_) do
  # Send a message to myself after 0.5 seconds
  _ = :erlang.send_after(500, :erlang.self(), :cancel_event_timeout)
  actions = [{:timeout, 1000, :stop_after_one_second}]
  {:ok, nil, nil, actions}
end

@impl :gen_statem
# Info Events
def handle_event(:info, :cancel_event_timeout, _state, _data) do
  :keep_state_and_data
end
```

### State Time-Out

State time-outs, however, survive any event that doesn't reset them or change the state.

For example: a connection time-out for a socket.  I might set the state to `:connecting` and start the connection process which consists of many individual events.  If the state is still `:connecting` after 5 seconds, I might want to change the state to `:disconnected` and retry the connection process after waiting for a few seconds with another state time-out.  If it's successful, I could change the state to `:connected`, which would cancel any existing state time-outs.

```elixir
## State Time-Out: Stop after 1 second example ##

@impl :gen_statem
def init(_) do
  actions = [{:state_timeout, 1000, :stop_after_one_second}]
  {:ok, nil, nil, actions}
end

@impl :gen_statem
# State Timeout Events
def handle_event(:state_timeout, :stop_after_one_second, _state, _data) do
  :stop
end
```

There are two ways to cancel a state time-out.

First, setting the state time-out to `:infinity` will cancel the time-out&hellip;

```elixir
## State Time-Out: Manual cancellation example ##

@impl :gen_statem
def init(_) do
  # Send a message to myself after 0.5 seconds
  _ = :erlang.send_after(500, :erlang.self(), :cancel_state_timeout)
  actions = [{:state_timeout, 1000, :stop_after_one_second}]
  {:ok, nil, nil, actions}
end

@impl :gen_statem
# Info Events
def handle_event(:info, :cancel_state_timeout, _state, _data) do
  actions = [{:state_timeout, :infinity, nil}]
  {:keep_state_and_data, actions}
end
```

Second, changing the state will cancel the time-out&hellip;

```elixir
## State Time-Out: Automatic cancellation example ##

@impl :gen_statem
def init(_) do
  # Send a message to myself after 0.5 seconds
  _ = :erlang.send_after(500, :erlang.self(), :cancel_state_timeout)
  actions = [{:state_timeout, 1000, :stop_after_one_second}]
  {:ok, :unstable, nil, actions}
end

@impl :gen_statem
# Info Events
def handle_event(:info, :cancel_state_timeout, :unstable, data) do
  {:next_state, :stable, data}
end
```

Notice that the initial state was `:unstable` and changing to the `:stable` state cancelled the state time-out.

Any other events handled that do not change the state or reset the state time-out will result in a `:state_timeout` event.

### Generic Time-Out

Generic time-outs survive any events or state changes and must be manually reset to `:infinity` in order to be cancelled.

For example: a request time-out, building on top of the socket connection time-out from earlier.  At the start of the request, I might set a generic time-out for 30 seconds.  I can then try multiple times to connect and reconnect until the request has actually been sent, but if it is still unsuccessful after 30 seconds, it's time to cancel the request.

```elixir
## Generic Time-Out: Stop after 1 second example ##

@impl :gen_statem
def init(_) do
  actions = [{{'{{'}}:timeout, :generic}, 1000, :stop_after_one_second}]
  {:ok, nil, nil, actions}
end

@impl :gen_statem
# Generic Timeout Events
def handle_event({:timeout, :generic}, :stop_after_one_second, _state, _data) do
  :stop
end
```

The only way to cancel a generic time-out is by setting it to `:infinity` in the same way that state time-outs may be cancelled&hellip;

```elixir
## Generic Time-Out: Manual cancellation example ##

@impl :gen_statem
def init(_) do
  # Send a message to myself after 0.5 seconds
  _ = :erlang.send_after(500, :erlang.self(), :cancel_generic_timeout)
  actions = [{{'{{'}}:timeout, :generic}, 1000, :stop_after_one_second}]
  {:ok, nil, nil, actions}
end

@impl :gen_statem
# Info Events
def handle_event(:info, :cancel_generic_timeout, _state, _data) do
  actions = [{{'{{'}}:timeout, :generic}, :infinity, nil}]
  {:keep_state_and_data, actions}
end
```

## My Favorite Mode

My favorite callback mode for `gen_statem` is actually `[:handle_event_function, :state_enter]`, which I would recommend for anyone who is trying to start using `gen_statem` for problem solving.

The main benefits of this callback mode are:

1. **Complex State**

   Your state can technically be any term (not just an atom), which opens up some fairly complex possibilities on what can be done with your state machine.

   For example, instead of just `:connected` you might have state as a tuple `{:connected, :heartbeat}` or `{:connected, :degraded}`.  You can then pattern match on the state to group together events common to the `{:connected, _}` state.
2. **State Enter Events**

   By default, state enter events (or transition events) are not emitted by `gen_statem`, but I have found that they can be very useful to help reduce code complexity.  This is especially noticeable with state time-outs that need to be started immediately after changing state.

   For example:

   ```elixir
   handle_event(:enter, :disconnected, :disconnected, _data)
   ```

   This means that my `init/1` callback function returned something like `{:ok, :disconnected, data}`, so `:disconnected` is my intial state.

   I might return a `{:state_timeout, 0, :connect}` to immediately attempt a connection and transition to the `:connecting` state.  If that fails, I might transition back to the `:disconnected` state, which would emit:

   ```elixir
   handle_event(:enter, :connecting, :disconnected, _data)
   ```

   In this case, I might want to wait for 1 second by returning `{:state_timeout, 1000, :connect}` to delay reconnecting.

   Typically, I tend to combine these two cases into a single handler:

   ```elixir
   def handle_event(:enter, old_state, :disconnected, _data) do
     actions =
       if old_state == :disconnected do
         [{:state_timeout, 0, :connect}]
       else
         [{:state_timeout, 1000, :connect}]
       end
     {:keep_state_and_data, actions}
   end
   ```

In general, I have found the aforementioned callback mode to be the most versatile and useful to better solve otherwise complicated problems.

Hopefully, [`GenStateMachine`](https://hexdocs.pm/gen_state_machine/GenStateMachine.html) will one day be part of Elixir core and you'll be able to write the following without any external dependencies:

```elixir
defmodule MyStateMachine do
  use GenStateMachine, callback_mode: [:handle_event_function, :state_enter]

  # ...
end
```

Until then, you can use the [`gen_statem`](http://erlang.org/doc/man/gen_statem.html) behaviour directly or add [`gen_state_machine`](https://hex.pm/packages/gen_state_machine) as a dependency to your mix file.
