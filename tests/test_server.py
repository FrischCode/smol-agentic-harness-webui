"""sahw.server — every route, answered on a real server on a port the operating system chose.

Nothing is faked below the HTTP layer: the fixture writes run folders and a front folder, the tests make
requests and read responses, and the stream test appends to a log from a second thread while the first
sits reading it. A route is judged on the four things a client sees — the status, the content type, the
body, and the error shape — and the port is 0 precisely so that two batteries, or a battery and a server
someone left running, cannot collide. The two processes behind the liveness verdict are real too: one
that ran and exited, one that was killed, both waited for and neither stood in for the other.
"""
import email.utils
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

from sahw import channel, envfile, runs, server, spawn

TIMEOUT = 15.0

# The front this tree ships, as opposed to the fixture's one-file stand-in: the tests about the icon kit
# are about the files that ship with the server, served the way the server serves them.
REAL_WEB = os.path.join(envfile.repo_root(), "web")


def get(url):
    """One GET as (status, content type, body bytes): the three things a response is judged on."""
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


def get_json(url):
    status, _, body = get(url)
    return status, json.loads(body)


def post_json(url, payload):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def expect_error(url, status, body=None):
    """The JSON body of an error response, having checked it is one error of that status and no other.

    The body is parsed as JSON here so that a route which answered with a traceback, or with a page, or
    with the file it was refusing to serve, fails this assertion instead of passing a status check.
    """
    target = url if body is None else urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(target, timeout=TIMEOUT)
    assert raised.value.code == status
    error = json.loads(raised.value.read().decode("utf-8"))
    assert set(error) == {"error"} and error["error"]
    return error


def write_log(run_dir, *steps):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(str(run_dir), "log.jsonl"), "w", encoding="utf-8") as handle:
        for step in steps:
            handle.write(json.dumps(step) + "\n")
    return run_dir


def started(cwd, ts, model="flash-next", **extra):
    return {"id": "000000-started", "kind": "started", "issuer": "core", "ts": ts, "cwd": cwd,
            "model": model, "run_id": "run", "root": "root", **extra}


def message(text, ts="2026-11-01T08:30:00+00:00"):
    return {"id": "000005-message", "kind": "message", "issuer": "core", "ts": ts,
            "role": "assistant", "text": text}


def ended(reason="complete", ts="2026-11-01T09:00:00+00:00"):
    return {"id": "000009-ended", "kind": "ended", "issuer": "core", "ts": ts, "reason": reason,
            "exit_code": 0}


def read_frame(stream):
    """One server-sent event as (event, data), consuming the blank line that closes it.

    Only the line endings come off the data: what is between `data: ` and the end of the line is the
    log's own line, byte for byte, and a frame reader that tidied it would not be reading the stream.
    """
    event = stream.readline().decode("utf-8").strip()
    data = stream.readline().decode("utf-8").rstrip("\r\n")
    stream.readline()
    return event.split(": ", 1)[1], data.split(": ", 1)[1]


