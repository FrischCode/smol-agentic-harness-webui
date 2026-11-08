"""sahw.server — the routes that act: two deletes (one run, or a batch — one workspace's runs, or every
workspace's), one export, and the machine's own window.

These routes change something or reach the machine, so every claim here is checked against what they leave
behind: the folder that is no longer there, the folders that still are, the export's bytes against the
translation the same log gives, and the argv a spawn that never happened would have run with. Nothing is
opened for real — `openers.launch` is the seam the module itself offers, held by a stand-in that reads the
argv and the flags and never touches a window — and the two pids behind the liveness guard are this
battery's own children: one still running, one that ran and was reaped.

The handles are held because the guard reads a pid, and the answers it must never confuse are exactly two:
a number that still names a process, and a number that names one no longer. A pid stays answerable until
the last handle to it closes, so holding it makes the dead answer a fact about the record rather than a
race with this box's reuse of the number.

The terminal a folder opens with is asked of the probe's `which` seam rather than of this machine's path:
which branch the act takes is a fact the server settles at startup, and a test that read the real path
would pass or fail depending on what the machine running it happens to have installed.
"""
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

from sahw import export, openers, runs, server

TIMEOUT = 15.0

ALPHA = r"C:\work\alpha"
BETA = r"C:\work\beta"

# ALPHA holds the three a delete is judged on — a run whose process answers, one whose pid is a number
# this box let go of, and one the log finished — and BETA holds a workspace whose whole batch is safe.
LIVE_ID = "r20261101-090000-aaaaaa"
DEAD_ID = "r20261101-080000-bbbbbb"
ENDED_ID = "r20261101-070000-cccccc"
BETA_ONE = "r20261101-060000-dddddd"
BETA_TWO = "r20261101-050000-eeeeee"
NO_LOG_ID = "r20261101-040000-ffffff"
GONE_ID = "r20261101-030000-0g0g0g"

