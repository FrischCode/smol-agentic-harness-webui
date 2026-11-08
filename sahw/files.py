"""sahw.files — a folder listed and a file read, for the two places the front asks the filesystem.

The listing is the directory browser's and the read is the preview pane's: one path in, one
JSON-shaped value out, with no paging, no search, and no cache — the front asks again when it wants to
look again, which is the only freshness a folder a run is writing into can be promised anyway.

Both read and refuse. A path that is not there, a folder asked of the reader, a binary file asked of
the text reader, a name that claims a kind the picture map does not hold: each is a `FileError` carrying
the HTTP code that says who to blame, so a route is one call and one `except`, and a stray permission or
a stray image never reaches a browser as a traceback.

Readers, and a cap most of them share. `read_file` decodes and refuses what is not text; `read_image`
hands back bytes for the kinds `PICTURE_TYPES` names and refuses what it is not, as the whole bytes the
frame owes, a browser painting a body that stops halfway painting a broken frame; `read_bytes` hands a
file to its download as its whole bytes, and `open_stream` hands it out in chunks to a route that cannot
afford the whole. The last three are the reads the cap has no say in: a body that stops at the cap is a
file's head, not a file — the head of a text is what the capped reader's flag names, and the head of a
picture is the frame the browser paints broken. The text
reader never learns a picture's bytes, and the picture reader never learns a text file's mime — the
refusal each raises is what tells a caller that it asked the wrong reader, and the bytes readers refuse
no kind at all, because the bytes the disk holds are exactly what a download answers for.
"""
from __future__ import annotations

import os

# The most text one response will carry. A preview pane shows a screen; a file larger than this arrives
# clipped rather than as a wait, and the flag says so rather than leaving the reader to find the seam.
READ_CAP = 256 * 1024

# The picture kinds this API answers, by the extension that claims them, each with the mime to answer it
# with: the kinds a run's `read` can hand back as a receipt, plus the two containers a browser paints from
# the same three letters a record names. Named here rather than asked of the platform's registry, because
# the mime a browser is handed decides whether it paints a picture or offers a file for download, and
# that must not depend on what else is installed. `.jpg` and `.jpeg` are one kind with two spellings, and
# both are answered `image/jpeg` because that is the name the kind carries on the wire.
PICTURE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}