@pytest.fixture
def box(tmp_path):
    """A fixture runs root, a fixture front, and a file beside both that the front must never serve."""
    write_log(tmp_path / "runs" / "r20261101-080000-aaaaaa",
              started(r"C:\work\alpha", "2026-11-01T08:00:00+00:00"), message("one"), ended())
    write_log(tmp_path / "runs" / "r20261101-081000-bbbbbb",
              started(r"C:\work\beta", "2026-11-01T08:10:00+00:00"))
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<!doctype html><title>SAHW</title>the front",
                                                 encoding="utf-8")
    (tmp_path / "web" / "app.css").write_text("body { margin: 0 }", encoding="utf-8")
    (tmp_path / "web" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("never served", encoding="utf-8")
    return tmp_path


@pytest.fixture
def serve(box):
    """`serve(**overrides)` — a server on a free port with the fixture's folders, and a base URL.

    The server itself is left on `start.httpd` as well, because one fact the API cannot answer is what
    this server holds about the runs it started — and the answer, which a test has to be able to read, is
    nothing at all.
    """
    started_servers = []

    def start(**overrides):
        options = {"runs_root": str(box / "runs"), "sah_tree": str(box / "sah-tree"),
                   "web_dir": str(box / "web")}
        options.update(overrides)
        httpd = server.make_server("127.0.0.1", 0, **options)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started_servers.append(httpd)
        start.httpd = httpd
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started_servers:
        httpd.shutdown()
        httpd.server_close()


def as_query(path):
    return urllib.parse.quote(str(path))


# --- the front ----------------------------------------------------------------------------------------

def test_the_front_is_served_with_its_content_type(serve):
    base = serve()
    status, content_type, body = get(base + "/")
    assert status == 200
    assert content_type.startswith("text/html")
    assert b"the front" in body
    for name, kind in (("app.css", "text/css"), ("app.js", "text/javascript")):
        status, content_type, _ = get(f"{base}/{name}")
        assert status == 200
        assert content_type.startswith(kind)


def test_a_served_file_carries_the_revalidation_its_browser_needs(serve, box):
    """A front file the browser cached without revalidation is a front file the browser keeps serving
    long after the one on disk moved: the response owes `no-cache` (keep the bytes, check before use)
    and the file's own stamp, so the check has something to run on."""
    base = serve()
    with urllib.request.urlopen(base + "/app.css", timeout=TIMEOUT) as response:
        assert response.headers.get("Cache-Control") == "no-cache", (
            "revalidate before use: the face must never stand on a sheet the browser kept from before")
        modified = response.headers.get("Last-Modified")
    assert modified, ("the file's own stamp: a response without one gives the revalidation nothing to check")
    stamp = email.utils.parsedate_to_datetime(modified).timestamp()
    assert abs(stamp - os.path.getmtime(os.path.join(box, "web", "app.css"))) < 2, (
        "the stamp is the file's own mtime, not the response's clock")


def test_a_file_that_is_not_there_is_not_found(serve):
    expect_error(serve() + "/nope.css", 404)


def test_a_path_that_climbs_out_of_the_fronts_folder_gets_the_same_answer(serve, box):
    base = serve()
    expect_error(f"{base}/../outside.txt", 404)
    expect_error(f"{base}/%2e%2e%2foutside.txt", 404)
    assert (box / "outside.txt").read_text(encoding="utf-8") == "never served"


def test_the_shipped_page_declares_the_icons_and_no_longer_holds_the_placeholder(serve):
    """The head as the server answers it: the kit's five declarations, and no `data:,` silence."""
    head = get(serve(web_dir=REAL_WEB) + "/")[2].decode("utf-8")
    assert "data:," not in head
    for link in ('<link rel="icon" href="/favicon.ico" sizes="any">',
                 '<link rel="icon" href="/favicon-96x96.png" sizes="96x96">',
                 '<link rel="icon" type="image/svg+xml" href="/favicon.svg">',
                 '<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">',
                 '<link rel="manifest" href="/site.webmanifest">'):
        assert link in head, link


def test_the_kit_is_served_as_the_kind_of_thing_it_is(serve):
    """A favicon served as octet-stream is a broken tab icon, and a manifest nothing was told to read is
    no manifest at all: the answer each of these files gets names what the file is."""
    base = serve(web_dir=REAL_WEB)
    for name, kind in (("favicon.ico", "image/x-icon"),
                       ("favicon-96x96.png", "image/png"),
                       ("web-app-manifest-192x192.png", "image/png"),
                       ("apple-touch-icon.png", "image/png"),
                       ("favicon.svg", "image/svg+xml"),
                       ("site.webmanifest", "application/manifest+json")):
        status, content_type, _ = get(f"{base}/{name}")
        assert status == 200, name
        assert content_type.startswith(kind), f"{name} answered {content_type}"


def test_the_manifest_names_this_site_and_finds_its_own_icons_where_it_says(serve):
    """The kit is at the site's root because that is where the manifest's icon paths point, and it is
    this site's manifest, not the tool's placeholder."""
    base = serve(web_dir=REAL_WEB)
    manifest = json.loads(get(base + "/site.webmanifest")[2].decode("utf-8"))
    assert manifest["name"] == "SAHW"
    assert manifest["short_name"] == "SAHW"
    assert manifest["icons"], "a manifest that names no icon declares nothing"
    for icon in manifest["icons"]:
        assert get(base + icon["src"])[0] == 200, icon["src"]


# --- the tree, the browser, the preview ---------------------------------------------------------------

def test_the_runs_tree_is_the_shape_the_front_is_built_against(serve):
    status, got = get_json(serve() + "/api/runs")
    assert status == 200
    assert [workspace["path"] for workspace in got["workspaces"]] == [r"C:\work\alpha", r"C:\work\beta"]
    assert got["workspaces"][0]["runs"] == [
        {"id": "r20261101-080000-aaaaaa", "ts": "2026-11-01T08:00:00+00:00", "model": "flash-next",
         "status": "ended", "reason": "complete"}]
    live = got["workspaces"][1]["runs"][0]
    assert live == {"id": "r20261101-081000-bbbbbb", "ts": "2026-11-01T08:10:00+00:00",
                    "model": "flash-next", "status": "live", "reason": None, "live": "unknown"}


def test_the_api_answers_json(serve):
    _, content_type, _ = get(serve() + "/api/runs")
    assert content_type.startswith("application/json")


# --- the verdict on a run the log left unfinished -------------------------------------------------------

@pytest.fixture
def gone():
    """Two processes that are no more, held open by this test: one that ran, one that was killed.

    The handles are the point. A pid stays answerable until the last handle to its process object
    closes, so while these are held the answer cannot be a race — the number cannot have been handed to
    a new process, and `dead` is a fact about the record rather than about this test's timing.
    """
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    killed = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    killed.kill()
    killed.wait()
    return ran, killed


def rows_of(tree_payload):
    """The tree's rows by run id: the lookup the page does, once, for a test that wants one row."""
    return {row["id"]: row for workspace in tree_payload["workspaces"] for row in workspace["runs"]}


def test_the_list_answers_what_an_unfinished_run_is_now(serve, box, gone):
    """`live` on every unfinished entry: the running one, the dead one, and the one nobody can claim."""
    ran, killed = gone
    workspace = r"C:\work\alive-or-not"
    write_log(box / "runs" / "r20261101-090000-mmmmmm",
              started(workspace, "2026-11-01T09:00:00+00:00", pid=os.getpid()))
    write_log(box / "runs" / "r20261101-090100-nnnnnn",
              started(workspace, "2026-11-01T09:01:00+00:00", pid=ran.pid))
    write_log(box / "runs" / "r20261101-090200-oooooo",
              started(workspace, "2026-11-01T09:02:00+00:00"))
    write_log(box / "runs" / "r20261101-090300-pppppp",
              started(workspace, "2026-11-01T09:03:00+00:00", pid=killed.pid))
    rows = rows_of(get_json(serve() + "/api/runs")[1])
    assert rows["r20261101-090000-mmmmmm"]["live"] == "live", "the process answering this request"
    assert rows["r20261101-090100-nnnnnn"]["live"] == "dead", "a child that ran and was reaped"
    assert rows["r20261101-090200-oooooo"]["live"] == "unknown", "the pre-pid log: nothing to ask"
    assert rows["r20261101-090300-pppppp"]["live"] == "dead", "a child that was killed, not exited"


def test_a_finished_run_is_asked_nothing_and_carries_no_verdict(serve, box, gone):
    """The key's absence is the page's `it ended` signal, so a finished row must not carry it."""
    _, killed = gone
    write_log(box / "runs" / "r20261101-090400-qqqqqq",
              started(r"C:\work\done", "2026-11-01T09:04:00+00:00", pid=killed.pid), ended())
    rows = rows_of(get_json(serve() + "/api/runs")[1])
    assert "live" not in rows["r20261101-090400-qqqqqq"]


def test_the_folder_browser_lists_directories_first(serve, box):
    workspace = box / "workspace"
    (workspace / "sub").mkdir(parents=True)
    (workspace / "a.txt").write_text("a", encoding="utf-8")
    status, got = get_json(f"{serve()}/api/fs?path={as_query(workspace)}")
    assert status == 200
    assert got == {"path": str(workspace), "entries": [{"name": "sub", "dir": True},
                                                       {"name": "a.txt", "dir": False}]}


def test_the_preview_reads_a_file_and_says_it_was_not_cut(serve, box):
    note = box / "note.md"
    note.write_text("# hello\n", encoding="utf-8")
    status, got = get_json(f"{serve()}/api/file?path={as_query(note)}")
    assert status == 200
    assert got == {"path": str(note), "content": "# hello\n", "truncated": False}


def test_the_file_routes_answer_their_errors(serve, box):
    binary = box / "blob.bin"
    binary.write_bytes(b"\xff\xfe\x00\x00")
    base = serve()
    expect_error(f"{base}/api/file?path={as_query(binary)}", 415)
    expect_error(f"{base}/api/file?path={as_query(box / 'gone.txt')}", 404)
    expect_error(f"{base}/api/fs?path={as_query(box / 'gone')}", 404)
    expect_error(f"{base}/api/file", 400)
    expect_error(f"{base}/api/fs", 400)


def test_the_download_answers_the_files_own_bytes_whole_with_their_name(serve, box):
    """A file past the pane's cap, asked for its download: the whole of it, as written, under its name."""
    note = box / "note.txt"
    body = ("line one\r\nline two\r\n" * 78125).encode("ascii")  # 1,250,000 bytes, well past the cap
    note.write_bytes(body)
    url = f"{serve()}/api/file?path={as_query(note)}&download=1"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        assert response.status == 200
        assert response.headers.get("Content-Type") == "application/octet-stream"
        assert response.headers.get("Content-Disposition") == 'attachment; filename="note.txt"'
        got = response.read()
    assert got == body, "the bytes the disk holds, line endings and all — as written, not a head of them"


def test_the_pane_and_the_download_answer_the_same_file_two_ways(serve, box):
    """One file, two answers: the pane's words to the cap, the download's bytes to the end of the file."""
    big = box / "big.txt"
    body = ("word " * 60000).encode("ascii")  # 300,000 bytes, past the 256 KiB cap
    big.write_bytes(body)
    status, got = get_json(f"{serve()}/api/file?path={as_query(big)}")
    assert status == 200 and got["truncated"] is True, "the pane's answer is the head, and the flag says so"
    url = f"{serve()}/api/file?path={as_query(big)}&download=1"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        assert response.read() == body, "and the download's answer is the file, whole"


def test_the_download_refusals_are_the_readers_own(serve, box):
    """The flag changes the answer's shape, not its reach: the same refusals the route already owes."""
    base = serve()
    expect_error(f"{base}/api/file?path={as_query(box / 'gone.txt')}&download=1", 404)
    # A folder asked of the bytes reader is the reader's own 400.
    expect_error(f"{base}/api/file?path={as_query(box)}&download=1", 400)
    expect_error(f"{base}/api/file?download=1", 400)  # the flag without the path is a request for nothing


def test_a_picture_arrives_whole_from_the_frame_and_as_the_download(serve, box):
    """A picture is the file on disk, on either route: the frame's body is what the browser paints, the
    download is what the disk wrote, and the cap is the text reader's, with no say in either.
    """
    shot = box / "shot.png"
    body = b"\x89PNG\r\n\x1a\n" + b"\x00" * (300 * 1024)  # past the pane's cap
    shot.write_bytes(body)
    status, mime, got = get(f"{serve()}/img?path={as_query(shot)}")
    assert status == 200 and mime == "image/png", "the frame the pane paints is answered as a picture"
    # The frame is the file on disk: a body short of the file is a frame the browser paints broken.
    assert got == body
    url = f"{serve()}/api/file?path={as_query(shot)}&download=1"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        assert response.headers.get("Content-Type") == "application/octet-stream"
        assert response.read() == body, "the picture as it is on the disk, whole"


# --- the stream ---------------------------------------------------------------------------------------

def test_the_stream_frames_the_log_then_follows_it_then_ends(serve, box):
    run_id = "r20261101-082000-cccccc"
    log = box / "runs" / run_id / "log.jsonl"
    first = started(r"C:\work\gamma", "2026-11-01T08:20:00+00:00")
    late = message("written while the reader was waiting")
    finish = ended()
    write_log(log.parent, first)

    def append_after_a_while():
        time.sleep(0.2)
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(late) + "\n")
        time.sleep(0.2)
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(finish) + "\n")

    base = serve()
    threading.Thread(target=append_after_a_while, daemon=True).start()
    with urllib.request.urlopen(f"{base}/api/runs/{run_id}/stream", timeout=TIMEOUT) as stream:
        assert stream.headers.get("Content-Type", "").startswith("text/event-stream")
        assert read_frame(stream) == ("step", json.dumps(first))
        assert read_frame(stream) == ("step", json.dumps(late))
        assert read_frame(stream) == ("ended", "done")
        assert stream.read() == b""


