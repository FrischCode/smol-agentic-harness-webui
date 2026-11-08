"""Put the repo root on the path so `import sahw` resolves to this tree.

And keep the battery hermetic in the same stroke, the two ways hermeticity can be broken. A test that
resolves a command line makes the server read a machine config whose values land in `os.environ`, and an
assertion about a default would then read this box's port and this box's paths instead of the shipped
ones: pin `SAHW_ENV_FILE` at a path that never exists, so the file is missing, the merge is a no-op, and
a default resolves the same way on every machine. A test that wants a file points `SAHW_ENV_FILE` at its
own.

The second way is ambient, and it is the one a pin cannot reach: a run started by the harness reads the
machine's config into the process environment before anything in this tree runs, and an ambient value
beats the file the pin names — so a battery launched from inside a run would inherit that box's port and
its paths. The battery's contract is the same on every machine and in every environment, so the ambient
SAHW_ values are cleared before the pin lands, and the pin is set after the clear: the tests are the only
voice on what a value is, and a monkeypatch that clears or sets one restores that cleared state after
itself.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for name in [key for key in os.environ if key.startswith("SAHW_")]:
    del os.environ[name]
os.environ["SAHW_ENV_FILE"] = str(ROOT / "tests" / "_no_env_for_the_battery")
