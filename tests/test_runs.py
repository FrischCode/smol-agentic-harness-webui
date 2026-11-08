"""sahw.runs — the tree read from the head and the tail of each log, one log followed as it grows, and
the whole of one read once for a cut.

The fixture root is hand-written logs: a `started` step carrying the workspace, the model and the stamp,
and for a run that finished an `ended` carrying the reason. Nothing here starts a run or opens a port;
what is under test is which facts are read out of a file, how they are ordered, where a reader stops,
and when one of the readers has to be asked of the machine instead. A log holds one `started`/`ended` pair
per objective, so the two-objective shapes below are not exotic: they are what a followed run leaves behind.

The cut's reader is the one that walks the whole file, and the shapes it is checked against are the ones
only a walk can tell apart: a step the conversation holds, a step a cut detached but the file kept, and a
step the number never named.

The poll is the same reading asked twice, and what is under test there is the debt between the two asks:
a log that stands answers with the row it answered before and costs no reading, a row that has not ended
re-asks the machine's verdict on every asking, and the only asking that owes the record again is a verdict
that moved under a log that did not.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from sahw import liveness, runs

WORKSPACE = r"C:\work"


def write_log(run_dir, *steps) -> str:
    """A run folder holding a log of exactly these steps, one JSON object per line."""
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for step in steps:
            handle.write(json.dumps(step) + "\n")
    return run_dir


def started(cwd, ts, model="flash-next", **extra):
    return {"id": "000000-started", "kind": "started", "issuer": "core", "ts": ts, "cwd": cwd,
            "model": model, "run_id": "run", "root": "root", **extra}


def message(text, ts="2026-11-01T08:30:00+00:00"):
    return {"id": "000005-message", "kind": "message", "issuer": "core", "ts": ts,
            "role": "assistant", "text": text}


def userMessage(text, ts="2026-11-01T08:00:01+00:00"):
    return {"id": "000001-message", "kind": "message", "issuer": "user", "ts": ts,
            "role": "user", "text": text}


def ended(reason="complete", ts="2026-11-01T09:00:00+00:00"):
    return {"id": "000009-ended", "kind": "ended", "issuer": "core", "ts": ts, "reason": reason,
            "exit_code": 0}


def control(text, ts="2026-11-01T09:30:00+00:00"):
    """The word one of the session's two dials leaves in the record: what the operator's channel wrote."""
    return {"id": "000011-notice", "kind": "notice", "issuer": "operator", "subject": "command",
            "ts": ts, "text": text}


@pytest.fixture
def runs_root(tmp_path):
    """Three runs across two workspaces: one ended, one live, one ended by a stop."""
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T08:00:00+00:00"),
              userMessage("make the thing"),
              message("one"), ended())
    write_log(str(root / "r20261101-081000-bbbbbb"),
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T08:10:00+00:00"))
    write_log(str(root / "r20261101-082000-cccccc"),
              started(os.path.join(WORKSPACE, "beta"), "2026-11-01T08:20:00+00:00"),
              ended("stopped"))
    return str(root)


def test_the_tree_groups_runs_by_the_workspace_their_log_names(runs_root):
    got = runs.tree(runs_root)
    assert [workspace["path"] for workspace in got["workspaces"]] == [
        os.path.join(WORKSPACE, "alpha"), os.path.join(WORKSPACE, "beta")]


def test_the_tree_row_carries_the_word_the_run_was_sent_with(runs_root):
    """The row's own name is the id; the word the operator sent rides under `task` when the log has it,
    and a log with no user word keeps the row to its id rather than the row inventing a word."""
    got = runs.tree(runs_root)
    rows = {row["id"]: row for workspace in got["workspaces"] for row in workspace["runs"]}
    assert rows["r20261101-080000-aaaaaa"]["task"] == "make the thing"
    assert "task" not in rows["r20261101-081000-bbbbbb"], "no user word is no task key"
    assert "task" not in rows["r20261101-082000-cccccc"], "and neither for the stopped run"


def test_a_multiline_objective_gives_the_row_its_first_line(tmp_path):
    """The row owes one line, and a multi-line objective owes the row its first: the rest of the
    lines stand in for nothing but a newline, so the word the row wears is the one sent first, not
    the whole objective flattened onto one line."""
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-083000-mmmmmm"),
              started(WORKSPACE, "2026-11-01T08:30:00+00:00"),
              userMessage("Two steps, then stop.\n1. the first file\n2. the second file"),
              ended())
    row = runs.tree(str(root))["workspaces"][0]["runs"][0]
    assert row["task"] == "Two steps, then stop.", "the first line, not the flattened whole"


def test_a_first_line_longer_than_the_cut_stands_as_its_cut_and_the_mark(tmp_path):
    """The row owes a name, not a paragraph: a first line longer than the cut stands as its cut and
    the mark that says the log holds the rest — and the tree's filter reads the word the row wears,
    so a word the whole paragraph held and the cut does not is not a word the row answers to."""
    root = tmp_path / "runs"
    word = "the word the operator sent, the whole of it, " * 4
    assert len(word) > runs.NAME_CUT
    write_log(str(root / "r20261101-085000-oooooo"),
              started(WORKSPACE, "2026-11-01T08:50:00+00:00"),
              userMessage(word),
              ended())
    row = runs.tree(str(root))["workspaces"][0]["runs"][0]
    assert row["task"] == word[:runs.NAME_CUT] + "\u2026", "the cut and the mark, and the log holds the rest"


def test_a_first_line_at_the_cut_stands_whole(tmp_path):
    """The cut is the most a word keeps: at it, a word keeps all of itself, and no mark stands."""
    root = tmp_path / "runs"
    word = "z" * runs.NAME_CUT
    write_log(str(root / "r20261101-086000-pppppp"),
              started(WORKSPACE, "2026-11-01T08:45:00+00:00"),
              userMessage(word),
              ended())
    row = runs.tree(str(root))["workspaces"][0]["runs"][0]
    assert row["task"] == word, "at the cut the word stands whole, unmarked"


def test_an_objective_that_opens_with_blank_lines_still_names_its_first_line(tmp_path):
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-084000-nnnnnn"),
              started(WORKSPACE, "2026-11-01T08:40:00+00:00"),
              userMessage("\n\nthe real word\na second line"),
              ended())
    row = runs.tree(str(root))["workspaces"][0]["runs"][0]
    assert row["task"] == "the real word", "the first non-blank line, blank lines skipped"


def test_an_ended_row_owes_no_verdict_even_while_its_process_still_stands(tmp_path):
    """The record's ending is the whole answer: an ended row carries no `live` key at any price.

    The process that wrote the ending may still be on its way out, and the machine would answer `live`
    if it were asked — but a run's process lives its objective's lifecycle, so the row that has an ending
    is settled and there is no third verdict for it to wear. Asking the machine here would be the reading
    this model left behind, and a row that carried the key would hand the face a spinner to wear on a run
    that has already answered.
    """
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-100000-settled"),
              started(WORKSPACE, "2026-11-01T10:00:00+00:00", pid=os.getpid()),
              userMessage("the first word"), ended())
    rows = {row["id"]: row for workspace in runs.tree(str(root))["workspaces"]
            for row in workspace["runs"]}
    assert rows["r20261101-100000-settled"]["status"] == "ended"
    assert "live" not in rows["r20261101-100000-settled"], "an ending needs no second opinion"


def test_an_ended_row_the_machine_calls_dead_stands_on_its_ending(tmp_path):
    root = tmp_path / "runs"
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    write_log(str(root / "r20261101-110000-over"),
              started(WORKSPACE, "2026-11-01T11:00:00+00:00", pid=ran.pid), ended())
    rows = {row["id"]: row for workspace in runs.tree(str(root))["workspaces"]
            for row in workspace["runs"]}
    assert "live" not in rows["r20261101-110000-over"], "a dead process is no listening to read"
    write_log(str(root / "r20261101-120000-nameless"),
              started(WORKSPACE, "2026-11-01T12:00:00+00:00"), ended())
    rows = {row["id"]: row for workspace in runs.tree(str(root))["workspaces"]
            for row in workspace["runs"]}
    assert "live" not in rows["r20261101-120000-nameless"], "a stamp that names no pid says nothing"


def test_a_workspace_lists_its_runs_newest_first(runs_root):
    alpha = runs.tree(runs_root)["workspaces"][0]
    assert [row["id"] for row in alpha["runs"]] == ["r20261101-081000-bbbbbb", "r20261101-080000-aaaaaa"]


def test_a_row_is_the_facts_the_api_shows(runs_root):
    runs_of_alpha = runs.tree(runs_root)["workspaces"][0]["runs"]
    # The row carries its word twice on purpose: `task` is the record's own first word, settled and never
    # rewritten, and `name` is what the row is worn by — the face's file, the boot's title, or this same
    # first word when neither named it (plan 38's rule, in `runs.worn_name`).
    assert runs_of_alpha[1] == {"id": "r20261101-080000-aaaaaa", "ts": "2026-11-01T08:00:00+00:00",
                                "model": "flash-next", "status": "ended", "reason": "complete",
                                "task": "make the thing", "name": "make the thing"}


def test_a_run_with_no_ended_is_live_and_owes_no_reason(runs_root):
    live = runs.tree(runs_root)["workspaces"][0]["runs"][0]
    assert live["status"] == "live"
    assert live["reason"] is None


def test_an_unfinished_row_carries_the_machines_verdict_and_a_finished_one_carries_no_key(tmp_path, gone):
    """Where the verdict is hung on a row: the log names the pid, the machine says what became of it.

    The unfinished rows are this process (still here) and a log from before the pid was ever stamped
    (nothing to ask about); the finished row's process died with its objective — the one-shot's death.
    A finished row carries no key at all, whatever its pid answers: see the settled row's own test.
    """
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=os.getpid()))
    write_log(str(root / "r20261101-081000-bbbbbb"), started(WORKSPACE, "2026-11-01T08:10:00+00:00"))
    write_log(str(root / "r20261101-082000-cccccc"),
              started(WORKSPACE, "2026-11-01T08:20:00+00:00", pid=gone.pid), ended())
    rows = {row["id"]: row for row in runs.tree(str(root))["workspaces"][0]["runs"]}
    assert rows["r20261101-080000-aaaaaa"]["live"] == "live"
    assert rows["r20261101-081000-bbbbbb"]["live"] == "unknown"
    assert "live" not in rows["r20261101-082000-cccccc"]


@pytest.fixture
def gone():
    """A process that ran and was reaped, held by this handle so its pid stays answerable as `dead`."""
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    return ran


def test_a_second_objective_is_a_row_about_the_process_behind_it(tmp_path, gone):
    """The whole point of the walk: a followed run is working, and the head's pid is long dead.

    One log, two objectives: the first stamped a pid that exited with its objective, the second stamped
    the process answering this request. Read by the head alone the row is an orphan; the record says
    otherwise, and the record is the one with a second `started` line under the first one's ending.
    """
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=gone.pid),
              message("one"), ended(),
              started(WORKSPACE, "2026-11-01T09:00:00+00:00", pid=os.getpid()),
              message("two"))
    row = runs.tree(str(root))["workspaces"][0]["runs"][0]
    assert row["status"] == "live"
    assert row["live"] == "live", "the second objective's process, not the first objective's"
    assert row["ts"] == "2026-11-01T08:00:00+00:00", "the row names the run, which the run opened with"


def test_a_finished_second_objective_leaves_the_row_ended(tmp_path, gone):
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=gone.pid), ended(),
              started(WORKSPACE, "2026-11-01T09:00:00+00:00", pid=gone.pid),
              message("two"), ended("stopped"))
    row = runs.tree(str(root))["workspaces"][0]["runs"][0]
    assert (row["status"], row["reason"]) == ("ended", "stopped")
    assert "live" not in row


def test_an_orphan_of_one_objective_is_still_an_orphan_of_two(tmp_path, gone):
    """A log whose every objective's process is gone owes the dead verdict and no walking excuse."""
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=gone.pid),
              message("one"), ended(),
              started(WORKSPACE, "2026-11-01T09:00:00+00:00", pid=gone.pid),
              message("two"))
    assert runs.tree(str(root))["workspaces"][0]["runs"][0]["live"] == "dead"


