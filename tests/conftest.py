from pathlib import Path
from sys import modules, path
from types import ModuleType

# Ensure local src/ is imported before any installed package
REPO_ROOT: Path = Path(__file__).resolve().parents[1]
SRC_PATH: Path = REPO_ROOT / "src"
if str(SRC_PATH) not in path:
    # Prepend to path so it takes precedence
    path.insert(0, str(SRC_PATH))

# If an installed package was already imported, remove it so pytest imports local
if "wizedispatcher" in modules:
    mod: ModuleType = modules["wizedispatcher"]
    mod_file: str = getattr(mod, "__file__", "")
    if "site-packages" in str(mod_file):
        del modules["wizedispatcher"]

# Import the local package to lock in the src path for the duration of tests
try:
    import wizedispatcher as _wd  # type: ignore[unused-import]

    _ = _wd
except Exception:
    # If import fails here, tests that import it will surface the error
    pass
