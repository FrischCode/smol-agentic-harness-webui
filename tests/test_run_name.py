"""sahw.runs and sahw.server — the run's name: the row's three sources, and the act that writes one of them.

The record is the machine's and holds the word the boot was started with; the run's *current* name is the
face's, held in `name.txt` beside that log — a file the run's own process never opens, which is the whole
of the safety the act needs and why it holds no liveness guard. What is pinned here is the division, from
both sides:

* **The row's rule**, in the one place it runs (`runs.worn_name`, read by `describe_run`): the file's word,
  else the head's `started.title`, else the operator's first word, and no `name` key at all when nothing
  says — the `live`/`fork`/`task` discipline of the row, with the record's own word still riding under
  `task` beside it.
* **The act's four answers** on the wire: a written word (200, `action: "wrote"`, the file standing beside
  the log with the word on one line), a clear (200, `action: "cleared"`, the file gone and the fallback the
  answer names standing in its place), a name carrying a line boundary (the 400 that names the boundary,
  the file untouched), and an id the tree does not hold (the 404 that names the id).
* **The record untouched**: a rename leaves `log.jsonl` byte-identical — the hash taken before the act
  standing equal to the hash taken after it, which is a fact about what the route does rather than a guard
  it enforces.
* **The tree's own reading**: the poll that remembers rows answers a renamed run under its new word, though
  the log never moved; and a folder moved under another runs root still wears its word, because the word
  lives in the folder.

No test here starts a run: `spawn.launch` is never reached, and the runs the fixture's roots hold are
records on disk, which is all the tree reads and all a rename asks of.
"""
import hashlib
import json
import os
import shutil
import threading
import urllib.error
import urllib.request

import pytest

from sahw import runs, server

TIMEOUT = 15.0

# The four runs the fixture's root holds, one per source of a name — the file's word, the boot's word, the
# operator's first word, and a run none of the three was said about.
RUN_FILE = "r20261109-080000-named"
RUN_TITLE = "r20261109-080100-booted"
RUN_TASK = "r20261109-080200-spoken"
RUN_NONE = "r20261109-080300-silent"