def test_the_newest_started_line_is_the_one_a_follow_inherits(tmp_path):
    """Reach and workspace come off the objective the conversation stands on, not off the first one."""
    log = tmp_path / runs.LOG_NAME
    with open(log, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00",
                                        grants={"read": [WORKSPACE], "write": []})) + "\n")
        handle.write(json.dumps(message("one")) + "\n")
        handle.write(json.dumps(ended()) + "\n")
        handle.write(json.dumps(started(os.path.join(WORKSPACE, "deeper"), "2026-11-01T09:00:00+00:00",
                                        grants={"read": [r"C:\other"], "write": [r"C:\other"]})) + "\n")
    stamp = runs.latest_started(str(log))
    assert stamp["cwd"] == os.path.join(WORKSPACE, "deeper")
    assert stamp["grants"]["write"] == [r"C:\other"]


def test_a_log_whose_newest_line_is_out_of_reach_falls_back_to_its_head(tmp_path, monkeypatch):
    """Past the walk's cap the honest answer is the run's own opening line, and no claim beyond it."""
    monkeypatch.setattr(runs, "TAIL_WINDOW", 64)
    monkeypatch.setattr(runs, "SEARCH_CAP", 256)
    log = tmp_path / runs.LOG_NAME
    with open(log, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=os.getpid())) + "\n")
        handle.write(json.dumps(message("x" * 4096)) + "\n")     # the newest started is past the cap
        handle.write(json.dumps(ended()) + "\n")
        handle.write(json.dumps(message("y" * 4096)) + "\n")
    assert runs.latest_started(str(log))["cwd"] == WORKSPACE


