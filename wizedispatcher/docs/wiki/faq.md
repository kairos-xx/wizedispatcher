# Frequently Asked Questions

## What is WizeDispatcher?

WizeDispatcher is a runtime dispatch library for Python. It
allows you to define multiple implementations (overloads) for the
same function or method, each constrained by type hints. At
runtime, the dispatcher selects the most specific implementation
that matches the arguments' types.

## Why use WizeDispatcher instead of if/elif?

Manually writing `if isinstance(...):` chains can become
error‑prone as your function grows. WizeDispatcher centralizes
the dispatch logic, reduces boilerplate, and makes the dispatch
criteria explicit. It also supports advanced typing constructs
like unions, optionals, and generics.

## Does WizeDispatcher slow down my code?

WizeDispatcher does introduce an overhead during the first call
with a given set of argument types, as it computes the best
overload. However, results are cached by the tuple of argument
types, so subsequent calls are fast. In typical applications the
overhead is negligible compared to the benefits.

## How does dispatch handle default values?

WizeDispatcher binds arguments to the original function signature
using `inspect.signature` and `BoundArguments`, applying defaults
as necessary. Only the arguments provided at call time are used
for dispatch decisions; default values do not influence dispatch.

## What happens if two overloads match equally?

If multiple overloads receive the same maximum specificity score,
they are considered equal winners. The dispatcher selects the
first winner in registration order. To break ties, add more
specific constraints.

## Can I register multiple overloads for the same function?

Yes. You can register as many overloads as necessary by applying
the `@dispatch.name` decorator multiple times. Use descriptive
type annotations or decorator arguments to differentiate them.

## How do I clear the dispatch cache?

Each registry caches the chosen overload by argument types. There
is no public API to clear the cache, but you can access the
registry via the `__dispatch_registry__` attribute on classes or
the `__fdispatch_registry__` attribute on modules and call
`._cache.clear()` manually.

## Does WizeDispatcher support asynchronous functions?

WizeDispatcher can dispatch on `async` functions. However, if
your base function is async, all overloads should also be async
and return awaitables. The dispatcher does not `await`
automatically; you must await the result yourself.

## Is WizeDispatcher thread‑safe?

Registries use dictionaries for caches and lists for overload
storage. While reading is thread‑safe, writing (registering new
overloads) is not designed for concurrent modification. Register
overloads at import time or protect registration with a lock in
multi‑threaded environments.

## Can I extend the matching algorithm?

The matching and scoring algorithm is encapsulated in the
`TypeMatch` class. You can subclass `TypeMatch` and override
`is_match` or `type_specificity_score` to customize behavior.
Then subclass `WizeDispatcher` and set its `_UNION_TYPE` and
other class variables accordingly. Replace the global `dispatch`
instance with your custom builder.