"""sahw.server — the file routes: `/img`, the preview's picture branch, and attached files.

Three things are judged here, all of them on the four things a client sees — the status, the content type,
the body, and the error shape — and none of it out of a sentence a route returned politely:

* **`GET /img`** answers one picture's bytes with the mime its name claims, and every refusal is the code
  the route's own reader assigns it: 404 a path that is not there, 415 a name that claims no picture kind,
  400 a folder or a relative name, 403 what the box itself refused (pinned in `test_files.py`, where the
  read happens). "Outside the roots" is not a fourth code — the route's reach is the pane's, so the answer
  a path beyond the folders any run stands in gets is the answer `/api/file` gives the same path, and that
  equivalence is what is asserted.
* **The preview** answers a picture file as a picture, which is the one behaviour of the old text-only
  route that went away; a binary that names no picture kind is still the 415 it always was.
* **The attachments a body carries under `files`** land in the run's own estate — the workspace's `.sahw`
  folder, made on the request that needs it, with the workspace's root keeping its own contents — and
  leave one reference line per file in the word — on the spawn's objective and on the word a follow or a
  steer carries — and a file of words is the same act as a file of pixels: same field, same write, same
  line, the kind deciding only what a display path makes of the name. Every refusal is answered before a
  folder is claimed or a process is stopped: the launch seam and the run folders themselves are read
  afterwards to show that nothing moved — the workspace included, estate and all. The one name the write
  path refuses is a structural one; the kind refusals are the display paths' and are asserted as such,
  against the same file that landed.

`spawn.launch` is the standing seam, so no SAH child is ever started here and every argv is read rather
than run. The two channels a word to an existing run can take are set up from the record alone: a log with
an `ended` line is the follow, and a `started` line whose process the machine calls gone is a log nothing
is writing to, which is the steer.
"""
import base64
import json
import os
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

from sahw import attach, runs, server, spawn

TIMEOUT = 15.0

# A png as far as this file cares: the eight bytes every png starts with, then whatever the reader is
# handed on. The route never looks inside a picture, so the bytes below are what the response must be —
# byte for byte, or the frame the browser paints is a frame of this test's own making.
PNG = b"\x89PNG\r\n\x1a\nthe rest of a very small picture, sent as it is"
PNG_B64 = base64.b64encode(PNG).decode("ascii")

# A file of words, sent the same way: the writer is kind-agnostic, so the one difference a test can point
# at is that these bytes are words and the answer a display path makes of them is different.
WORDS = b"# notes\n\nthe one word this file was made to hold: larkspur\n"
WORDS_B64 = base64.b64encode(WORDS).decode("ascii")

# The fixture's runs, by the state of the record each one holds.
FOLLOWED = "r20261103-080000-follower"       # the objective ended and its process is gone: a follow
STEERED = "r20261103-080100-steerme"        # no ending, and no live writer: the queue carries the word
NAMELESS = "r20261103-080200-noname"        # a `started` that names no workspace: no place to attach


def get(url):
    """One GET as (status, content type, body bytes): the three things a response is judged on."""
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


def post_json(url, payload):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def expect_error(url, status, body=None):
    """The JSON body of an error response, having checked it is one error of that status and no other.

    The status is asserted exactly: a route that answered 418 for a name it would not paint, or served the
    file it was refusing, fails here rather than passing a check for "some client error".
    """
    target = url if body is None else urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(target, timeout=TIMEOUT)
    assert raised.value.code == status
    error = json.loads(raised.value.read().decode("utf-8"))
    assert set(error) == {"error"} and error["error"]
    return error


def as_query(path):
    return urllib.parse.quote(str(path))