def test_an_unreadable_newest_line_leaves_the_verdict_unasked(tmp_path, monkeypatch, gone):
    """A walk that ran out of cap says nothing about the process, and `unknown` is not `dead`.

    The safe direction, twice over: a row that is not called dead wears no orphan mark, and a run the
    machine cannot vouch for is never resumed into a second writer.
    """
    monkeypatch.setattr(runs, "TAIL_WINDOW", 64)
    monkeypatch.setattr(runs, "SEARCH_CAP", 256)
    root = tmp_path / "runs"
    folder = root / "r20261101-080000-aaaaaa"
    folder.mkdir(parents=True)
    with open(folder / runs.LOG_NAME, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=gone.pid)) + "\n")
        handle.write(json.dumps(message("x" * 8192)) + "\n")     # the newest started is past the cap
    assert runs.tree(str(root))["workspaces"][0]["runs"][0]["live"] == "unknown"


LOG_READS = ("_started_step", "_ended_step", "dials", "objective", "describe_run")


def no_readings(monkeypatch):
    """A tally of the calls that read a record: the head, the tail, the dials' dig, the objective walk,
    and the row built out of them. A poll that answers from memory is the tally staying empty; the one
    look it does pay is `_log_stamp`'s `os.stat`, which is the question *did this move* and not a reading.
    """
    tally = {}
    for name in LOG_READS:
        tally[name] = 0
        real = getattr(runs, name)

        def counting(*args, _real=real, _key=name):
            tally[_key] += 1
            return _real(*args)

        monkeypatch.setattr(runs, name, counting)
    return lambda: {name: count for name, count in tally.items() if count}


def asked_verdicts(monkeypatch):
    """`liveness.probe_pids` wrapped in a list of the batches one poll handed the machine. The numbers a
    standing log still owes are asked once per poll, in one batch — so the list is the asking, and what
    it holds is which numbers the poll settled together."""
    batches = []
    real = runs.liveness.probe_pids

    def counting(pids):
        batches.append(list(pids))
        return real(pids)

    monkeypatch.setattr(runs.liveness, "probe_pids", counting)
    return batches


def test_a_standing_log_answers_a_second_poll_with_the_row_it_answered_the_first(tmp_path, monkeypatch):
    """The poll's whole reason for existing: a record that did not move is not read again.

    Two rows, one settled and one working, polled twice with nothing written between. The second answer
    is the first one row for row, and it costs no reading of either log — which is the weight the tree's
    half-second poll was spending on records that had not changed since it last read them.
    """
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00"), userMessage("make the thing"), ended())
    write_log(str(root / "r20261101-081000-bbbbbb"),
              started(WORKSPACE, "2026-11-01T08:10:00+00:00", pid=os.getpid()))
    poll = runs.Poll(str(root))
    first = poll.tree()
    readings = no_readings(monkeypatch)
    assert poll.tree() == first
    assert readings() == {}, "a poll over two standing logs reads neither of them"


def test_a_standing_log_behind_an_orphan_re_asks_the_verdict_and_not_the_reading(tmp_path, monkeypatch):
    """The one fact a standing log still owes: an orphan stays an orphan without its log being read.

    The log of a process that is gone, polled twice. The row is the dead row both times, the verdict is
    asked again on the second poll — it is the only thing asked — and the record itself is not read,
    because nothing in it moved and the ending of the verdict question is the machine's, not the log's.
    """
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=ran.pid), message("one"))
    poll = runs.Poll(str(root))
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "dead"
    readings = no_readings(monkeypatch)
    batches = asked_verdicts(monkeypatch)
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "dead"
    assert readings() == {}, "the dead row stands from the standing log; the reading is not owed twice"
    assert batches == [[ran.pid]], "the number the answer was stood on, asked again and once only"


def test_one_poll_of_many_unfinished_rows_is_one_look_at_the_machine(tmp_path, monkeypatch):
    """Dead numbers settle out of one process list, not one list per number.

    Three orphaned rows, polled twice. The first poll reads three records and asks about each on its own;
    the second asks nothing of the record and hands the machine the three numbers as one batch — the
    shape that keeps a tree of a few hundred folders, thirty of them unfinished, costing one look at the
    process table rather than thirty.
    """
    orphans = [subprocess.Popen([sys.executable, "-c", "pass"]) for _ in range(3)]
    for ran in orphans:
        ran.wait()
    root = tmp_path / "runs"
    for at, ran in enumerate(orphans):
        write_log(str(root / f"r20261101-080{at}00-aaaaaa"),
                  started(WORKSPACE, f"2026-11-01T08:0{at}:00+00:00", pid=ran.pid), message("one"))
    poll = runs.Poll(str(root))
    first = poll.tree()
    batches = asked_verdicts(monkeypatch)
    assert poll.tree() == first
    assert batches == [[ran.pid for ran in orphans]], "one batch, three numbers, one look at the machine"


def test_a_log_that_grew_is_read_fresh_by_the_next_poll(tmp_path):
    """The run that works is the log that moves, and a moved log is read as it always was: the row a poll
    answers with is the row the record now says, not the row the poll happened to remember.
    """
    root = tmp_path / "runs"
    folder = root / "r20261101-080000-aaaaaa"
    write_log(str(folder), started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=os.getpid()))
    poll = runs.Poll(str(root))
    assert "task" not in poll.tree()["workspaces"][0]["runs"][0]
    with open(folder / runs.LOG_NAME, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(userMessage("make the thing")) + "\n")
    assert poll.tree()["workspaces"][0]["runs"][0]["task"] == "make the thing"


