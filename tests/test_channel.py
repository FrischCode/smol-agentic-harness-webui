"""sahw.channel — the rule that places every arrival, and the two ways a word is placed.

The rule is a function of two facts, so it is tested as one: the record's ending and the machine's verdict,
forced into every combination they can arrive in, including the arrival the page cannot reach but a cut can
(a word that names the follow channel for a log a live process holds). `launch` is the seam the argv is
read through, so nothing here starts a SAH child; the one process the module is allowed to end is a child
of this battery, held by its handle, which is what makes the kill-first assertable against the process
table rather than against a sentence in a return value. The real verbs, against a real run folder and a
real SAH tree, are the end-to-end pass.
"""
import inspect
import json
import os
import subprocess
import sys

import pytest

from sahw import channel, liveness, runs, spawn

WORKSPACE = r"C:\work\alpha"        # the workspace the argv-builder tests name; no file is opened


class Child:
    """The handle `launch` hands back: a child that started. Nothing in it is kept by the caller."""

    pid = 4242


class Launches(list):
    """The launch seam's record: one `(argv, env, cwd)` per child the channel would have started.

    The seam can also be told to watch a pid. Every launch then records what the process table said about
    that pid *at the moment the new child would have started*, which is the only way to read the ordering
    the follow owes: the writer the log named is gone before the one that replaces it arrives.
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
    """The launch seam: every argv, environment and working directory the channel would have started."""
    calls = Launches()
    monkeypatch.setattr(spawn, "launch", calls.pretend)
    return calls


@pytest.fixture
def killed(monkeypatch):
    """The kill seam: every pid the channel ended, and the fact that nothing else ended one."""
    asked = []
    monkeypatch.setattr(liveness, "kill", lambda pid: asked.append(pid))
    return asked


@pytest.fixture
def gone():
    """A process that ran and was reaped, held by this handle so its pid stays answerably dead."""
    ran = subprocess.Popen([sys.executable, "-c", "pass"])
    ran.wait()
    return ran


@pytest.fixture
def sleeper():
    """A live process of this battery's own, put down here rather than left standing by a failed test."""
    alive = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    yield alive
    alive.kill()
    alive.wait()


@pytest.fixture
def folder(tmp_path):
    """A run folder beside a workspace that exists: a follow is launched *into* the workspace, and a
    server that names a folder which is not one refuses rather than starting a child that cannot run."""
    run_dir = tmp_path / "r20261101-080000-aaaaaa"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_dir.mkdir()
    return {"run_dir": str(run_dir), "workspace": str(workspace)}


def write_log(run_dir, *steps):
    with open(os.path.join(run_dir, runs.LOG_NAME), "w", encoding="utf-8") as handle:
        for step in steps:
            handle.write(json.dumps(step) + "\n")
    return run_dir


def started(workspace=WORKSPACE, ts="2026-11-01T08:00:00+00:00", **extra):
    grants = {"read": [workspace, r"C:\Work\SAH"], "write": [workspace], "exec": False,
              "unrestricted": False, "project_notes": True}
    return {"id": "000000-started", "kind": "started", "issuer": "core", "ts": ts, "cwd": workspace,
            "model": "flash-next", "run_id": "run", "root": "root", "grants": grants, **extra}


def message(text, ts="2026-11-01T08:30:00+00:00"):
    return {"id": "000005-message", "kind": "message", "issuer": "core", "ts": ts,
            "role": "assistant", "text": text}


def ended(reason="complete", ts="2026-11-01T09:00:00+00:00"):
    return {"id": "000009-ended", "kind": "ended", "issuer": "core", "ts": ts, "reason": reason,
            "exit_code": 0}


# --- the module's own vocabulary ---------------------------------------------------------------------

def test_the_rule_names_two_channels_and_holds_no_third():
    """The channels are the model's, and so is the absence: no session, no pipe, no held keyboard.

    A third channel would be a handle the server keeps to a process, which is the thing this model gave
    up: a run's process lives its objective's lifecycle, so the only two ways a word arrives are the
    queue the run reads at its next boundary and the relaunch that starts the process which reads it.
    """
    assert not hasattr(channel, "SESSION")
    assert (channel.STEER, channel.FOLLOW) == ("steer", "follow")
    for name in ("decide", "post_message"):
        assert "held" not in inspect.signature(getattr(channel, name)).parameters


# --- the rule, forced -------------------------------------------------------------------------------

