"""sahw.spawn — the command line a started run is handed, and the environment it is handed it in.

The child is faked the way the run's own loop takes a clock: `command=` names the program in place of
`python -m sah`, and the fake writes the two steps a run writes and a dump of its own argv, working
directory and environment. So what is asserted is this module's whole contract — which flags, in which
order, in which environment, in which folder — against a child that really started and really wrote,
and the run the parent claimed then shows up in the tree the API reads.
"""
import json
import os
import subprocess
import sys
import time

import pytest

from sahw import liveness, runs, spawn

FAKE_SAH = '''
# A stand-in for `python -m sah run`: say what it was asked to do, write the two steps a run writes,
# and exit. The dump is written before the log, so a reader that can see the log knows the dump is
# whole, and the log's ending is the last thing to arrive so that seeing it means the child is done.
# `FAKE_SAH_HOLD` stands the child between its two steps until the file named `RELEASE` appears in its
# own run folder: that is how a test holds a run working, and which run settles is then the test's call.
import json
import os
import sys
import time

argv = sys.argv[1:]


def flag(name):
    return argv[argv.index(name) + 1] if name in argv else ""


run_dir = flag("--run-dir")
grants = [argv[index + 1] for index, word in enumerate(argv) if word == "--grant"]
stamp = "2026-11-01T08:00:00+00:00"
with open(os.path.join(run_dir, "child.json"), "w", encoding="utf-8") as handle:
    json.dump({"argv": argv, "cwd": os.getcwd(), "pid": os.getpid(),
               "pythonpath": os.environ.get("PYTHONPATH"),
               "extension": os.environ.get("SAH_EXTENSION")}, handle)
with open(os.path.join(run_dir, "log.jsonl"), "w", encoding="utf-8") as handle:
    handle.write(json.dumps({"id": "000000-started", "kind": "started", "issuer": "core",
                             "ts": stamp, "cwd": grants[0] if grants else "",
                             "model": "fake", "run_id": os.path.basename(run_dir),
                             "pid": os.getpid(), "root": run_dir}) + "\\n")
if os.environ.get("FAKE_SAH_HOLD"):
    deadline = time.time() + 20
    while not os.path.exists(os.path.join(run_dir, "RELEASE")) and time.time() < deadline:
        time.sleep(0.05)
with open(os.path.join(run_dir, "log.jsonl"), "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"id": "000001-ended", "kind": "ended", "issuer": "core", "ts": stamp,
                             "reason": "complete", "exit_code": 0}) + "\\n")
'''


@pytest.fixture
def fake_sah(tmp_path):
    """The fake child, as a script a real interpreter can run."""
    script = tmp_path / "fake_sah.py"
    script.write_text(FAKE_SAH, encoding="utf-8")
    return str(script)


def rows_of(runs_root):
    """{run id: row} across every workspace, for asserting on a tree without walking it each time."""
    return {row["id"]: row for workspace in runs.tree(runs_root)["workspaces"] for row in workspace["runs"]}


