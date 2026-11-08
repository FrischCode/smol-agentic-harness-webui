"""sahw.server — the stop route: one act on one process, and the 409 that says there was none.

`POST /api/runs/<id>/stop` is the one route that reaches a run's process, and the act is the same one a
follow performs before it relaunches: read the pid the log's newest `started` line names, end it if the
machine says it is alive, and answer whether that happened. So nothing here is read out of a returned
sentence alone — the assertions are the process table (the child this battery owns, and the handle that
keeps its pid answerable afterwards) and the folder (the log the kill left byte for byte, the row the tree
answers with next).

What a stop is *not* is the half that matters as much: a settled run — an ending on the record, or a
process the machine calls dead — has nothing to stop, and the answer is the 409 that says so rather than an
act that quietly did nothing. A run that has settled is continued by a word, which arrives as a follow; the
stop is only ever for a process that is still working, and it is the reason the front offers it on no other
row.

The third shape is the one no process of this run's asked for: the number the record names can be handed to
another process while the run's own log stands silent, so a live answer on it is no evidence that there is
something here to end. The route asks the tree's poll whether the number is rebirthed before it asks for the
kill (see `runs.Poll.rebirthed`), and the battery stands that rebirth the way the module invites it to — the
answer read off a process table the test holds, because this box's number space cannot be ordered to rebirth
a number on demand. What the vouching refuses it refuses in words that say nothing was ended, and what it
vouches for is ended exactly as it always was: both halves stand in every check below.
"""
import http.client
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

from sahw import liveness, runs, server

TIMEOUT = 15.0

ALPHA = r"C:\work\alpha"

WORKING = "r20261102-090000-aaaaaa"       # no ending, and the process it stamped is alive
ORPHAN = "r20261102-090100-bbbbbb"        # no ending, and the process the machine calls dead
ENDED = "r20261102-090200-cccccc"         # the ending is on the record and the process is gone
SETTLING = "r20261102-090300-dddddd"      # the ending is on the record and the process has not exited
NAMELESS = "r20261102-090400-eeeeee"      # an ending, and a log that never stamped a pid to ask about


def post_json(url, payload=None):
    body = payload if isinstance(payload, bytes) else json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def expect_error(url, status, body=None):
    """The JSON body of an error response, having checked it is one error of that status and no other.

    Always a POST: the stop route is an act, and an act asked with a GET is a different request that gets
    a different answer — the helper is not in the business of answering the wrong question.
    """
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
            "ts": f"2026-11-02T09:00:{seq % 60:02d}+00:00", **fields}


