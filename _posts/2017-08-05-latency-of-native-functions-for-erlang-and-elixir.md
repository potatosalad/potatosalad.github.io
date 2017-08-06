---
layout: post
title: Latency of Native Functions for Erlang and Elixir
tags: C Elixir Erlang Performance
hash: post-2017-08-05-b55da7d7
---

Erlang and C first appeared within 14 years<sup>[*](#footnote-{{ page.hash }}-1)</sup> of one another.

In the 30+ years together both languages have gone through many changes.  The methods of interoperability have also changed with time.

There are now *several* methods to integrate native functions with Erlang or Elixir code.

My goal in writing this article is to explore these methods and measure latency from the perspective of the Erlang VM.

<small><sup><a name="footnote-{{ page.hash }}-1">*</a></sup> Based on C first appearing in 1972 and Erlang first appearing in 1986.</small>

<acronym title="Too long; didn't read">**TL;DR**</acronym> Need a native function (C, C++, Rust, etc.) integrated with Erlang or Elixir that is isolation, complexity, or latency sensitive?

Having a hard time deciding whether you should write a node, port, port driver, or NIF?

Use this potentially helpful and fairly unscientific table to help you decide:

<table>
  <tr>
    <th>Type</th>
    <th>Isolation</th>
    <th>Complexity</th>
    <th>Latency</th>
  </tr>
  <tr>
    <td><tt>Node</tt></td>
    <td style="background-color: #cfc;"><tt>Network</tt></td>
    <td style="background-color: #fcc;"><tt>Highest</tt></td>
    <td style="background-color: #fcc;"><tt>Highest</tt></td>
  </tr>
  <tr>
    <td><tt>Port</tt></td>
    <td style="background-color: #ffc;"><tt>Process</tt></td>
    <td style="background-color: #fcc;"><tt>High</tt></td>
    <td style="background-color: #fcc;"><tt>High</tt></td>
  </tr>
  <tr>
    <td><tt>Port Driver</tt></td>
    <td style="background-color: #fcc;"><tt>Shared</tt></td>
    <td style="background-color: #ffc;"><tt>Low</tt></td>
    <td style="background-color: #ffc;"><tt>Low</tt></td>
  </tr>
  <tr>
    <td><tt>NIF</tt></td>
    <td style="background-color: #fcc;"><tt>Shared</tt></td>
    <td style="background-color: #cfc;"><tt>Lowest</tt></td>
    <td style="background-color: #cfc;"><tt>Lowest</tt></td>
  </tr>
</table>

### Overview

Erlang has an excellent [Interoperability Tutorial User's Guide](http://erlang.org/doc/tutorial/users_guide.html) that provides examples for the different ways of integrating a program written in Erlang or Elixir with a program written in another programming language.

The simplest test I could think of to measure the latency was to round trip an Erlang term from the Erlang VM to the native function and back again.

However, the term would need to be large enough to hopefully expose any weaknesses for a given implementation.

Following the guidance from Erlang's documentation, I implemented slightly more complex examples of the following methods of interoperability:

1. [C Node](http://erlang.org/doc/tutorial/cnode.html)
   * [C source](https://github.com/potatosalad/elixirconf2017/tree/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/c_node)
   * [Elixir source](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/lib/latency/c_node.ex)
   * [Erlang source](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/src/latency_c_node.erl)
2. [NIF](http://erlang.org/doc/tutorial/nif.html)
   * [C source](https://github.com/potatosalad/elixirconf2017/tree/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/nif)
   * [Elixir source](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/lib/latency/nif.ex)
   * [Erlang source](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/src/latency_nif.erl)
3. [Port Driver](http://erlang.org/doc/tutorial/c_portdriver.html)
   * [C source](https://github.com/potatosalad/elixirconf2017/tree/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/drv)
   * [Elixir source](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/lib/latency/port_driver.ex)
   * [Erlang source](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/src/latency_drv.erl)
4. [Port](http://erlang.org/doc/tutorial/c_port.html)
   * [C source](https://github.com/potatosalad/elixirconf2017/tree/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/port)
   * [Elixir source](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/lib/latency/port.ex)

The NIF and Port Driver implementations have a few different internal strategies for additional comparison (like Dirty NIF and `iodata()` based port output).

Certain methods should have higher levels of latency based on serialization and isolation requirements.  For example, a C Node requires serialization of the entire term in order to pass it back and forth over a TCP connection.  A NIF, by comparison, requires no serialization and operates on the term itself in memory.

Each implementation was tested with a ~64KB binary full of 1's as the sole element of a 1-arity tuple for 100,000 iterations.  The measured elapsed time for each method were then fed into [HDR Histogram](http://hdrhistogram.org/) for latency analysis.

In other words, I essentially did the following on the [`Latency`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/lib/latency.ex) module:

```elixir
term = {:binary.copy(<<1>>, 1024 * 64)}
Latency.compare(term, 100_000)
```

### C Node/Port versus Port Driver/NIF

First, let's compare the 4 major types of native functions:

[![chart1]({{ site.url }}/assets/{{ page.hash }}/chart1.png)]({{ site.url }}/assets/{{ page.hash }}/chart1.png)

Comparison of results using the order of magnitude of average latency:

<table>
  <tr>
    <th>Type</th>
    <th>Isolation</th>
    <th>Latency</th>
  </tr>
  <tr>
    <td><tt>Node</tt></td>
    <td style="background-color: #cfc;"><tt>Network</tt></td>
    <td style="background-color: #fcc; text-align: right;"><tt>~100μs</tt></td>
  </tr>
  <tr>
    <td><tt>Port</tt></td>
    <td style="background-color: #ffc;"><tt>Process</tt></td>
    <td style="background-color: #fcc; text-align: right;"><tt>~100μs</tt></td>
  </tr>
  <tr>
    <td><tt>Port Driver</tt></td>
    <td style="background-color: #fcc;"><tt>Shared</tt></td>
    <td style="background-color: #ffc; text-align: right;"><tt>~10μs</tt></td>
  </tr>
  <tr>
    <td><tt>NIF</tt></td>
    <td style="background-color: #fcc;"><tt>Shared</tt></td>
    <td style="background-color: #cfc; text-align: right;"><tt>~0.1μs</tt></td>
  </tr>
</table>

These tests were run on the same machine, so there's little surpise that the Node and Port latencies are essentially just benchmarking pipe speeds of the operating system itself (in this case macOS 10.12).  Were the Erlang and C nodes located on different machines, I would expect the latency to be higher for the Node test.

It's also worth noting that C Nodes and Ports are the most isolated form of native function calling from the Erlang VM.  This means that a bug in the C code that causes the C Node or Port to crash will not take down the entire VM.

### Port Driver

Port drivers, under certain circumstances, can be roughly as fast as a NIF.  This is especially true for very small terms or when the majority of the work performed is I/O or binary-based.

The documentation for [`driver_entry`](http://erlang.org/doc/man/driver_entry.html) mentions that [`erlang:port_control/3`](http://erlang.org/doc/man/erlang.html#port_control-3) should be the fastest way to call a native function.  This seems to be true for very small terms, but larger terms cause the performance to be almost identical to [`erlang:port_call/3`](http://erlang.org/doc/man/erlang.html#port_call-3).  Converting terms to the [External Term Format](http://erlang.org/doc/apps/erts/erl_ext_dist.html) and sending with [`erlang:port_command/3`](http://erlang.org/doc/man/erlang.html#port_command-3) (which in turn calls the [`outputv`](http://erlang.org/doc/man/driver_entry.html#outputv) callback) actually appears to have slightly less latency.

1. [`call`](http://erlang.org/doc/man/driver_entry.html#call) &mdash; [lines 61-70 of `latency_drv.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/drv/latency_drv.c#L61-L70)
2. [`control`](http://erlang.org/doc/man/driver_entry.html#control) &mdash; [lines 41-52 of `latency_drv.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/drv/latency_drv.c#L41-L52)
3. [`outputv`](http://erlang.org/doc/man/driver_entry.html#outputv) &mdash; [lines 54-59 of `latency_drv.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/drv/latency_drv.c#L54-L59)

[![chart2]({{ site.url }}/assets/{{ page.hash }}/chart2.png)]({{ site.url }}/assets/{{ page.hash }}/chart2.png)

Also worth noting is the type of data allowed to be sent to the Port Driver.  For example, [`erlang:port_call/3`](http://erlang.org/doc/man/erlang.html#port_call-3) allows terms to be sent, but internally converts them to the external term format.  The other types are similar to C Node and Port implementations and require any terms sent to first be converted.

<table>
  <tr>
    <th>Type</th>
    <th>Data Type</th>
    <th>Latency</th>
  </tr>
  <tr>
    <td><tt>call</tt></td>
    <td style="background-color: #cfc;"><tt>term()</tt></td>
    <td style="background-color: #ffc; text-align: right;"><tt>~15μs</tt></td>
  </tr>
  <tr>
    <td><tt>control</tt></td>
    <td style="background-color: #ffc;"><tt>iodata()</tt></td>
    <td style="background-color: #ffc; text-align: right;"><tt>~15μs</tt></td>
  </tr>
  <tr>
    <td><tt>outputv</tt></td>
    <td style="background-color: #ffc;"><tt>iodata()</tt></td>
    <td style="background-color: #cfc; text-align: right;"><tt>~10μs</tt></td>
  </tr>
</table>

### NIF

[Native Implemented Function (NIF)](http://erlang.org/doc/man/erl_nif.html) is a relatively recent addition to OTP and is the fastest way to call native functions.  However, a mis-behaving NIF can easily destabilize or crash the entire Erlang VM.

[Dirty NIF](http://erlang.org/doc/man/erl_nif.html#dirty_nifs) and Yielding (or Future) NIF with [`enif_schedule_nif`](http://erlang.org/doc/man/erl_nif.html#enif_schedule_nif) are even more recent additions that help prevent blocking the Erlang VM schedulers during execution or (in the case of I/O) waiting.

1. Dirty CPU &mdash; [lines 20-24 of `latency_nif.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/nif/latency_nif.c#L20-L24)
2. Dirty I/O &mdash; [lines 26-30 of `latency_nif.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/nif/latency_nif.c#L26-L30)
2. Future &mdash; [lines 32-36 of `latency_nif.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/nif/latency_nif.c#L32-L36)
3. Normal &mdash; [lines 14-18 of `latency_nif.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/nif/latency_nif.c#L14-L18)

[![chart3]({{ site.url }}/assets/{{ page.hash }}/chart3.png)]({{ site.url }}/assets/{{ page.hash }}/chart3.png)

The Normal NIF call is the only one that doesn't have any sort of context switching involved.  The Yielding (or Future) NIF also doesn't involve much of a context switch as it yields control back to the same scheduler that dispatched the call.  Dirty NIF calls, however, result in a ~2μs context switch delay as the function gets enqueued on the dirty thread pool.

<table>
  <tr>
    <th>Type</th>
    <th>Context Switch</th>
    <th>Latency</th>
  </tr>
  <tr>
    <td><tt>Dirty CPU</tt></td>
    <td style="background-color: #ffc;"><tt>Thread Queue</tt></td>
    <td style="background-color: #ffc; text-align: right;"><tt>~2.0μs</tt></td>
  </tr>
  <tr>
    <td><tt>Dirty I/O</tt></td>
    <td style="background-color: #ffc;"><tt>Thread Queue</tt></td>
    <td style="background-color: #ffc; text-align: right;"><tt>~2.0μs</tt></td>
  </tr>
  <tr>
    <td><tt>Future</tt></td>
    <td style="background-color: #ffc;"><tt>Yield</tt></td>
    <td style="background-color: #cfc; text-align: right;"><tt>~0.5μs</tt></td>
  </tr>
  <tr>
    <td><tt>Normal</tt></td>
    <td style="background-color: #cfc;"><tt>None</tt></td>
    <td style="background-color: #cfc; text-align: right;"><tt>~0.1μs</tt></td>
  </tr>
</table>

Just for fun, I was curious about the latency differences between the new Dirty NIF functionality and the previous method of using a Threaded NIF or the Async NIF (or Thread Queue) by [Gregory Burd](https://github.com/gburd).

1. Thread New &mdash; [lines 38-72 of `latency_nif.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/nif/latency_nif.c#L38-L72)
2. Thread Queue &mdash; [lines 74-90 of `latency_nif.c`](https://github.com/potatosalad/elixirconf2017/blob/555763cd7505bf1ffcaa7c7099161a9e74c63a3f/apps/latency/c_src/nif/latency_nif.c#L74-L90)

[![chart4]({{ site.url }}/assets/{{ page.hash }}/chart4.png)]({{ site.url }}/assets/{{ page.hash }}/chart4.png)

As it turns out, creating and destroying a thread for each and every call is unwise for a few reasons; poor latency being one of them.  The Async NIF (or Thread Queue) has the advantage of providing a pool per NIF instead of having to share the global thread pool with other NIFs.  However, Dirty NIF thread pools are definitely more optimized and are typically 4x faster than the Async NIF implementation.

<table>
  <tr>
    <th>Type</th>
    <th>Pool Type</th>
    <th>Latency</th>
  </tr>
  <tr>
    <td><tt>Thread New</tt></td>
    <td style="background-color: #fcc;"><tt>None</tt></td>
    <td style="background-color: #fcc; text-align: right;"><tt>~50.0μs</tt></td>
  </tr>
  <tr>
    <td><tt>Thread Queue</tt></td>
    <td style="background-color: #ffc;"><tt>NIF</tt></td>
    <td style="background-color: #ffc; text-align: right;"><tt>~8.0μs</tt></td>
  </tr>
  <tr>
    <td><tt>Dirty CPU</tt></td>
    <td style="background-color: #ffc;"><tt>Global</tt></td>
    <td style="background-color: #cfc; text-align: right;"><tt>~2.0μs</tt></td>
  </tr>
  <tr>
    <td><tt>Dirty I/O</tt></td>
    <td style="background-color: #ffc;"><tt>Global</tt></td>
    <td style="background-color: #cfc; text-align: right;"><tt>~2.0μs</tt></td>
  </tr>
</table>

### Conclusions

If isolation from/protection of the Erlang VM is highest priority, a C Node or Port are your best options.  If your primary concern is low latency or low complexity, using a NIF for your native function is your best option.

*As a side note:* For very specific I/O operations, a Port Driver still may be the best option.  OTP-20 has the new [`enif_select`](http://erlang.org/doc/man/erl_nif.html#enif_select), which is starting to transition some of those I/O benefits to the NIF world, so this may not be true statement in the near future.