def test_a_folder_that_appeared_stands_in(tmp_path):
    """A run started between two polls is in the second one: the memory holds no list of what exists —
    the listing of the folders is the record's own, and it was never the cost.
    """
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00"), ended())
    poll = runs.Poll(str(root))
    assert [row["id"] for row in poll.tree()["workspaces"][0]["runs"]] == ["r20261101-080000-aaaaaa"]
    write_log(str(root / "r20261101-081000-bbbbbb"),
              started(WORKSPACE, "2026-11-01T08:10:00+00:00"), ended())
    assert [row["id"] for row in poll.tree()["workspaces"][0]["runs"]] == [
        "r20261101-081000-bbbbbb", "r20261101-080000-aaaaaa"]


def test_a_folder_that_vanished_stands_out_and_takes_its_row_with_it(tmp_path):
    """A run deleted between two polls is gone from the second one, and its page goes with it: the memory
    is rebuilt from every walk, so a row cannot outlive the folder it was read from.
    """
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00"), ended())
    write_log(str(root / "r20261101-081000-bbbbbb"),
              started(WORKSPACE, "2026-11-01T08:10:00+00:00"), ended())
    poll = runs.Poll(str(root))
    assert len(poll.tree()["workspaces"][0]["runs"]) == 2
    shutil.rmtree(str(root / "r20261101-081000-bbbbbb"))
    assert [row["id"] for row in poll.tree()["workspaces"][0]["runs"]] == ["r20261101-080000-aaaaaa"]
    assert list(poll.pages) == ["r20261101-080000-aaaaaa"], "no page is kept for a run that is not there"


def test_a_verdict_that_moves_under_a_standing_log_is_read_rather_than_answered_from_memory(
        tmp_path, monkeypatch):
    """A killed run does not grow its log: the log stands, the verdict moves, and the row moves with it.

    The re-ask is what sees the death, and seeing it is not the same as answering from it — a moved
    verdict is a moved claim about which objective is the newest, and that is owed the walk back through
    the log. So the poll that catches the death reads, once; the poll after it stands the dead row out of
    memory, the verdict re-asked and the record left where it stands.
    """
    ran = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=ran.pid), message("working"))
    poll = runs.Poll(str(root))
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "live"
    ran.kill()
    ran.wait()
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "dead"
    readings = no_readings(monkeypatch)
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "dead"
    assert readings() == {}, "the death settled: the standing log answers with it, unread"


def held_process_table(monkeypatch, live):
    """The machine's answer read off a process table the test holds: every number in `live` is a process,
    and every number outside it is not.

    The seam the module's own docstring names for a reader that wants the answer rather than the machine:
    the verdict is read off the process table, so a test that wants a dead run's number to be *reborn*
    into another process takes the table over rather than hunting the box's number space for a rebirth it
    cannot order. `live` is a set the caller keeps holding, so a test stands the rebirth by adding the
    number between two polls and takes it back by removing it.
    """
    def answered(pids):
        return {pid: (liveness.LIVE if pid in live else liveness.DEAD) for pid in pids}

    monkeypatch.setattr(runs.liveness, "probe_pids", answered)
    return live


def test_a_number_reborn_under_a_dead_verdict_keeps_the_rows_dead_verdict(tmp_path, monkeypatch):
    """The rebirth, stood at the seam the answer is read from: a live answer on a dead verdict's number,
    over a record that has not said a word since.

    This is the case the number space will not hand over on demand — a dead run's number given back to
    another process — so it is stood where the module stands its own answer: the process table, held. The
    re-ask answers live and the row keeps `dead`, because the only witness the flip has beside it is a log
    that has been silent since the verdict was stood; and the row carries the number it happened to, which
    is the reason a reader is owed for a row that answers dead while its number answers live.
    """
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=ran.pid), message("one"))
    live = held_process_table(monkeypatch, set())
    poll = runs.Poll(str(root))
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "dead", "the verdict the silence stands"
    live.add(ran.pid)
    readings = no_readings(monkeypatch)
    row = poll.tree()["workspaces"][0]["runs"][0]
    assert row["live"] == "dead", "a live answer on the number a dead verdict stood on is not a resurrection"
    assert row["reborn"] == ran.pid, "and the row carries the number rebirthed beside the verdict"
    assert readings() == {}, "the flip is settled out of the asking: the record is not read again"
    assert poll.rebirthed("r20261101-080000-aaaaaa"), "the fact the stop is owed before it ends one"


def test_the_rebirths_fact_stands_and_leaves_with_the_flip(tmp_path, monkeypatch):
    """The number's silence returning is the fact leaving: the row is owed a reason, not a history.

    The key answers *why this row stands dead while its number answers live*, so it rides exactly while
    that is what the machine says — and once the holder of the number is gone, the dead row needs no
    explaining and the row answers as the plain orphan it always was.
    """
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    root = tmp_path / "runs"
    write_log(str(root / "r20261101-080000-aaaaaa"),
              started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=ran.pid), message("one"))
    live = held_process_table(monkeypatch, set())
    poll = runs.Poll(str(root))
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "dead"
    live.add(ran.pid)
    assert "reborn" in poll.tree()["workspaces"][0]["runs"][0]
    live.discard(ran.pid)
    row = poll.tree()["workspaces"][0]["runs"][0]
    assert row["live"] == "dead" and "reborn" not in row
    assert not poll.rebirthed("r20261101-080000-aaaaaa"), "nothing answers under the name; nothing to refuse"