def test_the_console_line_written_after_the_ending_arrives_as_a_frame(serve, box):
    """A switch spoken at a resting run is a frame, not a line the stream walks past on its way out.

    The session's control is written under the line that closed the objective, and the page opens this
    route again precisely to read it: a stream that stopped at the ending would close with the console's
    word still in the file and tell the pane nothing about the act it just asked for.
    """
    run_id = "r20261101-082500-ccccc1"
    log = box / "runs" / run_id / "log.jsonl"
    opening = started(r"C:\work\gamma", "2026-11-01T08:25:00+00:00")
    turn = message("one")
    finish = ended()
    switched = {"id": "000011-notice", "kind": "notice", "issuer": "operator",
                "subject": "command", "ts": "2026-11-01T09:30:00+00:00",
                "text": "think: low (was xhigh)"}
    write_log(log.parent, opening, turn, finish, switched)
    base = serve()
    with urllib.request.urlopen(f"{base}/api/runs/{run_id}/stream", timeout=TIMEOUT) as stream:
        assert read_frame(stream) == ("step", json.dumps(opening))
        assert read_frame(stream) == ("step", json.dumps(turn))
        assert read_frame(stream) == ("step", json.dumps(switched)), \
            "the console's word is carried, because it is why the reader asked"
        assert read_frame(stream) == ("ended", "done")
        assert stream.read() == b""


