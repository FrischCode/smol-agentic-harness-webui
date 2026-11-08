"""sahw.openers — open a folder or a file on the operator's machine, as an argv list and never a command.

The server is the box's: it listens on 127.0.0.1, its own panes already list the operator's directories, and
the acts a person wants from a pane — show me that folder, open a terminal in it, open this file in the
program the box owes it — are acts on this machine rather than on a run. This module performs them. It opens
directories and files, through the machine's own openers, and nothing else: no URL, and no command an
operator types.

**The path is an argument, never text to parse.** Every spawn here is an argv list handed to the process with
no shell in between, because the path is the one thing in the request that a caller controls and a shell would
read it as program text: a folder named `C:\\work\\x && drop` is then two acts instead of one name. As an
argument it is a name, and the weirdest name the filesystem accepts is the weirdest name this can open.

**Which terminal this box has is asked once, at startup.** The probe is a `shutil.which` of the machine's
path, and the answer cannot change while the server is up in any way the operator would not notice — so it is
decided when the server is made and carried on the site, not per request. A box with Windows Terminal gets it
(`wt.exe -d <folder>`, a tab in the terminal the operator chose); a box without gets `cmd.exe`, told to change
drive-and-directory and then stay (`/k cd /d <folder>`) in a console window of its own, which is the fallback
that still lands the operator in the directory they asked for.

**The spawn is issued, not watched.** These processes are windows, not work: `explorer.exe` returns as soon as
it has asked the shell for a window, and a terminal outlives the request that opened it. So the answer goes
out when the spawn is issued and nothing waits for an exit — and the one thing waiting would achieve, a
failure to find the program, is the failure this reports.

**The file act is the box's default handler, and no editor is pinned.** Which program a name opens is the
operator's decision, made once in the system's own settings, and this module asks that question rather than
answering it: pinning an editor here would be a preference written into the wrong place, and a promise about
what is installed. What the act does promise is the shape — the path reaches the handler as one argument, and
the machine's own answer comes back — so the file opens wherever the box says it opens.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

EXPLORER = "explorer"
TERMINAL = "terminal"
FILE = "file"
SELECT = "select"

# The kinds this box can open, as the body's `kind` field names them: the two windows on a folder, the
# machine's own opener for a file, and the machine's own file browser stood on a file, selected.
KINDS = (EXPLORER, TERMINAL, FILE, SELECT)

EXPLORER_PROGRAM = "explorer.exe"
WT_PROGRAM = "wt.exe"
CMD_PROGRAM = "cmd.exe"

# The machine's own opener for a file, asked directly rather than through a shell: `rundll32` running the
# shell's protocol handler is the `start` command's effect, which is what hands a file to the program this
# box owes its kind — the editor an operator set once in the system's own settings, whatever that is today.
# `explorer.exe` is not it: given a file it shows the folder the file stands in, which is the folder act
# with a different path rather than the file opened. A box with no Windows shell has the same handler under
# `xdg-open`'s name.
FILE_PROGRAM = "rundll32.exe"
FILE_HANDLER = "url.dll,FileProtocolHandler"
XDG_PROGRAM = "xdg-open"

# The select act's switch: `explorer /select,<path>` stands the file browser in the file's own folder with
# the file itself marked. The comma is part of the switch's spelling, not a separator the caller would
# build — the switch and the path go to the machine as one token, and the launcher quotes what holds a
# space the same way it quotes every other argument, so a name like `a, b && drop.txt` reaches the switch
# as a name. Explorer splits the switch at the first comma only, and the rest of the token is the path.
SELECT_SWITCH = "/select,"

# The word an operator types to reach Windows Terminal, and what `shutil.which` resolves through PATHEXT and
# the app-execution aliases. Probing the stem is asking the question the Run dialog asks; the `.exe` spelling
# is asked too, because a box can hold the shim under one name and not the other.
WT_STEM = "wt"

# CREATE_NEW_CONSOLE. `cmd.exe` is a console program: spawned without it, the fallback terminal would inherit
# the server's own console and sit in a window the operator is not looking at, so the act would answer
# `{ok: true}` having opened nothing they can see. The GUI programs (explorer, Windows Terminal) need no flag:
# they bring their own window or none.
_NEW_CONSOLE = 0x00000010


class OpenError(Exception):
    """A path this server will not open, carrying the HTTP code that says who to blame, the way
    `spawn.SpawnError` and `channel.ChannelError` do: 400 when the request named no kind this box knows or a
    path that is not the shape the kind opens — a file where a folder was asked for, a folder where a file
    was — and 404 when the path is not there at all. The reason and the code are one decision, made where the
    path was looked at, so the route stays one `except` wide.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def terminal_program(which=shutil.which) -> str:
    """The terminal this box opens a folder with: Windows Terminal when it is on the path, else `cmd.exe`.

    `which` is the seam, not decoration: the answer is a fact about this machine's path and a test has no
    business installing an executable to assert which branch a machine is on, while it can name a path that
    holds nothing and one that holds a `wt`.
    """
    return WT_PROGRAM if (which(WT_STEM) or which(WT_PROGRAM)) else CMD_PROGRAM


def open_argv(kind: str, path: str, terminal: str = WT_PROGRAM) -> list[str]:
    """The argv that opens one path: the program and the path, and nothing that could be read as syntax.

    The `cd` and the `/d` are separate tokens on purpose: the launcher quotes any token that holds
    a space, and one token of `cd /d` quoted as `"cd /d"` is a program name to the shell that starts
    in the folder it was told to, not a change of directory. One token at a time is the only reading
    the command line has.

    Keyword-only would be kinder to a caller with two of these in a row, and there is only ever one caller,
    three arguments deep in a route. `terminal` is what this box was found to have at startup, so the branch
    is taken once and asserted about either way.
    """
    if kind == EXPLORER:
        return [EXPLORER_PROGRAM, path]
    if kind == TERMINAL:
        if terminal == CMD_PROGRAM:
            return [CMD_PROGRAM, "/k", "cd", "/d", path]
        return [terminal, "-d", path]
    if kind == FILE:
        return file_argv(path)
    if kind == SELECT:
        return select_argv(path)
    raise OpenError(f"nothing here opens kind {kind!r}: {' or '.join(KINDS)}")


