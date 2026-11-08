"""sahw.attach — the operator's files, carried into the run's own estate.

A file cannot ride a word: every channel this server has — the spawn's `--task`, the follow's, the queue
block a steer writes — carries text. So the bytes go where the run can reach them and the word names the
place. Each file the request hands over is written into the run's workspace — under its `.sahw` estate,
made on the request that needs it — the folder the run stands in and was granted write to, and the
operator's text then carries one line per file:

    attached: <the absolute path> — read it

**The estate, not the root.** The workspace is the project's own folder — the ground a run stands on and
the tree reads — and a file a browser sends in is not a name that ground should learn: a picture nobody
asked the project for, standing in the root beside the code, is a pollution the record then has to clean.
The estate is one home under one dot-prefixed name, and it stands under the root so the run's grant on
the root reaches it; the root keeps its own contents, and the estate is made only for a body the writer
has already decoded in full, so a request it refuses leaves the workspace exactly as it found it.

That line is part of the word, not an envelope around it. It is written into the same log the run's own
record is written into, so the sentence is there when the run reads its objective, when a later turn reads
the conversation, and when the page paints the row the operator sent; and it is the shape the page reads
back into the file it names, which is why the shape is a constant here rather than a format string in two
routes. A line names an address and asks for a read, so the sentence works the same way whether the file
behind it is a picture the run paints or words the run reads.

**The name is the server's choice.** The original name's extension is kept and its stem is carried over
after a timestamp, because a name the sender chose is a name two sends can spell the same way and a
workspace is not a place where one file may silently stand on another. The timestamp is the fixed part and
a taken name is drawn again, so the name says when the file arrived and never lies about being free; the
characters are the safe ones, because the name arrives from a browser and a workspace is not somewhere a
path gets to travel through. Nothing is looked up in the existing folder: a name is *taken* (exclusive
create), and the draw that loses races with nobody.

**What is refused, and when.** A body that names a list of files which is not a list, an entry that is not
an object, an entry whose name is empty, and a body whose bytes are not base64 are all 400s, and all are
answered before a folder is written or a process started — a request that cannot be honoured is the
caller's, and the answer says so before this tree has done anything that has to be unpicked. A workspace
that is not a folder is refused the same way, and nothing is written for any file when the folder is not
there to hold them.

**No kind is asked, and none is refused.** The writer takes bytes and a name and asks nothing else: a
picture and a file of words are one act here, and every refusal this module makes is about the entry's
shape. Which kinds are worth handing over is the face's decision, and what a name may be *shown* as is the
display paths' — the route that answers a picture's bytes, and the reader that answers a file's words and
refuses what it cannot decode. A file of a kind neither answers still lands as the bytes it was sent as and
its line still rides the word, because a writer that guessed at kinds would refuse a file some reader
would have been glad to show, and a silently dropped attachment is the one failure the sender never hears
about.
"""
from __future__ import annotations

import base64
import os
import re
import time

# The line a file leaves in the word, in the page's own voice: the sentence a run reads and the shape the
# page reads back. Fixed — the transcript's rows, the harness, and the e2e all assert these words, and a
# file the pane cannot find the line for is a file that never arrived as far as the record knows.
REFERENCE = "attached: {path} — read it"

# What a browser-named file may contribute to a folder name: the characters a filesystem and a log line
# both agree on. Anything else becomes a dash, which keeps the shape of what the sender called the file
# without letting the name reach anywhere it was not written.
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

# The workspace's estate for the files the operator sends in: one home, dot-prefixed so it stands apart
# from the project's own ground on a listing, and named for the face that carries a file in.
ESTATE_DIRNAME = ".sahw"