def write_log(run_dir, *steps):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(str(run_dir), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for line in steps:
            handle.write(json.dumps(line) + "\n")
    return run_dir


@pytest.fixture
def box(tmp_path):
    """A runs root holding every state a stop can be asked of, and the three processes behind them.

    The sleepers are this battery's children — one standing behind a run still working, one behind a run
    whose objective ended on its way out — and both are held open so their pids stay answerable after they
    are killed rather than becoming numbers the box may hand out again. The reaped child is the dead
    verdict none of them can be confused with.
    """
    working = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    settling = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    root = tmp_path / "runs"
    write_log(root / WORKING, step(0, "started", cwd=ALPHA, pid=working.pid),
              step(1, "message", role="user", text="the objective it is still working"))
    write_log(root / ORPHAN, step(0, "started", cwd=ALPHA, pid=ran.pid),
              step(1, "message", role="user", text="the objective nobody finished"))
    write_log(root / ENDED, step(0, "started", cwd=ALPHA, pid=ran.pid),
              step(1, "message", role="user", text="the objective that answered"),
              step(2, "ended", reason="complete", exit_code=0))
    write_log(root / SETTLING, step(0, "started", cwd=ALPHA, pid=settling.pid),
              step(1, "message", role="user", text="the objective that just answered"),
              step(2, "ended", reason="complete", exit_code=0))
    write_log(root / NAMELESS, step(0, "started", cwd=ALPHA),
              step(1, "message", role="user", text="a log from before the pid was stamped"),
              step(2, "ended", reason="complete", exit_code=0))
    yield {"root": root, "working": working, "settling": settling}
    for child in (working, settling):
        child.kill()
        child.wait()


@pytest.fixture
def serve(box):
    """`serve()` — the server on a free port over that runs root, and a base URL to ask it things."""
    started_servers = []

    def start():
        httpd = server.make_server("127.0.0.1", 0, runs_root=str(box["root"]))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started_servers.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started_servers:
        httpd.shutdown()
        httpd.server_close()


def rows_of(base):
    with urllib.request.urlopen(base + "/api/runs", timeout=TIMEOUT) as response:
        tree = json.loads(response.read())
    return {row["id"]: row for workspace in tree["workspaces"] for row in workspace["runs"]}


def log_bytes(box, run_id):
    return (box["root"] / run_id / runs.LOG_NAME).read_bytes()


# --- the stop of a working run ------------------------------------------------------------------------

def test_a_stop_ends_the_working_runs_process_and_keeps_everything_else(box, serve):
    """The act in full: the child is gone, the log is byte for byte what it was, and the row is listed.

    A stopped run is not a deleted run and not a finished one — no `ended` line is written for a kill, so
    the row takes the orphan's shape and the next word relaunches on the same record. The record is the
    thing the operator owns; the process was only ever borrowed.
    """
    base = serve()
    before = log_bytes(box, WORKING)
    assert box["working"].poll() is None
    assert post_json(f"{base}/api/runs/{WORKING}/stop") == (200, {"ok": True})
    assert box["working"].wait(timeout=5) is not None, "the pid the log named is off the table"
    assert log_bytes(box, WORKING) == before, "the record stands exactly where it stood"
    row = rows_of(base)[WORKING]
    assert row["status"] == "live" and row["live"] == "dead", "a stopped run is resumable, not finished"


def test_a_stop_that_landed_leaves_nothing_further_to_stop(box, serve):
    """The second stop is the 409: the act is not idempotent-by-silence, it says what it found.

    The process is gone by the first act, so the second has nothing to end — and the record it read is
    still the same bytes, because a stop that had nothing to do does not do anything else either.
    """
    base = serve()
    before = log_bytes(box, WORKING)
    post_json(f"{base}/api/runs/{WORKING}/stop")
    error = expect_error(f"{base}/api/runs/{WORKING}/stop", 409)
    assert "nothing to stop" in error["error"]
    assert log_bytes(box, WORKING) == before


# --- the stop that is owed a refusal ---------------------------------------------------------------

@pytest.mark.parametrize("run_id", [ORPHAN, ENDED, NAMELESS])
def test_a_stop_on_a_settled_run_is_the_no_op_that_names_the_state(box, serve, run_id):
    """An ended run, a run whose process died mid-objective, and a log that named no pid at all.

    Three ways a run is settled and none of them has a process to end: the answer is the 409 that says so
    — not a caller's mistake, and not an act that pretended to happen. What a settled run is owed is a
    word, and that arrives on the follow channel.
    """
    base = serve()
    before = log_bytes(box, run_id)
    error = expect_error(f"{base}/api/runs/{run_id}/stop", 409)
    assert "nothing to stop" in error["error"], error["error"]
    assert log_bytes(box, run_id) == before


def test_a_stop_of_a_run_that_is_not_there_is_not_found(box, serve):
    """The id is checked before the act: a run the root does not hold is the 404 every route answers."""
    base = serve()
    error = expect_error(f"{base}/api/runs/r20261102-099999-zzzzzz/stop", 404)
    assert "no such run" in error["error"]


# --- the connection the act must not leave behind --------------------------------------------------------

def test_a_stop_body_left_unread_is_not_the_next_requests_first_line(serve, box):
    """The pool that keeps a connection open reads at the place the last request left off.

    The act takes no body, and a caller may send one anyway: the body is the connection's to read, not the
    route's to want. Left in the socket, its bytes are the next request read at the wrong place, and the
    method that request is refused with is this one's leftovers. The proof is the same socket: a stop that
    carries a body, answered, and a listing on the connection it came over, arriving whole.
    """
    base = serve()
    parts = urllib.parse.urlparse(base)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=TIMEOUT)
    try:
        connection.request("POST", f"/api/runs/{WORKING}/stop", body=b"{}",
                           headers={"Content-Type": "application/json"})
        first = connection.getresponse()
        first.read()
        assert first.status == 200
        connection.request("GET", "/api/runs")
        second = connection.getresponse()
        tree = json.loads(second.read())
        assert second.status == 200, "the next request on the socket is read where the stop's body left it"
        ids = {row["id"] for workspace in tree["workspaces"] for row in workspace["runs"]}
        assert WORKING in ids
    finally:
        connection.close()


# --- the state the guard exists for --------------------------------------------------------------------