def test_the_stream_of_a_run_with_no_log_is_not_found(serve, box):
    folder = box / "runs" / "r20261101-083000-dddddd"
    folder.mkdir(parents=True)
    base = serve()
    expect_error(f"{base}/api/runs/r20261101-083000-dddddd/stream", 404)
    expect_error(f"{base}/api/runs/r20261101-083000-dddddd/report", 404)


# --- the trace on the stream: two files, one connection -----------------------------------------------

def fragment(text, ts="2026-11-01T08:20:01+00:00", call=None) -> str:
    """One trace line as SAH's `--live` writes it, returned without its newline: the file's line ends
    are the test's to place, and a Windows writer puts a `\\r` in front of each of them."""
    line = {"kind": "delta", "text": text, "ts": ts}
    if call:
        line["call"] = call
    return json.dumps(line, sort_keys=True)


def append_line(where, text):
    with open(where, "a", encoding="utf-8") as handle:
        handle.write(text + "\n")


def test_a_trace_that_appears_mid_stream_arrives_while_the_log_is_quiet(serve, box):
    """The merge as it runs: the step frames unchanged, the fragments of a run being written in between.

    The trace file is not there when the connection opens — it is created at the run's first fragment —
    and each frame below is read with nothing else on the wire to cause it: a fragment arrives because the
    route looks at the trace on the log's own poll, and a step arrives exactly as it always did. The last
    pair is the ending's own round: `stream_lines` stops mid-round at the ending line, so the fragment
    written under the last step is what the route's closing look delivers, before the frame that says the
    pane is owed nothing further.
    """
    run_id = "r20261101-082200-cdcccc"
    folder = box / "runs" / run_id
    log = folder / "log.jsonl"
    trace = folder / runs.LIVE_NAME
    first = started(r"C:\work\gamma", "2026-11-01T08:20:00+00:00")
    late = message("written while the reader was waiting")
    write_log(folder, first)
    base = serve()
    with urllib.request.urlopen(f"{base}/api/runs/{run_id}/stream", timeout=TIMEOUT) as stream:
        assert stream.headers.get("Content-Type", "").startswith("text/event-stream")
        assert read_frame(stream) == ("step", json.dumps(first))

        append_line(trace, fragment("the first "))
        assert read_frame(stream) == ("delta", fragment("the first "))
        append_line(trace, fragment("words of a turn"))
        assert read_frame(stream) == ("delta", fragment("words of a turn"))

        append_line(log, json.dumps(late))
        assert read_frame(stream) == ("step", json.dumps(late))

        append_line(trace, fragment("under the last step"))
        append_line(log, json.dumps(ended()))
        assert read_frame(stream) == ("delta", fragment("under the last step"))
        assert read_frame(stream) == ("ended", "done")
        assert stream.read() == b"", "the ending closes the connection, trace or no trace"