def test_a_new_line_standing_under_a_new_number_is_the_working_row_whatever_the_old_number_answers(
        tmp_path, monkeypatch):
    """A relaunch is a new line with a new number, and the old number's rebirth says nothing about it.

    The protected case, stood beside the one it must not be mistaken for: the record grows the objective a
    word started, that objective answers for itself, and the row is the working row — the rebirth's fact
    gone with the line that ended the record's silence, and the asking after it standing the working row
    from a record that no longer owes one. This is the reading the plan leaves exactly where it stood: a
    live answer on the number a moving record stamps *is* the run coming back.
    """
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    root = tmp_path / "runs"
    folder = root / "r20261101-080000-aaaaaa"
    write_log(str(folder), started(WORKSPACE, "2026-11-01T08:00:00+00:00", pid=ran.pid), message("one"))
    live = held_process_table(monkeypatch, set())
    poll = runs.Poll(str(root))
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "dead"
    live.add(ran.pid)
    assert "reborn" in poll.tree()["workspaces"][0]["runs"][0]
    live.add(os.getpid())                                    # the relaunched objective's own process works
    with open(folder / runs.LOG_NAME, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(started(WORKSPACE, "2026-11-01T09:00:00+00:00",
                                        pid=os.getpid())) + "\n")
        handle.write(json.dumps(message("two")) + "\n")
    row = poll.tree()["workspaces"][0]["runs"][0]
    assert row["live"] == "live", "the record moved, and what it moved under answers: the working row"
    assert "reborn" not in row, "and the old number's rebirth says nothing about a run that wrote again"
    assert poll.tree()["workspaces"][0]["runs"][0]["live"] == "live"
    live.discard(ran.pid)                       # the stranger under the old number goes away, too
    again = poll.tree()["workspaces"][0]["runs"][0]
    assert again["live"] == "live", "and the row goes on working off the number its newest line stamps"
    assert not poll.rebirthed("r20261101-080000-aaaaaa"), "a working row has no dead verdict to keep"


def test_the_reason_is_the_ones_own_word(runs_root):
    beta = runs.tree(runs_root)["workspaces"][1]
    assert (beta["runs"][0]["status"], beta["runs"][0]["reason"]) == ("ended", "stopped")


def test_a_folder_is_a_run_only_when_it_holds_a_log(tmp_path):
    root = tmp_path / "runs"
    (root / "notes" / "deep").mkdir(parents=True)
    (root / "last.txt").write_text("r20261101-080000-aaaaaa", encoding="utf-8")
    write_log(str(root / "r20261101-080000-aaaaaa"), started(WORKSPACE, "2026-11-01T08:00:00+00:00"))
    assert runs.run_dirs(str(root)) == ["r20261101-080000-aaaaaa"]
    assert len(runs.tree(str(root))["workspaces"]) == 1


def test_a_log_that_never_said_where_it_stood_is_not_filed_under_a_guess(tmp_path):
    root = tmp_path / "runs"
    write_log(str(root / "old"), {"id": "000000-started", "kind": "started", "issuer": "core",
                                  "ts": "2026-10-24T02:19:45+00:00", "model": "m", "root": "runs/old",
                                  "run_id": "old"})
    assert runs.tree(str(root)) == {"workspaces": []}


def test_a_root_that_is_not_there_has_no_runs(tmp_path):
    assert runs.tree(str(tmp_path / "nothing")) == {"workspaces": []}
    assert runs.run_dirs(str(tmp_path / "nothing")) == []


def test_a_log_still_writing_its_first_line_is_read_later_rather_than_raised(tmp_path):
    root = tmp_path / "runs"
    folder = root / "r20261101-080000-aaaaaa"
    folder.mkdir(parents=True)
    half = json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00"))[:40]
    (folder / runs.LOG_NAME).write_text(half, encoding="utf-8")
    assert runs.tree(str(root)) == {"workspaces": []}


def test_the_ending_is_found_at_the_tail_however_long_the_log_is(tmp_path):
    root = tmp_path / "runs"
    folder = root / "r20261101-080000-aaaaaa"
    body = json.dumps(message("x" * (300 * 1024)))          # a transcript longer than the tail window
    os.makedirs(folder)
    with open(os.path.join(str(folder), runs.LOG_NAME), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00")) + "\n")
        handle.write(body + "\n")
        handle.write(json.dumps(ended("complete")) + "\n")
    row = runs.tree(str(root))["workspaces"][0]["runs"][0]
    assert (row["status"], row["reason"]) == ("ended", "complete")


def test_a_minted_id_is_a_utc_stamp_and_six_hex_digits():
    assert re.fullmatch(r"r\d{8}-\d{6}-[0-9a-f]{6}", runs.mint_run_id())


def test_a_name_already_taken_is_drawn_again(tmp_path, monkeypatch):
    taken = "r20261101-080000-aaaaaa"
    (tmp_path / taken).mkdir()
    drawn = [taken, "r20261101-080001-bbbbbb"]
    monkeypatch.setattr(runs, "mint_run_id", lambda: drawn.pop(0))
    path = runs.fresh_run_dir(str(tmp_path))
    assert os.path.basename(path) == "r20261101-080001-bbbbbb"
    assert os.path.normcase(os.path.dirname(path)) == os.path.normcase(os.path.abspath(str(tmp_path)))


# --- streaming ------------------------------------------------------------------------

def test_the_stream_yields_the_log_and_stops_after_the_ending(tmp_path):
    log = tmp_path / runs.LOG_NAME
    with open(log, "w", encoding="utf-8") as handle:
        for step in (started(WORKSPACE, "2026-11-01T08:00:00+00:00"), message("one"), ended()):
            handle.write(json.dumps(step) + "\n")
    got = list(runs.stream_lines(str(log), poll=0.01))
    assert [json.loads(line)["kind"] for line in got] == ["started", "message", "ended"]


def test_the_stream_carries_an_ending_it_grew_past_and_follows_the_next_objective(tmp_path):
    """A log that holds a second objective holds the first one's ending in the middle of it.

    The ending that stops a reader is the one the log ends on: an `ended` line with whole lines under
    it is one objective closed and another opened, and a reader that stopped there would hand the page
    half of a record it was asked to follow to the end.
    """
    log = tmp_path / runs.LOG_NAME
    second = started(WORKSPACE, "2026-11-01T09:00:00+00:00")
    with open(log, "w", encoding="utf-8") as handle:
        for step in (started(WORKSPACE, "2026-11-01T08:00:00+00:00"), message("one"), ended(),
                     second, message("two")):
            handle.write(json.dumps(step) + "\n")
    stream = runs.stream_lines(str(log), poll=0.01)
    try:
        arrived = [json.loads(next(stream))["kind"] for _ in range(5)]
        assert arrived == ["started", "message", "ended", "started", "message"]
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(ended()) + "\n")
        assert json.loads(next(stream))["kind"] == "ended"
        with pytest.raises(StopIteration):
            next(stream)
    finally:
        stream.close()


def test_the_stream_hands_back_the_line_exactly_as_the_log_holds_it(tmp_path):
    line = json.dumps(message("raw"))
    (tmp_path / runs.LOG_NAME).write_text(line + "\n" + json.dumps(ended()) + "\n", encoding="utf-8")
    lines = runs.stream_lines(str(tmp_path / runs.LOG_NAME), poll=0.01)
    assert next(lines) == line.encode("utf-8")


