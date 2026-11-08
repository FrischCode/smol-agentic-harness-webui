"""sahw.server — the compact's routes: one verb on the run's queue, and the record it leaves untouched.

`POST /api/runs/<id>/compact` and `/compact-stop` carry the compact's verb to the run's queue through the
`send` seam, and answer which verb was carried. The verb is the queue's and the decision the run's — a
`compact` runs the compaction at the run's next turn boundary, and a `compact-stop` asks the compaction in
flight to stand down, refusing in the run's own words where no flight is working — so the route starts
nothing and, more importantly for what a test can assert, writes nothing: nothing here is the run's
state, and the record stands the flight and its two endings beside the log in the run's own words, so the
log this route touches not at all is the assertion that the route did not take a second voice.

The seam is `spawn.launch`, held by a stand-in that reads the argv and never starts a child, the way the
other act batteries hold theirs: what is asserted is the flags the verb would run with, and the bytes the
run's folder holds before and after. A route that answered a settled run differently from a working one
would be deciding for the run, so both are asked and both are owed the same carrying.
"""
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

from sahw import runs, server, spawn

TIMEOUT = 15.0

ALPHA = r"C:\work\alpha"

WORKING = "r20261103-090000-aaaaaa"     # no ending, and the process it stamped is alive
ENDED = "r20261103-090100-bbbbbb"       # the ending is on the record and the process is gone