def test_the_whole_table_one_assertion_per_case():
    """The two facts, every state they arrive in, and the channel each one places the word on.

    The record outranks the machine wherever it has something to say: an objective that wrote its ending
    is over, and the word continues it on the same log. Of the rows with no ending, `dead` alone is the
    follow — the orphan's log holds no writer — and `live` is the steer, because the run is mid-objective.
    """
    assert channel.decide(ended=True, verdict=liveness.LIVE) == channel.FOLLOW
    assert channel.decide(ended=True, verdict=liveness.DEAD) == channel.FOLLOW
    assert channel.decide(ended=True, verdict=liveness.UNKNOWN) == channel.FOLLOW
    assert channel.decide(ended=False, verdict=liveness.LIVE) == channel.STEER
    assert channel.decide(ended=False, verdict=liveness.DEAD) == channel.FOLLOW
    assert channel.decide(ended=False, verdict=liveness.UNKNOWN) == channel.STEER


def test_a_working_run_is_the_steer_channel_and_a_dead_one_is_the_follow_channel():
    assert channel.decide(ended=False, verdict=liveness.LIVE) == channel.STEER
    assert channel.decide(ended=False, verdict=liveness.DEAD) == channel.FOLLOW


def test_an_unanswerable_process_is_the_steer_channel_because_a_queue_is_never_lost():
    """`unknown` is not `dead`: a word queued waits for the next resume, and nothing is damaged.

    The follow channel is the only one that can put a second writer on a log, so it is offered to a
    run the machine named dead and to no other that has no ending to show.
    """
    assert channel.decide(ended=False, verdict=liveness.UNKNOWN) == channel.STEER


def test_the_one_refusal_is_a_follow_forced_onto_a_live_log():
    """The case the route cannot reach is still a case the rule owes a sentence to."""
    with pytest.raises(channel.ChannelError) as raised:
        channel.decide(ended=False, verdict=liveness.LIVE, wants=channel.FOLLOW)
    assert raised.value.status == 409
    assert raised.value.args[0] == channel.BUSY
    assert "the run is working" in channel.BUSY, "the sentence names the state and what to do instead"


def test_a_follow_asked_for_by_name_is_carried_wherever_the_rule_would_have_carried_it():
    """Naming the channel is refused only where naming it would be a second writer."""
    assert channel.decide(ended=True, verdict=liveness.LIVE, wants=channel.FOLLOW) == channel.FOLLOW
    assert channel.decide(ended=True, verdict=liveness.DEAD, wants=channel.FOLLOW) == channel.FOLLOW
    assert channel.decide(ended=False, verdict=liveness.DEAD, wants=channel.FOLLOW) == channel.FOLLOW
    with pytest.raises(channel.ChannelError):
        channel.decide(ended=False, verdict=liveness.LIVE, wants=channel.FOLLOW)


def test_a_named_follow_on_an_ended_run_is_the_follow_channel_however_the_probe_answers():
    """The cut's one demand on the rule: returning to a step rebuilds the conversation, and only a
    relaunch rebuilds a conversation — so the verdict about a process on its way out is nobody's business.
    """
    for verdict in (liveness.LIVE, liveness.DEAD, liveness.UNKNOWN):
        assert channel.decide(ended=True, verdict=verdict, wants=channel.FOLLOW) == channel.FOLLOW


# --- the two command lines ---------------------------------------------------------------------------

def test_the_steer_argv_is_the_verb_the_operator_would_type():
    argv = channel.send_argv(["python", "-m", "sah"], run_dir=r"C:\runs\r1", text="left of the turn")
    assert argv == ["python", "-m", "sah", "send", "--run-dir", r"C:\runs\r1",
                    "--from", "sahw", "steer", "left of the turn"]


def test_the_follow_argv_repasses_the_recorded_reach_and_resumes_the_same_folder():
    argv = channel.follow_argv(["python", "-m", "sah"], run_dir=r"C:\runs\r1", runs_root=r"C:\runs",
                               task="and then the second thing", max_turns=12, max_runtime=300,
                               think="high",
                               grants={"read": [WORKSPACE, r"C:\Work\SAH"], "write": [WORKSPACE]})
    assert argv[:6] == ["python", "-m", "sah", "run", "--run-dir", r"C:\runs\r1"]
    assert "--resume" in argv, "the conversation comes back from the run's own log"
    assert argv[argv.index("--grant") + 1] == WORKSPACE
    assert argv.count("--grant") == 2 and argv.count("--write") == 1
    assert argv[argv.index("--write") + 1] == WORKSPACE
    assert argv[argv.index("--max-turns") + 1] == "12"
    assert argv[argv.index("--max-runtime") + 1] == "300"
    assert argv[argv.index("--ask-timeout") + 1] == "inf", (
        "the face is the witness: an attended run, with no fuse on the question it may ask")
    assert "--live" in argv, (
        "and an attended run streams its words to the face that is attending: the same claim, in the "
        "same place of the command line, as the spawn's and the fork's")
    assert argv[argv.index("--live") + 1] == "--ask-timeout", "beside the fuse, where the flag was put"
    assert argv[argv.index("--think") + 1] == "high"
    assert argv[-2:] == ["--task", "and then the second thing"]
    assert argv[argv.index("--view") + 1] == "off", "the record is the report; nobody is watching"
    assert "-i" not in argv, "the followed objective is worked by a process that exits when it is done"


