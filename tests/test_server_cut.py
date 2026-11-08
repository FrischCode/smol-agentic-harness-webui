"""sahw.server — the cut on the message route: the word that returns a conversation to a step.

The route owns one ordering, and it is what this file is about: the record is asked before anything moves.
So nothing here is read out of a sentence a route returned — the assertions are the machine and the process
table afterwards: the child that is no longer in it, the argv the replacement was started with, and the
child that is still in it when the answer was a refusal. `spawn.launch` is the standing seam, so no SAH
child is ever started and every argv is read rather than run; the processes behind the liveness verdicts
are this battery's own children, one sleeping and one reaped, and the kill of the sleeping one is real,
because the fact a cut depends on is that the old writer is gone before the new one arrives.

The refusal is judged the same way. A cut naming a step the log does not hold — or one it holds only in a
detached lineage — has to leave the sleeping child sleeping and nothing launched, because the alternative
is a refusal that arrived after the process it was refusing had been stopped. And the channels that stood
before the field exists are checked standing: the cut-less word to the same settled run is still a follow,
and a working run is still the second-writer refusal rather than a rebuild.
"""
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

from sahw import channel, liveness, runs, server, spawn

TIMEOUT = 15.0

# The four states a cut can arrive at, each one run's own folder in the fixture's runs root.
SETTLED = "r20261102-080000-aaaaaa"      # the objective ended, and its process is still on its way out
DEAD = "r20261102-080100-bbbbbb"        # the objective ended, the process the machine calls dead
WORKING = "r20261102-080200-cccccc"     # no ending: the objective is still being worked, process live
ORPHAN = "r20261102-080300-dddddd"      # no ending and no process: the standing follow, cut and all
CUT = "r20261102-080400-eeeeee"         # a run already cut once: its middle steps are detached

SAH_TREE = r"C:\Work\SAH"


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


def step(seq, kind, **fields):
    """One log line, with the id the record's own numbering would have minted for it.

    The digits are what the cut names, so the fixtures write them rather than leaving them to a builder
    that might reorder the steps they belong to.
    """
    return {"id": f"{seq:06d}-{kind}", "kind": kind, "issuer": "core",
            "ts": f"2026-11-02T08:00:{seq % 60:02d}+00:00", **fields}