def post_json(url, payload=None):
    body = payload if isinstance(payload, bytes) else json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def expect_error(url, status, body=None):
    """The JSON body of an error response, having checked it is one error of that status and no other."""
    target = urllib.request.Request(url, data=body or b"{}", method="POST",
                                    headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(target, timeout=TIMEOUT)
    assert raised.value.code == status
    error = json.loads(raised.value.read().decode("utf-8"))
    assert set(error) == {"error"} and error["error"]
    return error


def step(seq, kind, **fields):
    return {"id": f"{seq:06d}-{kind}", "kind": kind, "issuer": "core",
            "ts": f"2026-11-03T09:00:{seq % 60:02d}+00:00", **fields}


def write_log(run_dir, *steps):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(str(run_dir), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for line in steps:
            handle.write(json.dumps(line) + "\n")
    return run_dir


@pytest.fixture
def launched(monkeypatch):
    """The launch seam: every argv, environment and working directory the route would have started."""
    calls = []
    monkeypatch.setattr(spawn, "launch", lambda argv, env, cwd: calls.append((argv, env, cwd)))
    return calls


@pytest.fixture
def box(tmp_path, launched):
    """A runs root holding the two states a compact's verb can be asked of.

    The sleeper is this battery's child, held open so the working run's process stays alive for the
    whole ask; the ended run is the record's own shape, and the two are owed the same carrying.
    """
    working = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    root = tmp_path / "runs"
    write_log(root / WORKING, step(0, "started", cwd=ALPHA, pid=working.pid),
              step(1, "message", role="user", text="the objective it is still working"))
    write_log(root / ENDED, step(0, "started", cwd=ALPHA, pid=working.pid),
              step(1, "message", role="assistant", text="the objective that answered"),
              step(2, "ended", reason="complete", exit_code=0))
    yield {"root": root, "working": working}
    working.kill()
    working.wait()


@pytest.fixture
def serve(box):
    """`serve()` — the server on a free port over that runs root, named at the tree the verbs run from."""
    started_servers = []

    def start(sah_tree=r"C:\Work\SAH"):
        httpd = server.make_server("127.0.0.1", 0, runs_root=str(box["root"]), sah_tree=sah_tree)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started_servers.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started_servers:
        httpd.shutdown()
        httpd.server_close()


def log_bytes(box, run_id):
    return (box["root"] / run_id / runs.LOG_NAME).read_bytes()


# --- the verb carried ------------------------------------------------------------------------------------

def test_a_compact_carries_its_verb_to_the_queue_and_touches_nothing_else(box, serve, launched):
    """The act in full: the answer names the verb, the queue holds the block the seam wrote, and the log
    is byte for byte what it was — the record stands the flight itself, and a route that wrote beside it
    would be a second voice claiming what the queue did.
    """
    base = serve()
    before = log_bytes(box, WORKING)
    status, body = post_json(f"{base}/api/runs/{WORKING}/compact")
    assert status == 200 and body == {"ok": True, "run": WORKING, "action": "compact"}, \
        "the answer is the verb carried, so the caller knows which act to read the record for"
    assert len(launched) == 1, "one launch, the send, and nothing beside it"
    argv, env, cwd = launched[0]
    assert argv[3] == "send", "the verb leads, as an operator types it"
    assert argv[argv.index("--run-dir") + 1] == str(box["root"] / WORKING)
    assert argv[argv.index("--from") + 1] == "sahw", "the record says who queued it"
    assert argv[-1] == "compact", "and the verb it names is the act the answer gave"
    assert "--resume" not in argv and "--task" not in argv, "a verb carries no text and starts no objective"
    assert env["PYTHONPATH"] == os.path.abspath(r"C:\Work\SAH")
    assert cwd == str(box["root"] / WORKING)
    assert log_bytes(box, WORKING) == before, "the record stands the flight itself"


def test_the_stop_carries_its_own_verb(box, serve, launched):
    """The stand-down is the same carrying with the other name: the queue receives the verb the answer
    gave, and nothing more is owed.
    """
    base = serve()
    before = log_bytes(box, WORKING)
    status, body = post_json(f"{base}/api/runs/{WORKING}/compact-stop")
    assert status == 200 and body == {"ok": True, "run": WORKING, "action": "compact-stop"}
    argv, _, _ = launched[0]
    assert argv[-1] == "compact-stop", "the verb the answer names is the verb the queue received"
    assert log_bytes(box, WORKING) == before


def test_two_asks_leave_two_blocks_in_the_queue(box, serve, launched):
    """A compact and its stop, one after the other: the seam carries both, in the order the asks went out.

    Which one the run acts on is the run's own reading at its boundary — a stop that finds no flight is
    refused in the run's own words — so the route owes the order and nothing about the outcome; the
    queue's own bytes are the seam's child to write, and the live pass reads them.
    """
    base = serve()
    post_json(f"{base}/api/runs/{WORKING}/compact")
    post_json(f"{base}/api/runs/{WORKING}/compact-stop")
    assert len(launched) == 2
    assert launched[0][0][-1] == "compact" and launched[1][0][-1] == "compact-stop", \
        "the asks went out in the order the route took them"


# --- the answer a settled run owes -----------------------------------------------------------------------

def test_a_compact_to_a_settled_run_is_carried_the_way_a_working_one_is(box, serve, launched):
    """The route does not decide for the run: a `compact` to a run whose ending is on the record is the
    compact that the word relaunching it reads at its first turn, and the carrying is the answer.
    """
    base = serve()
    before = log_bytes(box, ENDED)
    status, body = post_json(f"{base}/api/runs/{ENDED}/compact")
    assert status == 200 and body["action"] == "compact"
    argv, _, cwd = launched[0]
    assert argv[-1] == "compact" and cwd == str(box["root"] / ENDED)
    assert log_bytes(box, ENDED) == before


# --- the refusals the route owes ------------------------------------------------------------------------

def test_a_compact_of_a_run_that_is_not_there_is_not_found(box, serve, launched):
    """The id is checked before the act: a run the root does not hold is the 404 every route answers."""
    base = serve()
    error = expect_error(f"{base}/api/runs/r20261103-099999-zzzzzz/compact", 404)
    assert "no such run" in error["error"]
    assert launched == [], "a refusal starts nothing"


def test_a_compact_from_a_server_that_names_no_tree_is_refused(box, serve, launched):
    """The seam needs the tree whose interpreter runs the verb: a server that names none says so, and a
    refusal starts nothing and writes nothing.
    """
    base = serve(sah_tree="")
    before = log_bytes(box, WORKING)
    error = expect_error(f"{base}/api/runs/{WORKING}/compact", 503)
    assert "names no SAH tree" in error["error"]
    assert launched == []
    assert log_bytes(box, WORKING) == before