def test_the_follow_argv_names_no_level_it_was_not_given_and_no_reach_it_cannot_see():
    argv = channel.follow_argv(["sah"], run_dir="r", runs_root="rr", task="t", max_turns=1,
                               max_runtime=1)
    assert "--think" not in argv
    assert "--grant" not in argv and "--write" not in argv, "a record that named no reach invents none"


def test_the_follow_argv_carries_the_model_the_picker_stands_on_at_the_thinks_own_seam():
    """The seam a dial switched at a settled run comes true on: the objective after it, not the switch.

    A session that has ended has no process left for `/model` to have moved, so the picker's stand is a
    claim about the next launch — and this is that launch. It rides where `--think` rides, for the same
    reason and with the same silence when nothing is named.
    """
    argv = channel.follow_argv(["sah"], run_dir="r", runs_root="rr", task="t", max_turns=1,
                               max_runtime=1, think="low", model="deep")
    at = argv.index("--think")
    assert argv[at:at + 4] == ["--think", "low", "--model", "deep"], (
        "the two bounds side by side, in the order the composer's two controls stand")
    assert channel.follow_argv(["sah"], run_dir="r", runs_root="rr", task="t", max_turns=1,
                               max_runtime=1, model="") == channel.follow_argv(
        ["sah"], run_dir="r", runs_root="rr", task="t", max_turns=1, max_runtime=1), (
        "a picker standing on no model is the machine's own default, spelled silence")


# --- the cut: one argument of the follow's own --------------------------------------------------------

GRANTS = {"read": [WORKSPACE, r"C:\Work\SAH"], "write": [WORKSPACE]}

# The standing follow, written out rather than computed: the field is additive, and the only way to say so
# is to hold the whole command line the page gets when it sends no cut.
STANDING = ["python", "-m", "sah", "run", "--run-dir", r"C:\runs\r1", "--runs-root", r"C:\runs",
            "--view", "off", "--project-notes", "--resume",
            "--grant", WORKSPACE, "--grant", r"C:\Work\SAH", "--write", WORKSPACE,
            "--max-turns", "12", "--max-runtime", "300", "--live", "--ask-timeout", "inf",
            "--task", "and then the second thing"]


def follow(**extra):
    return channel.follow_argv(["python", "-m", "sah"], run_dir=r"C:\runs\r1", runs_root=r"C:\runs",
                               task="and then the second thing", max_turns=12, max_runtime=300,
                               grants=GRANTS, **extra)


def test_a_cut_replaces_the_bare_resume_with_the_step_it_names():
    argv = follow(cut="5")
    assert argv[argv.index("--resume") + 1] == "5", "the conversation returns to the step, as logged"
    assert argv[argv.index("--resume") + 2] == "--grant", "and the reach rides beside it, unmoved"
    assert argv[argv.index("--task") + 1] == "and then the second thing"
    assert argv.count("--grant") == 2 and argv.count("--write") == 1
    assert argv[-2:] == ["--task", "and then the second thing"]


def test_a_cut_that_was_not_named_leaves_the_follow_exactly_what_stood_before_it():
    """Byte for byte: the field is one argument, and a page that does not send it sends 05's command line.

    The empty string is the same answer as the argument's absence, because the route reads an absent field
    as empty rather than branching on `in body`.
    """
    assert follow() == STANDING
    assert follow(cut="") == STANDING
    assert follow(cut="5") != STANDING, "and the cut is what differs, one token after `--resume`"


