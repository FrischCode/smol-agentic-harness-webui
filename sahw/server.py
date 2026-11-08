"""sahw.server — the HTTP surface: the front as files, the API as JSON, and one log as a stream.

One handler class and twenty-four routes. Each route reads what it answers from the module that owns the fact
— `runs` for the tree, the stream and what the record says the session's dials stand on, including the
machine's verdict on a run's process that a row carries and the one-line name file that is the face's own
word for a run, `files` for the browser, the preview and a picture's bytes, `fspath` for the four changes
the spawn pane can ask a folder to make and the guards that
let them run, `models` for the profiles this machine's registry declares, `spawn` for a run and the
dials a run opens on, `channel` for a word to one that exists, the console line that moves one that rests,
and the process its log names, `attach` for the files a word arrives with, `export` for a run's transcript
as a file, `purge` for taking one (or a whole workspace's worth) off disk, `openers` for showing a folder
or a file to the operator — so this module's whole job is the shape of a request and the shape of a
response, and no fact is decided twice.

**The server holds nothing about a run.** A started run is a child of this process and no handle to it is
kept: the record and the machine answer every question a route asks, the log for what the run is and the
process table for whether the `pid` it stamped is still there. That is what lets two runs work at once and
what makes switching to another run, or reloading the page, nothing at all to a run — a process lives its
objective's lifecycle, not the selection's. The one act that reaches a process, the kill of the one a log
names, is `channel.kill_first`, asked by two routes and by nothing else: the stop route on its own, and the
follow the message route carries before it relaunches. The stop asks it only of a number the tree's poll
vouches for — a number can be given to another process, and that one is not this run's to end (see
`runs.Poll.rebirthed`).

**Two answer shapes, and the line between them.** `{"error": "<sentence>"}` with the 4xx the route names is
what a request that cannot be honoured gets — the path that is not there, the id that is a path, the body
that is not an object. `{"ok": true | false, ...}` is what an act gets: the request was understood, this
server went and did it, and the answer is whether it happened. An act that the machine refused — a run whose
process is still writing its log, a folder whose window would not open — is not a caller's mistake and is not
answered as one; it answers 200 with `ok: false` and the reason, so the page can read the sentence from the
same shape it reads the success from.

The one exception is deliberate: the spawn pane's four mutations answer `{"error": ...}` with the 4xx
`fspath.PathError` names, including the 409 that says *something already stands there*. The reason is that
a refusal about a path has to be read by the page the way a wrong path is read — one error path, the
sentence standing in the pane's note — and an act that half-happened is not something these routes know
how to claim: a rename that was refused left the folder exactly where it was, and `ok: false` beside a
200 would say the request was honoured and the answer was no.

**The shapes are the contract.** The front is built against the JSON this answers, and every value is
JSON-dumped from a dict written out here rather than from an object that happens to serialise: a
response is then readable in one place, in the order the reader of the API wants it, and adding a field
is a line that says what it is.

**Threading is the design, not a tuning knob.** A stream holds its connection open for as long as a run
runs — that is what a stream of a live run is — so a server that answered one request at a time would be
a UI that could not list the run it was streaming, and a page would hang on the one thing it opened.
Every connection is therefore its own thread, and those threads are daemons: they end when the server
ends, and a stream nobody closed is not a reason for a stopped server to stay alive.

**Errors are one shape.** `{"error": "<sentence>"}` with the 4xx the route names, from the same
exception the modules below raise — a path that is not there, a folder that is not a folder, a run with
no objective. The front has one error path, and a sentence is what tells an operator which flag to fix.
"""
from __future__ import annotations

import json
import os
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from sahw import attach, channel, envfile, export, files, fspath, models, openers, purge, runs, spawn

# The front's files, named rather than asked of the platform's mime registry: a stylesheet served as
# `application/octet-stream` by one machine's registry is a blank page, and the answer a browser is
# given must not depend on what else is installed. The kit's four icon types are the same claim about a
# smaller thing: a tab icon served as octet-stream is a broken face, and so is a manifest no browser
# was told was a manifest.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webmanifest": "application/manifest+json",
}

# The bytes one read of a streamed download carries: the raw route's whole body is this much at a time,
# so the memory a download costs is this number and not the file's size.
RAW_CHUNK = 64 * 1024

# The sentence the stop route owes the pane when there is nothing to stop, shaped like `channel.BUSY`: a
# stop names a process to end, and a settled run has none — its own log said so, or the machine did. The
# reader is owed what to do instead, which is a word to the run: a follow starts the next objective.
NOTHING_TO_STOP = "nothing to stop: the run's process is not live — send it a word to continue it"

# The sentence the same route owes when the number the record names answers live and is not the run's
# process — the number was given to another process while the record stood silent, so the machine that
# would end it would end a stranger the operator never named. The act is refused in full: nothing is
# ended, and the row keeps the dead verdict the record's silence stands (see `runs.Poll.rebirthed`).
NOT_THE_PROCESS = ("nothing ended: the number this run's record names answers live, but the process "
                   "behind it is not the one the record named")


class Site:
    """What a request needs beyond the request: the runs root to list, the SAH tree to launch from, the
    folder of front files to serve, the terminal this box was found to have, and the window the open act
    owes — or its refusal, when the server was started with `--no-open`.
    Defaulted to the tree this
    package sits in, so the server run from the checkout needs no flags to answer.

    The terminal is probed here, once, because it is a fact about the machine's path and not about a
    request: `openers` answers Windows Terminal or `cmd.exe`, and every act that opens a folder hands over
    the answer rather than asking again. A server started on a box with no Windows Terminal therefore opens
    a `cmd` console instead of failing to find a program that was never there.

    The window is owed, or refused, the same way: it is a fact about the server's own startup, not about a
    request. A server started with `--no-open` — the e2e discipline, that a probe's server never opens what
    an operator would open — answers the open act with its named refusal before the spawn is asked, and the
    operator's machine keeps its windows for the face's own server.

    Six facts and no state about the runs: what a run is doing is answered from its log and from the
    process table, not from anything this server remembers. A run it started is no different from a run
    the operator started by hand, which is what makes the page's attention irrelevant to the work.

    One thing is remembered, and it is remembered *over* the record rather than instead of it: the rows
    the tree's poll last answered, held per runs root beside the size and mark of the log each was read
    from (see `runs.Poll`). It is the server's working memory and not a second record — nothing in it
    persists, nothing in it is a fact the logs do not hold, and every entry is a re-read away from being
    recomputed.

    The stream's poll is a fact of the server's own startup: how often a followed run's stream asks its
    log whether it grew, in seconds. The record and the trace ride that one rhythm together — the trace
    is drained once per look (see `runs.stream_lines`) — so the pace is the pace of both, and the face
    fills as fast as the server looks. A server started without a word stands on the shipped default
    (`runs.POLL_SECONDS`); the command line and the environment are the voices that move it.
    """

    def __init__(self, runs_root: str, sah_tree: str = "", web_dir: str = "",
                 open_paths: bool = True, stream_poll: float = runs.POLL_SECONDS):
        self.runs_root = runs_root
        self.sah_tree = sah_tree
        self.web_dir = web_dir or os.path.join(envfile.repo_root(), "web")
        self.terminal = openers.terminal_program()
        self.open_paths = open_paths
        self.stream_poll = stream_poll
        self.polls: dict[str, runs.Poll] = {}

    def poll(self, runs_root: str = "") -> runs.Poll:
        """This server's working memory over a runs root: the rows it last answered from there, made on
        the first asking. Keyed by the root rather than held once, because the memory belongs to the
        record it stands over — two roots served by one server are two records, and a page read from one
        has nothing to say about the other. Defaults to the root the server was started on, which is the
        root the tree asks about."""
        root = runs_root or self.runs_root
        held = self.polls.get(root)
        if held is None:
            held = self.polls[root] = runs.Poll(root)
        return held