def get_json(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def refused(url, status, payload):
    """The JSON body of an error response, having checked it is one error of that status and no other."""
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(request, timeout=TIMEOUT)
    assert raised.value.code == status
    error = json.loads(raised.value.read().decode("utf-8"))
    assert set(error) == {"error"} and error["error"]
    return error["error"]


def tree_of(base):
    return {row["id"]: row for row in get_json(f"{base}/api/runs")[1]["workspaces"][0]["runs"]}


def make_log(run_dir, ts, title="", task=""):
    """One ended run's record: the head a row is built from, with the two words a head may carry.

    `title` is the boot's word and is stamped only when there is one — absent is the field's refusal, the
    shape SAH writes when the operator named nothing — and `task` is the user message the row's `task` is
    read from.
    """
    started = {"id": "000000-started", "kind": "started", "issuer": "core", "ts": ts,
               "cwd": "C:\\somewhere\\the workspace", "model": "flash-next",
               "run_id": os.path.basename(run_dir), "root": "root"}
    if title:
        started["title"] = title
    steps = [started]
    if task:
        steps.append({"id": "000001-message", "kind": "message", "issuer": "core", "role": "user",
                      "text": task})
    steps.append({"id": "000009-ended", "kind": "ended", "issuer": "core",
                  "ts": ts.replace("08:0", "09:0"), "reason": "complete", "exit_code": 0})
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for step in steps:
            handle.write(json.dumps(step) + "\n")
    return run_dir


def log_hash(run_dir):
    with open(os.path.join(run_dir, runs.LOG_NAME), "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def name_path(run_dir):
    return os.path.join(run_dir, runs.NAME_NAME)


def read_name(run_dir):
    with open(name_path(run_dir), "rb") as handle:
        return handle.read()


@pytest.fixture
def box(tmp_path):
    """A runs root of four records over one workspace, and a front of one file."""
    root = tmp_path / "runs"
    make_log(str(root / RUN_FILE), "2026-11-09T08:00:00+00:00", title="the boot word",
             task="the first word")
    make_log(str(root / RUN_TITLE), "2026-11-09T08:01:00+00:00", title="the boot word",
             task="the first word")
    make_log(str(root / RUN_TASK), "2026-11-09T08:02:00+00:00", task="the first word")
    make_log(str(root / RUN_NONE), "2026-11-09T08:03:00+00:00")
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<!doctype html><title>SAHW</title>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def serve(box):
    """`serve()` — the server on a free port over the fixture's root, with its base URL."""
    started = []

    def start():
        httpd = server.make_server("127.0.0.1", 0, runs_root=str(box / "runs"),
                                   sah_tree=str(box / "sah-tree"), web_dir=str(box / "web"))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started:
        httpd.shutdown()
        httpd.server_close()


# --- the row's rule, read by the tree ---------------------------------------------------------------------

def test_the_row_wears_its_three_sources_in_order(box):
    rows = {row["id"]: row for row in runs.tree(str(box / "runs"))["workspaces"][0]["runs"]}
    assert rows[RUN_FILE]["task"] == "the first word"        # the record's word keeps standing
    assert rows[RUN_TITLE]["name"] == "the boot word"        # no file: the head's word
    assert rows[RUN_TASK]["name"] == "the first word"        # no file, no title: the operator's word
    assert "name" not in rows[RUN_NONE], "a run nothing names carries no name key, as `live` and `fork` do"


def test_a_standing_file_wears_its_word_over_the_head(box):
    """The file is the current name and outranks both of the record's words — read as one line."""
    made = make_log(str(box / "runs" / "r20261109-080400-file-only"), "2026-11-09T08:04:00+00:00",
                    title="the boot word", task="the first word")
    with open(name_path(made), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("the word the face wrote\n")
    rows = {row["id"]: row for row in runs.tree(str(box / "runs"))["workspaces"][0]["runs"]}
    assert rows[os.path.basename(made)]["name"] == "the word the face wrote"
    assert rows[os.path.basename(made)]["task"] == "the first word"


def test_a_name_file_holding_nothing_names_nothing(box):
    """A file whose line is empty is no name: the row falls back rather than wearing a blank."""
    made = make_log(str(box / "runs" / "r20261109-080500-blank"), "2026-11-09T08:05:00+00:00",
                    task="the first word")
    with open(name_path(made), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n")
    assert runs.face_name(made) == ""
    rows = {row["id"]: row for row in runs.tree(str(box / "runs"))["workspaces"][0]["runs"]}
    assert rows[os.path.basename(made)]["name"] == "the first word"


def test_a_folder_with_no_name_file_answers_without_reading_one(box):
    """The absent case is the ordinary one of the tree, and it is not a fault to raise for."""
    assert runs.face_name(str(box / "runs" / RUN_TASK)) == ""
    assert runs.face_name(str(box / "runs" / "no-such-folder-at-all")) == ""


# --- the act: the four answers, on the wire ---------------------------------------------------------------

def test_rename_writes_the_word_beside_the_log(serve, box):
    base = serve()
    run = str(box / "runs" / RUN_TASK)
    before = log_hash(run)
    status, answer = post_json(f"{base}/api/runs/{RUN_TASK}/rename", {"name": "  the refund branch  "})
    assert status == 200
    assert answer == {"ok": True, "run": RUN_TASK, "action": "wrote", "name": "the refund branch"}
    assert read_name(run) == b"the refund branch\n", "one line: the word, and the newline that ends it"
    assert not os.path.exists(name_path(run) + ".tmp"), "the replace leaves no temp behind"
    assert log_hash(run) == before, "the rename leaves the record byte-identical"
    assert tree_of(base)[RUN_TASK]["name"] == "the refund branch"
    assert tree_of(base)[RUN_TASK]["task"] == "the first word", "the record's word keeps standing"


def test_a_rename_leaves_the_log_byte_identical(serve, box):
    """The guarantee the act owes the record: the hash the pin takes before the act equals the one after.

    Pinned apart from the act that passes, because it is the claim the whole division rests on: the name is
    not a line of the record, and a route that wrote it wrote something it was never given.
    """
    base = serve()
    run = str(box / "runs" / RUN_TITLE)
    before = log_hash(run)
    for word in ("first", "second", "third", "", "   "):
        post_json(f"{base}/api/runs/{RUN_TITLE}/rename", {"name": word})
        assert log_hash(run) == before
    assert not os.path.exists(name_path(run)), "the walk ends on a clear, and a clear leaves no file"


def test_clearing_a_name_answers_the_fallback_standing(serve, box):
    base = serve()
    run = str(box / "runs" / RUN_TITLE)
    post_json(f"{base}/api/runs/{RUN_TITLE}/rename", {"name": "a word to take back"})
    status, answer = post_json(f"{base}/api/runs/{RUN_TITLE}/rename", {"name": ""})
    assert status == 200
    assert answer == {"ok": True, "run": RUN_TITLE, "action": "cleared", "name": "the boot word"}
    assert not os.path.exists(name_path(run)), "the file goes when the word does"
    assert tree_of(base)[RUN_TITLE]["name"] == "the boot word", "the row falls back to the boot's word"


def test_clearing_a_name_that_only_the_operator_spoke_falls_to_that_word(serve, box):
    base = serve()
    post_json(f"{base}/api/runs/{RUN_TASK}/rename", {"name": "temporary"})
    _, answer = post_json(f"{base}/api/runs/{RUN_TASK}/rename", {"name": "   "})
    assert answer["action"] == "cleared" and answer["name"] == "the first word"


def test_clearing_a_run_that_was_never_named_is_a_clear_and_no_error(serve, box):
    """Nothing stood and nothing was held: the answer is the clear, and the row keeps its silence."""
    base = serve()
    status, answer = post_json(f"{base}/api/runs/{RUN_NONE}/rename", {"name": " "})
    assert status == 200
    assert answer == {"ok": True, "run": RUN_NONE, "action": "cleared", "name": ""}
    assert not os.path.exists(name_path(str(box / "runs" / RUN_NONE)))
    assert "name" not in tree_of(base)[RUN_NONE]


@pytest.mark.parametrize("word", ["two\nlines", "two\rlines", "\n", "a line\r\nand another"])
def test_a_name_of_two_lines_is_refused_with_its_named_line(serve, box, word):
    base = serve()
    run = str(box / "runs" / RUN_TITLE)
    before = log_hash(run)
    sentence = refused(f"{base}/api/runs/{RUN_TITLE}/rename", 400, {"name": word})
    assert sentence.startswith("a name is one line:"), sentence
    assert not os.path.exists(name_path(run)), "a refusal writes nothing"
    assert log_hash(run) == before
    assert tree_of(base)[RUN_TITLE]["name"] == "the boot word", "the row keeps the word it wore"


def test_a_run_the_tree_does_not_hold_is_refused_with_its_id(serve):
    base = serve()
    assert refused(f"{base}/api/runs/r20990101-000000-nope/rename", 404,
                   {"name": "a word for nothing"}) == "no such run: r20990101-000000-nope"


def test_a_run_id_that_is_a_path_is_refused_before_anything_is_named(serve, box):
    base = serve()
    assert refused(f"{base}/api/runs/..%2F..%2Fruns/rename", 400,
                   {"name": "a word for a folder"}) == "a run id is one folder name, not a path"
    assert not os.path.exists(name_path(str(box / "runs" / RUN_TASK)))


def test_a_rename_that_named_no_word_names_no_word(serve, box):
    """A body with no `name` field is a body that names nothing, which is the clear the route answers."""
    base = serve()
    post_json(f"{base}/api/runs/{RUN_TASK}/rename", {"name": "to be taken back"})
    _, answer = post_json(f"{base}/api/runs/{RUN_TASK}/rename", {})
    assert answer["action"] == "cleared" and answer["name"] == "the first word"


# --- the tree, the poll, and the folder that travels -------------------------------------------------------

def test_the_poll_answers_a_renamed_run_though_the_log_never_moved(serve, box):
    """The row is built from two files now, and the poll's memory is matched against both.

    The first listing warms the page; the rename writes only the name file; and the next listing — the same
    poll, over a log that moved no byte — has to answer the new word rather than the row it remembered.
    """
    base = serve()
    run = str(box / "runs" / RUN_TASK)
    warmed = tree_of(base)[RUN_TASK]
    stamped = os.stat(os.path.join(run, runs.LOG_NAME))
    post_json(f"{base}/api/runs/{RUN_TASK}/rename", {"name": "reworn"})
    assert tree_of(base)[RUN_TASK]["name"] == "reworn"
    after = os.stat(os.path.join(run, runs.LOG_NAME))
    assert (stamped.st_size, stamped.st_mtime_ns) == (after.st_size, after.st_mtime_ns), \
        "the record stood still while the row changed its word"
    assert tree_of(base)[RUN_TASK] == warmed | {"name": "reworn"}


def test_a_cleared_name_is_answered_again_from_the_record(serve, box):
    base = serve()
    post_json(f"{base}/api/runs/{RUN_TITLE}/rename", {"name": "here a while"})
    assert tree_of(base)[RUN_TITLE]["name"] == "here a while"
    post_json(f"{base}/api/runs/{RUN_TITLE}/rename", {"name": "gone"})
    post_json(f"{base}/api/runs/{RUN_TITLE}/rename", {"name": ""})
    assert tree_of(base)[RUN_TITLE]["name"] == "the boot word"


def test_the_name_travels_with_the_folder(box, tmp_path):
    """No name stands in the server's own state: a folder moved under another root still wears its word."""
    moved = str(tmp_path / "another-root" / RUN_TASK)
    os.makedirs(os.path.dirname(moved), exist_ok=True)
    shutil.move(str(box / "runs" / RUN_TASK), moved)
    assert runs.write_face_name(moved, "named where it stood") == "wrote"
    fresh = runs.tree(str(tmp_path / "another-root"))["workspaces"][0]["runs"]
    assert [row["name"] for row in fresh] == ["named where it stood"]
    left = runs.tree(str(box / "runs"))["workspaces"][0]["runs"]
    assert RUN_TASK not in [row["id"] for row in left], "the root it left simply has one row fewer"


def test_the_answer_carries_the_name_the_row_wears_and_the_face_patches_from_it(serve, box):
    """The wire's contract for the face: the answer alone is enough to re-wear the row, no re-list owed."""
    base = serve()
    _, answer = post_json(f"{base}/api/runs/{RUN_NONE}/rename", {"name": "named from nothing"})
    assert answer["name"] == "named from nothing"
    row = tree_of(base)[RUN_NONE]
    assert row["name"] == answer["name"], "the row wears exactly what the answer said, and nothing else"
    assert set(row) >= {"id", "ts", "model", "status", "reason", "name"}