class FileError(Exception):
    """A path the API cannot answer for, with the code that names the kind of not-working.

    404 when the path is not there, 415 when it is there but is not the kind the route asked for — not
    text asked of the text reader, not a picture asked of the picture reader — 400 when it is there, is
    not what the route asked for at all, or cannot be opened. The code is decided here, at the one place
    that has looked at the path, so the routes stay about the response.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def list_dir(path: str) -> list[dict]:
    """One folder as `[{"name": ..., "dir": ...}]`: directories first, then files, each alphabetical.

    Folders lead because the browser is a person walking towards a workspace, and a sort that files
    `Zebra/` after `apple.txt` makes them scan the whole list to be sure they have seen the folders. The
    comparison ignores case, because the names on this box's filesystem were not written case-consistently
    and a sort that separates `docs` from `Docs` by a code point is a sort with two of everything.

    Everything in the folder is listed, dot-prefixed names included: the browser offers the folder as it
    is, and a directory whose name begins with a dot is a place a run is started as often as any other.
    """
    if not os.path.exists(path):
        raise FileError(f"no such path: {path}", 404)
    if not os.path.isdir(path):
        raise FileError(f"not a folder: {path}")
    try:
        names = os.listdir(path)
    except OSError as exc:
        raise FileError(f"cannot read {path}: {exc}", 403) from exc
    entries = [{"name": name, "dir": os.path.isdir(os.path.join(path, name))} for name in names]
    entries.sort(key=lambda entry: (not entry["dir"], entry["name"].lower(), entry["name"]))
    return entries


def read_file(path: str) -> tuple[str, bool]:
    """One file as (text, truncated), read to at most `READ_CAP` bytes.

    Read as bytes and decoded here, because the cap counts bytes and a byte is not a character: a cut at
    the cap can land inside a multi-byte character, and a preview that dies on the cut is a preview of
    nothing. So a clipped read hands back everything up to the last whole character and only loses what
    was never read.

    A file that is not text is refused rather than returned with replacement characters: a binary file in
    a preview pane is a mistake about what the file is, and the most useful answer to that is the sentence
    that says it.

    Line endings arrive as the platform wrote them but are handed back normalized: the preview shows text,
    not the file's bytes, and a pane that renders a file's `\r\n` as a blank line is a pane that misshows it.
    """
    if not os.path.exists(path):
        raise FileError(f"no such file: {path}", 404)
    if os.path.isdir(path):
        raise FileError(f"not a file: {path}")
    try:
        with open(path, "rb") as handle:
            blob = handle.read(READ_CAP + 1)
    except OSError as exc:
        raise FileError(f"cannot read {path}: {exc}", 403) from exc
    truncated = len(blob) > READ_CAP
    if truncated:
        blob = blob[:READ_CAP]
    try:
        return blob.decode("utf-8").replace("\r\n", "\n"), truncated
    except UnicodeDecodeError as exc:
        if not truncated:
            raise FileError(f"not utf-8 text: {path}", 415) from exc
        for back in range(1, 4):
            try:
                return blob[:-back].decode("utf-8"), True
            except UnicodeDecodeError:
                continue
        raise FileError(f"not utf-8 text: {path}", 415) from exc


def read_bytes(path: str) -> bytes:
    """One file as its whole bytes: the read a download owes, and the only read this module has without
    the cap.

    A download is the file as it is on the disk, and a body that stops at the cap is not a file — it is
    a file's head, the head the preview's flag already names on the other route. So the read goes to the
    end of the file and stops, with no decoding and no normalizing: a download that smooths the line
    endings or re-encodes a character is a download that rewrites the file, and the bytes it hands the
    browser are the file's own, in the order the disk wrote them.

    The refusals are the two readers', in the shape they already stand: 404 for a path that is not
    there, 400 for a folder or a file that cannot be opened, 403 when the operating system says no.
    """
    if not os.path.exists(path):
        raise FileError(f"no such file: {path}", 404)
    if os.path.isdir(path):
        raise FileError(f"not a file: {path}")
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as exc:
        raise FileError(f"cannot read {path}: {exc}", 403) from exc


def open_stream(path: str) -> tuple[object, int]:
    """One file, opened for its whole bytes, and how many of them there are: the raw route's reader.

    The handle rather than the bytes, because the route that answers with them cannot hold them: a file
    the size of a disk is a body of that size, and a server that buffered it would be a server that ran
    out of memory answering a download. The count comes back with the handle so the response can name a
    `Content-Length` the body will honour, read off the opened file rather than off a second look at the
    path — the two are the same file, and a route that asked twice could be handed two answers.

    The refusals are the bytes reader's, asked before anything is opened: 404 a path that is not there,
    400 a folder, 403 what the box itself refused. Whoever holds the handle closes it.
    """
    if not os.path.exists(path):
        raise FileError(f"no such file: {path}", 404)
    if os.path.isdir(path):
        raise FileError(f"not a file: {path}")
    try:
        handle = open(path, "rb")
    except OSError as exc:
        raise FileError(f"cannot read {path}: {exc}", 403) from exc
    try:
        return handle, os.fstat(handle.fileno()).st_size
    except OSError as exc:
        handle.close()
        raise FileError(f"cannot read {path}: {exc}", 403) from exc


def picture_type(path: str) -> str:
    """The mime `path` claims, or "" when its extension names no picture kind.

    The extension is the claim and this only reports it — deciding whether the bytes are what the name
    says is a reader with the bytes in hand, and this answer is what a route chooses a response's
    `Content-Type` from. The lookup ignores case, because the names on this box's filesystem were not
    written case-consistently and `Shot.PNG` is the same kind as `shot.png`.
    """
    return PICTURE_TYPES.get(os.path.splitext(path)[1].lower(), "")


def read_image(path: str) -> bytes:
    """One picture as the whole bytes of the file: the read a picture owes a browser, which is the whole
    file — a frame painting a body that stops halfway paints a broken frame, and the clipping the text
    reader's flag names has no seam to land in a body the browser paints.

    The bytes, never a decoding: a picture has no character encoding to normalize and line endings to
    smooth, and what a browser paints is the file as written. The text reader's cap has no say here:
    it is one response's worth of text, and a picture is the kind of file the transcript and the pane
    point the browser at, for which the answer is the file, not its head.

    The refusals are the text reader's shape: 404 for a path that is not there, 400 for a folder or a file
    that cannot be opened, 403 when the operating system says no. A name `picture_type` does not recognise
    is 415 — the same code the text reader raises for a file that is not text, because it is the same
    answer to the same question: this route was asked for the wrong kind of file.
    """
    if not os.path.exists(path):
        raise FileError(f"no such file: {path}", 404)
    if os.path.isdir(path):
        raise FileError(f"not a file: {path}")
    if not picture_type(path):
        raise FileError(f"not a picture: {path}", 415)
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as exc:
        raise FileError(f"cannot read {path}: {exc}", 403) from exc
