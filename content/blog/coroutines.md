---
title: "C++ Coroutines: The Machinery Behind the Abstraction"
date: 2026-07-01
slug: "coroutines"
tags: ["c++", "coroutines"]
---

I was flummoxed the first time I encountered coroutines in C++.
As someone who has worked with coroutines in other languages, I had a grasp of the execution model and the problems coroutines are meant to solve, but the C++ syntax looked wholly unlike anything I'd seen before, and as usual, the reference documentation was written for someone who already knows what the topic is and understands the code.
When I searched around for good tutorials and explanations, I mostly found explanations of what coroutines are and why they are important, but less of a focus on understanding the nitty gritty of the building blocks in C++, which is what I was looking for.
The key to unlocking my understanding was recognizing that C++ provides the bare mechanisms for coroutines, but it does not prescribe any associated programming model whatsoever.
The definitions of things like tasks, schedulers, asynchronous execution, and so on are all left to the library implementer, which is a very different approach than other languages take.

I wanted to make sure I actually understood what each of the relevant pieces were, what the terminology was that was being used, and most importantly, what the actual suspension points were in the code, so I put together some simple examples to figure that out, and I wanted to share them here.
This blog is not going to teach you anything about coroutines themselves, since there are plenty of great tutorials out there for that.
The focus here is on the various types and hooks into asynchronous execution machinery that the compiler generates and how they fit together.

# A first working coroutine

The three magic keywords in C++ are `co_await`, `co_return`, and `co_yield`.
Any function that uses one of those keywords is a coroutine.

Take this basic example of a normal C++ function:
```cpp
void function() {}
```

To turn this into a coroutine, the first step is adding the keyword `co_return`:

```cpp
void coroutine() { co_return; }
```

This keyword immediately tells the compiler that this function is a **coroutine function**, and it will generate the machinery to make it so.
However, the compiler will complain about the code written above

```bash
error: coroutines require a traits template; cannot find 'std::coroutine_traits'
note: perhaps '#include <coroutine>' is missing
```

That immediately tells you that coroutines require the header `<coroutine>`, so we can fix that by adding the include.
The next error is much more interesting:

```bash
error: unable to find the promise type for this coroutine
```

This is the first real hint about how C++ coroutines work.
Coroutines expose flow control through their return types.
In other languages the return type is typically defined by the language.
For example, an `async def` function in Python returns a `coroutine`, and an `async fn` function in Rust returns a `Future`.
In C++, the return type is defined by the library implementer, which also means that the compiler will not automatically wrap the return value in a coroutine type.

To fix the error, we need to define a return type for our coroutine.
The return type is a struct that contains a nested `promise_type` struct.
The **promise type** is where the compiler will look for the hooks that it needs to generate the machinery for the coroutine.
This is a minimal implementation of a coroutine return type for a coroutine that does not return a value (a bare `co_return`).

```cpp
struct return_type {
    struct promise_type {
        return_type get_return_object() { return {}; }
        std::suspend_always initial_suspend() { printf("Initial suspend\n"); return {}; }
        std::suspend_never final_suspend() noexcept { printf("Final suspend\n"); return {}; }
        void unhandled_exception() { /* Never reached */ }
        void return_void() { printf("Return void\n"); }
    };
};

return_type coroutine() { printf("Coroutine\n"); co_return; }

int main() {
    auto task = coroutine();
    printf("Coroutine has finished executing.\n");
}
```

These are the minimal hooks that the compiler requires in this case:

- `get_return_object()` is called to produce the object returned to the caller. The compiler has already used the declared return type to find this promise type.
- `initial_suspend()` is called to determine whether the coroutine should suspend immediately after being called.
- `final_suspend()` is called to determine whether the coroutine should suspend immediately before returning.
- `unhandled_exception()` is called if an exception is thrown in the coroutine and not caught.
- `return_void()` is called when the coroutine returns without a value.