def test_a_cut_on_an_orphaned_log_rides_the_standing_follow(folder, gone, launched, killed):
    """Nothing new is needed where the rule already answers follow: the step is simply carried."""
    write_log(folder["run_dir"], started(folder["workspace"], pid=gone.pid), message("one"))
    carried = channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "carry on from there",
                                   wants=channel.FOLLOW, cut="1")
    assert carried == channel.FOLLOW
    argv = launched[0][0]
    assert argv[argv.index("--resume") + 1] == "1"
    assert argv[argv.index("--task") + 1] == "carry on from there"
    assert killed == [], "a log nobody is writing owes no kill"


# --- carrying a word ---------------------------------------------------------------------------------

def test_a_finished_run_is_followed_up_on_its_own_folder_with_its_own_reach(folder, launched):
    write_log(folder["run_dir"], started(folder["workspace"]), message("one"), ended())
    carried = channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "the second objective")
    assert carried == channel.FOLLOW, "the channel is the whole answer: no handle travels with it"
    argv, env, cwd = launched[0]
    assert argv[0].endswith("python.exe") and argv[1:3] == ["-m", "sah"]
    assert argv[argv.index("--run-dir") + 1] == folder["run_dir"]
    assert "--resume" in argv
    assert argv[argv.index("run") + 1] == "--run-dir", "a followed objective is one-shot, as the first was"
    assert argv[argv.index("--task") + 1] == "the second objective"
    assert argv[argv.index("--grant") + 1] == folder["workspace"]
    assert argv[argv.index("--write") + 1] == folder["workspace"]
    assert "--think" not in argv, "no level named is the machine's own default, as at the start"
    assert env["PYTHONPATH"] == os.path.abspath(r"C:\Work\SAH")
    assert env["SAH_EXTENSION"] == " "
    assert cwd == folder["workspace"], "a followed objective stands where the run stood"


def test_a_working_run_is_steered_into_its_own_queue(folder, launched, killed):
    write_log(folder["run_dir"], started(folder["workspace"], pid=os.getpid()))
    carried = channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"],
                                   "a word, not an objective")
    assert carried == channel.STEER
    argv, env, cwd = launched[0]
    assert argv[argv.index("send") + 1] == "--run-dir", "the verb leads, as an operator types it"
    assert argv[argv.index("--run-dir") + 1] == folder["run_dir"]
    assert argv[argv.index("--from") + 1] == "sahw", "the record says who queued it"
    assert argv[argv.index("steer") + 1] == "a word, not an objective"
    assert "--resume" not in argv and "--task" not in argv, "a steer starts no objective of its own"
    assert env["PYTHONPATH"] == os.path.abspath(r"C:\Work\SAH")
    assert cwd == folder["run_dir"], "the queue sits beside the log the run is writing"
    assert killed == [], "a steer starts nothing and ends nothing"
    assert liveness.probe_pid(os.getpid()) == liveness.LIVE, "least of all the run that is working"


def test_a_steered_word_starts_no_process_at_all(folder, launched):
    """The queue is a file append: the one launch the seam recorded is the `send`, and nothing else."""
    write_log(folder["run_dir"], started(folder["workspace"], pid=os.getpid()))
    channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "queued")
    assert len(launched) == 1 and launched[0][0][3] == "send", "the verb is the fourth token, as typed"


def test_an_orphan_is_followed_up_rather_than_steered_into_a_queue_nobody_reads(folder, gone, launched):
    write_log(folder["run_dir"], started(folder["workspace"], pid=gone.pid), message("one"))
    carried = channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "carry on")
    assert carried == channel.FOLLOW
    argv = launched[0][0]
    assert "--resume" in argv and argv[argv.index("--task") + 1] == "carry on"


# --- the kill-first: the one second-writer guard ------------------------------------------------------

def test_a_follow_ends_the_process_the_log_names_before_it_relaunches(folder, launched, sleeper):
    """The whole guard, read off the process table at the moment the new writer would have started.

    The objective wrote its ending and the child that wrote it is still on its way out — the state a
    session used to be the excuse for refusing. The follow does not refuse it and does not race it: the
    pid the newest `started` line names is killed first, and by the time the launch is issued the machine
    calls that pid dead.
    """
    write_log(folder["run_dir"], started(folder["workspace"], pid=sleeper.pid), message("one"), ended())
    launched.watch = sleeper.pid
    carried = channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "and next")
    assert carried == channel.FOLLOW
    assert launched.seen == [liveness.DEAD], "the old writer was gone before the new one was started"
    assert liveness.probe_pid(sleeper.pid) == liveness.DEAD
    assert sleeper.wait(timeout=5) is not None, "and the handle agrees the process is off the table"


