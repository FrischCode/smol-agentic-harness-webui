"""sahw.channel — how a word reaches a run: the queue while it works, the log once it has ended.

The page has one composer and the server has one route; which of SAH's verbs the words go to is decided
here, from the run's own record and the machine's verdict about its process. One rule fills in the whole
shape of it, and it is a rule about writers, not about moods: **one log, one writer at a time**. A second
writer is the only thing that can corrupt the record, so every arrival is placed by whether the log still
has one. A run's process lives its objective's lifecycle, not the page's: it works, it writes its ending,
it exits, and there are only the two states that leaves — **working** (no ending yet, the process the
record names still there) and **settled** (an ending, or no process).

The same two states answer the session's other act, which is not a word at all: the two dials the composer
stands on, the model and the reasoning level. A dial switched while the run works stands down and is
refused; switched at rest, it reaches the run as the run's own console line (see `post_command`) — and
because a session that has settled is a process that has gone, the switched dial also rides the argv of the
next objective the composer starts (see `follow_argv`), which is where a switch at a settled run takes
effect.

- **An `ended` line → follow**, whatever the probe says. The objective is over and a process that wrote
  its ending writes nothing after it, so resuming cannot race it — and the relaunch ends any process the
  log still names before it starts, which is the one case where a writer might still be finishing
  (`kill_first`). A word that insists on being a new objective arrives at this state too — a settled run
  has no writer to displace, and a cut back to a step is exactly that insistence, so naming the follow
  channel here is honoured however the probe answers.
- **No ending and the process live → steer.** The run is mid-objective; the word goes to the queue file
  and is read at the run's next turn boundary, where an in-flight tool call has already finished.
- **No ending and the process dead → follow**, the orphan's case: the log is intact, nothing is
  arriving, and the conversation continues where the record stopped.
- **A word that insists on being a new objective while a live process holds the log is refused**, with
  the sentence the pane already knows how to show. It is the only refusal, and it is the second writer.

The arrival the rule handles for free is a run mid-exit: its objective is done, the ending is not yet
written, the process is still there, so the word takes the steer channel and the process exits without
reading it. Nothing is lost — the queue outlives process boundaries and the next resume drains what is
pending. **The queue is the IOU**, and that is what makes the safe side of every judgement below the
cheap side too: an unknown verdict is never handed to the follow channel, and a word queued for a run
that turns out to have finished simply waits there.

The verbs are SAH's own (`python -m sah send … steer …`, `python -m sah run --resume --task …`, and
`python -m sah run --resume -i --task "/think high"` for one line at the console), so this module never
writes the log or the queue: it builds the command line an operator would type and launches it detached,
exactly as `spawn` launches a run. A follow is the one arrival that starts a process, and it is the one
place in this module that ends one: `kill_first` is the guard a relaunch owes the log it is about to write
again. The sender written into the queue block is
`sahw` — the record says who said it, and the record is read by people. A follow re-passes the reach
from the run's own `started` line rather than anything the request names, because permissions never
resume and the record, not the page, is what knows what the run was permitted.
"""
from __future__ import annotations

import os

from sahw import liveness, models, runs, spawn

STEER = "steer"
FOLLOW = "follow"

# The name the queue block carries as its sender: the record asks who queued it, and this is who did.
SENDER = "sahw"

# The arrival that names no channel: the page frames a composer and the rule below decides. `wants`
# exists for a caller that does have a channel in mind — the cut is a follow by name — and it is the only
# way the rule's one refusal can ever be reached.
MESSAGE = "message"

# The sentence for that refusal, in the pane's own voice: a failed send is a sentence the transcript
# owes the reader, and this one names what to do instead.
BUSY = "the run is working — steer it with a word, or wait for the objective to end"

# The sentence the session's two dials stand down with, and the answer a switch asked for in that window
# gets. It is the same second-writer fact `BUSY` states, told to the control that has to wait: the dial
# goes dim because a word is arriving, and the switch it was asked for lands when the run rests. The face
# says this sentence in the dial's own note hand and this route answers with it, so the refusal is one
# sentence whether the hand reached it or a client the page never was.
DIALS_DOWN = "the run is mid-turn — the model and the thinking level switch when it rests"

