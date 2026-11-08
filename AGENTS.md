# SAHW — Contributor Notes

Developer notes for **SAHW - Smol Agentic Harness's web UI**. Read before editing.

The product overview is in `README.md`; the reasoning behind every decision is in the relevant source.

## What this is

A companion web UI for SAH: a stdlib-only Python server serving a static front that is the tree's
own, reading SAH's run logs. It lists the runs a root holds, streams one, follows the words it
speaks, and spawns another in a directory the operator chose.

## Portability axiom

Everything must be copyable to another machine. The venv (`.venv`, uv) is a copyable directory.
The core imports stdlib only — `sah` is never imported, it is launched as a process from the tree
the operator names (that tree's interpreter, its `PYTHONPATH`) — and no runtime dependency may
enter `pyproject.toml` `dependencies` without the decision and its reason written in
`pyproject.toml` first.

Both Windows and POSIX are targeted and must be supported.

## Self-explanatory

The tree carries every reason a reader needs — a comment, a docstring. Nothing bound to outside
source.

## Environment & commands

- Python `>=3.11`. Own venv: `./.venv` (uv) holds the dev tools (ruff, pytest); the server itself
  is stdlib-only and runs under any interpreter.
- Run the server: `.venv/Scripts/python.exe -m sahw` (there is no console script; the module is
  the entry point — `sahw/__main__.py`), or `sahw.bat` / `sahw.sh` from this folder — the launcher
  finds the SAH tree (its `SAH_INSTALL_DIR`, or `sah` on PATH — and refuses with the line that names
  the missing install when it finds neither), extra arguments passed straight through (`sahw.bat
  --port 8391`).
- Machine config lives in a gitignored `.env` at the tree root (`.env.example` is the committed
  shape). The server reads it at start and fills only the variables it does not already have in
  the environment — a value the shell or a flag sets wins over the file. The shipped fallbacks are
  generic (loopback, port 8321, the two SAH locations left silent — a spawn that names its
  refusal); this box's real locations are the `.env`'s.
- Lint: ruff lives in the venv (dev-only; `dependencies` stays `[]`). `ruff check .` validates, and
  `ruff check --fix .` applies the safe auto-fixes. There is no routine `ruff format`: the layout
  is the house's deliberate style, so the repo is **lint-enforced, not formatter-enforced** — that
  is the guarantee, and it is not a universal formatting guarantee. The config is `[tool.ruff]` in
  `pyproject.toml` (line-length 110, the same select/ignore as SAH's). Suppression belongs in this
  config, never as an inline `# noqa: <code>` in the source — ruff is optional, and a rule code in
  the source is a reference to an external source (the Self-explanatory rule applies). Where an
  import is a deliberate re-export, prefer the self-alias idiom (`from … import X as X`) to any
  suppression at all.
- Tests: pytest lives in the venv. The suite stands under `tests/` and ships with the product: it
  is hermetic — no real spawns, no network, no machine config, `conftest.py` pinning the env file at
  a path that never exists and clearing the ambient `SAHW_` values before a pin lands — so it
  stands the same on every box. The config is `[tool.pytest.ini_options]` in `pyproject.toml`.
- The face is ES modules with no build step and no runtime dependency: `web/index.html` loads
  `web/assets/js/app.js` as the entry, which keeps the wiring and imports the regions the product
  is cut into (`components.js`, `composer.js`, `menus.js`, `modal.js`, `scroller.js`, `state.js`,
  `trace.js`, `transcript.js`, `tree.js`, `wire.js`). The face's checks are node-side (dev
  tools, not shipped): `node --check` on each of `web/assets/js/*.js`, and a css-tree parse of
  every `.css` under `web/` — a `.css` file stands only with zero parse errors, and presence in
  the served bytes is not well-formedness.
- No CDN, no build step. The vendored pieces stand in `web/assets/vendor/` with their license
  records in `web/VENDOR.md`.

## Docstrings & comments

Standalone, local, universal: readable with only the file open and nothing else. No task/session/
date/incident prose ("as discussed", "the bug from yesterday"). A comment that references another
module names it. When a non-obvious decision needs to survive, the *reason* goes in a comment,
not a memory note — the idea must travel with the source.

## Editing

Keep this file token-dense: no prose, no filler, every line earns its tokens.

## Static

This file is not to be modified without operator consent.