def test_the_ending_beats_the_probe_so_a_run_on_its_way_out_is_followed(folder, launched, sleeper):
    """The edge, as one line of state: `ended` written, the process still there, follow anyway."""
    write_log(folder["run_dir"], started(folder["workspace"], pid=sleeper.pid), message("one"), ended())
    assert channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "and next") == channel.FOLLOW


def test_the_kill_first_ends_the_newest_objectives_process_not_the_runs_first_one(folder, launched,
                                                                                 sleeper, gone):
    """A followed log holds one `started` line per objective; the newest is the process that holds it.

    The head line's pid is this battery's reaped child and the newest one is the sleeper, so only killing
    the newest spares a test from its own conclusion — which is the same fact that keeps a working run's
    row honest, and the reason the guard reads `latest_started` rather than the head.
    """
    write_log(folder["run_dir"], started(folder["workspace"], pid=gone.pid), message("one"), ended(),
              started(folder["workspace"], ts="2026-11-01T10:00:00+00:00", pid=sleeper.pid),
              message("two"), ended())
    launched.watch = sleeper.pid
    assert channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "third") == channel.FOLLOW
    assert launched.seen == [liveness.DEAD]


def test_the_kill_first_sends_no_signal_when_the_log_names_no_live_process(folder, launched, killed,
                                                                          gone):
    """A settled run's kill-first is the answer that nothing was live: no signal, and the launch goes on."""
    write_log(folder["run_dir"], started(folder["workspace"], pid=gone.pid), message("one"), ended())
    assert channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "next") == channel.FOLLOW
    assert killed == [] and len(launched) == 1


def test_the_kill_first_answers_whether_it_ended_anything(folder, killed, sleeper, gone):
    """The fact the stop route reads: a live process ended, or nothing there to end.

    The kill is the follow's own guard, and the stop route asks the same act to answer for itself, so the
    answer is the module's contract as much as the kill is.
    """
    write_log(folder["run_dir"], started(folder["workspace"], pid=gone.pid), message("one"))
    assert channel.kill_first(folder["run_dir"]) is False
    write_log(folder["run_dir"], started(folder["workspace"], pid=sleeper.pid),
              message("the objective it is working"))
    assert channel.kill_first(folder["run_dir"]) is True
    assert killed == [sleeper.pid]


# --- the refusals, which move nothing ----------------------------------------------------------------

def test_a_word_that_is_not_a_word_is_refused_before_anything_is_started(folder, launched, killed):
    write_log(folder["run_dir"], started(folder["workspace"]), ended())
    with pytest.raises(channel.ChannelError) as raised:
        channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "   ")
    assert raised.value.status == 400
    assert launched == [] and killed == []


def test_a_server_that_names_no_tree_cannot_run_the_verb(folder, launched, killed):
    write_log(folder["run_dir"], started(folder["workspace"]), ended())
    with pytest.raises(channel.ChannelError) as raised:
        channel.post_message(r"C:\runs", "", folder["run_dir"], "hello")
    assert raised.value.status == 503
    assert launched == [] and killed == []


def test_a_run_whose_workspace_is_gone_is_not_resumed_into_a_guess(folder, launched, killed, sleeper):
    """And the refusal is made before the guard: a run this server cannot continue keeps its process.

    The workspace named by the record is gone, so the follow has nowhere to stand — and the process still
    finishing the objective that record describes is left exactly where it was. A refusal that killed first
    would have destroyed the run it was refusing.
    """
    vanished = os.path.join(folder["workspace"], "cleaned-out")
    write_log(folder["run_dir"], started(vanished, pid=sleeper.pid), ended())
    with pytest.raises(channel.ChannelError) as raised:
        channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "continue")
    assert "not a folder" in raised.value.args[0]
    assert launched == [] and killed == []
    assert liveness.probe_pid(sleeper.pid) == liveness.LIVE, "the refused run keeps its own process"


def test_a_follow_on_a_working_run_is_the_second_writer_refusal(folder, launched, killed, sleeper):
    """The 409 the route cannot reach by accident, forced by a caller that insists.

    A working run is a log with a writer: the word that insists on becoming a new objective on it is
    refused, nothing is launched, and — the part the guard is about — nothing is killed either, because a
    refusal that ended the run it was refusing would be the corruption it exists to prevent.
    """
    write_log(folder["run_dir"], started(folder["workspace"], pid=sleeper.pid),
              message("the objective it is still working"))
    with pytest.raises(channel.ChannelError) as raised:
        channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "back to step one",
                             wants=channel.FOLLOW, cut="1")
    assert raised.value.status == 409
    assert launched == [] and killed == []
    assert liveness.probe_pid(sleeper.pid) == liveness.LIVE


