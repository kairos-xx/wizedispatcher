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

- [Installation](installation.md) – how to install the library.
- [Quickstart](quickstart.md) – a quick introduction with a working example.
- [Advanced Usage](advanced.md) – deeper topics such as method dispatch,
  property dispatch, and the TypeMatch scoring algorithm.
- [Typing normalization](advanced.md#typing-normalization-deep-dive) – how
  annotations are canonicalized so modern typing constructs behave
  consistently across Python versions.
- **TypingNormalize API** – complete reference and examples of the
  normalization utility used internally. See
  [TypingNormalize](typingnormalize.md).
- [API Reference](api_reference.md) – detailed descriptions of classes,
  functions, and methods with parameters and return types.
- [Demos](demos.md) – examples of using WizeDispatcher in real code,
  including how to run all demos.
- [Troubleshooting](troubleshooting.md) – common issues and how to resolve
  them.
- [FAQ](faq.md) – frequently asked questions and answers.
- [Development](development.md) – guidelines for contributing to
  WizeDispatcher and how the library works internally.

For details, examples, and API semantics see the dedicated
[TypingNormalize](typingnormalize.md) page. See Advanced Usage →
[Typing normalization](advanced.md#typing-normalization-deep-dive) for a
deep dive and API Reference for the `TypingNormalize` utility.
