# Installation

WizeDispatcher is distributed as a pure‑Python package. To install it,
ensure you have Python 3.8 or newer. You can install it from the
Python Package Index (PyPI) using `pip`:

```shell
pip install wizedispatcher
```

Alternatively, if you prefer to work with the latest development
version, clone the repository and install it in editable mode:

```shell
git clone https://github.com/kairos-xx/wizedispatcher.git
cd wizedispatcher
pip install -e .
```

In both cases, WizeDispatcher has no external dependencies beyond
the Python standard library. After installation, you can import the
library as follows:

```python
from wizedispatcher import dispatch

@dispatch.fn(int)
def _(value: int) -> str:
    ...
```

If you encounter problems installing the package, ensure your pip and
setuptools are up to date:

```shell
pip install --upgrade pip setuptools
```