In this first example, the actual suspension points are determined by the return values of `initial_suspend()` and `final_suspend()`.
The behavior at the suspension points is determined by the returned objects, which must satisfy the **awaiter** interface.
We'll discuss the interface in more detail later, but for now focus on the two simple default implementations provided by the standard library shown above: `std::suspend_always` always suspends, and `std::suspend_never` never suspends.
The fact that `initial_suspend()` returns `std::suspend_always` means that the coroutine will suspend immediately after being called, so the above will, perhaps surprisingly, print:

```bash
Initial suspend
Coroutine has finished executing. <-- THIS IS A LIE
```

The calling of the coroutine hits the first suspension point at `initial_suspend()`, then stops execution and returns to the caller, so the coroutine has not actually executed yet.
This first example is intentionally incomplete: because the returned object does not store a coroutine handle, it has no way to resume or destroy a coroutine that suspends at `initial_suspend()`.
We'll fix that shortly.
If we instead change `initial_suspend()` to return `std::suspend_never`, then the coroutine will execute immediately, and the output will be the expected:

```bash
Initial suspend
Coroutine
Return void
Final suspend
Coroutine has finished executing.
```

Note that `final_suspend` runs after the return value is computed, but before the coroutine actually returns to the caller.

# The coroutine frame is a resource

Once we have a working coroutine, we can add a return value to it.
Doing this safely requires adding materially more complexity, so let's take a look at the full code for a coroutine that returns an `int`:

```cpp
struct return_type {
    struct promise_type {
        // Enable state-tracking at construction
        return_type get_return_object() {
            return return_type{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        std::suspend_always initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        void unhandled_exception() { exception = std::current_exception(); }
        // Store the value when returning
        void return_value(int value) { this->value = value; }

        int value{};
        std::exception_ptr exception;
    };

    ~return_type() { if (h_) { h_.destroy(); } }

    // done and resume expose the coroutine's state to the caller via the safe
    // return_type object
    bool done() const noexcept { return !h_ || h_.done(); }
    bool resume() {
        if (!done()) { h_.resume(); }
        return !done();
    }

    // Access the produced result
    int result() const {
        if (!h_) { throw std::runtime_error("Coroutine handle is null"); }
        if (!done()) { throw std::runtime_error("Coroutine not finished yet"); }
        if (h_.promise().exception) { std::rethrow_exception(h_.promise().exception); }
        return h_.promise().value;
    }

    return_type(const return_type&) = delete;
    return_type& operator=(const return_type&) = delete;

private:
    using handle_type = std::coroutine_handle<promise_type>;
    explicit return_type(handle_type h) : h_(h) {}
    handle_type h_;
};

return_type coroutine() { co_return 42; }

int main() {
    printf("Hello from main!\n");
    auto task = coroutine();
    printf("Coroutine has been created\n");
    try {
        int value = task.result();
        printf("Coroutine has finished executing with value %d.\n", value);
    } catch (const std::runtime_error& e) {
        printf("Caught exception: %s\n", e.what());
    }
    task.resume();
    printf("Coroutine has finished executing with value %d.\n", task.result());
    return 0;
}
```

There are a few important things to note about this code:

- The coroutine frame is a resource that must be managed. The `return_type` owns the coroutine frame via the `std::coroutine_handle` and destroys it in its destructor.
- Since this coroutine is now returning a value, we need to implement `return_value()` in the promise type instead of `return_void()`. A promise type is required to implement either `return_void()` or `return_value()`, but not both.
- We typically don't want to expose the raw `std::coroutine_handle` to the caller, so the `return_type` exposes safer coroutine state management via the `done()`, `resume()`, and `result()` methods.
- Copying is deleted because two owners of the same coroutine handle would both try to destroy the same frame.
- `unhandled_exception()` stores an exception that escapes the coroutine body, and `result()` rethrows it to the caller.


# The awaiters control the suspension points

Now we can actually dive into what controls the suspension points in the coroutine: the **awaiters**.
The awaiter interface is defined by three functions that the compiler will call at each suspension point:

```cpp
struct awaiter {
    // await_ready() is called to determine whether the coroutine should
    // suspend or not.
    bool await_ready() const noexcept;
    // await_suspend() is called if await_ready() returns false, and is given a
    // handle to the coroutine that is being suspended.
    void await_suspend(std::coroutine_handle<>) const noexcept;
    // await_resume() is called when the coroutine is resumed, and is where the
    // result of the co_await expression is returned.
    void await_resume() const noexcept;
};
```