def until(satisfied, seconds=30.0):
    """Wait for a condition a child process is on its way to making true; False once the time is up."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if satisfied():
            return True
        time.sleep(0.05)
    return False


# --- the command line ---------------------------------------------------------------------------------

def test_the_argv_is_the_command_line_an_operator_types():
    argv = spawn.build_argv(["python", "-m", "sah"], run_dir=r"R:\runs\r1", runs_root=r"R:\runs",
                            sah_tree=r"C:\Work\SAH", workspace=r"C:\work", task="say hi",
                            max_turns=90, max_runtime=10800)
    assert argv == ["python", "-m", "sah", "run",
                    "--run-dir", r"R:\runs\r1",
                    "--runs-root", r"R:\runs",
                    "--view", "off",
                    "--project-notes",
                    "--grant", r"C:\work",
                    "--grant", r"C:\Work\SAH",
                    "--write", r"C:\work",
                    "--max-turns", "90",
                    "--max-runtime", "10800",
                    "--live",
                    "--ask-timeout", "inf",
                    "--task", "say hi"]


def test_the_run_streams_its_words_to_the_face_that_started_it():
    """`--live` beside `--ask-timeout inf`: the two flags that say *somebody is watching this run*.

    The trace is what the stream route reads to show a turn being written rather than landed, and the
    attended fuse is what keeps a question from ending the run before the face answers it. Both are the
    face's claim about the run it is starting, so both are always sent — and both land before `--task`,
    the way the whole command line is built.
    """
    argv = spawn.build_argv(["python", "-m", "sah"], run_dir=r"R:\runs\r1", runs_root=r"R:\runs",
                            sah_tree=r"C:\Work\SAH", workspace=r"C:\work", task="say hi",
                            max_turns=90, max_runtime=10800)
    assert "--live" in argv, "a run the page starts is a run whose trace the page can read"
    at = argv.index("--live")
    assert argv[at + 1:at + 3] == ["--ask-timeout", "inf"], "beside the attended fuse, as the plan puts it"
    assert argv.count("--live") == 1, "one flag, not one per objective it might grow"


def test_the_run_started_from_the_face_works_one_objective_and_exits():
    """No `-i`, anywhere, in any combination of the other flags.

    The flag is what a session asked for: a process that finishes an objective and waits at its prompt
    for the next word. A run started here has no next word waiting — the next one is a relaunch on the
    same log — so the flag is not a preference a caller may set either way; it is simply not sent.
    """
    base = dict(run_dir=r"R:\runs\r1", runs_root=r"R:\runs", sah_tree=r"C:\Work\SAH",
                workspace=r"C:\work", task="say hi", max_turns=90, max_runtime=10800)
    assert "-i" not in spawn.build_argv(["python", "-m", "sah"], **base)
    assert "-i" not in spawn.build_argv(["python", "-m", "sah"], think="xhigh", **base)
    assert "--interactive" not in spawn.build_argv(["python", "-m", "sah"], **base)


def test_the_thinking_level_is_the_servers_own_word_and_an_empty_one_is_not_sent():
    base = dict(run_dir=r"R:\runs\r1", runs_root=r"R:\runs", sah_tree=r"C:\Work\SAH",
                workspace=r"C:\work", task="say hi", max_turns=90, max_runtime=10800)
    argv = spawn.build_argv(["python", "-m", "sah"], think="xhigh", **base)
    assert argv[argv.index("--think") + 1] == "xhigh"
    assert argv[-2:] == ["--task", "say hi"]
    assert "--think" not in spawn.build_argv(["python", "-m", "sah"], **base)


def test_the_model_the_picker_stands_on_is_the_id_the_child_is_launched_with():
    """`--model` at the same seam as `--think`, for the same reason, and worded as the picker word it is.

    The id is the profile's name rather than a wire name worked out here: the child resolves it against
    the machine's own registry, which is where a profile's endpoint and level live, and a face that sent
    a resolved name would be freezing a decision the machine may change between two launches.
    """
    base = dict(run_dir=r"R:\runs\r1", runs_root=r"R:\runs", sah_tree=r"C:\Work\SAH",
                workspace=r"C:\work", task="say hi", max_turns=90, max_runtime=10800)
    argv = spawn.build_argv(["python", "-m", "sah"], model="deep", **base)
    assert argv[argv.index("--model") + 1] == "deep"
    assert argv[-2:] == ["--task", "say hi"], "the dial rides before the objective, where the level rode"
    both = spawn.build_argv(["python", "-m", "sah"], think="high", model="deep", **base)
    assert both[both.index("--think"):both.index("--think") + 4] == ["--think", "high", "--model", "deep"], (
        "the two bounds stand side by side, in the order the composer's two controls stand")


def test_no_model_named_sends_no_model_flag_at_all():
    """An empty stand is the machine's own default, and silence is how that default is spelled.

    A flag naming nothing would be a claim about the model the run speaks as, arriving before the machine
    has said anything — which is the failure the picker was rebuilt to stop.
    """
    base = dict(run_dir=r"R:\runs\r1", runs_root=r"R:\runs", sah_tree=r"C:\Work\SAH",
                workspace=r"C:\work", task="say hi", max_turns=90, max_runtime=10800)
    assert "--model" not in spawn.build_argv(["python", "-m", "sah"], **base)
    assert "--model" not in spawn.build_argv(["python", "-m", "sah"], model="", **base)


def test_the_launch_budgets_are_the_ones_the_launcher_ships():
    assert (spawn.DEFAULT_MAX_TURNS, spawn.DEFAULT_MAX_RUNTIME) == (90, 10800)


# --- the fork's command line ----------------------------------------------------------------------------

def test_the_fork_argv_is_the_command_line_an_operator_types():
    argv = spawn.fork_argv(["python", "-m", "sah"], source_dir=r"R:\runs\srcaaa",
                           run_dir=r"R:\runs\rfrkkk", runs_root=r"R:\runs", step="3",
                           task="the branch", max_turns=90, max_runtime=10800)
    assert argv == ["python", "-m", "sah", "fork", r"R:\runs\srcaaa",
                    "--run-dir", r"R:\runs\rfrkkk",
                    "--runs-root", r"R:\runs",
                    "--view", "off",
                    "--project-notes",
                    "--step", "3",
                    "--max-turns", "90",
                    "--max-runtime", "10800",
                    "--live",
                    "--ask-timeout", "inf",
                    "--task", "the branch"]


def test_the_fork_argv_names_no_grant_and_no_write_and_no_interactive():
    """A fork carries its source's reach; it is a run, not a session, so it asks for neither.

    `sah fork` reads the source's newest `started` and begins the branch with the reach that line
    stamped, so the argv sends no `--grant` and no `--write`; and a fork works its objective and exits,
    so it is not `-i`. The step is named always — a fork of a whole conversation has a last step — and it
    stands on the source's folder with the objective riding at the end, the way the spawn argv does.
    """
    base = dict(source_dir=r"R:\runs\srcaaa", run_dir=r"R:\runs\rfrkkk", runs_root=r"R:\runs",
                step="3", task="the branch", max_turns=90, max_runtime=10800)
    argv = spawn.fork_argv(["python", "-m", "sah"], **base)
    assert "--grant" not in argv and "--write" not in argv
    assert "-i" not in argv and "--interactive" not in argv
    assert argv[argv.index("--step") + 1] == "3"
    assert argv[-2:] == ["--task", "the branch"]


def test_the_fork_argv_sends_the_thinking_level_when_named():
    base = dict(source_dir=r"R:\runs\srcaaa", run_dir=r"R:\runs\rfrkkk", runs_root=r"R:\runs",
                step="3", task="the branch", max_turns=90, max_runtime=10800)
    argv = spawn.fork_argv(["python", "-m", "sah"], think="high", **base)
    assert argv[argv.index("--think") + 1] == "high"
    assert "--think" not in spawn.fork_argv(["python", "-m", "sah"], **base)


def test_the_fork_argv_sends_the_model_the_picker_stands_on_and_none_when_it_stands_on_none():
    """A branch is a new objective, and the composer's two dials are the composer's at a fork too.

    The same seam as the spawn's and for the same reason: a face that showed a model beside the fork's
    objective and launched the branch on the machine's default would be describing a run it did not start.
    """
    base = dict(source_dir=r"R:\runs\srcaaa", run_dir=r"R:\runs\rfrkkk", runs_root=r"R:\runs",
                step="3", task="the branch", max_turns=90, max_runtime=10800)
    argv = spawn.fork_argv(["python", "-m", "sah"], model="deep", **base)
    assert argv[argv.index("--model") + 1] == "deep"
    assert "--model" not in spawn.fork_argv(["python", "-m", "sah"], **base)
    assert "--model" not in spawn.fork_argv(["python", "-m", "sah"], model="", **base)


def test_the_child_is_launched_by_the_trees_own_venv():
    assert spawn.child_command(r"C:\Work\SAH") == [os.path.join(r"C:\Work\SAH", ".venv", "Scripts",
                                                              "python.exe"), "-m", "sah"]


# --- the environment ----------------------------------------------------------------------------------

def test_the_child_environment_is_the_servers_with_two_keys_set():
    base = {"PATH": "/somewhere", "SAH_EXTENSION": "extensions/other.py", "PYTHONPATH": "leftover"}
    env = spawn.child_env(r"C:\Work\SAH", base=base)
    assert env["PATH"] == "/somewhere"
    assert env["PYTHONPATH"] == r"C:\Work\SAH"
    assert env["SAH_EXTENSION"] == " "
    assert base["SAH_EXTENSION"] == "extensions/other.py"


# --- what is refused before anything starts -------------------------------------------------------------

def test_a_run_is_refused_before_anything_is_claimed(tmp_path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    runs_root = tmp_path / "runs"
    refusals = [
        ({"workspace": str(workspace), "task": "   "}, 400),
        ({"workspace": str(tmp_path / "gone"), "task": "say hi"}, 400),
        ({"workspace": str(workspace), "task": "say hi", "sah_tree": ""}, 503),
    ]
    for case, status in refusals:
        with pytest.raises(spawn.SpawnError) as got:
            spawn.spawn_run(str(runs_root), case.get("sah_tree", str(tmp_path / "sah")),
                            case["workspace"], case["task"])
        assert got.value.status == status
    assert not runs_root.exists()


# --- the folder the run writes into ---------------------------------------------------------------------

def test_the_folder_is_claimed_empty_and_redrawn_when_the_name_is_already_spoken(tmp_path, monkeypatch):
    taken = "r20261101-080000-aaaaaa"
    (tmp_path / taken).mkdir()
    drawn = [taken, "r20261101-080001-bbbbbb"]
    monkeypatch.setattr(runs, "mint_run_id", lambda: drawn.pop(0))
    path = spawn.claim_run_dir(str(tmp_path))
    assert os.path.basename(path) == "r20261101-080001-bbbbbb"
    assert os.path.isdir(path)
    assert os.listdir(path) == []


# --- the start itself ---------------------------------------------------------------------------------

def test_the_child_leads_a_group_of_its_own():
    kwargs = spawn.detach_kwargs()
    if sys.platform == "win32":
        assert kwargs == {"creationflags": spawn._NEW_PROCESS_GROUP}
    else:
        assert kwargs == {"start_new_session": True}


def test_the_child_is_started_with_nothing_to_read(tmp_path, monkeypatch):
    """All three streams are the null device: an objective to work, and nobody on either end of a pipe.

    The three are one decision each: a pipe nobody drains on the way out is a run that blocks on its own
    stdout, and a pipe on the way in is a keyboard for a run that has no prompt — a handle to keep, a
    buffer to fill, and a child that would only ever be spoken to by whoever held it.
    """
    captured = {}

    class RecordingPopen:
        def __init__(self, argv, **kwargs):
            captured["argv"], captured["kwargs"] = argv, kwargs
            self.pid = 4242

    monkeypatch.setattr(spawn.subprocess, "Popen", RecordingPopen)
    proc = spawn.launch(["python", "-c", ""], {"KEY": "value"}, cwd=str(tmp_path))
    assert proc.pid == 4242
    assert captured["argv"] == ["python", "-c", ""]
    assert captured["kwargs"]["cwd"] == str(tmp_path)
    assert captured["kwargs"]["env"] == {"KEY": "value"}
    assert captured["kwargs"]["stdin"] is subprocess.DEVNULL, "the server keeps no way in"
    for stream in ("stdout", "stderr"):
        assert captured["kwargs"][stream] is subprocess.DEVNULL
    assert captured["kwargs"] == {**captured["kwargs"], **spawn.detach_kwargs()}


def test_a_spawned_run_answers_its_id_and_nothing_else(tmp_path, monkeypatch):
    """The id is the whole answer: the launched child is not handed back and nothing about it is kept.

    The process is found again by the `pid` its own log stamps, so what a caller holds after a spawn is a
    name it can list and nothing that could be mistaken for a way of speaking to it.
    """
    launched = []
    monkeypatch.setattr(spawn, "launch", lambda argv, env, cwd: launched.append(argv) or object())
    workspace = tmp_path / "work"
    workspace.mkdir()
    run_id = spawn.spawn_run(str(tmp_path / "runs"), str(tmp_path / "sah"), str(workspace),
                             "say done", command=["fake-sah"])
    assert launched
    assert run_id == os.path.basename(launched[0][launched[0].index("--run-dir") + 1])


def test_a_spawned_run_arrives_in_the_tree_with_the_workspace_it_was_given(tmp_path, fake_sah):
    workspace = tmp_path / "work"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("# notes\n", encoding="utf-8")
    sah_tree = tmp_path / "sah-tree"
    runs_root = tmp_path / "runs"
    run_id = spawn.spawn_run(str(runs_root), str(sah_tree), str(workspace),
                             "Reply with exactly the single word: done",
                             command=[sys.executable, fake_sah])
    assert until(lambda: run_id in rows_of(str(runs_root))), "the run never reached the tree"

    folder = runs_root / run_id
    row = rows_of(str(runs_root))[run_id]
    # The row the tree answers with, and nothing about a held process: the child wrote its ending and was
    # gone, and the log's own tail is what the row stands on.
    assert row == {"id": run_id, "ts": "2026-11-01T08:00:00+00:00", "model": "fake",
                   "status": "ended", "reason": "complete"}
    assert {workspace_row["path"] for workspace_row in runs.tree(str(runs_root))["workspaces"]} == {
        os.path.abspath(str(workspace))}
    assert sorted(os.listdir(str(folder))) == ["child.json", "log.jsonl"]

    seen = json.loads((folder / "child.json").read_text(encoding="utf-8"))
    argv = seen["argv"]
    assert argv[0] == "run"
    assert argv[argv.index("--run-dir") + 1] == str(folder)
    assert argv[argv.index("--runs-root") + 1] == str(runs_root)
    assert argv[argv.index("--view") + 1] == "off"
    assert "--project-notes" in argv
    assert argv[argv.index("--grant") + 1] == str(workspace)
    assert argv.count("--grant") == 2
    assert argv[argv.index("--grant", argv.index("--grant") + 1) + 1] == str(sah_tree)
    assert argv[argv.index("--write") + 1] == str(workspace)
    assert argv[argv.index("--max-turns") + 1] == "90"
    assert argv[argv.index("--max-runtime") + 1] == "10800"
    assert argv[argv.index("--task") + 1] == "Reply with exactly the single word: done"
    assert argv.count("--task") == 1

    # The workspace is where the run stands: that is what `--project-notes` reads and what its own log
    # stamps, so it is compared through the child's own working directory rather than by string.
    assert os.path.normcase(seen["cwd"]) == os.path.normcase(os.path.realpath(str(workspace)))
    assert seen["pythonpath"] == os.path.abspath(str(sah_tree))
    assert seen["extension"] == spawn.EXTENSION_OFF


def test_two_runs_started_one_after_the_other_work_at_once(tmp_path, fake_sah, monkeypatch):
    """Multi-agent for free: there is no single active slot to enforce, so two runs work at once.

    Each child stands between its two steps until a release file of its own arrives, so the state is
    exactly what the claim needs — two working runs, two logs holding a `started` and no `ended`, two live
    pids that are not one another's — and settling one is an act on that one folder. The other keeps its
    process, its row and its log, and the run that finished leaves nothing on it at all.
    """
    workspace = tmp_path / "work"
    workspace.mkdir()
    runs_root = tmp_path / "runs"
    monkeypatch.setenv("FAKE_SAH_HOLD", "1")
    first = spawn.spawn_run(str(runs_root), str(tmp_path / "sah"), str(workspace), "the first objective",
                            command=[sys.executable, fake_sah])
    second = spawn.spawn_run(str(runs_root), str(tmp_path / "sah"), str(workspace),
                             "the second objective", command=[sys.executable, fake_sah])

    def pid_of(run_id):
        return runs.latest_started(str(runs_root / run_id / runs.LOG_NAME)).get("pid")

    def released(run_id):
        (runs_root / run_id / "RELEASE").write_text("", encoding="utf-8")

    try:
        assert until(lambda: all(rows_of(str(runs_root)).get(rid, {}).get("live") == "live"
                                 for rid in (first, second))), "both runs never reached working"
        rows = rows_of(str(runs_root))
        assert rows[first]["status"] == "live" and rows[second]["status"] == "live"
        pids = {rid: pid_of(rid) for rid in (first, second)}
        assert pids[first] and pids[first] != pids[second], "two processes, not one wearing two rows"
        assert all(liveness.probe_pid(pid) == liveness.LIVE for pid in pids.values())

        released(first)
        assert until(lambda: rows_of(str(runs_root))[first]["status"] == "ended"), \
            "the released run never settled"
        after = rows_of(str(runs_root))
        assert after[second]["status"] == "live" and after[second]["live"] == "live"
        assert liveness.probe_pid(pids[second]) == liveness.LIVE, "the run left working is still working"
        log = (runs_root / second / runs.LOG_NAME).read_text(encoding="utf-8")
        assert log.count('"started"') == 1 and '"ended"' not in log
    finally:
        for run_id in (first, second):
            released(run_id)


# --- the fork's launch ---------------------------------------------------------------------------------

def _source_run(tmp_path, run_id="r20261101-090000-srcaaa", cwd=None):
    """A source run's folder: a log whose newest started stamps the workspace the fork would stand in."""
    workspace = tmp_path / "src-work"
    workspace.mkdir(exist_ok=True)
    source = tmp_path / "runs" / run_id
    source.mkdir(parents=True, exist_ok=True)
    (source / runs.LOG_NAME).write_text(
        json.dumps({"id": "000000-started", "kind": "started", "issuer": "core",
                    "ts": "2026-11-01T09:00:00+00:00", "cwd": str(cwd or workspace),
                    "model": "flash-next", "run_id": run_id, "root": str(tmp_path / "runs"),
                    "pid": 1}) + "\n", encoding="utf-8")
    return str(source), str(workspace)