# --- two writers at once -------------------------------------------------------------------------------

def test_the_reach_of_the_objective_the_run_stands_on_is_the_newest_one(folder, launched):
    """Two objectives, two records of reach: the newest is the one the next objective joins."""
    deeper = os.path.join(folder["workspace"], "deeper")
    os.mkdir(deeper)
    write_log(folder["run_dir"], started(folder["workspace"]), ended(),
              started(deeper, ts="2026-11-01T10:00:00+00:00"), ended())
    carried = channel.post_message(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], "third")
    assert carried == channel.FOLLOW
    argv, _, cwd = launched[0]
    reach = lambda flag: [argv[i + 1] for i, a in enumerate(argv) if a == flag]
    assert reach("--grant") == [deeper, r"C:\Work\SAH"], \
        "every root the newest record named, and no older one"
    assert reach("--write") == [deeper]
    assert cwd == deeper


# --- the compact's verb --------------------------------------------------------------------------------

def test_a_working_run_is_compacted_into_its_own_queue(folder, launched, killed):
    """The verb leads the way an operator types it, and a compact starts no objective of its own.

    The run decides at its boundary whether the compaction runs and whether a stop finds one in flight;
    what the seam owes is the block in the queue, the writer's claim beside it, and the answer that says
    which verb was carried.
    """
    write_log(folder["run_dir"], started(folder["workspace"], pid=os.getpid()))
    carried = channel.post_compact(r"C:\runs", r"C:\Work\SAH", folder["run_dir"])
    assert carried == "compact", "the answer is the verb carried, so the caller knows which act to read"
    argv, env, cwd = launched[0]
    assert argv[argv.index("send") + 1] == "--run-dir", "the verb leads, as an operator types it"
    assert argv[argv.index("--run-dir") + 1] == folder["run_dir"]
    assert argv[argv.index("--from") + 1] == "sahw", "the record says who queued it"
    assert argv[-1] == "compact", "and the verb it names is the act it says it queued"
    assert "--resume" not in argv and "--task" not in argv and "--grant" not in argv, \
        "a verb carries no text and starts no objective of its own"
    assert env["PYTHONPATH"] == os.path.abspath(r"C:\Work\SAH")
    assert cwd == folder["run_dir"], "the queue sits beside the log the run is writing"
    assert killed == [], "a verb starts nothing and ends nothing"
    assert liveness.probe_pid(os.getpid()) == liveness.LIVE, "least of all the run that is working"


def test_the_stop_is_the_same_verb_with_its_own_name(folder, launched):
    """One seam, two words: the stop names the stand-down, and the answer carries the name it sent."""
    write_log(folder["run_dir"], started(folder["workspace"], pid=os.getpid()))
    carried = channel.post_compact(r"C:\runs", r"C:\Work\SAH", folder["run_dir"], stop=True)
    assert carried == "compact-stop"
    argv, env, cwd = launched[0]
    assert argv[-1] == "compact-stop", "the verb the answer names is the verb the queue received"
    assert argv[argv.index("--from") + 1] == "sahw"
    assert cwd == folder["run_dir"]


def test_a_compact_to_a_settled_run_still_rides_the_queue(folder, launched, killed):
    """The seam does not decide for the run: a settled run is the compact its next objective reads at
    its first turn, and the block is the seam's whole answer either way.
    """
    write_log(folder["run_dir"], started(folder["workspace"]), message("one"), ended())
    carried = channel.post_compact(r"C:\runs", r"C:\Work\SAH", folder["run_dir"])
    assert carried == "compact"
    argv, env, cwd = launched[0]
    assert len(launched) == 1 and argv[3] == "send", "the one launch the seam records is the send"
    assert argv[-1] == "compact"
    assert cwd == folder["run_dir"]
    assert killed == [], "a verb to a settled run starts nothing and ends nothing"


def test_a_compact_from_a_server_that_names_no_sah_tree_is_refused(folder, launched, killed):
    """The seam needs the tree whose interpreter runs the verb: a server that names none refuses, and a
    refusal starts nothing.
    """
    write_log(folder["run_dir"], started(folder["workspace"], pid=os.getpid()))
    with pytest.raises(channel.ChannelError) as raised:
        channel.post_compact(r"C:\runs", "", folder["run_dir"])
    assert raised.value.status == 503, "the code says this server, not the request, is to blame"
    assert launched == [] and killed == [], "a refusal starts nothing and ends nothing"