def test_a_stop_ends_the_process_a_finished_objective_left_behind(box, serve):
    """The run whose ending is written and whose process has not exited: there is something to end.

    The record says settled and the machine says alive, and it is the pair the follow's guard was written
    for — a relaunch beside a process still finishing is a second writer. The stop asks the same act, so
    it ends the same process, and the answer is `ok` because the act did happen. The face never offers it
    there (the row carries no Stop), which is the difference between the route's word and the page's.
    """
    base = serve()
    assert box["settling"].poll() is None
    assert post_json(f"{base}/api/runs/{SETTLING}/stop") == (200, {"ok": True})
    assert box["settling"].wait(timeout=5) is not None
    assert log_bytes(box, SETTLING).count(b'"ended"') == 1, "the ending the run wrote is still the tail"


# --- the number the record can no longer vouch for --------------------------------------------------------

def held_process_table(monkeypatch, live):
    """The machine answered from a table this battery holds: every number in `live` is a process, and every
    number outside it is not.

    The seam `liveness` names for a reader that wants the answer rather than the machine — the verdict is
    read off the process table — so the rebirth a stop is refused for can be stood on purpose instead of
    hunted for in a number space that does not hand a freed number back on request. `live` is the
    battery's own set, so a number is reborn by adding it between two askings.
    """
    def answered(pids):
        return {pid: (liveness.LIVE if pid in live else liveness.DEAD) for pid in pids}

    monkeypatch.setattr(liveness, "probe_pids", answered)
    return live


def stand_a_rebirth(box, base, monkeypatch):
    """The working run killed, its death stood on the row, and its number then handed to another process.

    The three steps in the order the machine tells them: the tree answers the run live on the process that
    is really there; the process goes and the tree answers it dead, which is the verdict the row goes on
    standing; and the number answers live again over a log that has not written a word since. What comes
    back is the table to hold and the list the kill seam appends to, so a check reads whether an act was
    asked for at all rather than inferring it from a process that is nobody's to end.
    """
    assert rows_of(base)[WORKING]["live"] == "live", "the row stands working on its own process"
    box["working"].kill()
    box["working"].wait()
    assert rows_of(base)[WORKING]["live"] == "dead", "the death stood, on the number the record named"
    before = log_bytes(box, WORKING)
    held = held_process_table(monkeypatch, {box["working"].pid, box["settling"].pid})
    asked: list = []
    monkeypatch.setattr(liveness, "kill", asked.append)
    return {"table": held, "kills": asked, "log": before}


def test_a_rebirthed_number_is_refused_in_the_machines_own_words_and_ends_nothing(box, serve, monkeypatch):
    """The stop asked of a name another process is wearing: the refusal, and nothing ended.

    The row still stands dead — the record has said nothing since the verdict — and the number answers
    live, and that pair is what says the process behind the number was never this run's. So the route
    refuses rather than ending a stranger, in the sentence the face stands at the head of the tree the act
    was asked from; the kill is never asked, and the record is the same bytes it was before the click.
    """
    base = serve()
    stop = stand_a_rebirth(box, base, monkeypatch)
    row = rows_of(base)[WORKING]
    assert row["live"] == "dead" and row["reborn"] == box["working"].pid, "the row carries the reason"
    error = expect_error(f"{base}/api/runs/{WORKING}/stop", 409)
    assert "not the one the record named" in error["error"], error["error"]
    assert "nothing ended" in error["error"], "and the refusal says the act did not happen"
    assert stop["kills"] == [], "no process was asked to end"
    assert log_bytes(box, WORKING) == stop["log"], "the record stands where the click left it"


def test_the_stop_on_a_number_the_record_vouches_for_ends_what_it_always_ended(box, serve, monkeypatch):
    """The other half of the same instant: the refusal stands on one name, and on no other number's stop.

    With the rebirth standing on the killed run's number and the kill seam watched, a run whose number the
    record names and whose row the poll never called dead is ended exactly as it always was — the vouching
    costs that stop nothing, and it asks for the one number and no other.
    """
    base = serve()
    stop = stand_a_rebirth(box, base, monkeypatch)
    assert rows_of(base)[ORPHAN]["live"] == "dead", "the orphan's number is asked of and answers dead"
    assert post_json(f"{base}/api/runs/{SETTLING}/stop") == (200, {"ok": True})
    assert stop["kills"] == [box["settling"].pid], "the act, asked of the number the record names"