This model also introduces us to the second main keyword in C++ coroutines: `co_await`.
This keyword is used to suspend the coroutine at a suspension point, and it is the mechanism by which the compiler will call the awaiter interface.
The `co_return` keyword can be thought of as roughly a combination of running either `promise_type.return_void` or `promise_type.return_value` and then calling `co_await promise_type.final_suspend()`.
While `co_return` is a statement, `co_await` is an expression that produces a value, which is the result of `await_resume()`.
Here is a trivial minimal awaiter that never suspends and does nothing when resumed:

```cpp
struct awaiter {
    bool await_ready() const noexcept { return true; }
    void await_suspend(std::coroutine_handle<>) const noexcept {}
    void await_resume() const noexcept {}
};
```

`await_ready` is effectively a fast path that allows the coroutine to keep executing and bypass suspension in some cases, but if necessary we go to `await_suspend` to schedule the coroutine for resumption later.
By having `await_ready()` return `true`, this awaiter will never suspend, and the coroutine will continue executing immediately after the `co_await` expression, which also means `await_suspend()` will never be called.
Conversely, if we changed `await_ready` to unconditionally return `false`, then `await_suspend` would be invoked immediately afterwards.
On its own, a custom awaiter does not provide any way to schedule the coroutine for resumption, so the coroutine would remain suspended indefinitely.
For that, we can start building a scheduler that can store the coroutine handle and resume it later.

```cpp
#include <queue>

struct scheduler {
    void schedule(std::coroutine_handle<> h) { queue_.push(h); }

    bool run_one() {
        if (queue_.empty()) { return false; }

        auto h = queue_.front();
        queue_.pop();
        if (!h.done()) { h.resume(); }
        return true;
    }
    void run() { while (run_one()) {} }
    bool has_work() const noexcept { return !queue_.empty(); }

private:
    std::queue<std::coroutine_handle<>> queue_;
};

struct awaiter {
    scheduler& sched;
    bool await_ready() const noexcept { return false; }
    void await_suspend(std::coroutine_handle<> h) const { sched.schedule(h); }
    void await_resume() const noexcept {}
};
```

We now have to make a few additional changes to the coroutine's promise type and return type.

```cpp
// This promise_type constructor stores a scheduler reference and stores it
// in the promise (you also have to add the scheduler as a member of the
// promise_type struct), so that it can be used in the initial_suspend() hook.
// IMPORTANT NOTE: the arguments to the promise_type constructor must match the
// arguments to the coroutine function, or more precisely, the arguments to the
// coroutine function must be convertible to the arguments of the promise_type
// constructor.
promise_type(scheduler& sched, int) : sched(sched) {}

// The initial_suspend() hook now returns our custom awaiter that will
// schedule the coroutine for resumption.
awaiter initial_suspend() { return awaiter{sched}; }

// Add one explicit suspension point in the body. Each coroutine is first
// scheduled by initial_suspend(), then scheduled again by this co_await.
return_type coroutine(scheduler& sched, int value) {
    co_await awaiter{sched};
    co_return value * 2;
}
```

With the above changes in place, `main()` can now create multiple coroutines and schedule them for execution:

```cpp
int main() {
    scheduler sched;
    auto first = coroutine(sched, 42);
    auto second = coroutine(sched, 123);
    auto third = coroutine(sched, 2026);

    printf("Scheduler has work: %s\n", sched.has_work() ? "true" : "false");
    try {
        int value = first.result();
        printf("First coroutine has finished executing with value %d.\n", value);
    } catch (const std::runtime_error& e) {
        printf("Caught exception: %s\n", e.what());
    }

    sched.run();
    printf("Coroutines finished executing with values %d, %d, %d.\n",
        first.result(), second.result(), third.result());
}
```