class AttachError(Exception):
    """A file this server will not carry, carrying the HTTP code that says who to blame — 400 for a
    body that cannot be honoured and for a workspace that cannot hold it. The reason and the code travel
    together, as `spawn.SpawnError` and `channel.ChannelError` do, so the routes stay one `except` wide.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def write_files(workspace: str, files) -> list[str]:
    """Write the files the body names into the workspace's estate, and answer their paths in order.

    The workspace is resolved the way the launch resolves it — `expanduser`, then absolute — so the path
    the reference line names is the path the run is granted and the path the browser's pane can list,
    rather than three spellings of one folder. The estate is made after every entry has decoded and only
    for a body that will be written: a refused body leaves the workspace exactly as it found it, no
    folder and no file. An empty body field is not a refusal and not a line: it is the word as it would
    have been typed, so `[]` answers and the caller appends nothing.
    """
    if files is None:
        return []
    if not isinstance(files, list):
        raise AttachError(f"files is not a list: {type(files).__name__}")
    if not files:
        return []
    folder = os.path.abspath(os.path.expanduser(str(workspace or "")))
    if not os.path.isdir(folder):
        raise AttachError(f"the workspace to attach into is not a folder: {folder}")
    taken = [_decode(entry, at) for at, entry in enumerate(files)]
    estate = os.path.join(folder, ESTATE_DIRNAME)
    try:
        os.makedirs(estate, exist_ok=True)
    except OSError as exc:
        raise AttachError(f"cannot open the estate under {folder}: {exc}") from exc
    return [_take(estate, blob, stem, ext) for blob, stem, ext, _name in taken]


def word_with_attachments(text: str, paths) -> str:
    """The word, with one reference line per file: the text and the lines, with a blank line between.

    A word with no paths is the word as it arrived, byte for byte — the route that carried no file must
    not be able to tell it carried one. A word that is only files keeps the lines without a blank line
    above them, because a leading blank line is a paragraph break before anything was said.
    """
    lines = [REFERENCE.format(path=path) for path in paths]
    if not lines:
        return text
    body = text.rstrip("\n")
    if not body.strip():
        return "\n".join(lines)
    return body + "\n\n" + "\n".join(lines)


def _decode(entry, at: int) -> tuple[bytes, str, str, str]:
    """One entry of the body's `files` as (bytes, stem, extension, the name as it arrived)."""
    if not isinstance(entry, dict):
        raise AttachError(f"files[{at}] is not an object: {entry!r}")
    name = str(entry.get("name") or "")
    if not name.strip():
        raise AttachError(f"files[{at}] has no name: a file arrives with the name it was sent as")
    raw = entry.get("bytes")
    if not isinstance(raw, str):
        raise AttachError(f"files[{at}] ({name}) holds {type(raw).__name__}, not base64 text")
    try:
        blob = base64.b64decode(raw, validate=True)
    except ValueError as exc:
        raise AttachError(f"files[{at}] ({name}) is not base64: {exc}") from exc
    stem, ext = _name_parts(name)
    return blob, stem, ext, name


def _take(folder: str, blob: bytes, stem: str, ext: str) -> str:
    """Write the bytes under a name nobody holds yet, and answer the absolute path it was written to.

    The timestamp leads, so the folder reads in the order the files arrived, and the draw is exclusive:
    two attachments named alike in the same second land as `name.png` and `name-2.png` rather than one of
    them overwriting the other.
    """
    base = f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{stem}"
    draw = 0
    while True:
        name = f"{base}{ext}" if draw == 0 else f"{base}-{draw + 1}{ext}"
        path = os.path.join(folder, name)
        try:
            with open(path, "xb") as handle:
                handle.write(blob)
            return path
        except FileExistsError:
            draw += 1
        except OSError as exc:
            raise AttachError(f"cannot write to {path}: {exc}") from exc


def _name_parts(name: str) -> tuple[str, str]:
    """The (stem, extension) this server will spell, from whatever the sender called the file.

    A name arrives from a browser and may hold a path, a Windows path, or nothing worth carrying: only the
    last element is looked at, and only the safe characters of it survive. The extension is lowercased
    because the kind it names is spelled one way on the wire and the sender's casing is not a fact about
    the bytes.
    """
    base = os.path.basename(str(name).replace("\\", "/").rstrip("/"))
    stem, ext = os.path.splitext(base)
    safe_stem = _SAFE_NAME.sub("-", stem).strip("-.") or "file"
    safe_ext = _SAFE_NAME.sub("", ext.lower()).lstrip(".")[:8]
    return safe_stem[:64], f".{safe_ext}" if safe_ext else ""