def test_the_stream_follows_a_log_that_grows(tmp_path):
    log = tmp_path / runs.LOG_NAME
    log.write_text(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00")) + "\n", encoding="utf-8")
    stream = runs.stream_lines(str(log), poll=0.01)
    try:
        assert json.loads(next(stream))["kind"] == "started"
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(message("appended")) + "\n")
        assert json.loads(next(stream))["text"] == "appended"
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(ended()) + "\n")
        assert json.loads(next(stream))["kind"] == "ended"
        with pytest.raises(StopIteration):
            next(stream)
    finally:
        stream.close()


def test_the_stream_carries_the_console_lines_a_run_grew_after_its_ending(tmp_path):
    """A switch spoken at a resting run stands under the ending, and it is the point of the read.

    The operator's channel writes its `notice` after the line that closed the objective, so a reader
    that turned back the moment it saw that ending would hand the page the record with the console's word
    still in the file — the one line the operator asked the stream for. The stop is the ending *with
    nothing but control under it*, and the control arrives before it.
    """
    log = tmp_path / runs.LOG_NAME
    with open(log, "w", encoding="utf-8") as handle:
        for step in (started(WORKSPACE, "2026-11-01T08:00:00+00:00"), message("one"), ended(),
                     control("think: low (was xhigh)"),
                     control("model: flash-next @ 127.0.0.1:8080 in force")):
            handle.write(json.dumps(step) + "\n")
    got = list(runs.stream_lines(str(log), poll=0.01))
    assert [json.loads(line)["kind"] for line in got] == [
        "started", "message", "ended", "notice", "notice"]
    assert [json.loads(line)["text"] for line in got[3:]] == [
        "think: low (was xhigh)", "model: flash-next @ 127.0.0.1:8080 in force"]


def test_a_console_line_at_the_tail_does_not_keep_the_stream_following(tmp_path):
    """The control lines are stepped over on the way to the stop, not past it.

    A switch spoken at a run that had settled is not an objective that opened, so the tail it leaves is
    the end of the record just as much as an ending is: the reader hands the two lines over and closes,
    rather than standing and polling a log that has said its last thing.
    """
    log = tmp_path / runs.LOG_NAME
    log.write_text(json.dumps(control("think: low (was xhigh)")) + "\n", encoding="utf-8")
    stream = runs.stream_lines(str(log), poll=0.01)
    try:
        assert json.loads(next(stream))["text"] == "think: low (was xhigh)"
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00")) + "\n")
        assert json.loads(next(stream))["kind"] == "started"
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(ended()) + "\n")
            handle.write(json.dumps(control("model: deep @ 127.0.0.1:8080 in force")) + "\n")
        assert json.loads(next(stream))["kind"] == "ended"
        assert json.loads(next(stream))["text"] == "model: deep @ 127.0.0.1:8080 in force"
        with pytest.raises(StopIteration):
            next(stream)
    finally:
        stream.close()