SENTENCE = "the record's own sentence, exported as written"


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
    """The JSON body of an error response, having checked it is one error of that status and no other."""
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
    with open(os.path.join(str(run_dir), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for step in steps:
            handle.write(json.dumps(step) + "\n")
    return run_dir


def started(cwd, ts, **extra):
    return {"id": "000000-started", "kind": "started", "issuer": "core", "ts": ts, "cwd": cwd,
            "model": "flash-next", "run_id": "run", "root": "root", **extra}


def message(text=SENTENCE):
    return {"id": "000005-message", "kind": "message", "issuer": "core",
            "ts": "2026-11-01T08:30:00+00:00", "role": "assistant", "text": text}


def ended():
    return {"id": "000009-ended", "kind": "ended", "issuer": "core", "ts": "2026-11-01T09:00:00+00:00",
            "reason": "complete", "exit_code": 0}


def rows_of(tree_payload):
    """The tree's rows by run id: the lookup a test wants instead of walking the workspaces."""
    return {row["id"]: row for workspace in tree_payload["workspaces"] for row in workspace["runs"]}


@pytest.fixture
def processes():
    """One child still running and one that ran and was reaped, both handles held by this battery."""
    live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    yield live, ran
    live.kill()
    live.wait()


@pytest.fixture
def root(tmp_path, processes):
    """A runs root with the two workspaces, and a folder beside the root the routes must never reach."""
    live, ran = processes
    write_log(tmp_path / "runs" / LIVE_ID, started(ALPHA, "2026-11-01T09:00:00+00:00", pid=live.pid))
    write_log(tmp_path / "runs" / DEAD_ID, started(ALPHA, "2026-11-01T08:00:00+00:00", pid=ran.pid))
    write_log(tmp_path / "runs" / ENDED_ID, started(ALPHA, "2026-11-01T07:00:00+00:00"), message(), ended())
    write_log(tmp_path / "runs" / BETA_ONE, started(BETA, "2026-11-01T06:00:00+00:00", pid=ran.pid))
    write_log(tmp_path / "runs" / BETA_TWO, started(BETA, "2026-11-01T05:00:00+00:00"), ended())
    (tmp_path / "outside").mkdir()
    return tmp_path / "runs"


@pytest.fixture
def serve(root):
    """`serve()` — the server on a free port over that runs root, and a base URL to ask it things."""
    started_servers = []

    def start():
        httpd = server.make_server("127.0.0.1", 0, runs_root=str(root))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started_servers.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started_servers:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def windows(monkeypatch):
    """The spawn, held: every argv and flag set `/api/open` would have run with, and no window."""
    asked = []

    def pretend(argv, flags):
        asked.append((argv, flags))
        return None

    monkeypatch.setattr(openers, "launch", pretend)
    return asked


@pytest.fixture
def hold_terminal(monkeypatch):
    """`hold_terminal(True)` is a box whose path answers `wt`; `hold_terminal(False)` one that answers
    nothing. The real probe runs either way — the seam it asks through is the one being held."""
    probe = openers.terminal_program

    def hold(has_windows_terminal):
        found = {"wt": r"C:\Program Files\wt.exe", "wt.exe": r"C:\Program Files\wt.exe"}
        monkeypatch.setattr(openers, "terminal_program",
                            lambda: probe(which=(found.get if has_windows_terminal else {}.get)))

    return hold


# --- the delete of one run -------------------------------------------------------------------------------

def test_a_delete_refuses_the_run_that_is_still_working_and_names_it(serve, root):
    base = serve()
    status, answer = post_json(f"{base}/api/runs/{LIVE_ID}/delete", {})
    # A live run is not a bad request: the act was understood, the machine declined it.
    assert status == 200
    assert answer["ok"] is False
    assert LIVE_ID in answer["reason"], "the refusal names the run it declined"
    assert "nothing was deleted" in answer["reason"]
    assert (root / LIVE_ID / runs.LOG_NAME).is_file(), "the record stands exactly where it stood"
    assert rows_of(get_json(base + "/api/runs")[1])[LIVE_ID]["live"] == "live", "the tree agrees"


def test_a_delete_takes_a_run_that_is_not_working_off_disk(serve, root):
    base = serve()
    status, answer = post_json(f"{base}/api/runs/{DEAD_ID}/delete", {})
    assert (status, answer) == (200, {"ok": True, "deleted": DEAD_ID})
    assert not os.path.exists(root / DEAD_ID), "the folder's absence is the check"
    assert DEAD_ID not in rows_of(get_json(base + "/api/runs")[1])
    for untouched in (LIVE_ID, ENDED_ID, BETA_ONE, BETA_TWO):
        assert (root / untouched).is_dir(), f"{untouched} was not asked about"


def test_a_run_the_log_finished_deletes_without_the_machine_being_asked(serve, root):
    base = serve()
    assert post_json(f"{base}/api/runs/{ENDED_ID}/delete", {})[1] == {"ok": True, "deleted": ENDED_ID}
    assert not os.path.exists(root / ENDED_ID)


def test_a_name_that_would_reach_out_of_the_runs_root_is_refused(serve, root, tmp_path):
    base = serve()
    for spelling in ("..%2f..%2foutside", "..%5c..%5coutside", "..%2fruns%2f" + DEAD_ID):
        error = expect_error(f"{base}/api/runs/{spelling}/delete", 400, b"{}")
        assert "one folder name" in error["error"], error["error"]
    error = expect_error(f"{base}/api/runs/{GONE_ID}/delete", 404, b"{}")
    assert "no such run" in error["error"]
    assert (tmp_path / "outside").is_dir(), "the folder outside the root was never even joined to it"
    assert sorted(os.listdir(root)) == sorted([LIVE_ID, DEAD_ID, ENDED_ID, BETA_ONE, BETA_TWO])


# --- the delete of a workspace's runs ---------------------------------------------------------------------

def test_the_batch_is_refused_whole_when_one_member_holds_a_process(serve, root):
    base = serve()
    status, answer = post_json(f"{base}/api/runs/delete-all", {"cwd": ALPHA})
    assert status == 200, "a refused act is the act's own shape, not a caller's mistake"
    assert answer["ok"] is False
    assert answer["live"] == [LIVE_ID], "the member that refused the batch is named by id"
    assert LIVE_ID in answer["reason"] and "nothing was deleted" in answer["reason"]
    for member in (LIVE_ID, DEAD_ID, ENDED_ID):
        assert (root / member).is_dir(), "a batch that half-happened is not a batch"


def test_the_batch_removes_the_workspaces_runs_and_no_other_folder(serve, root):
    base = serve()
    before = sorted(os.listdir(root))
    status, answer = post_json(f"{base}/api/runs/delete-all", {"cwd": BETA})
    # The batch answers the ids in the order the folders sort, which is the order they were minted.
    assert (status, answer) == (200, {"ok": True, "deleted": [BETA_TWO, BETA_ONE]})
    assert sorted(os.listdir(root)) == [name for name in before
                                        if name not in (BETA_ONE, BETA_TWO)], \
        "every named folder gone, and no folder that was not named"
    rows = rows_of(get_json(base + "/api/runs")[1])
    assert BETA_ONE not in rows and BETA_TWO not in rows
    assert LIVE_ID in rows and DEAD_ID in rows and ENDED_ID in rows, "the other workspace stands"


def test_a_batch_that_names_no_workspace_is_refused_as_a_bad_request(serve, root):
    # A body that carries `cwd` and holds nothing in it is a caller's mistake, not the whole-tree ask: the
    # ask for every workspace is a body that carries the field not at all, and this one is answered before
    # any folder is judged.
    base = serve()
    for spelling in ({"cwd": ""}, {"cwd": None}):
        error = expect_error(base + "/api/runs/delete-all", 400, json.dumps(spelling).encode("utf-8"))
        assert "cwd" in error["error"]
    for member in (LIVE_ID, DEAD_ID, ENDED_ID, BETA_ONE, BETA_TWO):
        assert (root / member).is_dir(), "a refused body deletes no folder, whole or otherwise"


# --- the delete of every workspace's runs ----------------------------------------------------------------

def test_the_whole_tree_batch_is_refused_whole_by_one_member_holding_a_process(serve, root):
    base = serve()
    status, answer = post_json(f"{base}/api/runs/delete-all", {})
    assert status == 200, "a refused act is the act's own shape, not a caller's mistake"
    assert answer["ok"] is False
    assert answer["live"] == [LIVE_ID], "the member that refused the batch is named, whoever it stands in"
    assert "every workspace" in answer["reason"], "and the sentence says which batch was refused"
    assert "nothing was deleted" in answer["reason"]
    for member in (LIVE_ID, DEAD_ID, ENDED_ID, BETA_ONE, BETA_TWO):
        assert (root / member).is_dir(), "and nothing was: a batch that half-happened is not a batch"


def test_the_whole_tree_batch_takes_every_workspaces_runs_and_names_them(serve, root, processes):
    live, _ = processes
    # The member that held a process is made a run whose process has gone: the batch refused above is the
    # same batch this one asks, and the only thing that changed is the machine's answer about that pid.
    live.kill()
    live.wait()
    base = serve()
    before = sorted(os.listdir(root))
    status, answer = post_json(f"{base}/api/runs/delete-all", {})
    # The same answer shape the per-workspace act gives, over both workspaces at once, in folder order.
    assert (status, answer) == (200, {"ok": True, "deleted": before})
    assert os.listdir(root) == [], "every run folder of every workspace is gone, and the root stays"
    assert get_json(base + "/api/runs")[1] == {"workspaces": []}, "the tree has nothing left to list"
    assert (root.parent / "outside").is_dir(), "the folder beside the root was never part of the batch"


def test_the_whole_tree_batch_leaves_what_the_tree_does_not_list(serve, root, processes):
    """The sweep is the tree's own rows: a folder the tree cannot name a run is not swept with them.

    Two such folders stand in the root — one with no log at all, and one whose log names no workspace,
    which is the way a row-less run arrives — and the act asked for as "every run the tree shows" leaves
    both exactly where they stood.
    """
    live, _ = processes
    live.kill()
    live.wait()
    (root / NO_LOG_ID).mkdir()
    write_log(root / GONE_ID, started("", "2026-11-01T02:00:00+00:00"))
    base = serve()
    listed = sorted(os.listdir(root))
    assert GONE_ID not in rows_of(get_json(base + "/api/runs")[1]), "the tree lists neither folder"
    status, answer = post_json(f"{base}/api/runs/delete-all", {})
    assert status == 200 and answer["ok"] is True
    assert sorted(answer["deleted"]) == [name for name in listed
                                         if name not in (NO_LOG_ID, GONE_ID)]
    assert (root / NO_LOG_ID).is_dir(), "a folder with no log is no run, and no run of any workspace"
    assert (root / GONE_ID).is_dir(), "a run in no workspace is in no batch over every workspace"


# --- the export ------------------------------------------------------------------------------------------

def test_the_export_answers_the_logs_own_translation_as_one_attachment(serve, root):
    base = serve()
    with urllib.request.urlopen(f"{base}/api/runs/{ENDED_ID}/export", timeout=TIMEOUT) as response:
        content_type = response.headers.get("Content-Type")
        disposition = response.headers.get("Content-Disposition")
        body = response.read()
    assert response.status == 200
    assert content_type == "text/markdown; charset=utf-8"
    assert disposition == f'attachment; filename="{ENDED_ID}.md"', "a file the browser writes, named"
    text = body.decode("utf-8")
    assert SENTENCE in text, "the file carries what the log says, not a page of boilerplate"
    assert text == export.markdown(os.path.join(str(root / ENDED_ID), runs.LOG_NAME)), \
        "the bytes are the translation this tree's one reader makes"


def test_the_export_of_a_folder_with_no_log_is_not_found(serve, root):
    (root / NO_LOG_ID).mkdir()
    expect_error(f"{serve()}/api/runs/{NO_LOG_ID}/export", 404)


def test_the_export_answers_json_as_the_records_own_lines_one_document(serve, root):
    base = serve()
    url = f"{base}/api/runs/{ENDED_ID}/export?format=json"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        content_type = response.headers.get("Content-Type")
        disposition = response.headers.get("Content-Disposition")
        body = response.read()
    assert response.status == 200
    assert content_type == "application/json; charset=utf-8"
    assert disposition == f'attachment; filename="{ENDED_ID}.json"', "a file the browser writes, named"
    text = body.decode("utf-8")
    steps = json.loads(text)
    assert isinstance(steps, list) and [step["kind"] for step in steps] == ["started", "message", "ended"], \
        "the document is the record's own lines, one array, in the order the log wrote them"
    assert SENTENCE in text, "the file carries what the log says, not a page of boilerplate"
    assert text == export.json_document(os.path.join(str(root / ENDED_ID), runs.LOG_NAME)), \
        "the bytes are the document this tree's one reader makes"


def test_the_export_with_a_shape_it_does_not_hold_is_refused(serve, root):
    expect_error(f"{serve()}/api/runs/{ENDED_ID}/export?format=docx", 400)


def test_the_export_named_md_is_the_markdown_it_answers_to(serve, root):
    base = serve()
    with urllib.request.urlopen(f"{base}/api/runs/{ENDED_ID}/export?format=md", timeout=TIMEOUT) as response:
        assert response.headers.get("Content-Type") == "text/markdown; charset=utf-8"
        assert response.headers.get("Content-Disposition") == f'attachment; filename="{ENDED_ID}.md"'
        assert response.status == 200


# --- the window on a folder ------------------------------------------------------------------------------

def test_the_explorer_act_hands_the_directory_over_as_one_argument(serve, windows, tmp_path):
    # The weirdest name the filesystem accepts is the weirdest name this can open: as an argument the
    # metacharacters are part of the folder's name, and there is no shell on the other end to read them.
    folder = tmp_path / "a folder && drop"
    folder.mkdir()
    status, answer = post_json(f"{serve()}/api/open", {"kind": "explorer", "path": str(folder)})
    assert (status, answer) == (200, {"ok": True})
    assert windows == [([openers.EXPLORER_PROGRAM, str(folder)], {})]


def test_a_box_with_windows_terminal_gets_it(serve, windows, hold_terminal, tmp_path):
    hold_terminal(True)
    base = serve()
    assert post_json(base + "/api/open", {"kind": "terminal", "path": str(tmp_path)})[1] == {"ok": True}
    argv, flags = windows[0]
    assert argv == [openers.WT_PROGRAM, "-d", str(tmp_path)]
    assert flags == {}, "Windows Terminal brings its own window; the console flags are the fallback's"


def test_a_box_without_it_gets_the_console_told_to_change_directory_and_stay(serve, windows,
                                                                            hold_terminal, tmp_path):
    hold_terminal(False)
    base = serve()
    assert post_json(base + "/api/open", {"kind": "terminal", "path": str(tmp_path)})[1] == {"ok": True}, \
        "a box with no `wt` answers ok: the fallback is a terminal this box has, not a missing program"
    argv, flags = windows[0]
    assert argv == [openers.CMD_PROGRAM, "/k", "cd", "/d", str(tmp_path)], \
        "one token at a time: `cd /d` quoted as one token would be a program name to cmd, and the " \
        "window would stand in the server's own directory"
    if sys.platform == "win32":
        # A console of its own, and the console's own input and outputs: the `None`s are the inherited
        # handles, and a `cmd /k` started on the null device reads EOF at once (closing the window the
        # act opened) and writes its prompt nowhere the operator can see (a black window, hanging).
        assert flags == {"creationflags": openers._NEW_CONSOLE, "stdin": None,
                         "stdout": None, "stderr": None}
    else:
        assert flags == {}


def test_the_terminal_is_the_one_the_server_found_when_it_was_made(serve, windows, monkeypatch, root):
    """The route asks nothing of the machine and reads nothing off the body: it hands over the terminal
    the site settled on once, which is what the module's own docstring declares and what a route that
    left the argument out quietly did not do."""
    asked = []

    def probe():
        asked.append(1)
        return openers.CMD_PROGRAM

    monkeypatch.setattr(openers, "terminal_program", probe)
    base = serve()
    assert len(asked) == 1, "asked once, at startup, when the server is made"
    post_json(base + "/api/open", {"kind": "terminal", "path": str(root)})
    assert len(asked) == 1, "a request does not go probing the machine's path again"
    assert windows[0][0][0] == openers.CMD_PROGRAM, "and the carried answer is the one the act ran with"


def test_a_path_the_machine_cannot_show_is_refused_before_anything_is_started(serve, windows, tmp_path):
    base = serve()
    note = tmp_path / "a-file.txt"
    note.write_text("not a folder", encoding="utf-8")
    missing = expect_error(f"{base}/api/open", 404,
                           json.dumps({"kind": "explorer", "path": str(tmp_path / "gone")}).encode("utf-8"))
    assert "no such folder" in missing["error"]
    refused = expect_error(f"{base}/api/open", 400,
                           json.dumps({"kind": "explorer", "path": str(note)}).encode("utf-8"))
    assert "not a folder" in refused["error"]
    expect_error(f"{base}/api/open", 400, json.dumps({"kind": "explorer", "path": "  "}).encode("utf-8"))
    expect_error(f"{base}/api/open", 400,
                 json.dumps({"kind": "editor", "path": str(tmp_path)}).encode("utf-8"))
    assert windows == [], "a request that names nothing openable never reaches the machine"


# --- the file in the program the box owes it -------------------------------------------------------------

def test_the_file_act_hands_the_file_to_the_machines_own_handler(serve, windows, tmp_path):
    # The plan's one promise about this act is its shape: the path reaches the machine's default handler
    # as one argument, and which program that is stays the box's. The weird name is the same claim the
    # folder acts make — a metacharacter in a name is part of the name when no shell reads it.
    note = tmp_path / "a file && drop.md"
    note.write_text("# the file the act opens\n", encoding="utf-8")
    status, answer = post_json(f"{serve()}/api/open", {"kind": "file", "path": str(note)})
    assert (status, answer) == (200, {"ok": True})
    handler = ([openers.FILE_PROGRAM, openers.FILE_HANDLER]
               if sys.platform == "win32" else [openers.XDG_PROGRAM])
    assert windows == [(handler + [str(note)], {})], (
        "the handler, its entry point, and the path as the last argument of the line — no shell in between")


def test_a_path_that_is_not_a_file_is_refused_before_anything_is_started(serve, windows, tmp_path):
    base = serve()
    folder = tmp_path / "a-folder"
    folder.mkdir()
    missing = expect_error(f"{base}/api/open", 404,
                           json.dumps({"kind": "file", "path": str(tmp_path / "gone.md")}).encode("utf-8"))
    assert "no such file" in missing["error"]
    refused = expect_error(f"{base}/api/open", 400,
                           json.dumps({"kind": "file", "path": str(folder)}).encode("utf-8"))
    assert "not a file" in refused["error"]
    expect_error(f"{base}/api/open", 400, json.dumps({"kind": "file", "path": " "}).encode("utf-8"))
    assert windows == [], "a request that names no file never reaches the machine"


# --- the file selected in the machine's own file browser -------------------------------------------------

def test_the_select_act_stands_the_explorer_on_the_file_selected(serve, windows, tmp_path):
    # The act's one promise is its shape: the file reaches explorer as the argument of the select switch,
    # the switch and the path one token, and no shell in between to read a name as program text. A comma
    # in a name is part of the name: the switch is split at the first comma only, and the rest of the
    # token is the path.
    note = tmp_path / "a, file && drop.md"
    note.write_text("# the file the act selects\n", encoding="utf-8")
    status, answer = post_json(f"{serve()}/api/open", {"kind": "select", "path": str(note)})
    assert (status, answer) == (200, {"ok": True})
    if sys.platform == "win32":
        assert windows == [([openers.EXPLORER_PROGRAM, openers.SELECT_SWITCH + str(note)], {})], (
            "the explorer asked to stand on the file selected — the switch and the path one token, no shell")
    else:
        assert windows == [([openers.XDG_PROGRAM, str(tmp_path)], {})], (
            "and a box without the switch stands its own opener on the directory the file stands in")


def test_a_path_that_is_not_a_file_is_refused_to_the_select_act(serve, windows, tmp_path):
    base = serve()
    folder = tmp_path / "a-folder"
    folder.mkdir()
    missing = expect_error(f"{base}/api/open", 404,
                           json.dumps({"kind": "select", "path": str(tmp_path / "gone.md")}).encode("utf-8"))
    assert "no such file" in missing["error"]
    refused = expect_error(f"{base}/api/open", 400,
                           json.dumps({"kind": "select", "path": str(folder)}).encode("utf-8"))
    assert "not a file" in refused["error"]
    expect_error(f"{base}/api/open", 400, json.dumps({"kind": "select", "path": " "}).encode("utf-8"))
    assert windows == [], "a request that names no file never reaches the machine"


def test_a_machine_that_refuses_the_file_answers_in_its_own_words(serve, monkeypatch, tmp_path):
    # The machine's refusal is not a caller's mistake: the act answers 200 with `ok: false`, and the
    # sentence the operator reads at the pane's head is the one the operating system said.
    def refuse(argv, flags):
        raise OSError("no handler is registered")

    monkeypatch.setattr(openers, "launch", refuse)
    note = tmp_path / "orphan.wav"
    note.write_text("bytes", encoding="utf-8")
    status, answer = post_json(f"{serve()}/api/open", {"kind": "file", "path": str(note)})
    assert status == 200
    assert answer["ok"] is False
    assert str(note) in answer["reason"] and "no handler is registered" in answer["reason"]


def test_a_server_started_without_its_window_refuses_the_open(root, windows):
    """`--no-open`: the e2e discipline — a probe's server never opens what an operator would open,
    and the refusal stands before the spawn is asked, so no window is owed by a server that owes
    none."""
    httpd = server.make_server("127.0.0.1", 0, runs_root=str(root), open_paths=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        error = expect_error(base + "/api/open", 503,
                             json.dumps({"kind": "explorer", "path": str(root)}).encode("utf-8"))
        assert "--no-open" in error["error"]
        assert windows == [], "the refusal is before the spawn: no argv was ever asked for"
    finally:
        httpd.shutdown()
        httpd.server_close()