class _Refused(Exception):
    """A request this server answers with an error rather than a result, carrying the code."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    """Every route, as methods on one class. `self.server.site` is the `Site` the server was made with.

    HTTP/1.1 on purpose: the clients that stand against this server (a browser, a fetch with a pooled
    connection) speak 1.1, and a handler that answers 1.1 requests with 1.0 status lines desyncs the
    pool that sent them — the request's keep-alive stands open on the server's side while the 1.0 word
    tells the client the connection is spent, and the two sides end up closing the same socket at
    different moments. 1.1 makes the version one fact both sides hold, and every route that answers
    already sends the `Content-Length` the version requires; the one that does not (the stream) says
    `Connection: close` and lets the closing delimit it.
    """

    server_version = "sahw/0.1"
    sys_version = ""          # the response names this server, not the interpreter's build
    protocol_version = "HTTP/1.1"

    # --- the verbs, each dispatching once and translating once ----------------------------------------

    def do_GET(self):
        try:
            self._get()
        except (_Refused, files.FileError) as refused:
            self._error(refused.status, str(refused))

    def do_POST(self):
        try:
            self._post()
        except (_Refused, files.FileError, fspath.PathError, spawn.SpawnError, channel.ChannelError,
                attach.AttachError) as refused:
            self._error(refused.status, str(refused))

    def _get(self):
        parsed = urlparse(self.path)
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if not parts:
            return self._static("index.html")
        if parts[0] == "api":
            return self._api_get(parts, parsed.query)
        if parts == ["img"]:
            return self._image(parsed.query)
        return self._static("/".join(parts))

    def _api_get(self, parts: list[str], query: str):
        if parts[1:] == ["runs"]:
            return self._json(200, self.server.site.poll().tree())
        if parts[1:] == ["models"]:
            return self._models()
        if parts[1:] == ["fs"]:
            return self._list_dir(query)
        if parts[1:] == ["file"]:
            return self._read_file(query)
        if parts[1:] == ["file", "raw"]:
            return self._raw_file(query)
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "stream":
            return self._stream(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "report":
            return self._report(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "dials":
            return self._dials(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "export":
            return self._export(parts[2], query)
        raise _Refused(404, f"no such endpoint: /{'/'.join(parts)}")

    def _post(self):
        # The body, read once at the door, before any route decides: the routes that take one read it
        # from the stash, and the ones that take none still owe the connection its bytes. A body left in
        # the socket is the pool's next request read at the wrong place, and the method that request is
        # refused with is this one's leftovers: a stop that sends two bytes and reads none otherwise
        # answers the listing that follows with a 501 whose method is those two bytes.
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError as exc:
            raise _Refused(400, f"Content-Length is not a number: {exc}") from exc
        parts = [unquote(part) for part in urlparse(self.path).path.split("/") if part]
        # The upload is the one route whose body is not a document about the request but the thing itself,
        # so it is dispatched before the drain: its reader is the file, and a route that stashed the bytes
        # to answer it would be a route that held a whole upload in memory to write it out again. The debt
        # the drain exists to pay is still paid — `fspath.upload` reads the body to its end on every path
        # out of here, refusal included — it is just paid a chunk at a time, into the file.
        if parts == ["api", "fs", "upload"]:
            return self._upload_file(urlparse(self.path).query, length)
        self._drained = self.rfile.read(length) if length > 0 else b""
        if parts == ["api", "runs"]:
            return self._create_run()
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "message":
            return self._post_message(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "command":
            return self._post_command(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "fork":
            return self._fork_run(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "stop":
            return self._stop_run(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "compact":
            return self._post_compact(parts[2], stop=False)
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "compact-stop":
            return self._post_compact(parts[2], stop=True)
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "rename":
            return self._rename_run(parts[2])
        if len(parts) == 4 and parts[1] == "runs" and parts[3] == "delete":
            return self._delete_run(parts[2])
        if parts[1:] == ["runs", "delete-all"]:
            return self._delete_all_runs()
        if parts == ["api", "open"]:
            return self._open_path()
        if parts == ["api", "fs", "mkdir"]:
            return self._make_folder()
        if parts == ["api", "fs", "rename"]:
            return self._rename_path()
        if parts == ["api", "fs", "delete"]:
            return self._delete_path()
        raise _Refused(404, f"no such endpoint: /{'/'.join(parts)}")

    # --- the routes ------------------------------------------------------------------------------------

    def _static(self, relative: str):
        """`GET /` and `GET /<name>`: one file from the front's folder, and nothing outside it.

        The containment check is the whole guard, and a request that climbs out — a `..`, a second drive,
        a link pointing elsewhere — gets the same answer as a file that was never there, because this
        route is not the one that says which folders exist outside the folder it serves.
        """
        root = os.path.realpath(self.server.site.web_dir)
        path = os.path.realpath(os.path.join(root, relative))
        if not path.startswith(root + os.sep) or not os.path.isfile(path):
            raise _Refused(404, f"no such file: /{relative}")
        try:
            with open(path, "rb") as handle:
                body = handle.read()
        except OSError as exc:
            raise _Refused(500, f"cannot read /{relative}: {exc}") from exc
        self._send(200, body, CONTENT_TYPES.get(os.path.splitext(path)[1].lower(),
                                                "application/octet-stream"),
                    os.path.getmtime(path))

    def _list_dir(self, query: str):
        """`GET /api/fs?path=<folder>`: the folder's entries, dirs first."""
        path = _query_value(query, "path")
        entries = files.list_dir(path)
        self._json(200, {"path": path, "entries": entries})

    def _read_file(self, query: str):
        """`GET /api/file?path=<file>`: the file's text, to the preview's cap, with the flag that says
        whether the cap bit — or, with `&download=1`, the file's own bytes whole, with the name the
        browser saves them under.

        The flag changes the answer's shape, not its reach: the same path, the same refusals, and a
        reader that owes the file as it is on the disk. A picture file is the one file this route does
        not read as words, and the one file a download does not answer as a picture: the bytes go out
        with the mime their extension claims, so the two addresses can never disagree about what a
        file is, and a picture asked for its download is its bytes, whole, not the frame's clipped
        read. Text, which is what every other file gets as words, is unchanged.
        """
        path = _query_value(query, "path")
        if _query_value(query, "download", required=False) == "1":
            self._send_download(path)
            return
        if files.picture_type(path):
            self._send_picture(path)
            return
        text, truncated = files.read_file(path)
        self._json(200, {"path": path, "content": text, "truncated": truncated})

    def _models(self):
        """`GET /api/models`: the profiles this machine's registry declares, as a picker stands on them.

        The registry is the operator's file — `data/models.json` in the SAH tree this server launches runs
        from — and it is read through `models`, which owns its shape, so the answer is the profile as the
        machine declared it, every field of it but the one `models.SECRET_FIELDS` keeps home. Nothing is
        invented beside it and nothing is defaulted: an empty table answers an empty list, and the face
        that reads one has no entry to offer. One word rides beside the table: `machine` is the reference a
        run launched from this tree speaks as when nothing names a model — `SAH_MODEL`, then the tree's
        `.env`, then nothing — which is the stand the picker holds before any run names one, and it is in
        the answer rather than worked out at the face because it is the machine's fact, read from where the
        machine keeps it.

        **The refusals are as load-bearing as the answer.** A face that stood a model list of its own
        behind a refused route would be a face lying about the machine, so each refusal is the sentence
        somebody could act on: this server names no SAH tree (the standing sentence every route that would
        have launched from that tree gives), this tree holds no `data/models.json` — which is a machine
        that declares no profiles rather than a broken one — and a file that is not the shape, refused in
        `models`' own words, naming the profile and the key at fault. All three answer 503, because the
        machine cannot answer this question today and nothing the request could be re-typed as would change
        that; the face's standing in each case is to say the sentence and offer no choice.
        """
        if not self.server.site.sah_tree:
            raise _Refused(503, "this server names no SAH tree: pass --sah-tree or set SAHW_SAH_TREE")
        tree_dir = os.path.abspath(os.path.expanduser(self.server.site.sah_tree))
        try:
            profiles = models.listed(tree_dir)
        except models.ModelError as exc:
            raise _Refused(503, str(exc)) from exc
        if profiles is None:
            raise _Refused(503, "the machine declares no model registry: no data/models.json under "
                                f"{tree_dir}")
        self._json(200, {"models": profiles, "machine": models.model_reference(tree_dir)})

    def _image(self, query: str):
        """`GET /img?path=<file>`: one picture's bytes, with the mime its extension claims.

        One route, two readers: the transcript's rows — a `read` whose answer carried the receipt, and an
        operator's attachment named by its reference line — and the preview pane, both pointing at this
        address for the same file. `files.read_image`'s refusals are this route's, in the one error shape:
        404 for a path that is not there, 415 for a name that claims no picture kind, 400 for a folder or
        a file that cannot be opened, 403 when the operating system says no.

        **The reach is the browser's, and so is the one rule that comes with it.** The pane walks this
        box's folders from a drive root, so `/api/fs` and `/api/file` already answer any folder the box
        lets them and this route reads no more than they do. What it will not do is resolve a name against
        the folder the server happens to stand in: the page asks for the absolute paths the record and the
        browser hold, and a relative name resolves under no root at all, so it is refused rather than
        guessed at.
        """
        self._send_picture(_absolute(_query_value(query, "path")))

    def _send_picture(self, path: str):
        """The bytes and their mime in one response — what `/img` answers, and what a picture file opened
        from the browser is answered with.

        The mime comes from the extension `files.read_image` accepted, so body and `Content-Type` cannot
        disagree, and a browser painted from a pair that does is shown a broken frame. A picture arrives
        as the file on disk: the read the frame owes is the whole bytes, and a clipping the text reader's
        flag names is a seam the browser would paint into the picture itself.
        """
        blob = files.read_image(path)
        self._send(200, blob, files.picture_type(path), os.path.getmtime(path))

    def _send_download(self, path: str):
        """`GET /api/file?path=<file>&download=1`: the file's own bytes, unclipped, with the name the
        browser saves them under.

        The one reader this route owes is the one that wants the file as it is on the disk, and the
        pane's cap has no place in that answer: a body that stops at the cap is not a file, it is a
        file's head, and the head is what the other route's flag already names. So the read goes to the
        end of the file (`files.read_bytes`), and the mime is the one that says *a thing the browser
        keeps* — not one it paints, and not one it reads: a picture asked as a download is its bytes,
        and a text file asked as a download is its bytes, line endings and all.

        The name the browser saves the bytes under is the file's own, in the header a download owes it
        — `Content-Disposition`, the basic form, and the name escaped the way that form owes a name
        that holds a quote. The refusals are the readers': 404 a path that is not there, 400 a folder
        or a file that cannot be opened, 403 what the box itself refused.
        """
        blob = files.read_bytes(path)
        self._send(200, blob, "application/octet-stream", os.path.getmtime(path),
                   disposition=f"attachment; filename={_download_name(path)}")

    def _raw_file(self, query: str):
        """`GET /api/file/raw?path=<file>`: the file's bytes, streamed, under the name it is saved as.

        The download the preview route already answers reads a whole file into memory to answer it, which
        is the right debt for a run's report and the wrong one for whatever the spawn pane is standing
        beside: a pane offered the box's own folders is offered artifacts — a database, an archive, a
        build output — and a route that holds one whole before it answers is a route that runs out of
        memory on the largest file on the disk. So this route reads in chunks and writes in chunks, and
        the only size it names is the one the file's own record gives.

        Nothing about the answer differs from the preview's download: the same octet-stream the browser
        keeps rather than paints, the same `Content-Disposition` name, the same no-cache and
        `Last-Modified`. It is a second address for one act, chosen because the pane's rows want an
        address of their own to put in an anchor, and because a route whose whole job is *the bytes*
        needs no flag on it to be asked for them.

        **The reach is the picture route's, and so is the guard that comes with it** — absolute paths
        only, and no rule about which folders, because the listing and the preview already answer any
        folder the box lets them. What is *not* here is the preview's cap: the caps on `/img` and the
        preview route stand on report-shaped answers, and a file offered for download is not an answer,
        it is the file. The refusals are the bytes reader's, asked before a single header goes out: 404 a
        path that is not there, 400 a folder, 403 what the box itself refused — and after the headers, no
        refusal at all: a reader that stopped listening mid-file has nobody left to be told anything, so
        the write is finished or abandoned, and the socket's end is the only witness.
        """
        path = _absolute(_query_value(query, "path"))
        handle, size = files.open_stream(path)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Last-Modified", formatdate(os.path.getmtime(path), usegmt=True))
            self.send_header("Content-Disposition", f"attachment; filename={_download_name(path)}")
            self.end_headers()
            while True:
                blob = handle.read(RAW_CHUNK)
                if not blob:
                    break
                self.wfile.write(blob)
        except OSError:
            pass        # the reader went away mid-file; there is no response left to complete
        finally:
            handle.close()

    def _run_folder(self, run_id: str) -> str:
        """The run's folder under the runs root, once the id has been checked for being an id.

        A run id is one folder name and never a path: it is the handle the API was handed by a browser,
        and a route that joined it straight to the runs root would be a route that reads any folder the
        caller names. The shape rule is the cheap half; the folder then has to exist, which is the
        difference between "not a valid id" and "no such run".
        """
        if (not run_id or run_id in (".", "..") or run_id != os.path.basename(run_id)
                or "/" in run_id or "\\" in run_id):
            raise _Refused(400, "a run id is one folder name, not a path")
        folder = os.path.join(self.server.site.runs_root, run_id)
        if not os.path.isdir(folder):
            raise _Refused(404, f"no such run: {run_id}")
        return folder

    def _report(self, run_id: str):
        """`GET /api/runs/<id>/report`: the Markdown a finished run left beside its log, as text.

        The read is the preview's, cap and all: a report is a run's final answer, and a report long
        enough to reach the cap is not something a sidebar was going to show anyway. The flag the cap
        sets has nowhere to go in a text body, so a report over the cap simply arrives shorter.
        """
        report = os.path.join(self._run_folder(run_id), runs.REPORT_NAME)
        if not os.path.isfile(report):
            raise _Refused(404, f"no report for run {run_id}")
        text, _ = files.read_file(report)
        self._send(200, text.encode("utf-8"), CONTENT_TYPES[".txt"])

    def _dials(self, run_id: str):
        """`GET /api/runs/<id>/dials`: what the record says the session's two dials stand on.

        The pair is the run's own record read back (see `runs.dials`): the model's name, the address a
        switch named beside it, and the reasoning level — each the newest statement of it, the console's
        notice over the opening step it follows and that step over every notice before it. Nothing is kept
        between calls and nothing is asked of the machine, and that is the point of the route: it is what
        lets the face's picker and dial settle on the record instead of on the last click, so a pane that
        re-asks it after a switch is a pane whose controls answer to what the log says rather than to what
        the operator meant to do.

        Each field answers null when the record does not state it, and null is an answer rather than a
        failure: a log with no opening step names no model, and the face's standing there is the machine's
        own default with the reason for it in the note hand. Only a run this server holds no folder for is
        refused, in the one error shape every run route refuses with.
        """
        self._json(200, runs.dials(os.path.join(self._run_folder(run_id), runs.LOG_NAME)))

    def _stream(self, run_id: str):
        """`GET /api/runs/<id>/stream`: the log's lines as server-sent events, then the ending frame.

        One frame per step — `event: step`, then the raw log line as `data:` — so the front tells a step
        apart from the end of the stream without parsing the transport. The ending is not re-sent as a
        step frame: the line that ends a run is the end, and a frame that announced it twice would be a
        step that was not a step. The one closing frame is how a client that cannot tell a finished run
        from a quiet one is told. The connection then closes: the stream is over, and keeping it open
        would be a connection held for a run that is not running.

        **The run's trace rides the same connection under its own event name: `event: delta`.** SAH
        writes `<run-dir>/live.jsonl` when the run was started with `--live`, and a pane that read only
        the record would show a long turn as silence and then a wall of prose. The trace is drained once
        per poll of the log, after that poll's step frames (`runs.stream_lines`'s `on_look`), and once
        more after the log's ending line before the closing frame — that last look is the ending round's,
        which is the one round the log's reader leaves early. The raw trace line goes out as `data:` the
        way the log line does, and the order across the two files is by discovery, not by write time:
        within each file the writer's own order is what settles a face, and a fragment never needs the
        other file's clock. These frames are the trace, not the record — what a fragment carries is what
        the whole step settles — and a run with no trace file is answered with the step frames alone,
        byte for byte what this route answered before the trace existed.
        """
        log_path = os.path.join(self._run_folder(run_id), runs.LOG_NAME)
        if not os.path.isfile(log_path):
            raise _Refused(404, f"no log for run {run_id}")
        live_path = os.path.join(self._run_folder(run_id), runs.LIVE_NAME)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        # The record is replayed whole - that is the stream's answer to the reader who arrived late. The
        # trace is not replayed: a connection that found the file already written follows it from the
        # end, and a connection that found it absent follows it from its first word, which is every word
        # of the run that is not in the record yet. A fragment of a turn the record has settled, delivered
        # after the step that settled it, would stand the closed turn's face back up in the pane - the
        # pane settles positionally (a fragment owes the turn in flight) and has no way to tell a replayed
        # word from a spoken one. The file keeps every word the stream withholds: the play of them is the
        # face the plan leaves to the file, and the stream owes the live.
        try:
            live_offset = os.path.getsize(live_path)
        except OSError:
            live_offset = 0

        def drain_trace() -> None:
            """The fragments that arrived since the last look, each as its own frame.

            Raw as the file holds them, the way the step frames carry the log. One look, not a following:
            this runs inside the log's own poll, and a reader that waited here for the next fragment would
            leave the record unread in the middle of a stream — the ending with it. A run with no trace
            file costs this call one failed open per poll and writes nothing.
            """
            nonlocal live_offset
            fragments, live_offset = runs.live_look(live_path, live_offset)
            for fragment in fragments:
                self.wfile.write(b"event: delta\ndata: " + fragment + b"\n\n")
                self.wfile.flush()

        stream = runs.stream_lines(log_path, on_look=drain_trace, poll=self.server.site.stream_poll)
        try:
            for line in stream:
                if not runs.is_ending(line):
                    self.wfile.write(b"event: step\ndata: " + line + b"\n\n")
                    self.wfile.flush()
            drain_trace()
            self.wfile.write(b"event: ended\ndata: done\n\n")
            self.wfile.flush()
        except OSError:
            # The reader went away mid-frame — the page navigated, the tab closed. That is how a front
            # stops a stream a run is still writing, and the only way this loop ends early.
            pass
        finally:
            stream.close()

    def _create_run(self):
        """`POST /api/runs`: start a run, and answer 201 with its id as soon as it has one.

        The reply is not an acknowledgement of the work — it is the run's id, which is why the folder is
        claimed before the child is started: by the time the id is in the response, the log the stream
        route follows already has a home. Nothing is kept of the child beyond that id: the run works its
        objective, writes its log, and exits, and every later question about it is answered from those two.
        `think`, when the body names one, rides to the child's `--think` verbatim; an empty one is not sent,
        and the machine's own default applies. `model` rides the same rule and for the same reason: an id
        the picker stands on is passed to `--model` verbatim, and an empty one is the machine's default —
        this server never resolves a profile against the registry, since the console that launches reads it
        and would refuse a name it does not hold in its own words.

        **The body's optional `files` field is the operator's files, carried into the run's estate** —
        pictures and words alike, since this route asks nothing of a file but its name and its bytes. Each
        is decoded and written into the `.sahw` estate of the workspace the run is about to stand in — the
        folder the spawn grants it write to — under a name this server chooses, and the objective then
        carries one reference line per file. The writing is the first thing this route does, before a
        folder is claimed: a body whose base64 does not decode, or whose file has no name, or whose
        workspace is not a folder, is the 400 that starts nothing — and leaves the workspace exactly as it
        found it, estate included — because a run launched on a file that never arrived would open its
        objective looking for a file the record then claims. With no `files` the objective is the words as
        they were typed, byte for byte.
        """
        body = self._body()
        workspace = str(body.get("cwd") or "")
        task = str(body.get("task") or "")
        think = str(body.get("think") or "")
        task = attach.word_with_attachments(task, attach.write_files(workspace, _attached(body)))
        run_id = spawn.spawn_run(self.server.site.runs_root, self.server.site.sah_tree,
                                 workspace, task,
                                 max_turns=_body_int(body, "max_turns",
                                                     spawn.DEFAULT_MAX_TURNS),
                                 max_runtime=_body_int(body, "max_runtime",
                                                       spawn.DEFAULT_MAX_RUNTIME),
                                 think=think, model=str(body.get("model") or ""))
        self._json(201, {"run_id": run_id})

    def _post_message(self, run_id: str):
        """`POST /api/runs/<id>/message`: one word into a run that already exists.

        One route, because the page does not choose how a word arrives — `channel` decides that from the
        run's record and the machine's verdict, answering which way it went: `steer` put the words in the
        run's queue to be read at its next turn boundary, `follow` started a new objective on the run's own
        log. A settled run is followed whoever started it and whatever its process is doing on its way out,
        because a follow is the one arrival that ends the process the log still names before it writes that
        log again — no page holds anything that can be in the way of it, and no page's attention keeps a run
        from settling.

        **The body's optional `cut` is the step the conversation returns to**, the digits as logged, and it
        is the arrival that names its own channel: a cut rebuilds the conversation from the prefix ending at
        that step, which only a relaunch does, so the word is posted as a follow and the follow argv carries
        `--resume <cut>` where 05 sent bare `--resume`. Nothing about the record has to be re-asked for the
        answer — `channel` places a named follow on an ended run the way it places any other follow — but
        the step is checked against the log first: a number the log does not hold, or one it holds only in a
        detached lineage, is the 400 that names the step and the log's last step, and it is answered before a
        process is stopped or started, since a refusal that arrived after the kill would have destroyed the
        run it was refusing. A cut aimed at a run still working its objective is the standing second-writer
        409, and it stops nothing for the same reason — the working run keeps its process.

        The body is the word plus the same budget fields a spawn takes, since a follow is a new objective
        and a new objective's bounds are the composer's; `think` and `model` ride only when they are named.
        The model is the id the picker stands on *now*, which is what makes a switch at a settled run come
        true on the objective after it: the switch itself is spoken at the console (see `_post_command`) and
        can relaunch nothing, so the dial's only lasting effect is on the next launch — and this is that
        launch. Nothing here writes the log or the queue: the answer is the verb's own doing, and a refusal
        is the sentence, in the one error shape every route uses.

        **A file rides the word, not the wire.** The body's optional `files` field is decoded and written
        into the `.sahw` estate of the workspace the run's own newest `started` line names — the record,
        not the page, knows where the run stands — and the word carries the reference line for each of
        them before it reaches `channel`, so the line arrives whether the word is queued as a steer or
        carried as a follow. A run whose log names no workspace cannot be shown a file, and that is
        answered before a process is stopped or started, as every refusal here is.
        """
        body = self._body()
        text = str(body.get("text") or "")
        attached = _attached(body)
        cut = "" if body.get("cut") is None else str(body.get("cut")).strip()
        run_dir = self._run_folder(run_id)
        if cut:
            refused = runs.cut_refusal(os.path.join(run_dir, runs.LOG_NAME), cut)
            if refused:
                raise _Refused(400, refused)
        if attached is not None:
            workspace = str((runs.latest_started(os.path.join(run_dir, runs.LOG_NAME))
                             or {}).get("cwd") or "")
            if not workspace:
                raise _Refused(400, f"the run's own log names no workspace to attach into: {run_id}")
            text = attach.word_with_attachments(text, attach.write_files(workspace, attached))
        carried = channel.post_message(self.server.site.runs_root,
                                       self.server.site.sah_tree, run_dir, text,
                                       think=str(body.get("think") or ""),
                                       model=str(body.get("model") or ""),
                                       max_turns=_body_int(body, "max_turns",
                                                           spawn.DEFAULT_MAX_TURNS),
                                       max_runtime=_body_int(body, "max_runtime",
                                                             spawn.DEFAULT_MAX_RUNTIME),
                                       wants=channel.FOLLOW if cut else channel.MESSAGE,
                                       cut=cut)
        self._json(200, {"ok": True, "channel": carried, "run": run_id})

    def _post_command(self, run_id: str):
        """`POST /api/runs/<id>/command`: speak one line of the session's own console at a run at rest.

        `{"line": "/think high"}` is the whole of what this route takes, and what the line is — which
        of the session's commands it is, and whether the session runs it, refuses it, or answers it
        with its own list — is the console's judgement and not the route's: the gate is the shape of
        the line (`channel.command_refusal`), one line of the console's own that begins with the
        operator's mark, and a line padded or tabbed so its words are not what they appear to be is
        the 400 naming what a console line is, as is a line without the mark at all — a word to the
        model is not a line to the console. The face is handed the run's command surface: the picker's
        two dial lines and the lines its own menu picks and its own prompt types ride this one door,
        and a command the session's dispatch does not know is the console's own refusal beside the
        log, recorded by the command that carried it.

        **Nothing is written here, and that is the route's whole design.** SAH's console records its own
        acts: the line arrives as the first thing a resumed session reads, dispatches as the operator's
        command rather than an objective, and its outcome lands beside the log as a `notice`. A route that
        wrote that notice too would be a second voice claiming what the command did, and a route that
        answered with the state it believes it set would be the picker's last click dressed up as the
        record — which is the thing this plan exists to refuse. So the answer is the line that was carried:
        a switch this server carried is a line the record will shortly name, and the face settles its dials
        on that naming when the stream brings it (see `_dials`). A session the line is spoken in closes at
        the end of its input, so a switch starts no work and stops nothing — no `kill_first` stands before
        it, and the gate refuses rather than displaces.
        """
        line = str(self._body().get("line") or "")
        carried = channel.post_command(self.server.site.runs_root, self.server.site.sah_tree,
                                       self._run_folder(run_id), line)
        self._json(200, {"ok": True, "line": carried, "run": run_id})

    def _fork_run(self, run_id: str):
        """`POST /api/runs/<id>/fork`: branch this run's conversation into a new run.

        The body is the objective the branch runs and, optionally, the step its carried prefix ends at;
        with no step the whole conversation is carried, from where it stands. **The branch step is settled
        against the source's log here, before the child is started** — `runs.fork_branch` walks the same
        lineage the cut walks and adds the one refusal a fork cannot leave to SAH's door: a child refused
        by `sah fork` exits without writing, and a route that had already answered 201 with a run id would
        have pointed the page at a folder that never becomes a run. A refusal therefore launches nothing.

        Nothing is stopped, and nothing of this run is touched: a fork reads the source's log and writes
        its own, which is what makes it safe to fork a run that has settled, orphaned, or is being worked
        elsewhere — and what makes the source's record byte for byte the one it was before the request.
        The answer is the new run's id, in the shape the spawn route gives, because a fork *is* a run: it
        lands in the tree like any other, wearing the fork its own record states.
        """
        body = self._body()
        task = str(body.get("task") or "")
        step = "" if body.get("step") is None else str(body.get("step")).strip()
        source = self._run_folder(run_id)
        branch, refused = runs.fork_branch(os.path.join(source, runs.LOG_NAME), step)
        if refused:
            raise _Refused(400, refused)
        spawned = spawn.spawn_fork(self.server.site.runs_root, self.server.site.sah_tree,
                                   source, branch, task,
                                   max_turns=_body_int(body, "max_turns", spawn.DEFAULT_MAX_TURNS),
                                   max_runtime=_body_int(body, "max_runtime", spawn.DEFAULT_MAX_RUNTIME),
                                   think=str(body.get("think") or ""),
                                   model=str(body.get("model") or ""))
        self._json(201, {"run_id": spawned})

    def _stop_run(self, run_id: str):
        """`POST /api/runs/<id>/stop`: end a working run's process and keep its record.

        The act is `channel.kill_first`, the kill of the process the log's newest `started` line names —
        the same act a follow performs on its way to relaunching, and the only path that ends a run's
        process. The folder stays: a stopped run is a dead run with an intact log, resumable the way any
        orphan is, and the next word relaunches on the same record. Nothing is written to the log, so a stop
        that landed mid-objective leaves no `ended` line — which is the orphan's own shape, and the resume's
        own case.

        A run that is not working answers as the 409 that names it rather than as an act that failed —
        nothing was attempted and nothing can half-happen, and the folder stands either way, so the caller is
        being told the state of the run and not that the request was badly made. A settled run has no process
        to stop: what it is owed is a word, which arrives as a follow.

        **A number is vouched for, or it is not ended.** The act reaches a process through a number, and a
        number is a name a machine can hand to whoever asks next: the tree's poll answers a run's row dead
        while the number its log stamped answers live, and the process standing under it is nobody the
        record ever named. So the route asks the poll whether this run's number is rebirthed before it asks
        for the kill, and refuses with the machine's own words when it is — the row the operator clicked
        from keeps its dead verdict, the stranger keeps its process, and the sentence stands at the head of
        the tree the act was asked from, as every refusal on this face stands. The number the record
        vouches for is ended exactly as it always was; the vouching costs no reading, only the one `stat`
        and the one probe the poll's own answer needs.
        """
        run_dir = self._run_folder(run_id)
        if self.server.site.poll().rebirthed(run_id):
            raise _Refused(409, NOT_THE_PROCESS)
        if not channel.kill_first(run_dir):
            raise _Refused(409, NOTHING_TO_STOP)
        self._json(200, {"ok": True})

    def _post_compact(self, run_id: str, stop: bool):
        """`POST /api/runs/<id>/compact` and `/compact-stop`: carry the compact's verb to the queue.

        The verb is the queue's and the decision the run's: a `compact` runs the compaction at the run's
        next turn boundary — the same act the trigger runs when the window is full — and a `compact-stop`
        asks the compaction in flight to stand down before the summary lands, refusing in the run's own
        words when no flight is working. So the route carries the block with the `send` seam — a file
        append and nothing else — and starts nothing, because nothing here is the run's state and the
        queue is the only channel to it: a `compact` to a settled run is the compact that the word that
        relaunches it reads at its first turn, and a run that is working takes the verb at its own
        boundary. **Nothing is written to the log, and that is the route's whole design.** The record
        stands the flight and its two endings — the summary step, the stopped act — beside the log in
        the run's own words, and a route that wrote a notice beside them would be a second voice claiming
        what the queue did. The answer is the verb carried, so the caller knows which act to read the
        record for.
        """
        carried = channel.post_compact(self.server.site.runs_root, self.server.site.sah_tree,
                                       self._run_folder(run_id), stop=stop)
        self._json(200, {"ok": True, "run": run_id, "action": carried})

    def _rename_run(self, run_id: str):
        """`POST /api/runs/<id>/rename`: name the run, or take the name back off it.

        `{"name": "the refund branch"}` is the whole of the body, and the word is the run's *current* name —
        the word its row wears in the tree and the word the head's filter finds it by. The name's home is
        `name.txt` beside the log (see `runs.face_name`): the face's own file, in the run's own folder, which
        the run's process never opens. That is the whole of the safety this act needs, so it asks no one's
        leave and holds no liveness guard — a rename of a working run renames a file that run does not hold
        open. **No path out of here opens, writes or replaces `log.jsonl`.** The record is the machine's, the
        name is not a line of it, and a rename leaving the log byte-identical is a fact of what this route
        does rather than a rule it polices.

        The word is trimmed, and a word that is nothing once trimmed **clears** the name: the file goes when
        it stands and the row falls back to what its own record calls it — the boot's `title`, or the
        operator's first word. A body that names no `name` field names no word and is that same clear; the
        face always sends the field, and a clear it sends is the empty word rather than a silence. A word
        carrying a line boundary is the 400 that names the boundary, refused before a byte is written: the
        name is one line because the file is one line, and an act that would make the file two of them is an
        act the reader could not answer.

        The answer carries what the act did — `wrote` or `cleared` — beside the name the row now wears, read
        through the one rule the row builder reads (see `runs.worn_name`). That is what lets the face patch
        its own row out of the answer and owe the tree no re-list. A run this server holds no folder for is
        the 404 that names the id, as every run route answers it, and nothing else is refused about a run:
        a folder that stands is nameable, log or no log, and the id stays the identifier either way.
        """
        word = str(self._body().get("name") or "")
        run_dir = self._run_folder(run_id)
        refused = runs.name_refusal(word)
        if refused:
            raise _Refused(400, refused)
        did = runs.write_face_name(run_dir, word)
        self._json(200, {"ok": True, "run": run_id, "action": did, "name": runs.worn_name(run_dir)})

    def _export(self, run_id: str, query: str = ""):
        """`GET /api/runs/<id>/export`: the run's log as one attachment, in the shape asked for.

        Two shapes over the one record: Markdown, the projection a report reads, and JSON, the
        record's own lines as a whole document. The shape the request names — and Markdown when it
        names none — is rendered on the spot and delivered with the attachment's headers and
        nothing else, because a file a browser is going to save is not a JSON a page is going to
        read. A name neither shape answers to is a bad request: the route says which shapes it holds.
        """
        log_path = os.path.join(self._run_folder(run_id), runs.LOG_NAME)
        if not os.path.isfile(log_path):
            raise _Refused(404, f"no log for run {run_id}")
        fmt = _query_value(query, "format", required=False)
        if fmt in ("", "md"):
            body = export.markdown(log_path).encode("utf-8")
            content_type = "text/markdown; charset=utf-8"
            suffix = ".md"
        elif fmt == "json":
            body = export.json_document(log_path).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            suffix = ".json"
        else:
            raise _Refused(400, f"no such export shape: {fmt} — the shapes the route holds are md and json")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{run_id}{suffix}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _delete_run(self, run_id: str):
        """`POST /api/runs/<id>/delete`: the run's folder off disk, or the refusal that names it.

        The guard is `purge`'s — a run whose process is still writing its log is declined, and the
        answer says so in the act's own shape: a live run is not a bad request, so the refusal arrives
        200 with `ok: false`, and only a fault that cannot remove the folder answers as one.
        """
        run_dir = self._run_folder(run_id)
        self._json(200, purge.delete_run(run_dir))

    def _delete_all_runs(self):
        """`POST /api/runs/delete-all`: runs off disk — one workspace's, or every workspace's.

        The body names the workspace whose runs are to go, exactly as the tree showed it; that act is this
        route as it has always been. A body that carries no `cwd` at all is the one other ask it answers:
        the batch over every workspace, the tree head's act. Both are `purge`'s one batch act, and both
        answer in the batch's own shape whichever way it went — `{deleted: [...]}` naming every folder it
        took, or `ok: false` with the sentence naming the live members that refused it and nothing removed.
        A `cwd` that is there but empty is not that second ask: a field that names nothing is a caller's
        mistake, and the sentence says so before any folder is judged.
        """
        body = self._body()
        if "cwd" not in body:
            self._json(200, purge.delete_every_workspace(self.server.site.runs_root))
            return
        cwd = str(body.get("cwd") or "")
        if not cwd:
            raise _Refused(400, "cwd is required: the workspace whose runs are to go, "
                                "or no cwd at all for every workspace")
        self._json(200, purge.delete_workspace(self.server.site.runs_root, cwd))

    def _open_path(self):
        """`POST /api/open`: a window on the operator's machine, on a folder or on a file.

        The act is `openers`' — the path checked against the shape its kind opens and handed over
        unresolved, the argv list the machine's shape names, the spawn issued and not watched — and this
        route's is the request's: a kind and a path read from the body, and `openers`' refusal, which
        carries its own code, translated once into the error shape every route answers with. The terminal
        is not read from the body and not probed here: it is the one the site settled on when the server was
        made, and the file act needs no answer from the machine beyond its own default handler.
        """
        # A server started with --no-open owes the act's refusal, not its window: the e2e discipline is
        # that a probe's server never opens what an operator would open, and the refusal stands as the
        # named line every route's refusal stands as — the act refused before the spawn was asked.
        if not self.server.site.open_paths:
            raise _Refused(503, "this server was started with --no-open: the open is refused, not a "
                                "silence — the face's own server is the one that opens")
        body = self._body()
        try:
            result = openers.open_path(str(body.get("kind") or ""), str(body.get("path") or ""),
                                       terminal=self.server.site.terminal)
        except openers.OpenError as refused:
            raise _Refused(refused.status, str(refused)) from refused
        self._json(200, result)

    def _make_folder(self):
        """`POST /api/fs/mkdir`: one new folder, `{path: <where>, name: <what it is called>}`.

        The act and every guard around it are `fspath`'s — the parent has to stand and be a folder, the
        name has to be one name, nothing already standing there is overwritten, and the runs root is not
        this page's to manage — and this route is the request's: two strings out of the body, the created
        path back out. A folder is made and never entered: the pane is what walks into it, on the listing
        this answer tells the face to ask for again.
        """
        body = self._body()
        self._json(200, fspath.make_folder(str(body.get("path") or ""), str(body.get("name") or ""),
                                           self.server.site.runs_root))

    def _rename_path(self):
        """`POST /api/fs/rename`: a new name for one folder or file, `{path: <which>, name: <new>}`.

        Never a new location, which is why the route takes a name and not a path: the thing stays where it
        stands and is called something else, and the guard that refuses a folder whose runs the tree still
        counts is asked of the old path — the one the records name — whatever the new name would be. The
        answer carries both spellings, so the face that re-lists can say what it moved and where it is.
        """
        body = self._body()
        self._json(200, fspath.rename(str(body.get("path") or ""), str(body.get("name") or ""),
                                      self.server.site.runs_root, self.server.site.poll().tree()))

    def _delete_path(self):
        """`POST /api/fs/delete`: one file, or one empty folder, off disk — `{path: <which>}`.

        The face stands behind its own consent for this act, as the tree's delete does; what the face's
        consent cannot decide is whether the machine allows it, and the two guards `fspath` asks before
        anything is removed are the answer to a question the pane cannot ask — whether the folder named is
        the machine's own record, and whether it is a workspace the tree still counts runs in. A folder
        that holds something is refused with the count, which is the sentence an operator needs in order
        to empty it or to have not meant this.
        """
        body = self._body()
        self._json(200, fspath.delete(str(body.get("path") or ""), self.server.site.runs_root,
                                      self.server.site.poll().tree()))

    def _upload_file(self, query: str, length: int):
        """`POST /api/fs/upload?path=<folder>&name=<file>`: the request's own bytes, into one new file.

        The body is the file, which is the whole reason this route reads differently from every other:
        no JSON, no cap, no whole-body buffer — `fspath.upload` is handed the socket and the length the
        request named, and copies one chunk at a time into the file it opens under a name the request
        chose. A name already standing in the folder is refused rather than overwritten, and the name is
        the same name the picker showed, because a file that arrives called something else is a file the
        operator will not find again.

        The refusal of a taken name, a name that is not a name, and a folder that is not a folder all
        happen before a byte is written, and `fspath.upload` reads the posted body to its end on those
        paths so the next request on the connection is not read out of this one's leftovers.
        """
        answer = fspath.upload(_query_value(query, "path"), _query_value(query, "name"),
                               self.rfile, self.server.site.runs_root, length)
        self._json(200, answer)

    # --- responses -------------------------------------------------------------------------------------

    def _json(self, status: int, payload):
        self._send(status, json.dumps(payload).encode("utf-8"), CONTENT_TYPES[".json"])

    def _error(self, status: int, text: str):
        self._send(status, json.dumps({"error": text}).encode("utf-8"), CONTENT_TYPES[".json"])

    def _send(self, status: int, body: bytes, content_type: str, mtime: float | None = None,
              disposition: str | None = None):
        """One response: status, type, length, body. Every one carries `no-cache` — a browser that
        keeps the bytes must check before it uses them — and, when a stamp is given, the file's own
        `Last-Modified`, the something the check runs on. Without both, a file a browser cached can
        never be told the disk moved, and the browser serves the bytes it kept, not the ones it would
        have fetched: a face standing on a sheet the disk no longer holds. When a name is given, the
        response also carries `Content-Disposition` — the way a body the browser is meant to keep,
        not paint or read, says what it is to be kept as.
        """
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        if mtime is not None:
            self.send_header("Last-Modified", formatdate(mtime, usegmt=True))
        if disposition is not None:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        """The request's JSON body, as the dict every route expects.

        The bytes are the `_post`'s own: read once at the door, and a route that takes a body takes it
        from the stash, so the socket owes nothing to the request that follows. Refused as a 400 rather
        than read as an empty one: a caller who sent no body, or one that is not JSON, or a list where an
        object was asked for, is about to be told their command line was wrong, and the sentence has to
        say so before it says anything about a missing `cwd`.
        """
        raw = self._drained
        if not raw:
            raise _Refused(400, "no body: this route takes a JSON object")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise _Refused(400, f"body is not a JSON object: {exc}") from exc
        if not isinstance(body, dict):
            raise _Refused(400, "body is not a JSON object")
        return body


