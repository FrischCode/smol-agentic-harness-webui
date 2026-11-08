"""sahw.fspath — the shape and the standing of a path the spawn pane asks to change.

The pane reaches the whole box: `GET /api/fs` has no root and `files` refuses only what the box itself
refuses. That reach is a standing decision, and it is why every *mutation* the pane can ask for stands
here first: one place that says what a name may be, what a folder must be for, and which folders this
page does not manage — the same checks, in the same words, in front of all four acts, so no route is the
one that has to remember them.

Three questions, asked in this order and answered the same way every time:

* **is it a name?** `checked_name` — one bare name, no separators, not `.` or `..`, no character this
  box's file systems will not take and no device name they reserve. Every act carries a name: the folder
  to make, the new name to give, the file to receive. A name that is a path is a caller building a
  location out of two fields, and a reserved device name would be a folder the box will not let anyone
  open; both are refused before the folder they name is looked at.
* **does this page manage it?** `not_the_record` — a target that is, or stands inside, the server's runs
  root belongs to the machine's own record of what its runs did, and the tree manages that with its own
  acts. And a folder the standing tree lists as a workspace holding runs is refused a rename or a delete,
  because either leaves those runs' records pointing at a folder that no longer stands. The count comes
  from the standing tree the server was handed, never from a walk: the record has already been read for
  the rows, and a second walk would be a second answer to a question the rows already hold.
* **what stands there now?** `parent_folder`, `name_free`, `emptied` — the folder the act lands in, the
  name beside it, the entries a folder holds. Each answers with the machine's own words and the code that
  says who to blame: 404 what is not there, 400 what is there but is not the shape the act asked for,
  409 what stands where the act would have stood.

The acts themselves are `files`' neighbours, not `files`' business: `files` reads and never writes, so
these four writers live here, beside the guards that let them run.
"""
from __future__ import annotations

import os

# The characters this box's file systems will not take in a name: the separators (a name is one name,
# never a path), what a drive and a stream are parted by, what a glob and a redirect mean to the shell
# the name would be typed into, and what quotes would need quoting. The control characters are not on
# that list because they are pretty — a name holding a bell or a newline is unwritable on this box and
# unsearchable in the listing that would have shown it.
BAD_NAME_CHARS = set('/\\:*?"<>|')

# The names a device wears rather than a file: opening one hangs whatever tries, and on this box that is
# true of the folder, not only of the file inside it, so the name is refused at the door. The digits run
# one to nine because that is what the box spells: `COM0` is a name like any other.
RESERVED_NAMES = ({'CON', 'PRN', 'AUX', 'NUL'}
                  | {f'COM{digit}' for digit in range(1, 10)}
                  | {f'LPT{digit}' for digit in range(1, 10)})

# What a name's own rule is, in the one sentence every name refusal ends with: the operator has to be
# able to fix the name from the sentence alone, so the rule is stated once and carried into every case.
NAME_RULE = ('a name is one bare name: no separators, not "." or "..", no character Windows will '
             'not take, and no device name it reserves')

# The bytes one read of a posted body carries: big enough that a file of a few hundred kilobytes is a
# handful of reads, small enough that no upload of any size ever holds a file in memory.
UPLOAD_CHUNK = 64 * 1024


