# Development

WizeDispatcher is an open‑source project. Contributions are
welcome! This section outlines how to set up a development
environment, run tests, and understand the code structure.

## Setting up a Development Environment

1. Clone the repository:

   ```shell
   git clone https://github.com/kairos-xx/wizedispatcher.git
   cd wizedispatcher
   ```

2. Create a virtual environment and install dependencies:

   ```shell
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   pip install -e .
   ```

3. Install development tools such as black, flake8, and mypy.

## Running Tests

The repository includes a test suite under the `tests` directory.
To run the tests:

```shell
pytest
```

Ensure that all tests pass before submitting a pull request.

## Code Structure

The core of the library is located in `wizedispatcher/core.py`. It
defines the `TypeMatch` and `WizeDispatcher` classes, along with
helper functions and classes. The global `dispatch` instance is
created in `wizedispatcher/__init__.py`.

Registries are built on demand when you access `@dispatch.name`
for the first time, and overloads are collected during class
construction using a descriptor.

## Extending the Library

If you need to customize the matching algorithm or support new
typing constructs, consider extending or overriding `TypeMatch`.
You can subclass `WizeDispatcher` and provide your own version
of `_resolve_hints` or `type_specificity_score`. Then instantiate
your custom builder and use it instead of the global `dispatch`.

Please open an issue or discuss your proposed changes before
making major modifications.

## Contribution Guidelines

- Use black for formatting (run `black .` before committing).
- Ensure docstrings follow Google style and wrap at 79 characters.
- Add tests for any new features or bug fixes.
- Update the documentation when you change the API.