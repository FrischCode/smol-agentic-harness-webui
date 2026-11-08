"""sahw.server — the machine's model table, and the two dials of a run's own session.

Three routes stand together here because they answer one question in three tenses: what this box can be
launched on, what this run's record says its bounds stand on now, and how an operator moves them. Nothing
behind them is invented by the face — the registry is read through `models`, the pair through `runs.dials`,
and a switch is SAH's own console line launched by `channel` — so each route is judged on what a client
sees: the profile fields with the one secret missing from them, the null that says the record never named a
level, the command line a console child would have been started with, and the sentence each refusal brings
back.

The launch is the seam, as it is across the battery: `spawn.launch` is captured, so a switch is asserted as
the argv it would have run — `-i`, and the line beside it, with neither `--model` nor `--think` in sight —
and no child of this battery is ever a session somebody's log has to account for. The liveness the gate
reads is a real pid held by this battery, because the pair that must never be confused is a number that
still names a process and a number that names one no longer.
"""
import json
import os
import pathlib
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

from sahw import channel, runs, server, spawn

TIMEOUT = 15.0

REST_ID = "r20261103-070000-restaaa"          # an objective that wrote its ending: the dials take
WORKING_ID = "r20261103-090000-workaaa"       # a process this battery holds: the dials stand down
SWITCHED_ID = "r20261103-080000-switaaa"      # a session the operator moved, twice, by console line
RELAUNCH_ID = "r20261103-061000-relaaaa"      # ... and a second objective launched over those notices
REACHED_ID = "r20261103-062000-reachaa"       # a record that named its reach and its window
QUIET_ID = "r20261103-060000-quietaa"         # a log with no opening step to name a bound

TABLE = {
    "flash-next": {"model": "flash-next", "host": "127.0.0.1", "port": 9090, "api_key": "sk-secret"},
    "deep": {"model": "deep-thinker", "think": "high", "vision": True},
}