def test_a_stream_that_found_the_trace_already_written_replays_only_the_record(serve, box):
    """A connection that opens on a run whose trace file already holds settled words: the record, whole,
    and no fragment of it.

    The trace is a side-channel of the live, not a second record: a fragment of a turn the record has
    settled, delivered after the step that settled it, would stand the closed turn's face back up in the
    pane - the pane settles positionally (a fragment owes the turn in flight) and cannot tell a replayed
    word from a spoken one. The replay is the record's: every step, and the end. The file keeps the words
    the stream withholds - the play of them is the face the plan leaves to the file.
    """
    run_id = "r20261101-082400-ceeeee"
    folder = box / "runs" / run_id
    first = started(r"C:\work\gamma", "2026-11-01T08:20:00+00:00")
    word = message("a whole turn, in the record")
    write_log(folder, first, word, ended())
    lines = [fragment("a whole "), fragment("turn, in the record"), fragment("and one after the last step")]
    (folder / runs.LIVE_NAME).write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    base = serve()
    with urllib.request.urlopen(f"{base}/api/runs/{run_id}/stream", timeout=TIMEOUT) as stream:
        body = stream.read()
    expected = (b"event: step\ndata: " + json.dumps(first).encode("utf-8") + b"\n\n"
                + b"event: step\ndata: " + json.dumps(word).encode("utf-8") + b"\n\n"
                + b"event: ended\ndata: done\n\n")
    assert body == expected
    assert b"delta" not in body, "the settled words are the record's, and the file keeps them for the play"