class PathError(Exception):
    """A path this server will not change, carrying the HTTP code that says who to blame.

    The same shape `files.FileError` and `openers.OpenError` stand: the code is decided once, where the
    path was looked at, so a route is one call and one `except`. 404 for a folder that is not there, 400
    for a name that is not a name or a folder that is not a folder, 409 for a change that would stand on
    something already standing — a name taken, a folder not empty, a folder this page does not manage.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def checked_name(name: str) -> str:
    """The name as this server will take it, or the refusal that says why it is not a name.

    The checks run cheap-before-dear: the shape of the word before anything is looked at on disk, so a
    name that is a path, a dot, or a device never reaches the folder it was meant for.
    """
    if not name:
        raise PathError(f"a name is required: {NAME_RULE}")
    if name != name.strip():
        raise PathError(f"a name does not begin or end with a space: {NAME_RULE}")
    if name in ('.', '..'):
        raise PathError(f"{name!r} is where a folder already stands: {NAME_RULE}")
    if any(char in BAD_NAME_CHARS or ord(char) < 32 for char in name):
        raise PathError(f"{name!r} is not a name: {NAME_RULE}")
    if name.endswith(('.', ' ')):
        raise PathError(f"{name!r} is not a name: {NAME_RULE}")
    if name.split('.')[0].upper() in RESERVED_NAMES:
        raise PathError(f"{name!r} is a device this box reserves: {NAME_RULE}")
    return name


def not_the_record(path: str, runs_root: str) -> str:
    """The target, refused when it is or stands inside the runs root — the guard every act owes.

    The runs root is the machine's own record of what its runs did: the log, the trace, the report, and
    the estate beside them. The tree already manages it, with the archive shelf and a delete that refuses
    a run whose process is still writing, and the pane does not: a folder taken from under the runs root
    is a run whose record has gone out from under every route that reads it.

    The comparison is made on resolved paths rather than on the words, because a runs root named through a
    link and one named whole are the same folder — and it is the whole folder that is refused, whatever
    spelling reached the route. A server that names no runs root refuses nothing here: there is no record
    for a target to stand in.
    """
    if not runs_root:
        return path
    root = os.path.realpath(os.path.abspath(runs_root))
    here = os.path.realpath(os.path.abspath(path))
    if here == root or here.startswith(root + os.sep):
        raise PathError(
            f"{path} is the machine's own record: the runs root and everything under it is managed by "
            "the tree's own acts, not by the spawn directory", 409)
    return path


def workspace_run_count(path: str, tree: dict) -> int:
    """How many runs of the standing tree name this folder as their workspace.

    The tree is the answer the server's own poll last built — `runs.Poll.tree()` — and this only counts
    over it: a folder the tree lists as a workspace holding runs is a folder whose rename or delete would
    leave those records pointing at a folder that no longer stands. The comparison is the tree's own,
    case and separator spelling included, because the tree is what the count is answered from.
    """
    standing = os.path.normcase(os.path.abspath(path))
    return sum(len(workspace.get("runs") or ())
               for workspace in tree.get("workspaces") or ()
               if os.path.normcase(os.path.abspath(str(workspace.get("path") or ""))) == standing)


def parent_folder(path: str) -> str:
    """The folder a name is to be made in or a file received into: it has to be there, and be a folder."""
    if not os.path.exists(path):
        raise PathError(f"no such folder: {path}", 404)
    if not os.path.isdir(path):
        raise PathError(f"not a folder: {path}")
    return path


def name_free(folder: str, name: str, what: str) -> str:
    """The path a fresh name earns in a folder, refused 409 when something already stands there.

    Nothing is overwritten and nothing is joined to what is there — `what` is the word the refusal uses
    for the act being refused, so the sentence names the act the operator asked for and the folder that
    would not take the name.
    """
    target = os.path.join(folder, name)
    if os.path.exists(target):
        raise PathError(f"{name!r} is taken: something already stands in {folder} — {what} refused", 409)
    return target


def make_folder(parent: str, name: str, runs_root: str) -> dict:
    """One new folder: the guards, then the folder, and the path it stands at.

    A race with another hand making the same name is the operating system's answer, not a second check
    here: `FileExistsError` is what the 409 says it would be, and it is given the same sentence.
    """
    parent = parent_folder(not_the_record(parent, runs_root))
    checked_name(name)
    try:
        os.mkdir(os.path.join(parent, name))
    except FileExistsError as taken:
        raise PathError(f"{name!r} is taken: something already stands in {parent} — "
                        "the folder refused", 409) from taken
    except OSError as refused:
        raise PathError(f"cannot make {name!r} in {parent}: {refused}", 403) from refused
    return {"ok": True, "path": os.path.join(parent, name)}


def rename(path: str, name: str, runs_root: str, tree: dict) -> dict:
    """One folder or file, under a new name in the same folder: never a new location.

    The old path is what is guarded and what is moved, and the new one is the old one's own folder with
    the new name on it — so a move across the box is not a thing this route can be asked for, and the
    guard that refuses a workspace's folder refuses the rename whatever the new name is.
    """
    path = not_the_record(path, runs_root)
    checked_name(name)
    if not os.path.exists(path):
        raise PathError(f"no such file or folder: {path}", 404)
    held = workspace_run_count(path, tree)
    if held:
        raise PathError(f"{path} stands as a workspace of {held} run(s): a rename would leave those "
                        "records pointing at a folder that no longer stands", 409)
    target = name_free(os.path.dirname(path), name, "the rename")
    try:
        os.rename(path, target)
    except OSError as refused:
        raise PathError(f"cannot rename {path} to {name!r}: {refused}", 403) from refused
    return {"ok": True, "path": target, "was": path}


def delete(path: str, runs_root: str, tree: dict) -> dict:
    """One file, or one empty folder, off disk: never a folder that holds something.

    Recursion is not a shape this tree has: an act that removes a folder along with its contents is an
    act no operator can be assumed to have meant, so a folder that is not empty is refused with the count
    it holds — and the operator empties it, or does not ask.
    """
    path = not_the_record(path, runs_root)
    if not os.path.exists(path):
        raise PathError(f"no such file or folder: {path}", 404)
    held = workspace_run_count(path, tree)
    if held:
        raise PathError(f"{path} stands as a workspace of {held} run(s): a delete would leave those "
                        "records pointing at a folder that no longer stands", 409)
    if os.path.isdir(path):
        emptied = os.listdir(path)
        if emptied:
            said = "entry" if len(emptied) == 1 else "entries"
            raise PathError(f"{path} is not empty: it holds {len(emptied)} {said} — an empty folder only",
                            409)
        try:
            os.rmdir(path)
        except OSError as refused:
            raise PathError(f"cannot remove {path}: {refused}", 403) from refused
        return {"ok": True, "path": path, "kind": "folder"}
    try:
        os.remove(path)
    except OSError as refused:
        raise PathError(f"cannot remove {path}: {refused}", 403) from refused
    return {"ok": True, "path": path, "kind": "file"}


def upload(folder: str, name: str, source, runs_root: str, length: int = -1) -> dict:
    """The request's own bytes, streamed into one new file under a name the request chose.

    The target folder is guarded and checked, the name is checked, and only then is the file opened: a
    refusal costs the posted bytes nothing — the socket still owes its reader the next request, so the
    body is read and thrown away on every path out of here, which is the same debt the door pays for
    every other route. The bytes go through in chunks and nothing is held whole, so the only limit on an
    upload is the disk's.

    `length` is how many bytes the request named, and it is what bounds the read; a body that ran out
    early leaves the file short, and the answer says how many bytes landed. A negative `length` reads to
    the end of the source, which is what a caller with a real file in hand asks for.
    """
    try:
        folder = parent_folder(not_the_record(folder, runs_root))
        checked_name(name)
        target = name_free(folder, name, "the upload")
    except PathError:
        _spent(source, length)
        raise
    written = 0
    try:
        with open(target, "wb") as handle:
            while length < 0 or written < length:
                blob = source.read(UPLOAD_CHUNK if length < 0 else min(UPLOAD_CHUNK, length - written))
                if not blob:
                    break
                handle.write(blob)
                written += len(blob)
    except OSError as refused:
        _spent(source, length - written)
        raise PathError(f"cannot write {target}: {refused}", 403) from refused
    return {"ok": True, "path": target, "bytes": written}


def _spent(source, remaining: int) -> None:
    """Read the body a refused upload still owes, and drop it: the next request stands behind it.

    A body left in the socket is the pool's next request read at the wrong place — the same fault the
    door's own drain exists to prevent — and a route that refuses an upload before opening the file has
    read nothing of it. A source that gives out early is the end of the body whatever the count said, so
    a short read is the answer and not another refusal.
    """
    while remaining > 0:
        blob = source.read(min(UPLOAD_CHUNK, remaining))
        if not blob:
            return
        remaining -= len(blob)