def file_argv(path: str) -> list[str]:
    """The argv that hands one file to the program this box owes it: the handler, its entry point, the path.

    The handler's name carries a comma because that is how `rundll32` spells "this function of that
    library", and it is one token of its own either way — the launcher quotes what holds a space, and a
    comma is not a separator to anything on this path. The path is the third token and the last thing on
    the line, which is the whole of what keeps a name like `notes && drop.txt` a name.
    """
    if sys.platform == "win32":
        return [FILE_PROGRAM, FILE_HANDLER, path]
    return [XDG_PROGRAM, path]


def select_argv(path: str) -> list[str]:
    """The argv that stands the file browser on one file, selected: the switch and the path, one token.

    The Windows switch carries the comma in its own spelling (see `SELECT_SWITCH`), and the token is the
    argument the machine receives whole. A box without the switch has no select of its own, and the
    fallback stands its own opener on the directory the file stands in — the closest act that box owes,
    named as a directory because that is the shape its opener opens.
    """
    if sys.platform == "win32":
        return [EXPLORER_PROGRAM, SELECT_SWITCH + path]
    return [XDG_PROGRAM, os.path.dirname(path) or "."]


def launch_flags(kind: str, terminal: str) -> dict:
    """The `Popen` flags this act needs: a console of its own, and that console's own input.

    Guarded on the platform because `creationflags` is this box's API: a POSIX box has no console to be new,
    and the flags that mean one there mean something else entirely.

    **The `stdin: None` is how the fallback keeps its window, and the `stdout` and `stderr` `None`s are
    how it shows a prompt at all.** `launch` sends a child's input and outputs to the null device, and the
    fallback is a shell that reads its input and writes its prompt: started with stdin already at
    end-of-file it reads nothing, takes that for the end, and closes the console the act just opened — a
    window that flashes and is gone. With the outputs at the null device, the prompt is written nowhere
    the operator can see — a black window that hangs with nothing in it. So this act asks for the
    console's own input and output: the operator's console when the server was launched from one, or
    whatever the new console is, which is where `cmd` writes the prompt and reads the line. Every other
    child, and the GUI branch that never reads or shows anything, keeps the null device.
    """
    if sys.platform == "win32" and kind == TERMINAL and terminal == CMD_PROGRAM:
        return {"creationflags": _NEW_CONSOLE, "stdin": None, "stdout": None, "stderr": None}
    return {}


def launch(argv: list[str], flags: dict):
    """Ask the operating system for the process, and do not wait for it.

    The one place this module reaches outside itself, so a test can hold the whole act steady by standing in
    for it and reading the argv that would have run. The input and the outputs go to the null device by
    default, because nobody is reading them, the same reason a spawned run's do: a process holding a pipe
    nobody drains is a process that blocks on its own stdout. An act that is a console asks to keep the
    console's own input *and* outputs, which is what `flags` entries of `None` say (see `launch_flags`):
    a `cmd /k` on the null device closes its window at once, and its prompt written to the null device is
    a black window that hangs without one.
    """
    options = dict(flags)
    stdin = options.pop("stdin", subprocess.DEVNULL)
    stdout = options.pop("stdout", subprocess.DEVNULL)
    stderr = options.pop("stderr", subprocess.DEVNULL)
    return subprocess.Popen(argv, stdin=stdin, stdout=stdout,
                            stderr=stderr, **options)


def open_path(kind: str, path: str, terminal: str = WT_PROGRAM) -> dict:
    """Open one path on this machine, and answer whether the window was asked for.

    Three shapes, one act: `explorer` and `terminal` stand a window on a folder, `file` hands a file to
    the program this box owes its name, and `select` stands the machine's own file browser on a file with
    the file itself marked. The refusals split the way every other act's split: a request that
    names no kind, no path, a path that is not there, or a path that is not the shape its kind opens — a
    folder where a file was asked for, a file where a folder was — is a bad request, and it answers in the
    tree's one error shape with the 4xx that says so. What is left is the act, and the act's own answer is
    `{ok: true}` once the spawn is issued — or `{ok: false, reason: ...}` if the operating system refused to
    start the program at all, which is a machine's answer rather than a caller's mistake.

    The path is checked and then handed over unresolved: not made absolute, not stripped, not expanded. The
    pane that asks for this read the path off this server's own listing or its own preview, and what it says
    is what the path is called; one that appeared between the check and the spawn is the act winning a race,
    and one that vanished is the spawn's own failure, which is answered too.
    """
    shape = "file" if kind in (FILE, SELECT) else "folder"
    if not str(path or "").strip():
        raise OpenError(f"a {shape} to open is the whole request: path is empty")
    if not os.path.exists(path):
        raise OpenError(f"no such {shape}: {path}", 404)
    if kind in (FILE, SELECT):
        if not os.path.isfile(path):
            raise OpenError(f"not a file: {path}")
    elif not os.path.isdir(path):
        raise OpenError(f"not a folder: {path}")
    argv = open_argv(kind, str(path), terminal)
    try:
        launch(argv, launch_flags(kind, terminal))
    except OSError as refused:
        return {"ok": False, "reason": f"cannot open {path}: {refused}"}
    return {"ok": True}