Each coroutine is first scheduled by `initial_suspend()`.
When the scheduler resumes a coroutine for the first time, the body starts, reaches the explicit `co_await`, and schedules itself again.
On the next resume, execution continues after that `co_await` and returns `value * 2`.
The important point is that `resume()` advances a coroutine only until the next suspension point; it does not necessarily run the coroutine to completion.

This outputs:

```bash
Scheduler has work: true
Caught exception: Coroutine not finished yet
Coroutines finished executing with values 84, 246, 4052.
```

# Producing values and handling exceptions

So far we've just had awaiters that return `void`, but `co_await` is an expression and thus can produce a value.
The value produced is the output of `await_resume()`, which can be non-void.
In our case, we could modify our examples like so:
```cpp
struct awaiter {
    scheduler& sched;
    int value;
    int await_resume() const noexcept { return value; }
    ...
}
// ...
// Now we can pass the value into the awaiter and have it return the value
// instead of returning it directly. More generally, it can return anything
// else as well.
return_type coroutine(scheduler& sched, int value)
{
    co_return co_await awaiter{sched, value};
}
```

Similarly, we also need to consider where exceptions can be thrown.
If any exception is thrown during the body of a coroutine's execution, the compiler will automatically call `promise_type.unhandled_exception()`, which can store the exception for later retrieval.
That includes exceptions thrown by the awaiters managing suspension points within the coroutine body.

To manage exceptions, we can modify our `awaiter` to throw an exception in `await_resume()`:

```cpp
// Make the promise_type's unhandled_exception() store the exception for later
// retrieval (also requires modifying the struct).
void unhandled_exception() { exception = std::current_exception(); }

int await_resume() const {
    throw std::runtime_error(std::to_string(value) + " failed");
    return value;
}
```

Now when the coroutine is resumed and reaches the `co_await`, it will throw an exception, which will be caught by the compiler-generated try/catch block around the body of the coroutine.

# Awaitables and awaiters

So far, I have been loosely calling the object used with `co_await` an awaiter, but the more precise terminology makes an important distinction.
The expression after `co_await` is an **awaitable**, and the compiler then obtains an awaiter from that awaitable.
Sometimes the awaitable already is the awaiter, which is how our examples so far work, as well as simple types like `std::suspend_always`.
In the more general case, though, the awaitable can produce a separate awaiter via `operator co_await()`:

```cpp
struct awaitable {
    struct awaiter {
        bool await_ready() const noexcept;
        void await_suspend(std::coroutine_handle<>);
        int await_resume();
    };

    awaiter operator co_await() const;
};
```

While this distinction may seem like a minor detail, it is in fact crucial to how real coroutine frameworks work.
Separating the awaitable and the awaiter allows for more complex behavior, such as having multiple awaiters for the same awaitable, or having an awaitable that produces different awaiters depending on the context.
One important example of this distinction is making a coroutine's own return type awaitable, allowing one coroutine to directly await another coroutine:

```cpp
return_type child(scheduler& sched, int value)
{
    (void)sched;
    printf("child coroutine body started\n");
    co_return value;
}

return_type coroutine(scheduler& sched, int value)
{
    printf("parent coroutine body started\n");

    int child_value = co_await child(sched, value);
    printf("child coroutine produced %d\n", child_value);
    co_return child_value + 1;
}
```

The awaiter is a new nested type, `task_awaiter`, which stores the child coroutine's handle:

```cpp
struct return_type {
    struct promise_type;
    using handle_type = std::coroutine_handle<promise_type>;

    struct task_awaiter {
        handle_type child;

        bool await_ready() const noexcept {
            return child.done();
        }

        void await_suspend(handle_type parent) const {
            child.promise().continuation = parent;
        }

        int await_resume() const {
            if (child.promise().exception) {
                std::rethrow_exception(child.promise().exception);
            }
            return child.promise().value;
        }
    };

    task_awaiter operator co_await() const noexcept {
        return task_awaiter{h_};
    }

    // ...
};
```

Notice that there are now two handles involved:

- the awaiter stores the child handle, because the parent is waiting for that child;
- `await_suspend(parent)` receives the parent handle, because the parent is the coroutine being suspended at this `co_await` expression.