def test_a_line_written_in_pieces_arrives_as_one_line(tmp_path):
    log = tmp_path / runs.LOG_NAME
    log.write_text(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00")) + "\n", encoding="utf-8")
    whole = json.dumps(message("written in two goes"))
    stream = runs.stream_lines(str(log), poll=0.01)
    try:
        assert json.loads(next(stream))["kind"] == "started"
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(whole[:12])
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(whole[12:] + "\n")
        assert json.loads(next(stream))["text"] == "written in two goes"
    finally:
        stream.close()


def test_a_log_that_goes_away_ends_the_stream_rather_than_polling_forever(tmp_path):
    log = tmp_path / runs.LOG_NAME
    log.write_text(json.dumps(started(WORKSPACE, "2026-11-01T08:00:00+00:00")) + "\n", encoding="utf-8")
    stream = runs.stream_lines(str(log), poll=0.01)
    try:
        assert json.loads(next(stream))["kind"] == "started"
        os.remove(str(log))
        with pytest.raises(StopIteration):
            next(stream)
    finally:
        stream.close()


# --- the trace: the second tail ------------------------------------------------------------------------

def fragment(text, ts="2026-11-01T08:00:01+00:00", call=None) -> str:
    """One trace line, in the shape SAH's `--live` writes it: keys sorted, the tool's call named if any."""
    line = {"kind": "delta", "text": text, "ts": ts}
    if call:
        line["call"] = call
    return json.dumps(line, sort_keys=True)


def test_the_trace_gives_the_fragments_that_arrived_since_the_last_look_in_order(tmp_path):
    trace = tmp_path / runs.LIVE_NAME
    trace.write_text(fragment("one") + "\n" + fragment("two") + "\n", encoding="utf-8")
    stream = runs.stream_live(str(trace), poll=0.01)
    try:
        assert [json.loads(next(stream))["text"] for _ in range(2)] == ["one", "two"]
        with open(trace, "a", encoding="utf-8") as handle:
            handle.write(fragment("three") + "\n")
        assert json.loads(next(stream))["text"] == "three"
        first, offset = runs.live_look(str(trace))
        assert [json.loads(line)["text"] for line in first] == ["one", "two", "three"]
        assert runs.live_look(str(trace), offset) == ([], offset), "the offset is the end of the file"
    finally:
        stream.close()


def test_the_trace_is_read_from_its_head_on_the_look_that_finds_it(tmp_path):
    """A file that appears partway into the following is read whole: it was created at the first fragment.

    The absence of the file is not a decision the reader gets to make once — a run started without
    `--live` never grows one, and a run started with it grows it whenever the first word arrives. Both
    cases are the same look, and the look that finds the file owes the head of it. The generator passing
    its silent looks at the absent path and then yielding the head of the file is also the proof that an
    absent file raises nothing: the looks it took while nothing was there are the ones that got here.
    """
    trace = tmp_path / runs.LIVE_NAME
    assert runs.live_look(str(tmp_path / "no-such-folder" / runs.LIVE_NAME)) == ([], 0)
    stream = runs.stream_live(str(trace), poll=0.01)
    try:
        assert runs.live_look(str(trace)) == ([], 0), "no file, no lines, and the offset has nowhere to be"
        trace.write_text(fragment("first") + "\n" + fragment("second") + "\n", encoding="utf-8")
        assert [json.loads(next(stream))["text"] for _ in range(2)] == ["first", "second"]
    finally:
        stream.close()


def test_a_trace_line_written_in_pieces_arrives_as_one_line(tmp_path):
    """Half a fragment is a fragment still arriving, and the pane is never handed half of one."""
    trace = tmp_path / runs.LIVE_NAME
    whole = fragment("written in two goes")
    stream = runs.stream_live(str(trace), poll=0.01)
    try:
        with open(trace, "a", encoding="utf-8") as handle:
            handle.write(whole[:14])
        with open(trace, "a", encoding="utf-8") as handle:
            handle.write(whole[14:] + "\n")
        assert json.loads(next(stream))["text"] == "written in two goes"
    finally:
        stream.close()


def test_a_trace_line_keeps_the_carriage_return_the_log_line_keeps(tmp_path):
    """The same bytes discipline on both files: `\\r\\n` on Windows, and `\\r` is never part of a line."""
    trace = tmp_path / runs.LIVE_NAME
    trace.write_bytes(fragment("crlf").encode("utf-8") + b"\r\n" + fragment("next").encode("utf-8") + b"\n")
    lines, offset = runs.live_look(str(trace))
    assert [json.loads(line)["text"] for line in lines] == ["crlf", "next"]
    assert b"\r" not in lines[0]
    assert runs.live_look(str(trace), offset) == ([], offset), "read to its end, the file has nothing left"


# --- the cut: which step the conversation can still be returned to -------------------------------------

def line(seq, kind, **fields):
    """One step, carrying the id its place in the file would have minted: the cut names those digits."""
    return {"id": f"{seq:06d}-{kind}", "kind": kind, "issuer": "core",
            "ts": "2026-11-02T08:00:00+00:00", **fields}


def log_of(tmp_path, *steps) -> str:
    """A log of exactly these steps, and the path a cut is resolved against."""
    path = tmp_path / runs.LOG_NAME
    path.write_text("".join(json.dumps(step) + "\n" for step in steps), encoding="utf-8")
    return str(path)


def once_cut(tmp_path) -> str:
    """A run cut once already: steps 3 and 4 are in the file and out of the conversation in force."""
    return log_of(tmp_path, line(0, "started", cwd=WORKSPACE),
                  line(1, "message", role="user", text="the objective worth keeping"),
                  line(2, "message", role="assistant", text="the answer it got"),
                  line(3, "message", role="user", text="the word that was walked away from"),
                  line(4, "ended", reason="complete"),
                  line(5, "cut", to="000001-message"),
                  line(6, "started", cwd=WORKSPACE),
                  line(7, "message", role="user", text="the corrected objective"),
                  line(8, "ended", reason="complete"))


def test_a_step_the_conversation_holds_is_no_refusal(tmp_path):
    """The answer the route wants is the empty one, and it is the same for either end of the lineage."""
    log = once_cut(tmp_path)
    assert runs.cut_refusal(log, 1) == "", "the step the last cut aimed at is still a step to return to"
    assert runs.cut_refusal(log, 7) == "", "and so is a step that lineage only the cut made"
    assert runs.cut_refusal(log, "000000") == "", "the digits arrive as the id's digits, not as an int"


def test_a_step_the_log_never_held_is_named_beside_the_logs_last_step(tmp_path):
    sentence = runs.cut_refusal(once_cut(tmp_path), 99)
    assert "99" in sentence and "000008-ended" in sentence, sentence
    assert "detach" not in sentence, "nothing was detached by this — the number names no step at all"


def test_a_step_a_cut_detached_is_refused_as_firmly_and_says_so(tmp_path):
    """In the file, not in the conversation: cutting to it would rebuild a tail this run already shed."""
    sentence = runs.cut_refusal(once_cut(tmp_path), 3)
    assert "3" in sentence and "detach" in sentence.lower(), sentence
    assert "000008-ended" in sentence, "and the log's last step is named, as always"


def test_a_second_cut_may_aim_at_a_step_the_first_one_made(tmp_path):
    """The projection composes: each cut applies to the conversation the one before it left.

    A cut is walked in file order and truncates the list it has built, so a later cut may aim at a step of
    a lineage an earlier cut created and a detached step never re-enters — it is off the list before the
    next cut runs. This log holds two objectives' worth of steps between two cuts and speaks only the
    prefix each cut left.
    """
    log = log_of(tmp_path, line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="one"),
                 line(2, "message", role="user", text="two"),
                 line(3, "cut", to="000001-message"),
                 line(4, "message", role="user", text="three"),
                 line(5, "cut", to="000004-message"),
                 line(6, "message", role="user", text="four"))
    assert runs.cut_refusal(log, 4) == "", "the step the second cut aimed at is of the lineage the first made"
    assert runs.cut_refusal(log, 6) == "", "and the newest step is the conversation's own tail"
    assert "detach" in runs.cut_refusal(log, 2).lower(), "step 2 is the first cut's shed tail"


def test_a_number_that_names_no_step_shape_is_refused_as_one(tmp_path):
    for value in ("the-first-one", "", "  ", "5x", None, 1.5):
        sentence = runs.cut_refusal(once_cut(tmp_path), value)
        assert sentence and "step's number" in sentence, f"{value!r} answered {sentence!r}"


def test_the_digits_are_the_steps_sequence_however_the_page_handed_them_over(tmp_path):
    """The id the page read is `000001-message`; the number it sends is that string's digits, and every
    spelling of the same number resolves to the same step — the door parses the digits, not the text."""
    log = once_cut(tmp_path)
    for value in (1, "1", "000001", " 1 "):
        assert runs.cut_refusal(log, value) == "", repr(value)


def test_a_log_with_no_steps_has_nothing_to_return_to(tmp_path):
    empty = log_of(tmp_path)
    assert "no steps" in runs.cut_refusal(empty, 1)
    assert "no steps" in runs.cut_refusal(str(tmp_path / "no-log-here.jsonl"), 1), "gone is the same answer"


def test_a_cut_that_names_no_step_of_its_own_conversation_refuses_the_projection(tmp_path):
    """A cut whose target is not in the conversation is corruption, not a gap to skip.

    The projection cannot be answered honestly against such a file, and a route that launched a relaunch
    and let SAH's door sort it out would have stopped a live session to ask the question.
    """
    log = log_of(tmp_path, line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="one"),
                 line(2, "cut", to="000007-message"),
                 line(3, "message", role="user", text="two"))
    sentence = runs.cut_refusal(log, 1)
    assert "000002-cut" in sentence and "000007-message" in sentence, sentence


def test_a_line_still_arriving_does_not_shorten_the_conversation(tmp_path):
    """The tolerance the head scan has, this reader has: half a line is a line still being written."""
    log = once_cut(tmp_path)
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(line(9, "message", role="assistant", text="mid-append"))[:20])
    assert runs.cut_refusal(log, 7) == "", "the projection is as long as the whole lines it was written"
    assert runs.cut_refusal(log, 3) != "", "and the detached answer is undisturbed by a torn tail"