def get_json(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def expect_error(url, status, body=None):
    """The JSON body of an error response, having checked it is one error of that status and no other."""
    packed = body if body is None or isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    target = url if packed is None else urllib.request.Request(
        url, data=packed, method="POST", headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(target, timeout=TIMEOUT)
    assert raised.value.code == status
    error = json.loads(raised.value.read().decode("utf-8"))
    assert set(error) == {"error"} and error["error"]
    return error


def command(base, run_id, line):
    """One line of the session's own console, spoken at a run: the whole body this route takes, sent as
    the page sends it."""
    return post_json(f"{base}/api/runs/{run_id}/command", {"line": line})


def write_log(run_dir, *steps):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(str(run_dir), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for step in steps:
            handle.write(json.dumps(step) + "\n")
    return run_dir


def step(seq, kind, **fields):
    return {"id": f"{seq:06d}-{kind}", "kind": kind, "issuer": "core",
            "ts": f"2026-11-03T10:00:{seq % 60:02d}+00:00", **fields}


def started(seq, ts, **extra):
    return step(seq, "started", model="flash-next", run_id="run", root="root", ts=ts, **extra)


def notice(seq, text):
    """The console's own word: an operator's command, recorded by the command that carried it."""
    return step(seq, "notice", issuer="operator", subject="command", text=text)


def think_said(seq, level, was):
    return notice(seq, f"think: {level} (was {was})")


def model_said(seq, profile, address, was="flash-next"):
    return notice(seq, f"model: {profile} @ {address} in force (models.json; was {was}); "
                       f"context 200000 (models.json)")


def write_tree(tree, table=TABLE):
    """A SAH tree holding `data/models.json` — or, with `table=None`, holding no table at all.

    The tree is named in full, because a test that means two machines needs two folders: the one this
    box was pointed at and the one with no table, or with a table that is not the shape, written into the
    first would be a fixture that quietly disagrees with itself.
    """
    tree = os.path.abspath(str(tree))
    (pathlib.Path(tree) / "data").mkdir(parents=True, exist_ok=True)
    if table is not None:
        (pathlib.Path(tree) / "data" / "models.json").write_text(json.dumps(table), encoding="utf-8")
    return tree


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
def box(tmp_path, processes):
    """The records the dials are read out of, the workspace they name, and the tree the table is read from.

    The workspace is a folder that exists because a switch is launched *in* it, and the two pids are this
    battery's own because the gate that stands the dials down reads a process table, not a wish.
    """
    live, ran = processes
    work = tmp_path / "work"
    work.mkdir()
    write_tree(tmp_path / "sah-tree")       # the machine this server was pointed at, table and all
    root = tmp_path / "runs"
    write_log(root / REST_ID,
              started(0, "2026-11-03T07:00:00+00:00", cwd=str(work), pid=ran.pid, thinking="medium"),
              step(1, "message", role="assistant", text="one"),
              step(2, "ended", reason="complete", exit_code=0))
    write_log(root / WORKING_ID, started(0, "2026-11-03T09:00:00+00:00", cwd=str(work), pid=live.pid))
    write_log(root / SWITCHED_ID,
              started(0, "2026-11-03T08:00:00+00:00", cwd=str(work), pid=ran.pid, thinking="medium"),
              think_said(1, "high", "medium"),
              model_said(2, "deep", "10.0.0.2:1234"),
              step(3, "ended", reason="complete", exit_code=0))
    write_log(root / RELAUNCH_ID,
              started(0, "2026-11-03T06:10:00+00:00", cwd=str(work), pid=ran.pid, thinking="medium"),
              think_said(1, "high", "medium"),
              model_said(2, "deep", "10.0.0.2:1234"),
              step(3, "ended", reason="complete", exit_code=0),
              started(4, "2026-11-03T06:20:00+00:00", cwd=str(work), pid=ran.pid, thinking="low"),
              step(5, "ended", reason="complete", exit_code=0))
    write_log(root / REACHED_ID,
              started(0, "2026-11-03T06:30:00+00:00", cwd=str(work), pid=ran.pid, thinking="medium",
                      context="200000",
                      grants={"read": [str(work), str(tmp_path / "sah-tree")], "write": [str(work)]}),
              step(1, "ended", reason="complete", exit_code=0))
    write_log(root / QUIET_ID, step(1, "message", role="assistant", text="a word before any bounds"))
    return {"root": root, "tree": tmp_path / "sah-tree", "work": str(work), "tmp": tmp_path}


@pytest.fixture
def launches(monkeypatch):
    """The launch seam: every command line a switch would have run, with nothing actually started."""
    calls = []

    def pretend(argv, env, cwd):
        calls.append({"argv": list(argv), "cwd": cwd})
        return 4242

    monkeypatch.setattr(spawn, "launch", pretend)
    return calls


@pytest.fixture
def serve(box):
    """`serve()` — the server on a free port over that root and tree, and a base URL to ask it things.

    The tree is a keyword of the call rather than baked in, because half of what is asked here is what the
    routes answer when the machine they would read is not standing where the server was told to look.
    """
    running = []

    def start(**options):
        settings = {"runs_root": str(box["root"]), "sah_tree": str(box["tree"])}
        settings.update({key: str(value) if value is not None else value
                         for key, value in options.items()})
        httpd = server.make_server("127.0.0.1", 0, **settings)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        running.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in running:
        httpd.shutdown()


# --- `GET /api/models`: the machine's table, its one secret kept --------------------------------------

def test_the_models_route_answers_the_table_with_ids_and_endpoint_fields(serve):
    status, answer = get_json(serve() + "/api/models")
    assert status == 200
    assert sorted(profile["id"] for profile in answer["models"]) == ["deep", "flash-next"]
    flashed = next(profile for profile in answer["models"] if profile["id"] == "flash-next")
    assert flashed["model"] == "flash-next", "the id selects, and the model field is the wire name"
    assert flashed["host"] == "127.0.0.1" and flashed["port"] == 9090, (
        "the endpoint fields ride, because a picker is naming the box a word would go to")
    deep = next(profile for profile in answer["models"] if profile["id"] == "deep")
    assert deep["think"] == "high" and deep["vision"] is True, "and a profile's own level with it"
    assert "api_key" not in json.dumps(answer), "the secret one profile holds is never in the answer"


def test_the_models_route_names_the_reference_a_run_launches_as(serve, monkeypatch):
    monkeypatch.setenv("SAH_MODEL", "deep")
    status, answer = get_json(serve() + "/api/models")
    assert status == 200 and answer["machine"] == "deep", (
        "the stand the picker holds before a run names one, read from the machine, not guessed at")


def test_the_models_route_answers_an_empty_table_with_no_entry(serve, box, monkeypatch):
    # Nothing names a model either: an empty table *and* no reference is a machine with no opinion, which
    # is the state the picker stands down on rather than guesses its way past. The tree is a folder of its
    # own, because `write_tree` keeps one folder per machine and this machine has no table in it.
    monkeypatch.delenv("SAH_MODEL", raising=False)
    monkeypatch.setenv("SAH_ENV_FILE", str(box["tmp"] / "no-env-for-this-test"))
    base = serve(sah_tree=write_tree(box["tmp"] / "empty-machine", table={}))
    status, answer = get_json(base + "/api/models")
    assert status == 200 and answer["models"] == [], "an empty table is a machine carrying no profiles"
    assert answer["machine"] == "", "and it names no reference beside them"


def test_the_models_route_refuses_a_tree_it_was_never_given(serve):
    error = expect_error(serve(sah_tree="") + "/api/models", 503)
    assert error["error"] == "this server names no SAH tree: pass --sah-tree or set SAHW_SAH_TREE"


def test_the_models_route_refuses_a_tree_that_declares_no_table(serve, box):
    error = expect_error(serve(sah_tree=write_tree(box["tmp"] / "bare-machine", table=None)) + "/api/models",
                         503)
    assert "no data/models.json" in error["error"], (
        "a machine that declares nothing says so, and the face that reads it offers no choice")


def test_the_models_route_refuses_a_malformed_table_in_the_readers_own_words(serve, box):
    broken = write_tree(box["tmp"] / "broken-machine", table={"oops": {"host": "127.0.0.1"}})
    error = expect_error(serve(sah_tree=broken) + "/api/models", 503)
    assert "oops" in error["error"] and "model" in error["error"], (
        "`models` names the profile and the key at fault, and the route hands the sentence straight through")


# --- `GET /api/runs/<id>/dials`: the record's own word on its two bounds ------------------------------

def test_a_run_that_never_switched_answers_its_opening_bounds(serve):
    status, answer = get_json(f"{serve()}/api/runs/{REST_ID}/dials")
    assert status == 200
    assert answer == {"model": "flash-next", "endpoint": None, "think": "medium"}, (
        "the model and the level the opening step named, and no address because no switch named one")


def test_the_notices_a_session_was_switched_by_outrank_the_step_they_follow(serve):
    status, answer = get_json(f"{serve()}/api/runs/{SWITCHED_ID}/dials")
    assert status == 200
    assert answer["model"] == "deep", "the newest `/model` notice names the model the session runs on"
    assert answer["endpoint"] == "10.0.0.2:1234", "and the address it names is the box a word went to"
    assert answer["think"] == "high", "the newest `think:` notice outranks the opening level likewise"


def test_a_second_objective_outranks_the_notices_of_the_session_before_it(serve):
    status, answer = get_json(f"{serve()}/api/runs/{RELAUNCH_ID}/dials")
    assert answer["model"] == "flash-next" and answer["think"] == "low", (
        "a new objective runs on the flags it was launched with, notices below it notwithstanding")
    assert answer["endpoint"] is None, "and an address the new launch never named is not carried up to it"


def test_a_log_with_no_opening_step_names_no_bound_at_all(serve):
    status, answer = get_json(f"{serve()}/api/runs/{QUIET_ID}/dials")
    assert status == 200 and answer == {"model": None, "endpoint": None, "think": None}, (
        "null is the absence a face has to be able to read; no default is filled in here")


def test_a_run_this_server_holds_no_folder_for_is_refused_like_every_other_route(serve):
    expect_error(f"{serve()}/api/runs/r20261103-000000-nopeeee/dials", 404)


def test_the_tree_names_the_box_a_switch_moved_a_run_to(tmp_path):
    """The row's own reading: a switched run carries the address it was moved to, and one that never
    moved carries no such key — a face that showed an address for every run would be showing a fact
    that was never stated about most of them.
    """
    work = tmp_path / "work"
    work.mkdir()
    root = tmp_path / "runs"
    write_log(root / SWITCHED_ID, started(0, "2026-11-03T08:00:00+00:00", cwd=str(work)),
              model_said(1, "deep", "10.0.0.2:1234"))
    write_log(root / REST_ID, started(0, "2026-11-03T07:00:00+00:00", cwd=str(work)))
    rows = {row["id"]: row for workspace in runs.tree(str(root))["workspaces"] for row in workspace["runs"]}
    assert rows[SWITCHED_ID]["endpoint"] == "10.0.0.2:1234"
    assert "endpoint" not in rows[REST_ID], "a run that never moved owes its row no address to show"


# --- `POST /api/runs/<id>/command`: the session's own console line, spoken at a run at rest ------------

def test_a_switch_at_a_resting_run_is_the_console_line_the_operator_would_type(serve, launches):
    status, answer = command(serve(), REST_ID, "/think high")
    assert status == 200 and answer == {"ok": True, "line": "/think high", "run": REST_ID}, (
        "the line that was carried is the whole of the answer: the record is what will name the change")
    assert len(launches) == 1, "one detached child, and nothing written by this route at all"
    argv = launches[0]["argv"]
    assert argv[-2:] == ["--task", "/think high"], "the line whole, and nothing after it"
    assert argv[argv.index("--task") - 1] == "-i", (
        "the flag that makes the line a line the console reads rather than an objective")
    assert "--think" not in argv and "--model" not in argv, (
        "no flag claims the bound the line is standing there to move")
    assert "--resume" in argv, "the run's own session, on the run's own folder"
    assert "--live" not in argv and "--ask-timeout" not in argv, (
        "a session that speaks one line runs no turn, so the attended run's flags are not its business")


def test_the_reach_and_the_window_the_record_names_are_repassed_to_the_session(serve, launches, box):
    command(serve(), REACHED_ID, "/model deep")
    argv = launches[-1]["argv"]
    assert argv.count("--grant") == 2 and argv.count("--write") == 1, (
        "a resume inherits nothing, so the reach the record named comes back to it")
    assert argv[argv.index("--context") + 1] == "200000", (
        "and so does the window, rather than being re-asked of the endpoint in a notice of its own")
    assert launches[-1]["cwd"] == box["work"], "spoken in the workspace the run's own record names"


def test_a_mid_turn_switch_is_refused_with_the_sentence_the_stood_down_dial_wears(serve, launches):
    error = expect_error(f"{serve()}/api/runs/{WORKING_ID}/command", 409, {"line": "/think low"})
    assert error["error"] == channel.DIALS_DOWN
    assert launches == [], "a session opened beside a live process is a second writer: nothing started"


def test_the_gate_is_the_shape_of_the_line_and_the_console_answers_what_it_is(serve, launches):
    """The door is wide now, and wide on purpose: the face is handed the session's command surface,
    not two of its commands, so a line is carried so long as it is one line of the console's own
    — it begins with the operator's mark, and its words are the words they appear to be. What the
    line is, and whether the session runs it, refuses it, or answers it with its own list, is the
    console's judgement: the dispatch that does not know the command records its own refusal beside
    the log, and the route that has a request does not become a second registry.

    The refusals this door still earns are the shape's own: a line without the mark is a word to the
    model, not a line to the console, and a line whose words are not the words they appear to be — a
    tab, a newline, padding between the words — is not one line of the console's own either.
    """
    for line in ["/quit", "/think", "/think high now", "/model deep extra", "/backto 2", "/fork 3", "/new",
                 "/export", "/live", "/compact"]:
        status, answer = command(serve(), REST_ID, line)
        assert status == 200 and answer["line"] == line, (
            f"{line!r}: one line of the console's own is carried, and the console answers what it is")
    carried = [call["argv"][-1] for call in launches]
    assert carried == ["/quit", "/think", "/think high now", "/model deep extra", "/backto 2", "/fork 3",
                       "/new", "/export", "/live", "/compact"], (
        "and each carried line is the whole line the console child would have read")
    refused_at = len(launches)
    for line in ["think high", "a word to the model", "", "   "]:
        error = expect_error(f"{serve()}/api/runs/{REST_ID}/command", 400, {"line": line})
        assert "carries none" in error["error"], (
            f"{line!r}: a line without the operator's mark is a word, not a line, and the door says so")
    for line in ["/model deep\n/think high", "/model\tdeep", "  /model deep", "/model deep ", "/think  high"]:
        error = expect_error(f"{serve()}/api/runs/{REST_ID}/command", 400, {"line": line})
        assert "one line of the console's own" in error["error"], (
            f"{line!r}: a line whose words are not the words they appear to be is not one line")
    assert len(launches) == refused_at, "the refusals started nothing: a door to the console is not a shell"


def test_what_a_line_carries_is_the_consoles_judgement_and_not_this_routes(serve, launches):
    """The gate is the shape of the line, and the line's meaning is SAH's to read.

    A profile the registry does not hold, a level the backend has never heard of, a prompt number the
    conversation does not hold, even a name that begins like another command: this route cannot tell
    those from the real thing without becoming a second registry, and the console that has the table in
    front of it refuses them and records why.
    """
    for line in ["/model no-such-profile", "/think ultramax", "/model /think"]:
        status, _ = command(serve(), REST_ID, line)
        assert status == 200, line
    assert [call["argv"][-1] for call in launches] == ["/model no-such-profile", "/think ultramax",
                                                       "/model /think"]


def test_a_switch_is_refused_by_a_server_that_names_no_tree(serve, launches):
    error = expect_error(serve(sah_tree="") + f"/api/runs/{REST_ID}/command", 503,
                         {"line": "/think high"})
    assert "no SAH tree" in error["error"] and launches == []


def test_a_body_naming_no_line_at_all_is_refused_as_a_bad_request(serve):
    error = expect_error(f"{serve()}/api/runs/{REST_ID}/command", 400, {})
    assert "carries none" in error["error"]


def test_a_line_that_is_not_a_word_is_refused_rather_than_stringified_into_one(serve, launches):
    for value in [None, 7, ["/think high"], {"line": "high"}]:
        error = expect_error(f"{serve()}/api/runs/{REST_ID}/command", 400, {"line": value})
        assert "carries none" in error["error"], repr(value)
    assert launches == []