The final piece is that the child needs to schedule that continuation when it completes.
That belongs in the child's `final_suspend()` hook, because that is where the child has finished computing its result but the coroutine frame is still alive:

```cpp
struct promise_type {
    struct final_awaitable {
        bool await_ready() const noexcept {
            return false;
        }

        void await_suspend(handle_type finished_child) const noexcept {
            auto& promise = finished_child.promise();
            if (promise.continuation) {
                promise.sched.schedule(promise.continuation);
            }
        }

        void await_resume() const noexcept {}
    };

    final_awaitable final_suspend() noexcept {
        return {};
    }

    scheduler& sched;
    int value{};
    std::exception_ptr exception;
    handle_type continuation{};

    // ...
};
```


Now the control flow is:

1. `main()` creates the parent task.
2. The parent task is scheduled by its `initial_suspend()`.
3. The scheduler resumes the parent.
4. The parent creates the child task.
5. The child task is scheduled by its own `initial_suspend()`.
6. The parent awaits the child task.
7. In this example, the child is not done yet, so `await_ready()` returns `false`.
8. `task_awaiter::await_suspend()` stores the parent handle as the child's continuation.
9. The scheduler resumes the child.
10. The child reaches `co_return`, stores its value, and reaches `final_suspend()`.
11. The child's `final_suspend()` schedules the parent continuation.
12. The scheduler resumes the parent at the suspended `co_await child(...)` expression.
13. `task_awaiter::await_resume()` returns the child's stored value, and the parent continues executing.

This code illustrates the key handoff for traditional asynchronous execution: the parent coroutine is suspended, and its continuation is scheduled to resume when the child completes.
The continuation is just another coroutine handle that gets passed back to `scheduler.schedule()` once the thing it was waiting for has completed.
By separating awaitables and awaiters, you can extend this idea to support multiple parents waiting on the same shared task, for instance, or have multiple awaiters for the same awaitable, each with different behavior.

# Transforming awaited expressions

The `operator co_await()` hook lets an awaitable decide how it should be awaited.
There is one more customization point that happens even earlier: the promise type can decide what an expression means when it is awaited inside this kind of coroutine.
That hook is called `await_transform()`.

For example, this would normally not compile:

```cpp
return_type coroutine(scheduler& sched, int value)
{
    (void)sched;
    int transformed_value = co_await value;
    co_return transformed_value;
}
```

An `int` is not an awaiter, and it does not have an `operator co_await()`.
But the promise type can give `co_await value` a meaning by transforming the integer into an awaitable:

```cpp
struct promise_type {
    promise_type(scheduler& sched, int) : sched(sched) {}

    awaitable await_transform(int value) {
        return awaitable{sched, value};
    }

    scheduler& sched;

    // ...
};
```

Now when the coroutine body says:

```cpp
int transformed_value = co_await value;
```

the promise transforms that into something like:

```cpp
int transformed_value = co_await awaitable{sched, value};
```

Then the normal awaitable-to-awaiter process continues.
If the transformed object already implements the awaiter interface, the compiler can use it directly.
If the transformed object has `operator co_await()`, the compiler can call that to obtain the awaiter.

This gives us a useful way to distinguish the layers:

- `await_transform()` is chosen by the coroutine's promise type. It customizes what expressions mean when awaited inside this coroutine.
- `operator co_await()` is chosen by the awaited object. It customizes how that object turns into an awaiter.
- `await_ready()`, `await_suspend()`, and `await_resume()` are the awaiter protocol. They customize what happens at the actual suspension point.

Real coroutine libraries can use `await_transform()` to attach a scheduler, inject cancellation state, add tracing, reject unsupported awaits, or give domain-specific meaning to ordinary expressions.
The important thing is that this hook belongs to the coroutine doing the awaiting, not necessarily to the object being awaited.

# Yielding values

The last coroutine keyword is `co_yield`.
This is the keyword used to build generators: coroutines that produce a sequence of values over time instead of one final value.

The key point is that `co_yield` also reuses the await machinery.
Roughly speaking, this:

```cpp
co_yield value;
```