def test_a_reopened_stream_of_a_live_run_delivers_no_fragment_the_record_already_settled(serve, box):
    """The pane's reconnect: the follow rewinds the log, the old stream replays its ending and closes, and
    the reader's connection opens again on a run that is live and whose trace holds a settled turn.

    The reopened connection replays the record - every step as it stands - and follows the trace from
    where the file stands. A fragment of the settled turn delivered as if it were just spoken would grow
    the next turn's face on top of the last turn's words, so nothing of the settled trace crosses the
    wire; a word the run still speaks arrives.
    """
    run_id = "r20261101-082500-cfxxxx"
    folder = box / "runs" / run_id
    trace = folder / runs.LIVE_NAME
    first = started(r"C:\work\gamma", "2026-11-01T08:20:00+00:00")
    word = message("the settled turn")
    write_log(folder, first, word)
    trace.write_text(fragment("the ") + "\n" + fragment("settled turn") + "\n", encoding="utf-8")
    base = serve()
    with urllib.request.urlopen(f"{base}/api/runs/{run_id}/stream", timeout=TIMEOUT) as stream:
        assert read_frame(stream) == ("step", json.dumps(first))
        assert read_frame(stream) == ("step", json.dumps(word))
        # the settled turn's fragments have not crossed the wire, and the next frame is a word the run
        # still speaks, not one of the words the record already holds
        append_line(trace, fragment("a word the run still speaks"))
        assert read_frame(stream) == ("delta", fragment("a word the run still speaks"))


def test_a_run_with_no_trace_streams_exactly_what_this_route_always_streamed(serve, box):
    """No `live.jsonl`, no `delta` frame, no difference at all: the absence of the file is a state.

    This is the pin that keeps the second file from changing the first — the whole body of the response,
    compared byte for byte against what the route wrote before the trace existed. A run started without
    SAH's `--live` is not a run with something missing from it, and the stream says so by being silent
    about it.
    """
    run_id = "r20261101-082600-cfffff"
    folder = box / "runs" / run_id
    first = started(r"C:\work\gamma", "2026-11-01T08:20:00+00:00")
    word = message("no trace was ever written here")
    write_log(folder, first, word, ended())
    assert not (folder / runs.LIVE_NAME).exists()
    base = serve()
    with urllib.request.urlopen(f"{base}/api/runs/{run_id}/stream", timeout=TIMEOUT) as stream:
        body = stream.read()
    steps = [first, word, ended()]
    expected = b"".join(b"event: step\ndata: " + json.dumps(step).encode("utf-8") + b"\n\n"
                        for step in steps[:-1])
    assert body == expected + b"event: ended\ndata: done\n\n"
    assert b"delta" not in body, "a route that asked for a file it does not have would still say nothing"