def write_log(run_dir, *steps):
    os.makedirs(str(run_dir), exist_ok=True)
    with open(os.path.join(str(run_dir), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for step in steps:
            handle.write(json.dumps(step) + "\n")
    return run_dir


def started(cwd, ts, **extra):
    return {"id": "000000-started", "kind": "started", "issuer": "core", "ts": ts, "cwd": cwd,
            "model": "flash-next", "run_id": "run", "root": "root", **extra}


def ended(ts="2026-11-03T08:00:30+00:00"):
    return {"id": "000009-ended", "kind": "ended", "issuer": "core", "ts": ts,
            "reason": "complete", "exit_code": 0}


def written_as(path, blob):
    """One file, written as bytes: a text-mode write on this box would translate the newlines away."""
    with open(str(path), "wb") as handle:
        handle.write(blob)
    return str(path)


@pytest.fixture
def workspace(tmp_path):
    """The folder the fixture's runs stand in — where a file the record's word names has to land."""
    folder = tmp_path / "workspace"
    folder.mkdir()
    return str(folder)


@pytest.fixture
def reaped():
    """A child that ran and was reaped, its handle held here: the `dead` verdict, safely not this process.

    The runs of this fixture name this pid because a follow ends whatever the record says is still writing,
    and the one pid that must never be named is the one belonging to the process running the test.
    """
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    return child


@pytest.fixture
def box(tmp_path, workspace, reaped):
    """A runs root holding the two channels a word can take, and a front of one file."""
    grants = {"read": [workspace], "write": [workspace]}
    write_log(tmp_path / "runs" / FOLLOWED,
              started(workspace, "2026-11-03T08:00:00+00:00", pid=reaped.pid, grants=grants),
              {"id": "000001-message", "kind": "message", "issuer": "core",
               "ts": "2026-11-03T08:00:10+00:00", "role": "user", "text": "the first objective"},
              ended())
    write_log(tmp_path / "runs" / STEERED,
              started(workspace, "2026-11-03T08:01:00+00:00", grants=grants))
    write_log(tmp_path / "runs" / NAMELESS,
              started("", "2026-11-03T08:02:00+00:00", pid=reaped.pid), ended("2026-11-03T08:02:30+00:00"))
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<!doctype html><title>SAHW</title>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def serve(box):
    """`serve(**overrides)` — the server on a free port over the fixture's folders, and its base URL."""
    started_servers = []

    def start(**overrides):
        options = {"runs_root": str(box / "runs"), "sah_tree": str(box / "sah-tree"),
                   "web_dir": str(box / "web")}
        options.update(overrides)
        httpd = server.make_server("127.0.0.1", 0, **options)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started_servers.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started_servers:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def launched(monkeypatch):
    """The launch seam: every argv, environment and working directory the server would have started."""
    calls = []
    monkeypatch.setattr(spawn, "launch", lambda argv, env, cwd: calls.append((argv, env, cwd)))
    return calls


def word_of(argv):
    """The word the argv carries: the objective after `--task`, or the block after the queue verb."""
    return argv[argv.index("--task") + 1] if "--task" in argv else argv[-1]


def reference(path):
    """The line this server writes for one file, in the words the record and the page both read."""
    return attach.REFERENCE.format(path=path)


def landed_one(workspace, pattern):
    """The one file in the workspace's estate the pattern names, having checked it is the only file there."""
    estate = os.path.join(workspace, attach.ESTATE_DIRNAME)
    names = os.listdir(estate)
    assert len(names) == 1, names
    assert re.fullmatch(pattern, names[0]), names[0]
    return os.path.join(estate, names[0])


def lines_of(word):
    """The reference lines out of a word, in the order the word carries them."""
    return [line for line in word.split("\n") if line.startswith("attached: ")]


# --- `GET /img` -----------------------------------------------------------------------------------------

def test_the_image_route_answers_the_pictures_bytes_and_the_mime_its_name_claims(serve, workspace):
    """Body and `Content-Type` in one response, and the casing of the name is not a second kind.

    The pair is what a browser paints from, so both halves are read from the same request: the bytes the
    file holds, all of them, under the mime the extension claims.
    """
    picture = written_as(os.path.join(workspace, "shot.png"), PNG)
    base = serve()
    assert get(f"{base}/img?path={as_query(picture)}") == (200, "image/png", PNG)

    capital = written_as(os.path.join(workspace, "SHOT.PNG"), PNG)
    assert get(f"{base}/img?path={as_query(capital)}") == (200, "image/png", PNG)


def test_a_path_beyond_the_folders_any_run_stands_in_is_answered_the_browsers_own_way(serve, box):
    """The reach of `/img` is the reach of the pane that asks it — and so is the answer for what is there.

    The page walks this box's folders from a drive root through `/api/fs`, so a picture it can name it
    could have listed itself: this route keeps no second list of folders, and therefore no second set of
    answers for what falls outside one. A name that claims no picture kind is the 415 `files` hands the
    browser's own route for that same name, and a path that is not there is its 404.
    """
    elsewhere = box / "elsewhere"
    elsewhere.mkdir()
    words = elsewhere / "notes.txt"
    words.write_text("words, not a picture", encoding="utf-8")
    base = serve()
    expect_error(f"{base}/img?path={as_query(words)}", 415)
    expect_error(f"{base}/img?path={as_query(elsewhere / 'gone.png')}", 404)

    picture = written_as(elsewhere / "elsewhere.png", PNG)
    assert get(f"{base}/img?path={as_query(picture)}") == get(f"{base}/api/file?path={as_query(picture)}")


def test_a_folder_and_a_name_that_resolves_under_nothing_are_the_bad_request(serve, workspace):
    """400 for the two ways a request names something this route cannot answer at all.

    A folder is not a file whatever it is called. A relative name is the one thing a page never holds —
    the record stamps absolute paths and so does the browser — and resolving one against the folder the
    server happens to stand in would answer for a file nobody meant, so the route refuses it and says why.
    """
    base = serve()
    expect_error(f"{base}/img?path={as_query(workspace)}", 400)
    relative = expect_error(f"{base}/img?path={as_query('scratch/shot.png')}", 400)
    assert "absolute" in relative["error"], relative["error"]


# --- the preview's picture branch -----------------------------------------------------------------------

def test_the_preview_answers_a_picture_as_a_picture_and_a_binary_still_as_a_refusal(serve, box):
    """The one text-only refusal that went away, and the one that stands.

    A picture file opened from the browser's pane is painted, which is the mime and the bytes rather than
    the 415 the text reader used to hand back for it; a file that names no picture kind and is not text is
    still the wrong kind of file for the route that reads words.
    """
    picture = written_as(box / "preview.png", PNG)
    binary = written_as(box / "blob.bin", b"\xff\xfe\x00\x00")
    base = serve()
    assert get(f"{base}/api/file?path={as_query(picture)}") == (200, "image/png", PNG)
    expect_error(f"{base}/api/file?path={as_query(binary)}", 415)
    expect_error(f"{base}/api/file?path={as_query(box / 'gone.webp')}", 404)


# --- the files a spawn arrives with ---------------------------------------------------------------------

def test_the_line_a_file_leaves_in_the_word_is_the_shape_the_page_parses():
    """The words, pinned: the record's rows, the face and the e2e all read this one line.

    It is a constant in `sahw.attach` for exactly this reason — a file the pane cannot find the line for is
    a file that never arrived as far as the record knows — so the sentence is asserted here in its own
    words as well as through the constant it comes from. One line for a picture and one for a page of words
    are the same sentence: the destination the face makes of the path is the display path's business.
    """
    assert attach.REFERENCE == "attached: {path} — read it"
    assert reference(r"C:\work\shot.png") == "attached: C:\\work\\shot.png — read it"
    assert reference(r"C:\work\notes.md") == "attached: C:\\work\\notes.md — read it"


def test_a_spawned_word_carries_its_picture_into_the_runs_workspace_and_its_line_into_the_objective(
        serve, box, workspace, launched):
    """The whole act, read afterwards: the file is where the run will stand, and the word says where.

    The name is this server's — a timestamp, then the sender's stem, then the extension the sender's name
    claimed, joined by one dot because the extension already carries it — so two sends cannot stand on one
    another, and the run finds the bytes by reading the sentence it was handed.
    """
    base = serve()
    status, got = post_json(base + "/api/runs", {
        "cwd": workspace, "task": "say what this shows",
        "files": [{"name": "shot.png", "bytes": PNG_B64}]})
    assert status == 201 and set(got) == {"run_id"}

    landed = landed_one(workspace, r"\d{8}-\d{6}-shot\.png")
    with open(landed, "rb") as handle:
        assert handle.read() == PNG
    assert word_of(launched[0][0]) == "say what this shows\n\n" + reference(landed)


def test_a_spawned_word_carries_a_file_of_words_the_same_way_and_its_words_are_its_own(
        serve, box, workspace, launched):
    """A `notes.md` is not a special case: the field, the write and the line are the picture's, unchanged.

    What the text kind earns is the reader instead of the frame — the bytes land as they were sent and the
    preview's text route answers them as words — which is what makes the write path's kind-blindness a fact
    a test can point at rather than a claim.
    """
    base = serve()
    status, _ = post_json(base + "/api/runs", {
        "cwd": workspace, "task": "read the note and answer with its word",
        "files": [{"name": "notes.md", "bytes": WORDS_B64}]})
    assert status == 201

    landed = landed_one(workspace, r"\d{8}-\d{6}-notes\.md")
    with open(landed, "rb") as handle:
        assert handle.read() == WORDS
    assert word_of(launched[0][0]) == ("read the note and answer with its word\n\n" + reference(landed))
    # The words route answers the landed file as words, which is the destination a picture's name has never
    # had and the reason the write path was never asked which kind it was writing.
    answered = json.loads(get(f"{base}/api/file?path={as_query(landed)}")[2].decode("utf-8"))
    assert answered["content"] == WORDS.decode("utf-8") and answered["truncated"] is False


def test_a_picture_and_a_file_of_words_in_one_word_land_as_two_files_and_two_lines(
        serve, box, workspace, launched):
    """One field, two kinds, one line apiece, in the order they arrived.

    The kinds never meet on the way in: each entry is decoded and written on its own, and the word carries
    both sentences the way it would carry two of either kind.
    """
    base = serve()
    status, _ = post_json(base + "/api/runs", {
        "cwd": workspace, "task": "the picture and the note",
        "files": [{"name": "shot.png", "bytes": PNG_B64}, {"name": "notes.md", "bytes": WORDS_B64}]})
    assert status == 201

    names = sorted(os.listdir(os.path.join(workspace, attach.ESTATE_DIRNAME)))
    assert len(names) == 2, names
    word = word_of(launched[0][0])
    lines = lines_of(word)
    assert len(lines) == 2, word
    named = [line.removeprefix("attached: ").removesuffix(" — read it") for line in lines]
    assert sorted(os.path.basename(path) for path in named) == sorted(names)
    assert named[0].endswith(".png") and named[1].endswith(".md"), "the order the word carries them"
    for path, blob in zip(named, (PNG, WORDS), strict=True):
        with open(path, "rb") as handle:
            assert handle.read() == blob


def test_two_files_leave_two_files_and_two_lines_in_the_order_they_arrived(serve, box, workspace,
                                                                           launched):
    """Including the case the sender cannot help: one name, twice, in the same second.

    The draw is exclusive and the loser draws again, so both files survive — the second under a name of its
    own — and each line names a file that holds the bytes it was sent as, with one dot between the stem and
    the kind.
    """
    base = serve()
    status, _ = post_json(base + "/api/runs", {
        "cwd": workspace, "task": "two of them",
        "files": [{"name": "shot.png", "bytes": PNG_B64}, {"name": "shot.png", "bytes": PNG_B64}]})
    assert status == 201

    names = sorted(os.listdir(os.path.join(workspace, attach.ESTATE_DIRNAME)))
    assert len(names) == 2, names
    assert all(re.fullmatch(r"\d{8}-\d{6}-shot(-2)?\.png", name) for name in names), names
    word = word_of(launched[0][0])
    lines = lines_of(word)
    assert len(lines) == 2, word
    named = [line.removeprefix("attached: ").removesuffix(" — read it") for line in lines]
    assert len(set(named)) == 2, "two files, two files"
    for path in named:
        with open(path, "rb") as handle:
            assert handle.read() == PNG
        assert ".." not in os.path.basename(path), "one dot between the stem and the kind it claims"


def test_an_empty_list_of_files_is_the_word_exactly_as_it_was_typed(serve, box, workspace, launched):
    """No line and no blank line above it, and no file: the route cannot be told it carried the field.

    `[]` is not a refusal — it is a composer with the tray empty — and the objective a run reads has to be
    the one that was typed, byte for byte, or every route that ever carried a word would owe a line about a
    file nobody sent.
    """
    base = serve()
    status, _ = post_json(base + "/api/runs", {"cwd": workspace, "task": "words only", "files": []})
    assert status == 201
    assert word_of(launched[0][0]) == "words only"
    assert os.listdir(workspace) == []


def test_a_word_that_names_no_field_at_all_is_the_word_as_it_was_typed(serve, box, workspace, launched):
    """The other half of the same settlement: an absent field is not a refusal either.

    A body with neither `files` nor the old name sends the word the composer holds, and the route answers
    exactly as it did before any file could ride — because the plain word is the commonest request this
    server makes and it must never be able to acquire a line about nothing.
    """
    base = serve()
    status, _ = post_json(base + "/api/runs", {"cwd": workspace, "task": "just the task"})
    assert status == 201
    assert word_of(launched[0][0]) == "just the task"
    assert os.listdir(workspace) == []


# --- what is refused before a run starts ----------------------------------------------------------------

def test_the_old_field_name_is_refused_with_the_new_one_named(serve, box, workspace, launched):
    """A body under the name that used to be true is answered, not quietly emptied.

    `images` carried every entry this route ever wrote and is a lie about a `notes.md`, so the refusal is
    the sentence that names `files`; and a silently dropped attachment is the one failure the sender never
    hears about, so nothing is written and nothing is started.
    """
    base = serve()
    before = set(os.listdir(str(box / "runs")))
    error = expect_error(base + "/api/runs", 400, json.dumps({
        "cwd": workspace, "task": "read the note",
        "images": [{"name": "notes.md", "bytes": WORDS_B64}]}).encode("utf-8"))
    assert "files" in error["error"], error["error"]
    assert launched == [] and set(os.listdir(str(box / "runs"))) == before
    assert os.listdir(workspace) == []


def test_a_body_carrying_both_names_is_still_the_refusal_that_names_files(serve, box, workspace,
                                                                         launched):
    """The old name is never read, and its presence is a mistake whoever sent the body can be told about.

    Choosing the new field and writing it would leave the operator's other attachment on the floor with no
    word said, which is the failure this route exists to refuse; the answer is the same sentence.
    """
    base = serve()
    error = expect_error(base + "/api/runs", 400, json.dumps({
        "cwd": workspace, "task": "one of each, under both names",
        "files": [{"name": "notes.md", "bytes": WORDS_B64}],
        "images": [{"name": "shot.png", "bytes": PNG_B64}]}).encode("utf-8"))
    assert "files" in error["error"] and "images" in error["error"], error["error"]
    assert launched == [] and os.listdir(workspace) == []


def test_a_file_that_is_not_base64_starts_nothing(serve, box, workspace, launched):
    """The body is the caller's, and the answer is a sentence, not a run looking for a file it never got.

    Read afterwards: no folder in the runs root that was not there before, no launched child, and no file
    in the workspace — the decoding is the first thing the route does.
    """
    base = serve()
    before = set(os.listdir(str(box / "runs")))
    error = expect_error(base + "/api/runs", 400, json.dumps({
        "cwd": workspace, "task": "say what this shows",
        "files": [{"name": "shot.png", "bytes": "not base64 at all!!"}]}).encode("utf-8"))
    assert "base64" in error["error"], error["error"]
    assert launched == []
    assert set(os.listdir(str(box / "runs"))) == before
    assert os.listdir(workspace) == []


def test_a_file_with_no_name_starts_nothing(serve, box, workspace, launched):
    """A file arrives with the name it was sent as: the extension it claims is the kind it is written
    under, and a name that is blank leaves the server choosing a kind for bytes it cannot see."""
    base = serve()
    error = expect_error(base + "/api/runs", 400, json.dumps({
        "cwd": workspace, "task": "say what this shows",
        "files": [{"name": "   ", "bytes": PNG_B64}]}).encode("utf-8"))
    assert "no name" in error["error"], error["error"]
    assert launched == [] and os.listdir(workspace) == []


def test_a_workspace_that_is_not_a_folder_is_refused_before_the_run_is_started(serve, box, launched):
    """The 400 arrives with the workspace named, and the runs root untouched.

    Without the field this body would be refused by the launcher for the same reason; with files in it the
    refusal is the writer's, and it comes first, so a run is never launched into a folder that cannot hold
    what its own objective claims is there.
    """
    base = serve()
    before = set(os.listdir(str(box / "runs")))
    error = expect_error(base + "/api/runs", 400, json.dumps({
        "cwd": str(box / "gone"), "task": "say what this shows",
        "files": [{"name": "shot.png", "bytes": PNG_B64}]}).encode("utf-8"))
    assert "not a folder" in error["error"] and "gone" in error["error"], error["error"]
    assert launched == [] and set(os.listdir(str(box / "runs"))) == before


# --- the files a word to an existing run arrives with ---------------------------------------------------

def test_a_follow_carries_its_picture_into_the_workspace_the_record_names(serve, box, workspace, launched):
    """The body names no folder, and the picture still lands where the run stands.

    The workspace comes from the run's own newest `started` line — the record, not the page, knows where a
    run is — and the follow's objective carries the line the way the spawn's does, so a second objective
    reads the same kind of sentence as the first.
    """
    base = serve()
    status, got = post_json(f"{base}/api/runs/{FOLLOWED}/message", {
        "text": "and this one?", "files": [{"name": "second.png", "bytes": PNG_B64}]})
    assert (status, got) == (200, {"ok": True, "channel": "follow", "run": FOLLOWED})

    landed = landed_one(workspace, r"\d{8}-\d{6}-second\.png")
    argv = launched[0][0]
    assert "--resume" in argv
    assert word_of(argv) == "and this one?\n\n" + reference(landed)


def test_the_estate_stands_under_the_root_and_the_root_keeps_its_own_contents(serve, box, workspace,
                                                                             launched):
    """The files ride under the workspace's estate, and the root keeps everything else.

    The workspace is the project's own folder — the ground a run stands on and the tree reads — so a file
    the operator sends in stands under the estate's one dot-prefixed name, made on the request that needs
    it, and the root that held nothing but the project holds nothing but the estate afterwards. The line
    names the path under it, so the run reaches the bytes on the grant it already holds on the root.
    """
    base = serve()
    status, _ = post_json(base + "/api/runs", {
        "cwd": workspace, "task": "say what this shows",
        "files": [{"name": "shot.png", "bytes": PNG_B64}]})
    assert status == 201

    assert os.listdir(workspace) == [attach.ESTATE_DIRNAME], "the root keeps its own contents"
    estate = os.path.join(workspace, attach.ESTATE_DIRNAME)
    landed = landed_one(workspace, r"\d{8}-\d{6}-shot\.png")
    assert landed.startswith(estate + os.sep), landed
    assert word_of(launched[0][0]) == "say what this shows\n\n" + reference(landed)


def test_a_follow_carries_a_file_of_words_into_the_same_word_the_way_a_spawn_does(
        serve, box, workspace, launched):
    """The second objective's text file is the first objective's picture: field, write, line — one path.

    Read from the record afterwards, the follow's `--resume` argv carries the operator's sentence, a blank
    line, and the one sentence naming the file the run was handed — which is all any channel has ever
    carried, and the reason a run with no eyes works a text file at all.
    """
    base = serve()
    status, got = post_json(f"{base}/api/runs/{FOLLOWED}/message", {
        "text": "and the note?", "files": [{"name": "notes.md", "bytes": WORDS_B64}]})
    assert (status, got) == (200, {"ok": True, "channel": "follow", "run": FOLLOWED})

    landed = landed_one(workspace, r"\d{8}-\d{6}-notes\.md")
    with open(landed, "rb") as handle:
        assert handle.read() == WORDS
    assert word_of(launched[0][0]) == "and the note?\n\n" + reference(landed)


def test_a_steer_carries_the_same_line_into_the_queued_word(serve, box, workspace, launched):
    """A word that goes to the queue is still the word, lines and all.

    The reference line is part of what was typed, so it arrives on every channel one can take — the queue
    block here, since nothing is writing to this log and a queued word waits for the next resume. A file of
    words earns the same queue block as a picture: the steer carries text and nothing else.
    """
    base = serve()
    status, got = post_json(f"{base}/api/runs/{STEERED}/message", {
        "text": "look at this one", "files": [{"name": "notes.md", "bytes": WORDS_B64}]})
    assert (status, got) == (200, {"ok": True, "channel": "steer", "run": STEERED})

    argv = launched[0][0]
    assert argv[argv.index("send") + 1] == "--run-dir", "the queue verb, not a relaunch"
    assert word_of(argv) == "look at this one\n\n" + reference(
        os.path.join(workspace, attach.ESTATE_DIRNAME,
                     os.listdir(os.path.join(workspace, attach.ESTATE_DIRNAME))[0]))


def test_a_run_whose_own_log_names_no_workspace_cannot_be_shown_a_file(serve, box, workspace,
                                                                        launched):
    """The refusal is the sentence, and it is answered before a process is stopped or started."""
    base = serve()
    error = expect_error(f"{base}/api/runs/{NAMELESS}/message", 400, json.dumps({
        "text": "see this?", "files": [{"name": "shot.png", "bytes": PNG_B64}]}).encode("utf-8"))
    assert "no workspace to attach into" in error["error"], error["error"]
    assert launched == [] and os.listdir(workspace) == []


def test_a_word_whose_file_does_not_decode_is_refused_before_the_run_is_touched(serve, box, workspace,
                                                                                launched):
    """The follow's refusals are answered with the record already read and nothing yet moved."""
    base = serve()
    error = expect_error(f"{base}/api/runs/{FOLLOWED}/message", 400, json.dumps({
        "text": "see this?", "files": [{"name": "shot.png", "bytes": "!!!not base64!!!"}]}).encode("utf-8"))
    assert "base64" in error["error"], error["error"]
    assert launched == [] and os.listdir(workspace) == []


def test_a_message_under_the_old_field_name_is_refused_with_the_new_one_named(serve, box, workspace,
                                                                              launched):
    """The follow route is the other half of the contract, and refuses the old name the same way.

    Read afterwards: the run's process was not stopped, no child was launched, and the workspace holds
    nothing — the field is settled before the record is asked anything about the run.
    """
    base = serve()
    error = expect_error(f"{base}/api/runs/{FOLLOWED}/message", 400, json.dumps({
        "text": "read the note", "images": [{"name": "notes.md", "bytes": WORDS_B64}]}).encode("utf-8"))
    assert "files" in error["error"], error["error"]
    assert launched == [] and os.listdir(workspace) == []


# --- kind is the display paths' business ----------------------------------------------------------------

def test_a_kind_no_display_path_answers_lands_as_bytes_and_the_display_paths_refuse_it(
        serve, box, workspace, launched):
    """The writer asks no kind question, so a file neither a frame nor a reader answers still arrives.

    The bytes are the ones no reader answers — not utf-8, and an extension no picture map holds — and the
    refusal, when the operator looks, is the display path's own: 415 from the picture route and 415 from
    the words route, in the one error shape. Both come after the write and neither empties the word; the
    line is the record's and the bytes are the workspace's.
    """
    opaque = b"\xff\xfe\x00\x00"
    base = serve()
    status, _ = post_json(base + "/api/runs", {
        "cwd": workspace, "task": "what is this?",
        "files": [{"name": "mystery.qwerty",
                   "bytes": base64.b64encode(opaque).decode("ascii")}]})
    assert status == 201

    landed = landed_one(workspace, r"\d{8}-\d{6}-mystery\.qwerty")
    with open(landed, "rb") as handle:
        assert handle.read() == opaque
    assert lines_of(word_of(launched[0][0])) == [reference(landed)]
    picture = expect_error(f"{base}/img?path={as_query(landed)}", 415)
    words = expect_error(f"{base}/api/file?path={as_query(landed)}", 415)
    assert picture["error"] and words["error"]