means:

```cpp
co_await promise.yield_value(value);
```

As with the other hooks, the language does not prescribe what yielding means.
The promise type decides by implementing `yield_value()`.
For a simple generator, `yield_value()` stores the yielded value in the promise, then returns an awaitable that suspends the coroutine so the caller can observe that value.
Unlike `return_void()` and `return_value()`, `yield_value()` is not mutually exclusive with either completion hook.
A generator commonly implements `yield_value()` for intermediate values and `return_void()` for the eventual end of the sequence.
It is also possible to implement `yield_value()` alongside `return_value()` if the coroutine type wants to yield intermediate values and later finish with a final result.

```cpp
struct generator {
    struct promise_type {
        generator get_return_object() {
            return generator{
                std::coroutine_handle<promise_type>::from_promise(*this)
            };
        }

        std::suspend_always initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }

        void unhandled_exception() {
            exception = std::current_exception();
        }

        void return_void() {}

        std::suspend_always yield_value(int value) {
            current_value = value;
            return {};
        }

        int current_value{};
        std::exception_ptr exception;
    };

    ~generator() {
        if (h_) {
            h_.destroy();
        }
    }

    bool next() {
        if (!h_ || h_.done()) {
            return false;
        }

        h_.resume();

        if (h_.promise().exception) {
            std::rethrow_exception(h_.promise().exception);
        }

        return !h_.done();
    }

    int value() const {
        return h_.promise().current_value;
    }

    using handle_type = std::coroutine_handle<promise_type>;
    generator(const generator&) = delete;
    generator& operator=(const generator&) = delete;

private:
    explicit generator(handle_type h) : h_(h) {}
    handle_type h_;
};
```

With that return type, a coroutine can yield several values:

```cpp
generator numbers()
{
    co_yield 1;
    co_yield 2;
    co_yield 3;
}
```

The caller drives the coroutine forward one yield at a time:

```cpp
auto g = numbers();

while (g.next()) {
    printf("Generated value %d\n", g.value());
}
```

The control flow is:

1. `numbers()` creates the coroutine frame and suspends at `initial_suspend()`.
2. The first call to `next()` resumes the coroutine.
3. The coroutine reaches `co_yield 1`.
4. The promise stores `1` in `yield_value(1)`.
5. `yield_value()` returns `std::suspend_always`, so the generator suspends.
6. `next()` returns `true`, and the caller reads the stored value with `value()`.
7. The next call to `next()` resumes immediately after `co_yield 1`.
8. After the final yielded value, one more call to `next()` resumes the coroutine, reaches the end of the body, calls `return_void()`, reaches `final_suspend()`, and then reports that the generator is done.

So `co_yield` is not an entirely separate mechanism.
It is another promise hook that produces an awaitable.
The difference is the shape of the public API: instead of a task that eventually produces one result, a generator exposes a `next()` operation that repeatedly resumes the coroutine to the next yield point.

# Conclusion

C++ coroutines felt strange to me at first because the language gives you mechanisms rather than a complete programming model.
There is no built-in `task`, no built-in event loop, no built-in scheduler, and no single blessed meaning for asynchronous execution.
Instead, the compiler recognizes the coroutine keywords and then asks your types what each step should mean.

That is a lot of machinery, but the pieces are individually small:

- the return type leads the compiler to the promise type;
- the promise owns the hooks for starting, finishing, yielding, returning, and transforming awaits;
- the coroutine frame stores the state that survives suspension;
- awaitables and awaiters define what happens at suspension points;
- schedulers and continuations decide when suspended work becomes ready to run again.

Once those roles are clear, the syntax starts to look less magical.
`co_await`, `co_return`, and `co_yield` are not complete features on their own.
They are entry points into a protocol.
Libraries such as task systems, generators, thread pools, timers, and async I/O runtimes are built by filling in that protocol with a particular policy.

The toy examples here are intentionally small to make the hidden handoffs visible: where values are stored, where exceptions go, which coroutine is suspended, and how another coroutine gets scheduled to resume later.
Once you can see those handoffs, production coroutine libraries become much easier to read.