def test_a_run_id_is_one_folder_name_and_never_a_path(serve):
    base = serve()
    expect_error(f"{base}/api/runs/..%2f..%2fsecret/stream", 400)
    expect_error(f"{base}/api/runs/nothing-here-at-all/stream", 404)


# --- the report ---------------------------------------------------------------------------------------

def test_the_report_is_the_text_beside_the_log(serve, box):
    run_id = "r20261101-084000-eeeeee"
    folder = box / "runs" / run_id
    write_log(folder, started(r"C:\work\delta", "2026-11-01T08:40:00+00:00"), ended())
    base = serve()
    expect_error(f"{base}/api/runs/{run_id}/report", 404)
    (folder / "report.md").write_text("# done\n", encoding="utf-8")
    status, content_type, body = get(f"{base}/api/runs/{run_id}/report")
    assert status == 200
    assert content_type.startswith("text/plain")
    assert body == b"# done\n"


# --- starting a run -----------------------------------------------------------------------------------

class Launched(list):
    """The launch seam's record: one `(argv, env, cwd)` per child the server would have started.

    A child that started leaves the server nothing — no stdin, no handle, no entry to keep — so the record
    of a launch is the command line alone, which is what these route tests are about.
    """


@pytest.fixture
def launched(monkeypatch):
    """The launch seam: every argv, environment and working directory the server would have started."""
    calls = Launched()
    monkeypatch.setattr(spawn, "launch", lambda argv, env, cwd: calls.append((argv, env, cwd)))
    return calls


def test_posting_starts_a_run_and_answers_201_with_its_id(serve, box, launched):
    workspace = box / "workspace"
    workspace.mkdir()
    base = serve()
    status, got = post_json(base + "/api/runs", {"cwd": str(workspace), "task": "say done"})
    assert status == 201
    assert set(got) == {"run_id"}
    folder = box / "runs" / got["run_id"]
    assert folder.is_dir() and os.listdir(str(folder)) == []

    argv, env, cwd = launched[0]
    assert argv[0].endswith("python.exe") and argv[1:3] == ["-m", "sah"]
    assert argv[argv.index("--run-dir") + 1] == str(folder)
    assert "-i" not in argv, "a run started here works its objective and exits"
    assert "--think" not in argv  # an un-named level sends no flag: the machine's own default applies
    assert argv[argv.index("--task") + 1] == "say done"
    assert env["PYTHONPATH"] == str(box / "sah-tree")
    assert env["SAH_EXTENSION"] == " "
    assert cwd == str(workspace)


def test_the_site_holds_six_facts_and_no_registry(serve, box, launched):
    """What a server knows about a run is what its log says, and what the process table says.

    The site is configuration — the runs root, the SAH tree, the front's folder, the terminal this box was
    found to have, the window the open act owes, or its refusal when the server was started with
    `--no-open`, and the stream's poll, the pace the server looks at a followed log — and a spawned run adds
    nothing to it: no pipe, no child, no entry keyed by run id.
    That is the fact the rest of the model stands on: with nothing held, two runs work at once for free, a
    page that reloads disturbs nothing, and the only way to reach a process is the kill the record names.

    The tree's working memory is the one thing held across requests, and it is memory over the record
    rather than of the runs: no process, no child, no pipe, and every row in it a re-read away from being
    recomputed from the logs it was read from. A spawned run adds no page to it either — the page arrives
    with the poll that first lists the run, and a server that answered nothing would remember nothing.
    """
    workspace = box / "workspace"
    workspace.mkdir()
    base = serve()
    assert sorted(vars(serve.httpd.site)) == ["open_paths", "polls", "runs_root", "sah_tree", "stream_poll",
                                              "terminal", "web_dir"], \
        "the memory over the record is the one thing added, and it is empty before the first poll"
    post_json(base + "/api/runs", {"cwd": str(workspace), "task": "say done"})
    assert sorted(vars(serve.httpd.site)) == ["open_paths", "polls", "runs_root", "sah_tree", "stream_poll",
                                              "terminal", "web_dir"], \
        "and a run launched through the server still adds no fact to it: no pipe, no child, no registry"
    assert not hasattr(server, "NOT_OURS"), "and the refusal that read that registry went with it"