def _query_value(query: str, name: str, required: bool = True) -> str:
    """One query parameter: the value, or a 400 that names it — and, when the parameter is the one a
    route answers without, the empty value a route that was not asked for it reads.

    `required` names the parameter's own standing, not the caller's: `path` is required on the file's
    route, and a request that names no path is a request for nothing; `download` is the flag that
    changes the answer's shape, and a request that names no flag is the route's ordinary answer, not a
    request for nothing.
    """
    values = parse_qs(query, keep_blank_values=True).get(name)
    if not values:
        if not required:
            return ""
        raise _Refused(400, f"{name} is required: pass ?{name}=<path>")
    return values[0]


def _download_name(path: str) -> str:
    """The name a kept file is given, in the one header that spells it: quoted, and every quote escaped.

    `Content-Disposition`'s basic form has one rule about a name that holds a double quote — the quote is
    preceded by a backslash — and this is the only place that rule is written, so the preview's download
    and the raw route's cannot drift apart on the one thing a browser saves a file *as*. Everything else
    in the name is the name: a space, a non-ASCII letter, a dot at either end, all of it carried as the
    file has it, because a file that lands on the disk called something other than what it is called is a
    file the operator did not ask for.
    """
    return '"' + os.path.basename(path).replace('\\', '\\\\').replace('"', '\\"') + '"'


