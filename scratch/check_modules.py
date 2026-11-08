"""Every face name a module reaches for, it names an import of (plan 36's static check).

   The browser links modules before it runs them: a name one file declares and another reaches for without
   naming where it stands is a `ReferenceError` at the first act that needs it, not a wiring the reader can
   see. That is the one class of breakage the no-browser harness cannot answer — it stands the face's files
   as one body, where every declaration is in scope of every other — so the answer is asked here, of the
   text, before any browser opens:

     1. the face's files are the entry's own walk (the same import list the browser reads);
     2. every top-level name of every file is the pool a reach could mean;
     3. a name reached from file F that stands in another file must stand in F's import list;
     4. an import naming something F never reaches is a line the reader has to disbelieve; and
     5. a section marker in the entry is a section the entry holds — and the entry's closed set
        names the only ones it may hold: the set stands in this file, and a marker it does not
        name is a product section a move left in the entry, which is the god file's page again
        (plan 39's extent rule: rules one to four ask the split is correct, this one asks it
        is complete).

   (3) and (5) fail the run: (3) is a page that throws, (5) is a page that still reads the file
   the move owed to break. (4) is reported and does not, because an unused import runs
   perfectly and is only untidy — but it is the same list read the other way, and it is how a name left
   behind by a move stays visible.

     python scratch/check_modules.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from split_modules import declarations, references  # noqa: E402

TREE = Path(__file__).resolve().parent.parent
WEB = TREE / "web"
ENTRY = WEB / "assets" / "js" / "app.js"

IMPORTS = re.compile(r"^import\s*\{([\s\S]*?)\}\s*from\s*'(\.[^']*)';", re.M)
EXPORT = re.compile(r"^export\s+(?=(?:const|let|var|function|class|async[ \t]+function)\b)", re.M)
# The marker a section stands under: one line, `/* --- the name, and its dashes` — the comment
# that follows rides on until the file's one comment closes it, and the rule reads the marker's
# own line only, which is the line a move plants.
SECTION = re.compile(r"\s*/\*\s*---\s+(?P<name>.+?)\s*(?:-{2,}\s*)?$")
# The entry's closed set: the section markers the entry may hold. The move (plan 39) took every
# product section out of the entry — the trace, the menus, the scroller, the transcript, the
# reading, the tree, the composer stand in their own modules — and what the entry owes is the
# boot, the event wiring, the keyboard and the standing layers, none of which stands under a
# marker. The set is therefore empty, and it is named here, in the file the rule lives in, with
# the reason beside it: a marker this set does not name is a section the entry still reads.
ENTRY_SECTIONS: list[str] = []


def own_names(text: str) -> set[str]:
    """The names a file declares at its top level, with or without the `export` the loader needs."""
    return {found["name"] for found in declarations(EXPORT.sub("", text))}


def imports_of(text: str) -> dict[str, str]:
    """Every name the file imports, and the file it says it stands in."""
    return {
        name.strip(): spec[2:]
        for names, spec in IMPORTS.findall(text)
        for name in names.split(",")
        if name.strip()
    }


def face_files() -> list[Path]:
    """The entry and every file its import list names, walked once (a file twice named stands once)."""
    seen: list[Path] = []

    def walk(path: Path) -> None:
        if path in seen:
            return
        seen.append(path)
        for _names, spec in IMPORTS.findall(path.read_text(encoding="utf-8")):
            walk(path.parent / spec[2:])

    walk(ENTRY)
    return seen


def main() -> int:
    files = face_files()
    text = {path: path.read_text(encoding="utf-8") for path in files}
    declared = {path: own_names(text[path]) for path in files}
    home = {name: path for path in files for name in declared[path]}
    print(f"{len(files)} files, {len(home)} names the face declares at its top level")

    broken: list[str] = []
    for path in files:
        reached = references(text[path], (0, len(text[path])), set(home) - declared[path])
        imported = imports_of(text[path])
        for name in sorted(reached):
            where = imported.get(name)
            if where is None:
                at = next(  # the first line reaching for it, so the reader is sent somewhere
                    i for i, line in enumerate(text[path].splitlines(), 1)
                    if re.search(rf"(?<![\w.$]){re.escape(name)}\b", line)
                )
                broken.append(f"{path.name}:{at} reaches for {name}, which stands in {home[name].name}, "
                              f"and names no import of it")
    # Rule five: the entry's section markers stand in its closed set. The move took the product's
    # sections out of the entry and left the wiring it owes — a marker planted there is a section
    # that move did not take, and the check is the reader that catches it where the browser never
    # would (a page that still reads the god file parses, loads and runs: no browser sees the debt).
    entry_text = text[ENTRY]
    for at, line in enumerate(entry_text.splitlines(), 1):
        found = SECTION.match(line)
        if found is not None and found["name"] not in ENTRY_SECTIONS:
            broken.append(f"{ENTRY.name}:{at} holds the section {found['name']!r}, which the entry's "
                          "closed set does not name: the entry owes its wiring only, and a section it "
                          "holds is the god file standing again")

    for line in broken:  # every fault gets its line, so the reader is sent somewhere
        print("FAIL  " + line)

    for path in files:
        unused = sorted(set(imports_of(text[path])) - references(
            text[path], (0, len(text[path])), set(imports_of(text[path]))
        ))
        if unused:
            print(f"note  {path.name} imports what it never reaches: {', '.join(unused)}")

    print(f"{sum(1 for path in files)} files, {len(broken)} fault(s): unbound reach or a section the entry holds")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