def test_a_named_thinking_level_rides_to_the_child_argv(serve, box, launched):
    workspace = box / "workspace"
    workspace.mkdir()
    base = serve()
    status, got = post_json(
        base + "/api/runs", {"cwd": str(workspace), "task": "think it over", "think": "high"})
    assert status == 201
    argv, env, cwd = launched[0]
    assert argv[argv.index("--think") + 1] == "high"
    assert argv[argv.index("--task") + 1] == "think it over"


def test_posting_names_the_budgets_it_was_given(serve, box, launched):
    workspace = box / "workspace"
    workspace.mkdir()
    post_json(serve() + "/api/runs", {"cwd": str(workspace), "task": "say done",
                                      "max_turns": 3, "max_runtime": 60})
    argv = launched[0][0]
    assert argv[argv.index("--max-turns") + 1] == "3"
    assert argv[argv.index("--max-runtime") + 1] == "60"


def test_a_word_to_a_settled_run_rides_the_dial_the_picker_stands_on(serve, box, launched):
    """A switch is a fact about a process that has already gone, and it comes true on the launch the
    next word owes.

    The dial the picker stands on rides the word to the relaunch: a follow that names a model is told
    `--model` verbatim, and a follow that names none sends no flag, the machine's own default speaking
    — the same rule the spawn route stands, so the record's next `started` line names the model the
    operator moved the dial to, not the one the first launch was given.
    """
    workspace = box / "workspace"
    workspace.mkdir()
    run_id = "r20261101-082000-settled"
    write_log(box / "runs" / run_id,
              started(str(workspace), "2026-11-01T08:20:00+00:00"),
              message("the first word"),
              ended())
    base = serve()
    status, got = post_json(base + f"/api/runs/{run_id}/message",
                            {"text": "the next word", "model": "deep"})
    assert status == 200 and got["channel"] == channel.FOLLOW
    argv = launched[0][0]
    assert argv[argv.index("--model") + 1] == "deep"
    assert argv[argv.index("--task") + 1] == "the next word"
    status, got = post_json(base + f"/api/runs/{run_id}/message", {"text": "the next word again"})
    assert status == 200 and got["channel"] == channel.FOLLOW
    assert "--model" not in launched[1][0], "a follow that names no model sends no flag"


def test_posting_refuses_a_workspace_that_is_not_a_folder_without_starting_one(serve, box, launched):
    base = serve()
    expect_error(base + "/api/runs", 400,
                 json.dumps({"cwd": str(box / "gone"), "task": "say done"}).encode("utf-8"))
    assert launched == []


def test_posting_refuses_a_body_that_is_not_a_request(serve, box, launched):
    base = serve()
    workspace = box / "workspace"
    workspace.mkdir()
    url = base + "/api/runs"
    expect_error(url, 400, b"")
    expect_error(url, 400, b"{not json")
    expect_error(url, 400, json.dumps(["a list, not an object"]).encode("utf-8"))
    expect_error(url, 400, json.dumps({"cwd": str(workspace), "task": "   "}).encode("utf-8"))
    expect_error(url, 400, json.dumps({"cwd": str(workspace), "task": "x",
                                       "max_turns": "many"}).encode("utf-8"))
    assert launched == []


def test_posting_refuses_when_the_server_names_no_sah_tree(serve, box, launched):
    workspace = box / "workspace"
    workspace.mkdir()
    error = expect_error(serve(sah_tree="") + "/api/runs", 503,
                         json.dumps({"cwd": str(workspace), "task": "say done"}).encode("utf-8"))
    assert "sah-tree" in error["error"]
    assert launched == []


# --- routes nobody wrote --------------------------------------------------------------------------------

def test_a_route_that_does_not_exist_is_not_found_in_either_direction(serve):
    base = serve()
    expect_error(base + "/api/nope", 404)
    expect_error(base + "/api/file/extra", 404)
    expect_error(base + "/api/nope", 404, b"{}")