def write_log(run_dir, *steps):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(str(run_dir), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for line in steps:
            handle.write(json.dumps(line) + "\n")
    return run_dir


class Launches(list):
    """The launch seam's record: one `(argv, env, cwd)` per child the route would have started.

    The seam can watch a pid: every launch then records what the process table said about that pid at the
    moment the new child would have started, which is how a kill-before-relaunch is read rather than
    inferred from the fact that both happened.
    """

    def __init__(self):
        super().__init__()
        self.watch = None
        self.seen = []

    def pretend(self, argv, env, cwd):
        self.append((argv, env, cwd))
        if self.watch is not None:
            self.seen.append(liveness.probe_pid(self.watch))


@pytest.fixture
def launched(monkeypatch):
    """The launch seam: every argv, environment and working directory the route would have started."""
    calls = Launches()
    monkeypatch.setattr(spawn, "launch", calls.pretend)
    return calls


@pytest.fixture
def no_kills(monkeypatch):
    """The kill seam: every pid the route ended, and the fact that nothing else ended one."""
    killed = []
    monkeypatch.setattr(liveness, "kill", lambda pid: killed.append(pid))
    return killed


@pytest.fixture
def box(tmp_path):
    """A runs root holding the five states, a workspace that exists, and two processes to stand on.

    The sleeping child is the live verdict that can be killed for real and the open handle that keeps its
    pid answerable afterwards; the reaped one is the dead verdict that cannot be confused with it. Both are
    this battery's children, and the sleeper is put down here rather than left to the box.
    """
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = tmp_path / "runs"
    grants = {"read": [str(workspace), SAH_TREE], "write": [str(workspace)]}
    stamp = {"cwd": str(workspace), "pid": sleeper.pid, "grants": grants}
    write_log(root / SETTLED, step(0, "started", **stamp),
              step(1, "message", role="user", text="the first objective, as sent"),
              step(2, "message", role="assistant", text="done"),
              step(3, "ended", reason="complete", exit_code=0))
    write_log(root / DEAD, step(0, "started", cwd=str(workspace), pid=ran.pid, grants=grants),
              step(1, "message", role="user", text="the first objective, as sent"),
              step(2, "ended", reason="complete", exit_code=0))
    write_log(root / WORKING, step(0, "started", **stamp),
              step(1, "message", role="user", text="the objective it is still working"),
              step(2, "message", role="assistant", text="further to go"))
    write_log(root / ORPHAN, step(0, "started", cwd=str(workspace), pid=ran.pid, grants=grants),
              step(1, "message", role="user", text="the objective nobody finished"))
    write_log(root / CUT, step(0, "started", **stamp),
              step(1, "message", role="user", text="the objective worth keeping"),
              step(2, "message", role="assistant", text="the answer it got"),
              step(3, "message", role="user", text="the word that was walked away from"),
              step(4, "message", role="assistant", text="and its reply"),
              step(5, "ended", reason="complete", exit_code=0),
              step(6, "cut", to="000001-message"),
              step(7, "started", **stamp),
              step(8, "message", role="user", text="the corrected objective"),
              step(9, "ended", reason="complete", exit_code=0))
    yield {"root": root, "workspace": str(workspace), "sleeper": sleeper}
    sleeper.kill()
    sleeper.wait()


@pytest.fixture
def serve(box):
    """`serve()` — the server on a free port over that runs root; `serve.httpd` is the site to read."""
    started_servers = []

    def start():
        httpd = server.make_server("127.0.0.1", 0, runs_root=str(box["root"]), sah_tree=SAH_TREE)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started_servers.append(httpd)
        start.httpd = httpd
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started_servers:
        httpd.shutdown()
        httpd.server_close()


def resume_of(argv):
    """The argument `--resume` was sent with, or None when it was sent bare."""
    position = argv.index("--resume")
    following = argv[position + 1]
    return None if following.startswith("--") else following


# --- the kill-first, then the relaunch -----------------------------------------------------------------

def test_a_cut_ends_the_process_the_log_names_and_launches_the_step(box, serve, launched):
    """The cut's whole act, read afterwards: the old writer is gone and the new one carries the step.

    The kill is the follow's own guard on the pid the log's newest `started` line names — the sleeping
    child that wrote the ending and had not finished exiting — and the ordering is read at the launch: the
    process table says `dead` by the time the replacement would have started. Nothing is held about the
    run afterwards, because a relaunch leaves the server nothing to keep.
    """
    base = serve()
    launched.watch = box["sleeper"].pid
    status, answer = post_json(f"{base}/api/runs/{SETTLED}/message",
                               {"text": "the corrected first objective", "cut": 1, "max_turns": 7,
                                "max_runtime": 700, "think": "high"})
    assert (status, answer) == (200, {"ok": True, "channel": "follow", "run": SETTLED})
    assert launched.seen == [liveness.DEAD], "one new process, after the old writer was ended"
    assert box["sleeper"].wait(timeout=5) is not None, "the process the record named is off the table"

    assert len(launched) == 1
    argv, env, cwd = launched[0]
    assert resume_of(argv) == "1", "the conversation returns to the step, as logged"
    assert argv[argv.index("--task") + 1] == "the corrected first objective"
    reach = lambda flag: [argv[i + 1] for i, a in enumerate(argv) if a == flag]
    assert reach("--grant") == [box["workspace"], SAH_TREE], "the re-passed reach, as the follow always sends"
    assert reach("--write") == [box["workspace"]]
    assert reach("--max-turns") == ["7"] and reach("--max-runtime") == ["700"]
    assert reach("--think") == ["high"]
    assert "-i" not in argv, "the followed objective is worked by a process that exits when it is done"
    assert cwd == box["workspace"]
    assert env["PYTHONPATH"] == os.path.abspath(SAH_TREE)


def test_a_cut_on_a_run_the_machine_calls_dead_kills_nothing_and_carries_the_step(box, serve, launched,
                                                                                 no_kills):
    """A settled run whose process is already gone owes no signal, and the step is carried all the same."""
    base = serve()
    status, answer = post_json(f"{base}/api/runs/{DEAD}/message",
                               {"text": "onward from step one", "cut": 1})
    assert (status, answer) == (200, {"ok": True, "channel": "follow", "run": DEAD})
    assert no_kills == [], "a process the machine calls dead owes no kill"
    assert resume_of(launched[0][0]) == "1"


def test_a_cut_on_an_orphaned_run_is_the_standing_follow_with_the_step(box, serve, launched, no_kills):
    """No ending and no process is already the follow channel; the cut only adds the step to it."""
    base = serve()
    status, answer = post_json(f"{base}/api/runs/{ORPHAN}/message", {"text": "finish it from step one",
                                                                     "cut": 1})
    assert (status, answer) == (200, {"ok": True, "channel": "follow", "run": ORPHAN})
    assert no_kills == []
    assert resume_of(launched[0][0]) == "1"


def test_a_word_with_no_cut_ends_the_same_process_and_relaunches(box, serve, launched):
    """The case the held-keyboard refusal used to answer with a 409: it is now simply the follow.

    The objective ended and its process still stands, and this page never started either — there is no
    registry that could say whose keyboard it was, and none is needed: the follow ends the writer the
    record names and starts the one that reads the word, so a run settled elsewhere is continued the same
    way as one this page spawned.
    """
    base = serve()
    launched.watch = box["sleeper"].pid
    status, answer = post_json(f"{base}/api/runs/{SETTLED}/message", {"text": "one more objective"})
    assert (status, answer) == (200, {"ok": True, "channel": "follow", "run": SETTLED})
    assert launched.seen == [liveness.DEAD]
    argv = launched[0][0]
    assert resume_of(argv) is None, "no cut named, so the whole conversation resumes"
    assert argv[argv.index("--task") + 1] == "one more objective"


# --- the refusals, which move nothing ---------------------------------------------------------------

def test_a_cut_on_a_working_run_is_the_standing_refusal_and_stops_nothing(box, serve, launched,
                                                                          no_kills):
    """The 409 that already stood, asked of the run whose process holds the log.

    A run still working its objective is refused by the channel rule, and a route that ended the process
    first would have destroyed the very run it was about to refuse — the guard belongs to the relaunch,
    and a refusal relaunches nothing.
    """
    base = serve()
    error = expect_error(f"{base}/api/runs/{WORKING}/message", 409,
                         json.dumps({"text": "back to step one", "cut": 1}).encode("utf-8"))
    assert error["error"] == channel.BUSY
    assert no_kills == [] and launched == []
    assert box["sleeper"].poll() is None, "the run the refusal named is still working"


def test_a_cut_to_a_step_the_log_does_not_hold_is_refused_before_anything_moves(box, serve, launched,
                                                                                no_kills):
    """The record is asked first, and the sentence names the step and the log's last step."""
    base = serve()
    error = expect_error(f"{base}/api/runs/{SETTLED}/message", 400,
                         json.dumps({"text": "back to a step that is not there",
                                     "cut": 99}).encode("utf-8"))
    assert "99" in error["error"], error["error"]
    assert "000003-ended" in error["error"], "the log's last step, so the reader knows how far it goes"
    assert no_kills == [] and launched == []
    assert box["sleeper"].poll() is None, "the process the run stands on was never asked about"


def test_a_cut_to_a_detached_step_is_refused_as_firmly(box, serve, launched, no_kills):
    """A step in the file and not in the conversation: cutting to it would rebuild a tail this run shed.

    The log was cut once already, so its middle steps — the words the operator walked away from — are in
    the file and out of the conversation in force. The number names them, so the answer is the refusal;
    the steps a cut made live (step 8, the corrected objective) are another question.
    """
    base = serve()
    error = expect_error(f"{base}/api/runs/{CUT}/message", 400,
                         json.dumps({"text": "back to the word I already detached",
                                     "cut": 3}).encode("utf-8"))
    assert "3" in error["error"] and "detach" in error["error"].lower(), error["error"]
    assert "000009-ended" in error["error"], "the log's last step is named too"
    assert no_kills == [] and launched == []
    assert box["sleeper"].poll() is None


def test_a_cut_that_is_not_a_number_is_a_bad_request(box, serve, launched, no_kills):
    base = serve()
    error = expect_error(f"{base}/api/runs/{DEAD}/message", 400,
                         json.dumps({"text": "back to the start", "cut": "the-first-one"}).encode("utf-8"))
    assert "step's number" in error["error"] and "the-first-one" in error["error"]
    assert launched == [] and no_kills == []


# --- the channels that stood before the field, standing -----------------------------------------------

def test_the_steers_of_a_working_run_are_undisturbed_by_a_field_it_never_names(box, serve, launched,
                                                                               no_kills):
    """A word to a working run is queued, exactly as it was: no cut in the body, no rebuild in the argv.

    And the queue neither starts nor ends a process — the run keeps working its objective, which is the
    one state a steer is the answer for.
    """
    base = serve()
    status, answer = post_json(f"{base}/api/runs/{WORKING}/message", {"text": "a word, not an objective"})
    assert (status, answer) == (200, {"ok": True, "channel": "steer", "run": WORKING})
    argv = launched[0][0]
    assert argv[argv.index("send") + 1] == "--run-dir"
    assert "--resume" not in argv and "--task" not in argv
    assert no_kills == [], "a queued word ends nothing"
    assert box["sleeper"].poll() is None