def test_a_forked_run_answers_its_id_and_inherits_the_sources_reach(tmp_path, monkeypatch):
    """The fork's argv names no `--grant` and no `--write`: the branch stands on the source's reach.

    The step is named always, and the workspace the branch stands in is the one the source stamped, read
    from the source's newest started line — a fork is the same run on a different path, so the cwd is the
    source's, not the requester's.
    """
    launched = []
    monkeypatch.setattr(spawn, "launch", lambda argv, env, cwd: launched.append((argv, cwd)) or object())
    source, workspace = _source_run(tmp_path)
    run_id = spawn.spawn_fork(str(tmp_path / "runs"), str(tmp_path / "sah"), source, "2",
                              "the branch", command=["fake-sah"])
    assert launched
    argv, cwd = launched[0]
    assert run_id == os.path.basename(argv[argv.index("--run-dir") + 1])
    assert argv[1] == "fork"
    assert argv[2] == source
    assert argv[argv.index("--step") + 1] == "2"
    assert "--grant" not in argv and "--write" not in argv and "-i" not in argv
    assert os.path.normcase(cwd) == os.path.normcase(os.path.realpath(workspace))


def test_a_fork_is_refused_before_anything_is_claimed(tmp_path, monkeypatch):
    """The refusals are the spawn's, in the spawn's order: no objective, no tree, no log, no folder.

    Each one leaves the child unlaunched and the runs root unclaimed — a fork that has nothing to carry
    owes the machine a sentence, not an empty folder.
    """
    launched = []
    monkeypatch.setattr(spawn, "launch", lambda argv, env, cwd: launched.append(argv) or object())
    runs_root = str(tmp_path / "runs")
    source, _ = _source_run(tmp_path)
    for task, sah_tree in [("   ", str(tmp_path / "sah")), ("the branch", "")]:
        with pytest.raises(spawn.SpawnError) as got:
            spawn.spawn_fork(runs_root, sah_tree, source, "2", task, command=["fake-sah"])
        assert got.value.status in (400, 503)
    with pytest.raises(spawn.SpawnError):
        spawn.spawn_fork(runs_root, str(tmp_path / "sah"),
                         str(tmp_path / "runs" / "r20261101-091000-gone"), "2", "the branch",
                         command=["fake-sah"])
    source_gone, _ = _source_run(tmp_path, run_id="r20261101-092000-gonews", cwd=str(tmp_path / "gone"))
    with pytest.raises(spawn.SpawnError):
        spawn.spawn_fork(runs_root, str(tmp_path / "sah"), source_gone, "2", "the branch",
                         command=["fake-sah"])
    assert not launched