# --- the fork's record and the branch point it settles at ----------------------------------------------

def test_a_forked_run_wears_the_fork_it_was_carried_in_on(tmp_path):
    """The row's fact is read from the log's own `fork` record and nothing else: the source's id and the
    digits of the step the carried prefix ends at. A log whose opening `started` names another run is the
    seam, and the record sits at it."""
    folder = str(tmp_path / "r20261101-100000-rfrkkk")
    write_log(folder,
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T09:50:00+00:00",
                      run_id="r20261101-090000-srcaaa"),
              userMessage("the carried word"),
              message("the carried answer"),
              {"id": "000003-fork", "kind": "fork", "source_run": "r20261101-090000-srcaaa",
               "source_step": "000002-message"},
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T09:55:00+00:00",
                      run_id="r20261101-100000-rfrkkk"),
              userMessage("the fork's own word"),
              message("the fork's own answer"),
              ended())
    _, row = runs.describe_run(folder)
    assert row["fork"] == {"source": "r20261101-090000-srcaaa", "step": "2"}
    assert row["status"] == "ended"


def test_a_run_that_began_as_its_own_run_carries_no_fork_key(tmp_path):
    """The ordinary case owes no key: the head names this run, so there is no seam before it, and the
    absence is read the way the absence of `live` is read — as the ordinary case, not as a missing thing."""
    folder = str(tmp_path / "r20261101-080000-aaaaaa")
    write_log(folder,
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T08:00:00+00:00",
                      run_id="r20261101-080000-aaaaaa"),
              userMessage("the word"), message("the answer"), ended())
    _, row = runs.describe_run(folder)
    assert "fork" not in row


def test_a_fork_of_a_fork_wears_the_newer_forks_record(tmp_path):
    """The carried prefix carries the elder's record too, so the row's fact is the last one the seam
    walk passes: the fact about this run, not the fact about the run it was carried in from."""
    folder = str(tmp_path / "r20261101-120000-ffffcc")
    write_log(folder,
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T09:00:00+00:00",
                      run_id="r20261101-080000-srceee"),
              line(1, "message", role="user", text="one"),
              {"id": "000002-fork", "kind": "fork", "source_run": "r20261101-080000-srceee",
               "source_step": "000001-message"},
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T09:30:00+00:00",
                      run_id="r20261101-100000-ffffbb"),
              line(3, "message", role="user", text="two"),
              {"id": "000004-fork", "kind": "fork", "source_run": "r20261101-100000-ffffbb",
               "source_step": "000003-message"},
              started(os.path.join(WORKSPACE, "alpha"), "2026-11-01T09:45:00+00:00",
                      run_id="r20261101-120000-ffffcc"),
              line(5, "message", role="user", text="three"),
              ended())
    _, row = runs.describe_run(folder)
    assert row["fork"] == {"source": "r20261101-100000-ffffbb", "step": "3"}


def test_fork_branch_defaults_to_the_conversations_last_step(tmp_path):
    """With no step named the whole conversation is carried, and a whole conversation has an end that can
    be named just as well as a middle: the branch is where it stands."""
    log = log_of(tmp_path,
                 line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="first"),
                 line(2, "message", role="assistant", text="one"),
                 line(3, "message", role="user", text="second"),
                 line(4, "message", role="assistant", text="two"))
    branch, refused = runs.fork_branch(log, "")
    assert refused == "" and branch == "4"


def test_fork_branch_names_the_step_the_page_named(tmp_path):
    log = log_of(tmp_path,
                 line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="first"),
                 line(2, "message", role="assistant", text="one"),
                 line(3, "message", role="user", text="second"))
    assert runs.fork_branch(log, 2) == ("2", "")
    assert runs.fork_branch(log, "3") == ("3", "")


def test_fork_branch_refuses_a_step_the_log_does_not_hold(tmp_path):
    log = log_of(tmp_path,
                 line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="one"),
                 line(2, "message", role="assistant", text="two"))
    branch, refused = runs.fork_branch(log, 9)
    assert branch == "" and "does not hold" in refused and "000002" in refused


def test_fork_branch_refuses_a_step_a_cut_detached(tmp_path):
    """In the file, not in the conversation: forking at it would carry a tail the conversation gave up."""
    log = log_of(tmp_path,
                 line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="one"),
                 line(2, "message", role="assistant", text="two"),
                 line(3, "message", role="user", text="three"),
                 line(4, "message", role="assistant", text="four"),
                 line(5, "cut", to="000002-message"),
                 line(6, "message", role="user", text="five"))
    branch, refused = runs.fork_branch(log, 4)
    assert branch == "" and "detach" in refused.lower()


def test_fork_branch_refuses_a_step_that_is_not_a_number(tmp_path):
    """A named step that is not a number refuses; the empty one is not a refusal, it is the whole
    conversation — the fork's default is where the conversation stands, not the cut's demand for a name."""
    log = log_of(tmp_path,
                 line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="one"))
    for value in ("the-first", "1x", 1.5):
        branch, refused = runs.fork_branch(log, value)
        assert branch == "" and "not one" in refused, f"{value!r} answered {refused!r}"
    assert runs.fork_branch(log, None) == ("1", "")
    assert runs.fork_branch(log, "") == ("1", "")


def test_fork_branch_refuses_a_log_with_no_steps(tmp_path):
    empty = log_of(tmp_path)
    branch, refused = runs.fork_branch(empty, "")
    assert branch == "" and "no steps" in refused


def test_fork_branch_refuses_a_prefix_that_ends_mid_exchange(tmp_path):
    """A carried prefix whose last call was never answered is not a place to branch: the server the branch
    is replayed to refuses it, and the fork's door has to say so before it launches rather than inside a
    child nobody is reading. The answer's prefix holds the same call answered, so it stands."""
    log = log_of(tmp_path,
                 line(0, "started", cwd=WORKSPACE),
                 line(1, "message", role="user", text="first"),
                 line(2, "call", name="bash"),
                 line(3, "result", refs="000002-call", text="the answer"),
                 line(4, "message", role="assistant", text="the reply"))
    branch, refused = runs.fork_branch(log, 2)
    assert branch == "" and "owed a result" in refused
    branch, refused = runs.fork_branch(log, 4)
    assert refused == "" and branch == "4"
