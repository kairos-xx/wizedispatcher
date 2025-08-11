# WizeDispatcher Documentation

Welcome to the **WizeDispatcher** wiki. WizeDispatcher is a Python
library that provides a simple, extensible runtime dispatch system. It
allows you to register multiple implementations for a single function
or method and automatically dispatch to the most appropriate
implementation based on the types of the runtime arguments. The goal
is to offer a clean, efficient alternative to ad‑hoc type‑checking
code and complicated manual dispatch logic.

This documentation is organized into several sections to help you
understand, use, and extend WizeDispatcher:

- **Installation** – how to install the library.
- **Quickstart** – a quick introduction with a working example.
- **Advanced Usage** – deeper topics such as method dispatch,
  property dispatch, and the TypeMatch scoring algorithm.
- **API Reference** – detailed descriptions of classes, functions,
  and methods with parameters and return types.
- **Demos** – examples of using WizeDispatcher in real code,
  including how to run all demos.
- **Troubleshooting** – common issues and how to resolve them.
- **FAQ** – frequently asked questions and answers.
- **Development** – guidelines for contributing to
  WizeDispatcher and how the library works internally.

## New in This Version

- **Partial Type Hints**: Overload functions can specify only some parameter
  type hints; missing types are taken from the fallback function.
- **Missing Arguments Filled**: If an overload omits parameters entirely,
  their types and default values are completed from the fallback.
- **`*args` / `**kwargs` Handling**: When overloads use var-positional or
  var-keyword parameters without explicit annotations, these are matched
  using the fallback’s annotations.
- **Mixed Overload Strategies**: You can combine positional, keyword, and
  fallback-derived type hints within a single overload registration.
