"""sahw.server — the fork route: branch a run's conversation into a new run.

`POST /api/runs/<id>/fork` reads the source's log and settles the branch step before anything is
started. The refusal is the cut's question about the same record — a step the log does not hold, or one
a cut detached — plus the one a fork cannot leave to SAH's door (a prefix that ends mid-exchange), and
a refusal launches nothing. The launch is the seam: `spawn.spawn_fork` is captured, not run, so what is
asserted is the branch step the route settled and the sentence it refused with — never a child the box
owns. The `ended` refusal the cut keeps is deliberately absent: branching from a finished conversation
is the point of the act.
"""
import json
import os
import threading
import urllib.error
import urllib.request

import pytest

from sahw import runs, server, spawn

TIMEOUT = 15.0

ALPHA = r"C:\work\alpha"
SOURCE = "r20261102-100000-srcaaa"     # a settled conversation the fork can branch
SOURCE_CUT = "r20261102-101000-srccut"  # a conversation that was cut once: its middle steps are detached

FAKE_FORK = "r20261102-110000-forkxx"  # the run id the seam answers with


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def expect_error(url, status, body=None):
    """The JSON body of an error response, having checked it is one error of that status and no other."""
    target = urllib.request.Request(url, data=body, method="POST",
                                    headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(target, timeout=TIMEOUT)
    assert raised.value.code == status
    error = json.loads(raised.value.read().decode("utf-8"))
    assert set(error) == {"error"} and error["error"]
    return error


def step(seq, kind, **fields):
    return {"id": f"{seq:06d}-{kind}", "kind": kind, "issuer": "core",
            "ts": f"2026-11-02T10:00:{seq % 60:02d}+00:00", **fields}


def write_log(run_dir, *steps):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(str(run_dir), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for line in steps:
            handle.write(json.dumps(line) + "\n")
    return run_dir


@pytest.fixture
def box(tmp_path):
    """A runs root with the two source conversations a fork can be asked of.

    `SOURCE` is a settled conversation with a plain tail; `SOURCE_CUT` was cut once, so the steps after
    the cut's target are in the file but out of the conversation a fork would carry.
    """
    root = tmp_path / "runs"
    write_log(root / SOURCE,
              step(0, "started", cwd=ALPHA),
              step(1, "message", role="user", text="first"),
              step(2, "message", role="assistant", text="one"),
              step(3, "message", role="user", text="second"),
              step(4, "message", role="assistant", text="two"),
              step(5, "ended", reason="complete", exit_code=0))
    write_log(root / SOURCE_CUT,
              step(0, "started", cwd=ALPHA),
              step(1, "message", role="user", text="one"),
              step(2, "message", role="assistant", text="two"),
              step(3, "message", role="user", text="three"),
              step(4, "message", role="assistant", text="four"),
              step(5, "cut", to="000002-message"),
              step(6, "message", role="user", text="five"),
              step(7, "ended", reason="complete", exit_code=0))
    return {"root": root}


@pytest.fixture
def capture(monkeypatch):
    """The fork's launch, captured: the route's seam, so no child is ever started.

    The captured argument is the branch step the route settled against the source's log — the number
    `sah fork` will be asked to carry — which is the fact the route owes the launch and nothing else.
    """
    calls = []

    def fake(runs_root, sah_tree, source_dir, step, task, max_turns=90, max_runtime=10800,
             think="", **kwargs):
        calls.append({"source": os.path.basename(source_dir), "step": step, "task": task})
        return FAKE_FORK

    monkeypatch.setattr(spawn, "spawn_fork", fake)
    return calls


@pytest.fixture
def serve(box):
    """`make_server` on a free port over that runs root, and a base URL to ask it things."""
    started = []

    def start():
        httpd = server.make_server("127.0.0.1", 0, runs_root=str(box["root"]))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started:
        httpd.shutdown()
        httpd.server_close()


# --- the fork that settles --------------------------------------------------------------------------------

def test_a_fork_of_a_settled_run_branches_from_where_it_stands(box, serve, capture):
    """No step named, no refusal owed: a fork of an ended run settles at the conversation's last step.

    The `ended` refusal the cut keeps is not a fork's — branching from a finished conversation is the
    point of the act — so the route settles the whole conversation at its tail and launches it.
    """
    base = serve()
    status, body = post_json(f"{base}/api/runs/{SOURCE}/fork", {"task": "the branch"})
    assert status == 201 and body == {"run_id": FAKE_FORK}
    assert len(capture) == 1
    assert capture[0] == {"source": SOURCE, "step": "4", "task": "the branch"}


def test_a_fork_named_at_a_step_branches_there(box, serve, capture):
    """A named step is carried to the launch as the digits the log holds: the branch is where the page
    pointed, not where the conversation stands."""
    base = serve()
    status, body = post_json(f"{base}/api/runs/{SOURCE}/fork", {"task": "the branch", "step": "2"})
    assert status == 201 and body == {"run_id": FAKE_FORK}
    assert capture[0]["step"] == "2"


# --- the fork that is refused ------------------------------------------------------------------------------

def test_a_fork_naming_a_step_the_log_does_not_hold_refuses_and_launches_nothing(box, serve, capture):
    base = serve()
    error = expect_error(f"{base}/api/runs/{SOURCE}/fork", 400,
                         json.dumps({"task": "the branch", "step": "9"}).encode("utf-8"))
    assert "does not hold" in error["error"]
    assert not capture, "a refusal settles a sentence and starts no child"


def test_a_fork_naming_a_detached_step_refuses_and_launches_nothing(box, serve, capture):
    """In the file, not in the conversation: a cut detached the step, and forking at it would carry a
    tail the conversation gave up. The refusal is the cut's in the fork's words, and it launches nothing."""
    base = serve()
    error = expect_error(f"{base}/api/runs/{SOURCE_CUT}/fork", 400,
                         json.dumps({"task": "the branch", "step": "4"}).encode("utf-8"))
    assert "detach" in error["error"].lower()
    assert not capture


def test_a_fork_of_a_run_that_is_not_there_is_the_absence_not_a_refusal(box, serve, capture):
    """A run id that names no folder is the 404 the listing owes: there is no conversation to branch."""
    base = serve()
    error = expect_error(f"{base}/api/runs/r20261102-109999-gonesss/fork", 404,
                         json.dumps({"task": "the branch"}).encode("utf-8"))
    assert "no such run" in error["error"]
    assert not capture