def _absolute(path: str) -> str:
    """The picture path this server will answer for: one that already names a root of this box.

    An absolute path is the shape the record stamps and the browser pane holds, so a request arriving with
    anything else is not asking for a file the page can see. Resolving a relative name would hang it on the
    folder the server happens to stand in — a folder no page ever meant, and one that changes with how the
    server was started — so the route refuses it instead of guessing which folder the name was meant under.
    """
    if not path or not os.path.isabs(path):
        raise _Refused(400, f"a picture is asked for by its absolute path, not {path!r}")
    return path


def _attached(body: dict):
    """The body's `files`: every file a word travels with, a picture and a page of words being one thing.

    A body that names them by the older name is refused rather than quietly read. `images` was true of
    every entry the route ever carried and is a lie about the first `notes.md` that rides it, and the
    choice the routes are left with is between naming the field that works and dropping the operator's file
    without a word — so the sentence names `files`, and nothing the refused body carried is written. A body
    with neither field is not a refusal at all: it is the word as it was typed, which is what `None` means
    to `attach.write_files`.
    """
    if "images" in body:
        raise _Refused(400, "images is not the field: the files a word travels with ride the body's "
                            "`files` field, of whatever kind they are")
    return body.get("files")


def _body_int(body: dict, name: str, default: int) -> int:
    """One optional integer from the body, defaulted and checked: a budget that is not a number is a
    mistake in the request, and the answer names the key rather than starting a run with a budget of zero.
    """
    value = body.get(name)
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise _Refused(400, f"{name} is not a number: {value!r}") from exc
    if number < 1:
        raise _Refused(400, f"{name} must be at least 1: got {number}")
    return number


def make_server(host: str, port: int, *, runs_root: str, sah_tree: str = "",
                web_dir: str = "", open_paths: bool = True,
                stream_poll: float = runs.POLL_SECONDS) -> ThreadingHTTPServer:
    """The server, bound and not yet serving: pass port 0 to have the operating system choose one.

    `serve_forever` is the caller's call — the command line blocks on it, a test runs it on a thread of
    its own — so binding and serving stay two acts and a test can ask which port it got before anyone
    talks to it.
    """
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    httpd.site = Site(runs_root, sah_tree=sah_tree, web_dir=web_dir, open_paths=open_paths,
                      stream_poll=stream_poll)
    return httpd