# The lines this server carries to a session are the session's own console lines — the operator's
# channel, and the face is handed its surface, not a door to two of its commands. Which of them a
# line is, and what its argument means, is the console's judgement and not this module's: the
# command a dispatch does not know answers with its own refusal beside the log, and a switch,
# a cut, a detach and a spawn each record themselves as a `notice` by the command that carried
# them. This door checks the line's shape and nothing else — a console line is one line of the
# console's own, and a door that checked command names would be a second registry standing in
# for the console that has the table in front of it.


class ChannelError(Exception):
    """A word this server will not carry, carrying the HTTP code that says who to blame: 400 when the
    request gave nothing to send or named a run the follow cannot stand on, 409 when a live process
    holds the log and the arrival insisted on becoming a second writer for it, 503 when this server was
    never pointed at the SAH tree whose verbs carry the word. The reason and the code are one decision,
    so they travel together and a route stays one `except` wide, as `spawn.SpawnError` does.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def decide(ended: bool, verdict: str, wants: str = MESSAGE) -> str:
    """Which channel carries a word: `steer` or `follow`, from the record and the machine's verdict.

    Pure, and deliberately so — the whole safety edge is one function of two facts, so the case the
    route can never reach (a caller naming `follow` for a log a live process holds) is still a case a
    test can force and read the sentence out of, with no child started.

    An `ended` line outranks the probe because it outranks the process: the objective is over, and a
    process that wrote its ending writes nothing after it, so the conversation is continued by a relaunch
    whoever may still be on its way out — and it is the relaunch that ends that process, which is the one
    second-writer guard this model keeps (see `kill_first`). A caller that names the follow channel is
    answered with it here whatever the verdict, because only it knows why it insisted: a cut back to a
    step rebuilds the conversation, and only a relaunch rebuilds one.

    Of the answers left when there is no ending, `dead` alone chooses the follow channel: `live` is a log
    with a writer, and `unknown` is not `dead` — a steer is the channel that costs nothing for being
    wrong, since a queued block waits for the next resume instead of racing the one that is already
    running. A word for a run that has settled is never lost either way: an ending the log holds is the
    record's own word that nothing is in flight.
    """
    if ended:
        return FOLLOW
    if wants == FOLLOW and verdict == liveness.LIVE:
        raise ChannelError(BUSY, 409)
    return FOLLOW if verdict == liveness.DEAD else STEER


def command_refusal(line) -> str:
    """Whether this line rides the session's console, or the sentence that says it does not.

    A console line is the operator's, and it begins with the operator's mark. The face carries the
    session's command surface — the line it types at the prompt and the lines its menu picks — and
    what the line is — which of the console's commands, whether the session runs it, refuses it,
    or answers it with its own list — is the console's judgement: a command the dispatch does not
    know to its own refusal beside the log, a switch and a cut and a spawn to the acts they
    record. This door checks only the line's shape, and it is one line of the console's own — it
    begins with the mark, its words are the words they appear to be (`text != " ".join(words)` is
    how a tab, a newline or padding between the words shows itself), and nothing is written
    beside them. A line without the mark is a word to the model, not a line to the console, and
    this door is not where it goes.
    """
    text = str(line if line is not None else "")
    words = text.split()
    if not words or not words[0].startswith("/"):
        return f"a console line is the operator's, and begins with its mark — {line!r} carries none"
    if text != " ".join(words):
        return (f"a console line is one line of the console's own, nothing between its words — "
                f"{line!r} is not")
    return ""


def send_argv(prefix: list[str], *, run_dir: str, text: str) -> list[str]:
    """The argv that queues a steer: `send`, the run's folder, the sender, then the word.

    On the child's side this is a file append and nothing else — no backend call, no waiting — which
    is why a steer costs the page nothing it can feel. `--from` is not decoration: the queue keeps the
    writer's claim beside the block, and the block says `sahw` because this server queued it.
    """
    return list(prefix) + ["send", "--run-dir", run_dir, "--from", SENDER, "steer", text]


def compact_argv(prefix: list[str], *, run_dir: str, stop: bool) -> list[str]:
    """The argv that queues the compact's verb: `send`, the run's folder, the sender, then the verb.

    The verb is `compact` — run the compaction now, the same act the trigger runs when the window is
    full — or `compact-stop`, the stop that asks the compaction in flight to stand down before the
    summary lands. Both are decided at the run's turn boundary by the run itself, so what this argv
    owes is the block in the queue and nothing else: no backend call, no waiting, the way a steer's
    owes. `--from` is not decoration, and a verb carries no text: the queue keeps the writer's claim
    beside the block, and a verb that said nothing is a verb the run's own drain reads.
    """
    verb = "compact-stop" if stop else "compact"
    return list(prefix) + ["send", "--run-dir", run_dir, "--from", SENDER, verb]


def follow_argv(prefix: list[str], *, run_dir: str, runs_root: str, task: str, max_turns: int,
                max_runtime: int, think: str = "", model: str = "", grants: dict | None = None,
                cut: str = "", vision: bool = False) -> list[str]:
    """The argv that continues a run: the command that started it, with `--resume`.

    `spawn.build_argv`'s shape is mirrored on purpose — the same runs root, the same `--view off`, the
    same budgets, and no `-i` — because a follow is a new objective in a run that already exists, a second
    objective should not arrive in an environment of its own, and the process that works it is the same
    kind of process the first one was: it works the objective it was given, writes its ending, and exits.
    What differs is the reach: **`--grant` and `--write` come from the run's own `started` line**, re-passed
    as the record names them, since a resume never inherits permission and nothing outside the record says
    what the run was actually stamped with. A record that named no reach re-passes none rather than
    inventing one, and the run's own boot gate then says what it refuses. `--think` rides only when a level
    is named, as at the start, and `--model` only when the picker stands on one: **the new objective's
    bounds are the composer's, exactly as a spawn's** — which is what carries a dial switched at a resting
    run into the objective that follows it, since a switch spoken at a session that has settled is a fact
    about a process that has already gone (see `post_command`). The budgets are the composer's, because a
    new objective may want its own.

    `--resume` is sent bare, which is SAH's "the whole conversation", unless `cut` names a step: then the
    digits follow the flag and SAH rebuilds the conversation from the prefix ending there, detaching the
    steps after it — kept in the log, never in a conversation again. The cut changes that one argument and
    nothing else about the command line, so a follow that returns to a step inherits the same
    second-writer safety, the same re-passed reach, and the same record as a follow that simply carries on;
    and whether the log holds the step named is settled before this is ever asked (see `runs.cut_refusal`),
    because SAH refuses a cut it cannot resolve by exiting without writing, which is an answer the page
    would never hear.

    `vision` rides the machine's decision, the same one the spawn and the fork ride: a relaunch is a run
    like any other, and the picture a model can be shown is a fact about the model this box names, not
    about the word that arrived.

    `--ask-timeout inf` rides the same decision the spawn and the fork ride: the operator who sent the word
    is at the face, and the run they are reading is attended — prose is the delivery, and the word they
    type next is the answer. `inf` is the attended default with no fuse: the question is answered when the
    operator looks, not decided by the clock.

    `--live` rides the same two decisions, and a follow has the strongest claim of the three: the objective
    is being written into a log somebody is watching, and the words of it are the answer they came for.
    The file is the run's own `live.jsonl`, so the second objective's fragments arrive in the trace the
    first one began — one file per run folder, in the order the run wrote it, which is the order the pane
    settles fragments under.
    """
    reach = grants if isinstance(grants, dict) else {}
    resume = ["--resume", str(cut)] if cut else ["--resume"]
    argv = list(prefix) + ["run", "--run-dir", run_dir, "--runs-root", runs_root, "--view", "off",
                           "--project-notes", *resume]
    for root in reach.get("read") or []:
        argv += ["--grant", str(root)]
    for root in reach.get("write") or []:
        argv += ["--write", str(root)]
    argv += ["--max-turns", str(max_turns), "--max-runtime", str(max_runtime)]
    if think:
        argv += ["--think", str(think)]
    if model:
        argv += ["--model", str(model)]
    if vision:
        argv += ["--vision"]
    return argv + ["--live", "--ask-timeout", "inf", "--task", task]


def console_argv(prefix: list[str], *, run_dir: str, runs_root: str, line: str, max_turns: int,
                 max_runtime: int, grants: dict | None = None, context="") -> list[str]:
    """The argv that speaks one line at the run's own console: `follow_argv`'s resume, opened as a session.

    The console is where an operator's slash lines go — `sah/cli.py` reads a line, and a line that opens
    with `/` is the operator's own act on the session, never an objective, its outcome recorded beside the
    log by the command itself. A caller cannot type at a process it did not start, so this is the command
    that operator would have typed, built the way the follow builds it: the same run folder, the same runs
    root, the same `--view off`, `--resume`, and the reach re-passed from the record because a resume
    inherits nothing. What makes it a spoken line rather than an objective is the pair at the end.

    **`-i` is the flag that carries it.** With `-i`, `--task` is not the objective: it is the first line
    the console reads, put through the same path a typed line takes — so a task that begins with `/` is
    dispatched as a command and never sent to the model. Without `-i` the same `--task` would be an
    objective, which is precisely the thing a switch is not. And because the launch hands the child the
    null device for stdin (see `spawn.launch`), the session reads its one line, records it, and closes at
    the end of input: the command is the whole of what the child was started for.

    **No `--think` and no `--model` ride this argv, and that is the point**: the line *is* the switch, and
    a flag naming the level the composer stood on before the switch would be a second claim about the same
    fact, arriving first. `--context` is the one bound re-passed beyond the reach, and only when the record
    names one — the number the run runs on is the run's own fact, and re-passing it keeps the session from
    going to the endpoint for a window the log already holds (which would also leave a `context` notice in
    the record on the strength of a switch that said nothing about the window). The budgets ride because a
    session needs some bound and the composer's are the ones this box launches runs with; no turn runs
    against them here, since no turn runs at all.

    `--project-notes` rides for the same reason the spawn and the follow carry it: the session the line is
    spoken in is the run's own, and assembling what it stands on is the boot's work, not this caller's
    guess about which parts of it a one-line session could do without.
    """
    reach = grants if isinstance(grants, dict) else {}
    argv = list(prefix) + ["run", "--run-dir", run_dir, "--runs-root", runs_root, "--view", "off",
                           "--project-notes", "--resume"]
    for root in reach.get("read") or []:
        argv += ["--grant", str(root)]
    for root in reach.get("write") or []:
        argv += ["--write", str(root)]
    argv += ["--max-turns", str(max_turns), "--max-runtime", str(max_runtime)]
    if context:
        argv += ["--context", str(context)]
    return argv + ["-i", "--task", line]


def kill_first(run_dir: str) -> bool:
    """End the process the log still names, and answer whether there was one.

    The one second-writer guard this model keeps, for the one moment it can bite: an objective that wrote
    its ending may not have exited yet, and a relaunch started beside it would be a second process
    appending to a log the first one is still finishing. The process to end is the one the record names —
    the `pid` of the newest `started` line, the same number the tree's spinner reads and the stop route
    ends (the stop first asks the tree's poll to vouch for the number, which is the poll's question and not
    this one — see `runs.Poll.rebirthed`) — because no handle to it was ever kept and the log is what
    knows it.

    The answer is the same fact two callers read differently: a follow only needs the ending done and goes
    straight on to launching, and the stop route turns a `False` into the 409 that says nothing was
    working. A pid the machine calls dead, and a log that names no pid, are both answered without a signal
    — a settled run has no process to stop, and its record stands exactly as it stood.
    """
    pid = (runs.latest_started(os.path.join(run_dir, runs.LOG_NAME)) or {}).get("pid")
    if liveness.probe_pid(pid) != liveness.LIVE:
        return False
    liveness.kill(pid)
    return True


def post_message(runs_root: str, sah_tree: str, run_dir: str, text: str,
                 think: str = "", max_turns: int = spawn.DEFAULT_MAX_TURNS,
                 max_runtime: int = spawn.DEFAULT_MAX_RUNTIME, model: str = "",
                 *, wants: str = MESSAGE,
                 cut: str = "", command: list[str] | None = None) -> str:
    """Carry one word into the run whose folder this is, and answer which channel carried it.

    The state comes from the record (the ending at the log's tail) and from the machine (the verdict about
    the process behind the objective the log holds), never from what the request believes: the page frames
    the composer, this decides. A word to a working run goes to the queue file and starts nothing; a word
    to a settled one starts the process that will read it. Nothing is returned beside the channel — the
    server holds no handle to any run it started, so a launch that happened needs no keeping and a queue
    that was written needs no watching.

    A follow asks the record one more thing — the `started` line of the objective the conversation stands
    on, whose `cwd` is where the run stands and whose `grants` are the reach to re-pass. A log that names
    no workspace is a record this server cannot continue, and that is the sentence it answers with; both
    refusals are made before anything is stopped, because a refusal that arrived after the kill would have
    destroyed the run it was refusing. Then `kill_first`, then the launch: the guard is the last thing
    before the new writer, so no path reaches the launch with a live process left holding the log.

    `command` is `spawn`'s seam, standing in for the child program so a test can hold the launch steady
    and read the argv; the flags after it are built the same way whoever runs them.

    Whether the relaunched child may be shown a picture is the machine's answer, not this word's:
    `models.vision_for_launch` is asked of the tree the launch is made from, the same lookup the spawn and
    the fork ride, so a run that could see its first objective sees its second and one that could not is
    not made able by arriving as a follow. A steer starts no process, so it carries no such decision.

    `cut` is the step the conversation returns to, and it arrives with `wants` already set to the follow
    channel by the caller that names it: the cut is a follow, so a step and a channel come together or not
    at all. It rides to the follow's argv (see `follow_argv`) and nowhere else — a word that went to the
    queue carried no conversation to rebuild — and whether the log holds the step it names is the record's
    question, answered by the route before this is reached, because a refusal after a stopped process is
    not a refusal.
    """
    if not str(text).strip():
        raise ChannelError("a word to a run is the whole point: text is empty")
    if not sah_tree:
        raise ChannelError("this server names no SAH tree: pass --sah-tree or set SAHW_SAH_TREE", 503)
    log_path = os.path.join(run_dir, runs.LOG_NAME)
    present = runs.objective(log_path)
    channel = decide(bool(present.ended), present.verdict, wants)
    tree_dir = os.path.abspath(os.path.expanduser(sah_tree))
    prefix = list(command) if command else spawn.child_command(tree_dir)
    env = spawn.child_env(tree_dir)
    if channel == STEER:
        spawn.launch(send_argv(prefix, run_dir=run_dir, text=text), env, run_dir)
        return channel
    stamp = runs.latest_started(log_path) or {}
    workspace = str(stamp.get("cwd") or "")
    if not workspace:
        raise ChannelError(f"the run's own log names no workspace to continue it in: {run_dir}")
    if not os.path.isdir(workspace):
        raise ChannelError(f"the workspace this run stands in is not a folder: {workspace}")
    argv = follow_argv(prefix, run_dir=run_dir, runs_root=os.path.abspath(runs_root), task=text,
                       max_turns=int(max_turns), max_runtime=int(max_runtime), think=think,
                       model=model, grants=stamp.get("grants"), cut=cut,
                       vision=models.vision_for_launch(tree_dir, named=model))
    kill_first(run_dir)
    spawn.launch(argv, env, os.path.abspath(workspace))
    return channel


def post_compact(runs_root: str, sah_tree: str, run_dir: str, stop: bool = False,
                 command: list[str] | None = None) -> str:
    """Carry the compact's verb to the run's queue, and answer which verb was carried.

    The queue is the only channel to a run's conversation, and the verb is the queue's — the run
    decides at its turn boundary whether the compact runs, and whether the stop finds a compaction in
    flight — so this carries the block and starts nothing: a `compact` to a settled run is the compact
    that word's next objective reads at its first turn, and a `compact-stop` with no flight is refused
    by the run in its own words. Nothing here is the run's state, and nothing is written to the log:
    the record stands the flight and its ending itself, and a route that wrote a notice beside it would
    be a second voice claiming what the queue did. The answer is the verb carried, so the caller knows
    which act to read the record for.

    `command` is `spawn`'s seam, standing in for the child program so a test can hold the launch
    steady and read the argv; the flags after it are built the same way whoever runs them.
    """
    if not sah_tree:
        raise ChannelError("this server names no SAH tree: pass --sah-tree or set SAHW_SAH_TREE", 503)
    tree_dir = os.path.abspath(os.path.expanduser(sah_tree))
    prefix = list(command) if command else spawn.child_command(tree_dir)
    env = spawn.child_env(tree_dir)
    spawn.launch(compact_argv(prefix, run_dir=run_dir, stop=stop), env, run_dir)
    return "compact-stop" if stop else "compact"


def dials_down(log_path: str) -> bool:
    """Whether the session's two dials stand down: whether a writer may still hold this log.

    The record answers first, and answers cheaply: an `ended` line at the tail says the objective is
    over, and an objective that wrote its ending writes nothing after it — so the log the console child
    is about to append to is a log nobody is mid-sentence in. What the record cannot answer alone is the
    process: a run that has just written its ending can still be on its way out, and a run with no
    ending at all may be mid-objective. That is the machine's question, and it is asked of the one
    number the record names — the `pid` of the newest `started` line, the same number the tree's spinner
    wears and the stop route ends.

    A live process stands the dials down, whether or not an ending is underneath it: the switch is
    delivered by opening the run's session again, and a session opened beside a live process is the
    second writer this module exists to keep apart. `unknown` stands them down too when the log holds no
    ending, for the same reason the steer is the cheap side of a word — a switch that waited costs
    nothing, and a switch that landed beside a writer it could not see costs the record. A dead process
    and an ending it finished are both rest, and an orphaned log with nobody behind it is rest as well:
    its next console line opens its session the way its next word would.
    """
    present = runs.objective(log_path)
    if present.verdict == liveness.LIVE:
        return True
    if not present.ended:
        return present.verdict != liveness.DEAD
    pid = (runs.latest_started(log_path) or {}).get("pid")
    return liveness.probe_pid(pid) == liveness.LIVE


def post_command(runs_root: str, sah_tree: str, run_dir: str, line: str,
                 max_turns: int = spawn.DEFAULT_MAX_TURNS,
                 max_runtime: int = spawn.DEFAULT_MAX_RUNTIME, *,
                 command: list[str] | None = None) -> str:
    """Speak one line of the run's own console, and answer the line that was carried.

    This is the whole of what the session's command surface does: the line the operator would have typed
    at the run's prompt is put into the command an operator would have typed to open that run, and the
    command is launched detached. Nothing is written here — not the log, not the queue — because the
    console records its own acts and a companion that wrote the notice too would be a second voice
    claiming what the command did. The line it carries is checked as a console line and nothing else (see
    `command_refusal`), the gate is the log's own (see `dials_down`), and the answer is the line: what
    this server carried is a line the record will shortly name — or refuse to — and the face settles
    on that rather than on this answer.

    The refusal for a working run is `DIALS_DOWN` at 409 — the sentence the dial itself already wears, so
    a client that asked anyway hears what the control was saying. And unlike a follow, which is a new
    objective and so ends the process the log still names before it starts its own, this carries no
    `kill_first`: a switch never ends a process. The gate refuses rather than displaces, which is the
    cheap side for a control the operator can simply move again a moment later.
    """
    refused = command_refusal(line)
    if refused:
        raise ChannelError(refused)
    if not sah_tree:
        raise ChannelError("this server names no SAH tree: pass --sah-tree or set SAHW_SAH_TREE", 503)
    log_path = os.path.join(run_dir, runs.LOG_NAME)
    if dials_down(log_path):
        raise ChannelError(DIALS_DOWN, 409)
    stamp = runs.latest_started(log_path) or {}
    workspace = str(stamp.get("cwd") or "")
    if not workspace:
        raise ChannelError(f"the run's own log names no workspace to speak in: {run_dir}")
    if not os.path.isdir(workspace):
        raise ChannelError(f"the workspace this run stands in is not a folder: {workspace}")
    tree_dir = os.path.abspath(os.path.expanduser(sah_tree))
    prefix = list(command) if command else spawn.child_command(tree_dir)
    argv = console_argv(prefix, run_dir=run_dir, runs_root=os.path.abspath(runs_root),
                        line=str(line).strip(), max_turns=int(max_turns),
                        max_runtime=int(max_runtime), grants=stamp.get("grants"),
                        context=stamp.get("context") or "")
    spawn.launch(argv, spawn.child_env(tree_dir), os.path.abspath(workspace))
    return str(line).strip()
