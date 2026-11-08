"""sahw.runs — the runs root read two ways: the two-level tree, and one log as it grows.

A run folder is a folder under the runs root that holds a `log.jsonl`. The log is what makes a folder
a run, and that test is what excludes the root's own neighbours — a pointer file, a notes folder, a
stray export — from the listing, so nothing opens a folder that was never a run.

**The tree reads the head and the tail of a log and never the body.** A workspace groups runs by the
`cwd` their `started` step stamps, and the two facts a row owes are the two ends of the file:
`started` is the run's own first step and `ended` is its last. Everything between them is the
transcript — the largest thing in the folder and the one thing a listing must not read. A root of a
few hundred runs is then a few hundred head lines and a few hundred tail windows, not a few hundred
whole files.

**One reader walks the body, and it is not the listing.** A cut back to a step has to be answered
against every step the log holds — the number may name no step, or a step a later cut already detached —
and that is one arrival at one run rather than a row of a tree, so `cut_refusal` pays the whole read the
listing's shape exists to avoid. A fork's branch point is the same question about the same record and pays
the same way; what a *row* owes of the fork is one fact, and it is read without walking the body, because
a carried prefix arrives still naming the run it was written by and the seam announces itself at the head
(see `_fork_step`).

**A row whose log never ended asks the machine one question.** The absence of `ended` is not a verdict:
a run still working and a run killed outright leave the same tail, and the log has no third thing to
say. So a row for an unfinished run carries `live`, the answer `liveness` gives about the pid the run
stamped — the record's part being only to name the number, which is why the answer is not decided here.
A finished row asks nothing: its ending is the answer, and the process that wrote it is on its way out by
definition, so a row that ended carries no `live` key and the face reads its absence as settled. The cost
shape is the question's: a head line and a tail window for every row, and one probe for every row the
record cannot answer alone. The number it asks about is the one the *objective in
flight* stamped: a log holds one `started` line per objective, so the head's pid goes stale the moment a
followed objective begins, and calling a working run dead is the one mistake this reader may not make —
a page would wear an orphan mark on a run that is answering, and a server would resume a log that
already has a writer. Walking back for the newest `started` line is therefore paid only by a row the
machine already called dead: the true orphan, and the run that grew a second objective.

**The name is the face's, and is read beside the record.** A row wears a word under `name` from three
places, in this order: `name.txt` in the run's folder — the face's own mutable file, which the run's process
never opens and never will — then the `title` the boot stamped on its own `started` line, then the operator's
first word (see `worn_name`). The record keeps the boot's word and reads nothing back; the current name is a
file the face writes and the machine is not involved in, which is what makes a rename safe on a working run
without a liveness guard. The cost is the one honest one: a row is now built from two files, so the page a
poll remembers is matched against both (see `_name_stamp`) and a renamed run is read afresh rather than
answered from a memory that named it the way it used to be named.

**The readers are tolerant, because a live log is written while it is read.** A half-written line is
not damage, it is a line still arriving: the head scan stops at the first line that does not parse and
the tail scan begins at the first line boundary inside its window. A run whose row says nothing is a
gap in the tree; a run that drops out because it was mid-append is a run that vanished between two
refreshes, so the row waits for the next one and no reader raises for a log that is merely awkward.

**The session's own channel stands beside the record, not after it.** A console line the operator spoke
between objectives — the model switched, the level switched — records a `notice` the console's way, and
that line arrives after the `ended` it follows. It is not an objective and it does not end one, so both
readers of the tail step over it on the way to the line that bounds the log (see `_control`): a run whose
operator switched its model is a run that ended, not a run that stopped short of its ending, and a stream
asked about it says so and closes rather than polling a record that has finished speaking.

**Streaming is a poll, not a notification.** The log is append-only and sits on a filesystem, where
nothing announces *new line*, so following it means asking again shortly: the lines already there go
out first, then the file is asked on every poll (`POLL_SECONDS`) for what arrived since the last
look. The stream
ends after the `ended` line that *ends the log*, because the log says when a run is over — the same
authority the tree's status reads — and a stream still open past it would be a connection held for a
run that is not running. A log that holds several objectives holds one ending per objective, and the
ending a reader stops at is the last one: an `ended` line with lines under it is one objective that
finished and another that began, and a reader that closed there would hand the page half the record.

**The trace is read, and is not the record.** A run started with SAH's `--live` also writes
`live.jsonl` beside its log: one line per fragment as the words arrive, before the step that holds them
is finished. `live_look` reads it with the log's own discipline and no more, and nothing here decides
what a fragment means — every fact in it is a fact the finished step carries, which is why the tree, the
status, the cut and the export all read the record and only the stream route reads both. A run folder
with no trace file is the ordinary shape of the tree: SAH writes the file at the first fragment, and the
absence answers without a word.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from collections.abc import Iterator

from sahw import liveness

LOG_NAME = "log.jsonl"
LIVE_NAME = "live.jsonl"
REPORT_NAME = "report.md"
# The face's own word for the run, one line beside the log it never touches. The record is the machine's
# and holds the boot's word; the run's *current* name is the face's mutable state, held in the run's own
# folder so it travels with the folder and dies with it (see `face_name` and `write_face_name`).
NAME_NAME = "name.txt"

HEAD_LINES = 8         # the most lines read while looking for the step that opens a run
NAME_CUT = 80          # the most characters the row's word keeps; the log holds the rest
TAIL_WINDOW = 8 * 1024  # the bytes read at the end of a log while looking for the step that closes one
SEARCH_CAP = 4 * 1024 * 1024  # the most of a log ever walked backwards looking for a step that opens one
POLL_SECONDS = 0.02    # how often a followed log is asked whether it grew


class Objective:
    """What a log says about the objective it holds, as far as the record and the machine can tell.

    `ended` is the record's own word: the `ended` step that closes the log, or None when the log has
    not ended. It is the step rather than a bare yes, because the reason a run ended is one of the two
    facts a row of the tree shows.

    `verdict` is the machine's word about the process behind the log, and it is asked only when the
    record had no ending to give — `liveness.probe_pid`'s three answers, `unknown` standing for the
    logs whose process cannot be named, including every log that ended and therefore owes no question.

    `asked` is the number that word was stood on, or None when no number was: a log that ended asks
    nothing, and a verdict that ran out of walking cap has no number to stand behind its silence. It is
    carried because a reader that asks the same log again — the tree's poll, remembering what it answered
    (see `Poll`) — owes that one question afresh on every asking and owes it of the same number, the one
    the answer was made from.
    """

    __slots__ = ("ended", "verdict", "asked")

    def __init__(self, ended: dict | None = None, verdict: str = liveness.UNKNOWN, asked=None):
        self.ended = ended
        self.verdict = verdict
        self.asked = asked


def mint_run_id() -> str:
    """A run id: a UTC stamp and a random tail, `r20261101-080119-aa8e41`.

    The stamp is fixed-width and UTC rather than the machine's local shape because the id is a folder
    name and the folder name is how a later reader finds the newest run: a stamp whose fields the locale
    rearranges does not sort, and a listing that does not sort is a listing that lies about which run is
    newest. The tail carries the uniqueness, so the stamp is there to be read and never has to be.
    """
    return time.strftime("r%Y%m%d-%H%M%S", time.gmtime()) + "-" + secrets.token_hex(3)


def fresh_run_dir(runs_root: str) -> str:
    """A path under the runs root that no other run has: an id that is not a folder yet.

    A collision (the same second and the same six hex digits) re-draws rather than naming a folder that
    already holds a run — the case the run itself refuses to write into, which would turn a request to
    start something into an error about something else. The check and the taking are two steps and two
    different questions — which name is free, and is this name mine — so the caller that means to start a
    run takes the folder with `os.makedirs` and draws again if the answer arrives too late.
    """
    base = os.path.abspath(os.path.expanduser(runs_root))
    while True:
        path = os.path.join(base, mint_run_id())
        if not os.path.exists(path):
            return path


def run_dirs(runs_root: str) -> list[str]:
    """The run ids under a root, in folder-name order: the folders that hold a `log.jsonl`.

    Name order is minted-stamp order for every id this tree mints, because the fields are fixed-width
    UTC; a hand-named folder simply sorts where its name sorts. A root that is not there answers with no
    runs rather than an error: a server started before its first run has no history yet, which is not a
    fault.
    """
    if not os.path.isdir(runs_root):
        return []
    return sorted(name for name in os.listdir(runs_root)
                  if os.path.isfile(os.path.join(runs_root, name, LOG_NAME)))


def _parse(line: str | bytes):
    """One line as a step, or None when it is not a whole JSON object.

    None is the answer for three cases a live log hands out for real — an empty line, a line still
    arriving, and a line whose bytes are not text — and the callers all read it the same way: nothing to
    learn here yet, so stop looking rather than raise.
    """
    text = line.strip()
    if not text:
        return None
    try:
        value = json.loads(text)
    except (ValueError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _started_step(log_path: str) -> dict | None:
    """The run's opening step: the first `started` among the head lines, or None when the log has not
    said it yet.

    `started` is the first step a run writes, but not necessarily the first line of the file: a resumed
    log opens where the earlier run left off, and older logs opened with a notice. So the scan walks a
    few lines rather than trusting line one. A line that does not parse ends the scan: it is a line
    mid-append, and a log has nothing further to say than what it has finished writing.
    """
    try:
        with open(log_path, "rb") as handle:
            for _ in range(HEAD_LINES):
                line = handle.readline()
                if not line or not line.endswith(b"\n"):
                    return None
                step = _parse(line)
                if step is None:
                    return None
                if step.get("kind") == "started":
                    return step
    except OSError:
        return None
    return None


def _first_objective(log_path: str) -> str:
    """The word that started the run: the text of the first user `message` in the head lines, or ''
    when the log carries none.

    The tree asks which run is which, and the id answers that only for the machine that minted it: the
    word the operator sent is what a reader of a list of ids remembers. That word is the log's first
    user message — a line or two under the `started` the head scan already walks, so it costs the read
    that read has already paid. The walk stops at the first user message and says only its first line,
    because the row owes one line: a multi-line objective is several lines of the same word, and the
    first is the one sent first, with the rest of the lines standing in for nothing but a newline. The
    row owes a name, not a paragraph: a first line longer than the cut stands as its cut and the mark
    that says the log holds the rest, and the tree's filter reads the word the row wears — so a word a
    whole paragraph held and the cut does not is not a word the row answers to. A log that never carried
    a user word (an empty prompt that quit, or a record the shape predates) answers nothing, and the row
    stands on its id instead of a word invented for it.
    """
    try:
        with open(log_path, "rb") as handle:
            for _ in range(HEAD_LINES):
                line = handle.readline()
                if not line or not line.endswith(b"\n"):
                    return ""
                step = _parse(line)
                if step is None:
                    return ""
                if step.get("kind") == "message" and step.get("role") == "user":
                    for piece in str(step.get("text") or "").splitlines():
                        if piece.strip():
                            word = " ".join(piece.split())
                            return word if len(word) <= NAME_CUT else word[:NAME_CUT] + "\u2026"
                    return ""
    except OSError:
        return ""
    return ""


def _control(line: bytes) -> bool:
    """Whether this raw line is the session's own control: a `notice` a console command recorded.

    The console is the operator's channel on a session, and what it records is a line beside the log
    rather than a step of the objective — `kind: notice`, `issuer: operator`, `subject: command`, the
    three fields SAH stamps on the word a slash line leaves. Such a line stands between two objectives as
    naturally as it stands after one, which is why a reader that asks the log *what is it doing* has to
    know the shape of one: an operator who switched the model at a resting run did not start the run
    again, and a reader that read the switch as an unfinished objective would report a run that stopped
    short of an ending it already wrote.

    Only the operator's channel is stepped over. A `notice` from `core` — a nudge, a compaction, a crash —
    is part of the telling of the objective it landed in, and machinery standing at the tail is the run
    still being mid-sentence, which is the claim this reader must not make lightly.
    """
    step = _parse(line)
    return (bool(step) and step.get("kind") == "notice" and step.get("issuer") == "operator"
            and step.get("subject") == "command")


def _ended_step(log_path: str) -> dict | None:
    """The step that closed this run: the log's last line that bounds an objective, when it is `ended`.

    Only the tail is read, because only the tail answers what a listing asks. `ended` is the last step
    of a finished run and is a few hundred bytes, so a window of a few KiB cannot miss it, while the
    transcript above it is the largest thing in the folder and nothing a row of the tree shows.

    The **last** line, and not the last ending anywhere in the window: a log that holds several
    objectives holds one ending per objective, and the ending of the first of them says nothing about
    whether the second is still arriving. This is the same judgement the follow makes — a stream stops
    at the ending that ends the log — and a reader that stopped at any ending would mark a run that was
    followed up idle the moment its second objective wrote a line. A window that reaches no ending at
    all says the run is live, which is the same judgement the run's own folder makes: nothing at the
    end, nothing over.

    The control lines the session speaks after that last line are stepped over on the way to it (see
    `_control`): the operator's channel stands beside the record, and an act spoken between two objectives
    neither closes one nor opens another. What bounds the log is the last line that is not that channel,
    and if that line is an ending the run is over however many switches were spoken after it.
    """
    try:
        size = os.path.getsize(log_path)
        read_from = max(0, size - TAIL_WINDOW)
        with open(log_path, "rb") as handle:
            handle.seek(read_from)
            blob = handle.read(size - read_from)
    except OSError:
        return None
    if read_from:
        # The window began somewhere inside a line, and the piece of a JSON object on this side of that
        # seam is not a step. The first newline says where the first whole line of the window begins.
        _, _, blob = blob.partition(b"\n")
    if not blob.endswith(b"\n"):
        # Nothing on this side of the last newline: the log's last line is still arriving, and a record
        # mid-sentence has not said it ended. The next look sees the whole line.
        blob, _, _ = blob.rpartition(b"\n")
    lines = [line for line in blob.splitlines() if line.strip()]
    while lines and _control(lines[-1]):
        lines.pop()              # the session's own channel stands beside the record, not after it
    if not lines:
        return None                                   # no whole line in the window: nothing to judge
    step = _parse(lines[-1])
    return step if step is not None and step.get("kind") == "ended" else None


def _walk_for_started(log_path: str, marker: bytes):
    """The newest `started` line in the log, walked back from its end: (the step or None, whether the
    walk was conclusive).

    A `started` line is the biggest line a log holds — it carries the exact system prose and tool
    contract the objective was sent with — so the walk starts at the same tail window the ending read
    uses and doubles until it either finds one or has the whole file. `marker` is the cheap half of
    the test: a line is parsed only when the step's name appears in it, and a line that merely quotes
    the word is parsed and rejected. Conclusive is the answer a caller has to have with the step:
    a walk that found nothing but read every byte says the log holds one objective, and a walk that
    ran out of cap says nothing, which is not the same claim and must not be read as one.
    """
    try:
        size = os.path.getsize(log_path)
    except OSError:
        return None, True
    window = TAIL_WINDOW
    while True:
        read_from = max(0, size - window)
        try:
            with open(log_path, "rb") as handle:
                handle.seek(read_from)
                blob = handle.read(size - read_from)
        except OSError:
            return None, True                       # gone: nothing newer is coming from it
        if read_from:
            _, _, blob = blob.partition(b"\n")
        for raw in reversed(blob.splitlines()):
            if marker not in raw:
                continue
            step = _parse(raw)
            if step is not None and step.get("kind") == "started":
                return step, True
        if read_from == 0:
            return None, True                       # every byte was read: nothing newer is in the log
        if window >= SEARCH_CAP:
            return None, False                      # the head is out of reach: nothing can be claimed
        window *= 2


def objective(log_path: str, started: dict | None = None) -> Objective:
    """What this log says about the objective it holds, read from the two ends and, only when it has
    to, from the machine.

    The record answers the first half — an `ended` line at the end of the file — and answers it
    completely, so a log that ended costs no more than the two reads the tree already pays and gets no
    verdict asked of the machine. The second half is the process behind the log, and the number to ask
    about is the one the newest objective stamped: the head's own line is the cheap answer while that
    process is still there, and once the machine says it is gone the log may already have grown a
    second objective whose `started` line sits further down. Walking back for it is what keeps the two
    honest answers apart — the orphan nobody killed, and the run that was followed up.
    """
    ended = _ended_step(log_path)
    if ended is not None:
        return Objective(ended)
    head = _started_step(log_path) if started is None else started
    head_pid = (head or {}).get("pid")
    # The number to ask, and the number to hand to the next asking of the same log: a value the record
    # called a pid that is not one has no process behind it to settle and no key to be remembered by.
    head_ask = head_pid if liveness.is_pid(head_pid) else None
    head_verdict = liveness.probe_pid(head_pid)
    if head_verdict == liveness.LIVE:
        return Objective(None, head_verdict, head_ask)
    newest, conclusive = _walk_for_started(log_path, b'"started"')
    if newest is not None and newest.get("pid") != head_pid:
        newest_pid = newest.get("pid")
        newest_ask = newest_pid if liveness.is_pid(newest_pid) else None
        return Objective(None, liveness.probe_pid(newest_pid), newest_ask)
    # Nothing newer answers, and either the file was read to its beginning — so the head's process
    # *is* the objective in flight — or the walk ran out of cap and no number can be stood behind.
    return Objective(None, head_verdict if conclusive else liveness.UNKNOWN,
                     head_ask if conclusive else None)


def latest_started(log_path: str) -> dict | None:
    """The step that opened this log's newest objective: what a resumed objective inherits from.

    The reach and the workspace a follow re-passes are the ones the record holds, and a log that ran
    several objectives holds one record of them per objective — the newest is the one the conversation
    actually stands on. A log that never wrote a `started` line, or one whose newest sits past the
    walk's cap and never showed itself, answers through its head line instead: it names the same run,
    and naming the run's opening reach is a claim the record supports where naming nothing would leave
    the follow to guess.
    """
    step, conclusive = _walk_for_started(log_path, b'"started"')
    if step is not None or conclusive:
        return step
    return _started_step(log_path)


def _model_said(text) -> tuple[str, str] | None:
    """The address a console notice put in force, or None when the notice put no address in force.

    The console's word for a switch is `model: <name> @ <host>:<port> in force (<where it came from>; was
    <the old address>); context <n> (<source>); think=<level>` — and every other line that opens `model:`
    is something else wearing the same first word: a registry that refused to load, an id of two words, a
    listing that went to the terminal instead of the log. That is why `in force` is what this looks for and
    not the prefix: the record names the act it is recording, and a reader that took the console's sentence
    about a failed command for a new address would settle the face's picker on a switch that never happened.

    The address is returned beside the name because they are separate facts: the name is what the request
    carries and what a profile is resolved by, and the address is the box it is carried to — which a switch
    of profile may move and a switch of a literal name on the box in force may not.
    """
    head, _, forced = str(text or "").partition(" in force ")
    if not forced.strip() or not head.startswith("model: "):
        return None
    name, _, host = head[len("model: "):].partition(" @ ")
    name = name.strip()
    return (name, host.strip()) if name else None


def _level_said(text) -> str | None:
    """The reasoning level a console notice put in force, or None when it put none in force.

    `think: <level>` stands alone or carries its reason in parentheses — `(was xhigh)`, `(in force
    already)`, the clause about the summary calls keeping their own level — and the one line of the shape
    that states no level is the console's refusal of a level of several words. The same test rejects both:
    a level is one word, so anything that is not a single word before the first parenthesis is the console
    talking about a command rather than recording one. `none` is the console's own spelling for the field
    omitted and is a level like any other, not an absence the reader may fill in.
    """
    text = str(text or "")
    if not text.startswith("think: "):
        return None
    word = text[len("think: "):].partition("(")[0].strip()
    return word if word and " " not in word else None


def dials(log_path: str) -> dict:
    """What the session's two dials stand on, as the record says it: the model name, its address, its level.

    A run's bounds are written when it opens and are moved afterwards only by the operator's own channel,
    so the answer for each dial is the **newest statement of it**: a `/model` notice outranks the `started`
    line it follows, and that `started` line outranks every notice before it, because a relaunch runs on the
    flags it was launched with and not on the dial a previous session left standing. Each dial is answered
    out of the same newest `started` step, so a run that switched one dial and never the other is read as
    the run it is rather than as two runs.

    The walk is the newest-statement walk the tree already pays: back from the end through a doubling
    window, stopping the moment both dials have an answer — which for the common case (a switch spoken at
    a resting run) is the last few lines of the file — and capped where the walk for an opening step is
    capped. Past the cap the answer is whatever the tail stated, and a dial it never stated stays None.

    None is the absence the face has to be able to read, and it is the only answer a log that names no
    `started` step gives at all: a picker stood on a default filled in here would be a face naming a
    machine the record never named. `endpoint` is None until a switch names one — the opening step records
    a model, not an address — and a caller shows the address when the record carries it and not otherwise.
    """
    model, endpoint, level = None, None, None
    bounded = False
    try:
        size = os.path.getsize(log_path)
    except OSError:
        return {"model": None, "endpoint": None, "think": None}
    window = TAIL_WINDOW
    while True:
        read_from = max(0, size - window)
        try:
            with open(log_path, "rb") as handle:
                handle.seek(read_from)
                blob = handle.read(size - read_from)
        except OSError:
            break                                   # gone: what was read is the last word there is
        if read_from:
            _, _, blob = blob.partition(b"\n")      # the window began inside a line
        if not blob.endswith(b"\n"):
            blob, _, _ = blob.rpartition(b"\n")     # the last line is still arriving
        for raw in reversed(blob.splitlines()):
            if b'"notice"' not in raw and b'"started"' not in raw:
                continue                            # the cheap half of the test, as the walk's is
            step = _parse(raw)
            if step is None:
                continue
            kind = step.get("kind")
            if kind == "started":
                if model is None:               # a notice above this one already stated the dial
                    model = step.get("model") or None
                if level is None:
                    level = step.get("thinking") or None
                bounded = True                  # the opening bounds every line above it
                break
            if kind == "notice" and step.get("issuer") == "operator":
                text = str(step.get("text") or "")
                said = _model_said(text)
                if said is not None:
                    if model is None:
                        model, endpoint = said[0], (said[1] or None)
                elif level is None:
                    level = _level_said(text)
        if bounded or read_from == 0 or (model is not None and level is not None):
            break                                   # bounded, read to the head, or both dials answered
        if window >= SEARCH_CAP:
            break           # the opening is out of reach: what the tail stated is the whole claim there is
        window *= 2
    return {"model": model, "endpoint": endpoint, "think": level}



def _whole_log(log_path: str) -> list[dict]:
    """Every whole step in a log, in file order, skipping the lines that do not parse.

    The tolerance is the head scan's for the same reason: a line caught mid-append is a line still
    arriving, not damage, and a reader of a live log comes across one. A line that is genuinely
    unreadable drops out of the read rather than ending it, because the writer that died mid-append
    leaves its torn line in the middle of the file for the rest of the log's life, and a reader that
    stopped there would read a long run as a short one.
    """
    try:
        with open(log_path, "rb") as handle:
            blob = handle.read()
    except OSError:
        return []
    parsed = [_parse(line) for line in blob.splitlines()]
    return [step for step in parsed if step is not None]


def _digits(step_id) -> str:
    """The number a step's id carries, told the way a page names it: `000003-message` is step `3`.

    The digits are what an operator reads and what a route is posted with; the rest of the id only says
    what kind of line it was. An id that does not open with a number — a hand-written record, a step from
    a log whose shape predates the numbering — answers with the empty string, which every caller below
    reads as "no number to name".
    """
    head = str(step_id or "").split("-", 1)[0]
    return str(int(head)) if head.isdigit() else ""


def _owed_calls(steps: list[dict]) -> list[dict]:
    """The calls in a stretch of the record that hold no answer in it.

    A `result` speaks about its `call` by naming that step's id in `refs`, so a stretch that stops after
    a call and before the answer holds a conversation that ended mid-exchange — which is the one thing a
    carried prefix may not be, because the server it is replayed to refuses it.
    """
    answered = {str(step.get("refs") or "") for step in steps if step.get("kind") == "result"}
    return [step for step in steps
            if step.get("kind") == "call" and str(step.get("id") or "") not in answered]


def _fork_step(log_path: str, run_id: str, started: dict) -> dict | None:
    """The log's own `fork` record, or None when the row has no fork to wear.

    A fork's log is the source's prefix carried whole, then the `fork` record naming where it was carried
    from, then the run's own steps — so the record sits at the seam between the conversation this run
    inherited and the one it is having. The seam marks itself for free: a carried line still names the run
    that wrote it, so a log whose opening `started` names *this* folder opened where it stands and has no
    seam at all, and that one head line is what the tree reads for every row anyway. Only a log that opens
    by naming another run is walked, and the walk ends at the first line that names this one, because the
    record is written before the fork's own first step and nothing past that is a fork record.

    A fork of a fork carries its elder's record inside the prefix, so the walk keeps the **last** record it
    passes rather than the first: the last one before this run's own opening is the fact about this run.
    The reach is `SEARCH_CAP`, the same one the newest-opening walk pays; past it nothing is claimed, and a
    row without the key is the honest answer, where a guess about the seam would be neither.
    """
    if not started.get("run_id") or started.get("run_id") == run_id:
        return None                       # the log opened as its own run: there is no seam before it
    found: dict | None = None
    read = 0
    try:
        with open(log_path, "rb") as handle:
            for raw in handle:
                if read > SEARCH_CAP:
                    return None           # the seam is past any reach this row will pay for
                read += len(raw)
                if not raw.endswith(b"\n"):
                    break                 # the last line is still arriving; nothing beyond it is whole
                if b'"fork"' not in raw and b'"started"' not in raw:
                    continue              # the marker is the cheap half of the test, as always
                step = _parse(raw)
                if step is None:
                    continue
                if step.get("kind") == "fork":
                    found = step
                elif step.get("kind") == "started" and step.get("run_id") == run_id:
                    return found          # this run's own opening: the seam, if any, is behind us
    except OSError:
        return None
    return found


def fork_branch(log_path: str, step) -> tuple[str, str]:
    """The step a fork branches at, and the sentence that refuses it — one of the two, never both.

    `step` is the digits as the page read them, or empty for "the whole conversation, from where it
    stands", and the answer is always a step's digits: `sah fork` names the step the carried prefix ends at,
    and a whole conversation has an end that can be named just as well as a middle. The branch point is
    settled against the record **here**, before a child is started, for the reason the cut learned: the
    fork's own door refuses a branch it cannot resolve by exiting without writing anything, which is an
    answer that never reaches the page after the route has already answered with a run id.

    The refusals are the cut's, in the fork's words — the log holds no such step, or a later cut detached
    the one it names — plus the one the cut leaves to SAH's door and a fork cannot: a carried prefix whose
    last call was never answered would be replayed to a server that refuses it, and here the refusal has to
    land before the launch rather than inside a child nobody is reading. The `ended` refusal the cut keeps
    is not a fork's: branching from a finished conversation is the point of the act.
    """
    steps = _whole_log(log_path)
    if not steps:
        return "", "a fork carries a conversation, and this run's log holds no steps to carry"
    ids: list[str] = []           # every step the file holds, in the order it holds them
    held: list[dict] = []         # the steps the conversation in force holds, cuts applied
    for step_held in steps:
        step_id = str(step_held.get("id") or "")
        if step_id:
            ids.append(step_id)
        if step_held.get("kind") == "cut":
            target = str(step_held.get("to") or "")
            at = next((index for index, s in enumerate(held) if str(s.get("id") or "") == target), -1)
            if at < 0:
                return "", (f"this run's log cannot be forked: its cut step {step_id} names {target!r}, "
                            "which is not in the conversation it detaches a tail from")
            held = held[: at + 1]
            continue              # a cut is what the operator did, not a step of the conversation
        held.append(step_held)
    if step is None or str(step).strip() == "":
        # the whole conversation: the branch is the last step of the conversation that is a place to
        # stand — a message or a result — and not the ending the run wrote after it, because a fork
        # carries a conversation and the ending is not a place in one.
        at = next((index for index in range(len(held) - 1, -1, -1)
                   if held[index].get("kind") in ("message", "result")), -1)
        if at < 0:
            return "", "a fork carries a conversation, and this run's log holds no steps to carry"
    else:
        try:
            seq = int(str(step).strip())
        except (TypeError, ValueError):
            return "", f"the fork is a step's number, as logged: {step!r} is not one"
        wanted = f"{seq:06d}-"
        at = next((index for index, s in enumerate(held)
                   if str(s.get("id") or "").startswith(wanted)), -1)
        if at < 0:
            last = ids[-1] if ids else "nothing"
            if any(step_id.startswith(wanted) for step_id in ids):
                return "", (f"the fork names step {seq}, which a later cut detached from this run's "
                            f"conversation; the log's last step is {last}")
            return "", (f"the fork names step {seq}, which this run's log does not hold; "
                        f"the log's last step is {last}")
    owed = _owed_calls(held[: at + 1])
    if owed:
        named = ", ".join(f"{s.get('name') or 'call'} ({s.get('id')})" for s in owed[:3])
        return "", (f"forking at {held[at].get('id')} would leave {named} owed a result — the carried "
                    "conversation would end mid-exchange; branch at a step that ends one")
    return _digits(held[at].get("id")), ""


def cut_refusal(log_path: str, step) -> str:
    """The sentence that refuses a cut back to `step`, or '' when the conversation in force holds it.

    The page names the step by the digits it read off that step's own id — `5` for `000005-message` —
    and the cut has to be answered against the record before anything moves, because the two ways it can
    be wrong are invisible to everything but the log: there is no step with that number, or there is one
    and a cut has already detached it. A detached step is in the file and not in the conversation, and
    returning to it would rebuild a prefix that holds a tail this run no longer owns. The projection is
    SAH's own `lineage`, walked here rather than imported because this tree reads SAH's logs and never
    its code: file order, truncating at each `cut` at the step it names, so a later cut may aim at a step
    an earlier one made and a detached step never re-enters.

    Every whole line is read, which makes this the one reader here that walks a transcript. The tree's
    whole shape — a head line, a tail window, and one question to the machine — is built on never doing
    it, and a cut is the arrival that owes it: one request about one run, asking a question that is about
    every step the log holds. Two refusals a step *in* the conversation can still earn — cutting at the
    run's own ending, and cutting where a tool call is owed its result — stay SAH's door's, made there
    before it writes anything; these are the two that must be made *here*, ahead of the stop and the
    relaunch the route would otherwise have already performed.
    """
    try:
        seq = int(str(step).strip())
    except (TypeError, ValueError):
        return f"the cut is a step's number, as logged: {step!r} is not one"
    wanted = f"{seq:06d}-"
    steps = _whole_log(log_path)
    if not steps:
        return f"the cut names step {seq}, and this run's log holds no steps to return to"
    ids: list[str] = []           # every step the file holds, in the order it holds them
    in_force: list[str] = []      # the same ids with every cut applied: the conversation in force
    for held in steps:
        step_id = str(held.get("id") or "")
        if step_id:
            ids.append(step_id)
        if held.get("kind") == "cut":
            target = str(held.get("to") or "")
            if target not in in_force:
                return (f"this run's log cannot be cut: its cut step {step_id} names {target!r}, "
                        "which is not in the conversation it detaches a tail from")
            in_force = in_force[: in_force.index(target) + 1]
            continue              # a cut is what the operator did, not a step of the conversation
        if step_id:
            in_force.append(step_id)
    if any(step_id.startswith(wanted) for step_id in in_force):
        return ""
    last = ids[-1] if ids else "nothing"
    if any(step_id.startswith(wanted) for step_id in ids):
        return (f"the cut names step {seq}, which a later cut detached from this run's conversation; "
                f"the log's last step is {last}")
    return f"the cut names step {seq}, which this run's log does not hold; the log's last step is {last}"


def face_name(run_dir: str) -> str:
    """The name the face gave this run, or '' when it has given none.

    `name.txt` is the face's mutable state and the run's own process never opens it. The record is the
    machine's and holds the word the boot was started with; the word the operator calls the run by *now* is
    not a line of that record, which is why naming and renaming stand safe whether the run works or rests —
    the safety is the safety of a file the run does not hold open, not a guard the act asks the run for.

    One line, the word, and the newline that ends it: the shape `write_face_name` writes. The reader is the
    tree's own kind and tolerant the same way — no file, no folder, and a file whose first line holds nothing
    all answer '' — because a run with no face name is the ordinary case of the tree and not a fault to raise
    for. Only the first line is asked of the file: a name is one line, and whatever stands under it is not a
    name.
    """
    try:
        with open(os.path.join(run_dir, NAME_NAME), "rb") as handle:
            line = handle.readline()
    except OSError:
        return ""
    return line.decode("utf-8", "replace").split("\n", 1)[0].strip()


def name_refusal(word: str) -> str:
    """Why this word cannot stand as the run's name, or '' when it can.

    The name is one line and the file is one line, so the act that would make the file two lines is the act
    the record cannot hold: a word carrying a line boundary — the newline a field's own `Shift+Enter` hands
    out, or the carriage return this box writes one with — is refused with the sentence that says what a name
    is. Nothing else is asked of it. The trim is the act's and an empty word clears the name (see
    `write_face_name`), and no length is asked of a word the row already wears as it comes.
    """
    for mark, called in (("\n", "a newline"), ("\r", "a carriage return")):
        if mark in word:
            return f"a name is one line: {called} would make {NAME_NAME} two of them"
    return ""


def write_face_name(run_dir: str, word: str) -> str:
    """Write, or clear, the face's word for this run — and answer which of the two the act did.

    The word is trimmed first, and a word that is nothing once trimmed is no word: the file goes when it
    stands, and the run falls back to what its own record says it is called (see `worn_name`). A word that
    stands is written the way the machine writes its own projections — a temp file in the same folder, then
    the replace over the name — so a reader of the tree never stands on a half word, and the clear is the
    plain remove, a file that is not there being a name that is not held. `newline` is named so the file is
    the same one line on every box rather than this box's idea of one.

    **The act never touches `log.jsonl`.** The record is the machine's and the name is not a line of it, so
    a rename leaves the log byte-identical — not by a guard, but because nothing here opens it. The caller
    has the line boundaries refused already (`name_refusal`); this writes what it is handed.
    """
    said = word.strip()
    held = os.path.join(run_dir, NAME_NAME)
    if not said:
        try:
            os.remove(held)
        except FileNotFoundError:
            pass        # nothing stood, nothing was held: the clearing of a name that was never named
        return "cleared"
    tmp = os.path.join(run_dir, NAME_NAME + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(said + "\n")
    os.replace(tmp, held)
    return "wrote"


def worn_name(run_dir: str, started: dict | None = None, task: str | None = None) -> str:
    """The word this run's row wears, from the three places a name comes from, in their order.

    The face's own word first, because the operator named the run and that is the word they will look for.
    Then the boot's word — the `title` the run's opening step was stamped with, which is the record's account
    of what it was started as, read here and never written back there. Then the operator's first word, the
    objective cut to the row's one line (see `_first_objective`). And '' when nothing says: the row carries
    no `name` key then, the same discipline `live`, `task` and `fork` keep, and the face falls back to the
    id's tail rather than to a word invented for it.

    `started` and `task` are the two facts a caller already holds rather than two more reads of the log — a
    row builder has the head in its hand and the word already read — and a caller that holds neither (the
    act that has just renamed a run, answering what the row will now wear) asks for both, paying the head
    read that row would have paid anyway.
    """
    named = face_name(run_dir)
    if named:
        return named
    log_path = os.path.join(run_dir, LOG_NAME)
    head = _started_step(log_path) if started is None else started
    word = _first_objective(log_path) if task is None else task
    return str((head or {}).get("title") or "").strip() or word


def describe_run(run_dir: str, present: Objective | None = None) -> tuple[str, dict] | None:
    """One run as (the workspace to file it under, the row the API shows), or None when the log cannot
    name a workspace.

    `present` is the objective's reading a caller already holds: the tree's poll reads a log to settle
    the one fact the record cannot give it, and owes that log no second reading to learn the same
    (see `Poll`). A caller that holds nothing passes nothing, and the reading is asked for here, as it
    always was.

    The workspace is the `cwd` the run stamped, and only the run states it: the folder the log lives in
    says which runs root it was written to, which is a fact about the server. A run that stamped no
    `cwd` — a log from before the field, or a fixture that never had one — has no workspace to file it
    under, and inventing one would place a run in a folder it never stood in.

    A log with no ending gets the one fact it cannot give itself: `live`, the machine's answer about
    the process behind the objective the log holds, because the record has run out of ways to say
    whether it is still arriving. A finished row carries no such key — its ending is the answer, and the
    process behind it has one job left — so the key's absence is the front's signal that this run has
    settled, the same signal the status badge already reads. The verdict is `liveness`'s to make and
    `objective`'s to ask for; this function only hands the answer on.

    The row's own facts come from the log's *first* `started` line: they name the run, which is what a
    row is, and a second objective shares the workspace and the opening stamp of the first. The model is
    the record's newest word instead — the same reading the pane's dials settle on (see `dials`) — because
    the endpoint is the one bound the operator's own channel moves, and a row that went on naming the box a
    run opened on after it was switched to another would be naming a box its words no longer go to. Where
    that reading runs out of reach the opening step's model stands, which is the row it always was. The
    address a switch named rides under `endpoint`, and a run that never switched carries no such key, as
    `live` and `task` and `fork` are absent when they have nothing to say.
    The word the operator sent rides under `task`, in the cut the row owes, when the log carries it — a
    list of ids names runs to the machine that minted them and to nobody else — and a log without a user
    word keeps the row to its id, rather than the row inventing a word the record never said.

    A run that was carried in from another run's conversation wears that fact under `fork`: the source's
    id and the digits of the step the carried prefix ends at, read from the log's own `fork` record and
    nothing else. A row with no such record carries no such key, so the face reads its absence the way it
    reads the absence of `live` — as the ordinary case, not as a missing thing.

    The word the row is *named* by rides under `name`, and it is the one row fact not read from the record:
    the face's own file when the face has named the run, the boot's word when only the boot named it, the
    operator's first word when neither did — the rule and its order stand in `worn_name`, in the one place
    they are read. A row the three leave speechless carries no `name` key at all, and the face wears the id's
    tail in its place. `task` keeps standing beside it as the record's own word, unchanged: the name is the
    face's mutable word and the task is the log's settled one, and a list that could not tell the two apart
    could not tell a renamed run from one that never was.
    """
    log_path = os.path.join(run_dir, LOG_NAME)
    started = _started_step(log_path)
    if started is None or not started.get("cwd"):
        return None
    if present is None:
        present = objective(log_path, started)
    stated = dials(log_path)
    row = {
        "id": os.path.basename(run_dir),
        "ts": str(started.get("ts") or ""),
        "model": str(stated["model"] or started.get("model") or ""),
        "status": "ended" if present.ended else "live",
        "reason": str(present.ended["reason"]) if present.ended else None,
    }
    if stated["endpoint"]:
        row["endpoint"] = stated["endpoint"]
    task = _first_objective(log_path)
    if task:
        row["task"] = task
    named = worn_name(run_dir, started, task)
    if named:
        row["name"] = named
    carried = _fork_step(log_path, row["id"], started)
    if carried is not None:
        row["fork"] = {"source": str(carried.get("source_run") or ""),
                       "step": _digits(carried.get("source_step"))}
    if not present.ended:
        row["live"] = present.verdict
    return str(started["cwd"]), row


class Page:
    """One run folder, as the last poll answered it: the row it answered with, and what that row was
    answered from — the log's size and mark, the name file's (see `_name_stamp`), the workspace it was
    filed under, and the number the machine's verdict was stood on (`None` for a row that asked nothing,
    which is every settled row and every log no process can be named behind).

    A page is worth exactly one re-read: nothing in it is not also in the log or in the name file, it holds
    no fact those two do not hold, and losing it costs the next poll one reading of one folder.
    """

    __slots__ = ("stamp", "named", "workspace", "row", "asked")

    def __init__(self, stamp, named, workspace: str, row: dict, asked=None):
        self.stamp = stamp
        self.named = named
        self.workspace = workspace
        self.row = row
        self.asked = asked


def _log_stamp(run_dir: str):
    """The log's size and its mark: the two facts that answer whether this record moved.

    A log moves by appending, so a byte moved is a byte more, and a log touched at all moves its mark;
    the pair is therefore the whole question a poll asks a folder it has read before, and it is asked
    with one `stat`. None when the log cannot be looked at — a folder removed between the listing and
    the look, a log this reader may not open — which is no mark to match against and a fresh read owed;
    the read itself is what says what the log really is.
    """
    try:
        seen = os.stat(os.path.join(run_dir, LOG_NAME))
    except OSError:
        return None
    return (seen.st_size, seen.st_mtime_ns)


def _name_stamp(run_dir: str):
    """The name file's size and mark, or None when no name stands: the other half of the question a poll
    asks a folder it has read before.

    A row is built from two files — the record, and the face's own word beside it — so a page is only worth
    reusing while both stand where the row was answered from. A rename writes the name over a replace, which
    moves the pair however the word went (a clear takes the file away, and no file answers with no pair), so
    this is the whole question *has the word this row wears moved since I read it*, asked with one `stat` and
    answered with None by the ordinary case of a run that was never named.

    The log's own stamp stays the record's and stays alone (see `_log_stamp`): the one reader that asks
    whether the *record* spoke — `Poll.rebirthed`, deciding whether a dead run's number is still its own —
    is not about to be talked out of its answer by a word the face wrote beside it.
    """
    try:
        seen = os.stat(os.path.join(run_dir, NAME_NAME))
    except OSError:
        return None
    return (seen.st_size, seen.st_mtime_ns)


class Poll:
    """One runs root, asked again and again: the rows this reader last answered, and the log each was
    answered from.

    A poll costs the record its whole weight — every log read from both ends, the dials' words dug out
    of the tail, the objective walked back for — and a tree of a few hundred folders asked twice a second
    spends that weight over logs that did not move between the two asks. So the answer is kept beside the
    log it came from: the log's size and mark (see `_log_stamp`) are the question *has this record moved
    since I last read it*, and a log standing where it stood answers with the row it answered before.

    One fact a standing log does not hold, and does not stop owing: the machine's verdict on the process
    behind a run that has not ended. A killed run leaves its log standing and moves only that verdict, so
    a row that has not ended re-asks it on every poll — `liveness` of the number the last answer stood on
    — and a settled row re-asks nothing, its ending being the answer. The questions are gathered before
    any of them is asked, because the machine is looked at once for all of them (see
    `liveness.probe_pids`). A re-ask that answers *otherwise* than the row carries is no longer a verdict
    but a moved claim, and the claim it moved is the newest objective's: that one owes the walk back
    through the log, which is a reading, and so a moved answer is read fresh rather than answered from a
    memory that just proved itself stale — **except for the one answer a reading cannot settle**, the
    flip of a dead verdict to live on the very number that verdict was stood on while the log has not
    moved a byte (see `rebirthed`). A row whose verdict no number stands behind — nothing stamped
    a process, or the walk ran past its cap — asks nothing and is reused, the standing log having said
    the same nothing twice.

    A log that grew (the run that works) is read fresh, as it always was, and so is a folder whose name file
    moved — written, rewritten or taken away — because the word the row wears is read from that file and a
    page answered before the rename is a memory that has just proved itself stale. A folder that appeared is
    read and stands in; a folder that left the listing is not in the answer, and its page goes with it —
    the memory is rebuilt from every walk, so a run that vanished cannot leave a row standing behind.

    Nothing here persists, and nothing here is a record: the log holds every fact a row is built from,
    and losing a page — this reader's, or the whole server's — costs one re-read, which is all a page was
    ever worth. Two polls at once therefore do no harm beyond asking twice: each builds its own pages and
    the later walk's memory stands, and no fact in here is a counter a second answer would corrupt.
    """

    def __init__(self, runs_root: str) -> None:
        self.runs_root = runs_root
        self.pages: dict[str, Page] = {}

    def tree(self) -> dict:
        """The two-level tree: workspaces, each holding its runs.

        `{"workspaces": [{"path": ..., "runs": [{"id", "ts", "model", "status", "reason"}]}]}` —
        workspaces sorted by path, runs newest first. A run whose log never ended carries a sixth key,
        `live`, and a run that ended does not: the key is the machine's verdict about a process the
        record cannot account for, so it stands for the working run and for the orphan the machine called
        dead, and its absence is the settled row the ending already described. An orphan whose own number
        the machine now answers live carries that number under `reborn` beside the dead verdict: the
        number was given to another process, and the row keeps standing dead for exactly that reason (see
        `rebirthed`) — while a row the machine answers live has no such key, because it has nothing to
        explain. A run whose log carries a user word carries the word under `task`, and one that never did
        has no such key. A run the face has been named wears that word under `name`, and so does one the boot
        stamped a title for, or one whose only word is the operator's first — the rule and its order stand in
        `worn_name` — and a run the three leave speechless carries no `name` key, the face wearing the id's
        tail in its place. A run carried in from another run's conversation carries that fact under `fork`,
        and one that began as its own run has no such key. A run the operator switched to another
        address carries that address under `endpoint`, and one that has talked only to the box it opened
        on has not. The sort is on the pair
        (stamp, id) rather than on the stamp alone: two runs minted in the same second then still have a
        fixed order, and a listing that changes between refreshes for no reason is a listing the front
        cannot diff against anything.
        """
        folders = {name: os.path.join(self.runs_root, name) for name in run_dirs(self.runs_root)}
        # First pass: which pages still stand, and the one question each of them still owes. Every
        # question is asked before any answer is used, so the machine is looked at once for the lot.
        standing = {}
        owed = []
        for name, folder in folders.items():
            held = self.pages.get(name)
            if held is None or held.stamp != _log_stamp(folder) or held.named != _name_stamp(folder):
                continue          # no page, or the record or the name moved: the row is read fresh
            standing[name] = held
            if held.asked is not None:
                owed.append(held.asked)
        answers = liveness.probe_pids(owed) if owed else {}
        # Second pass: the answers in hand, each folder is either its old row or a fresh reading.
        grouped: dict[str, list[dict]] = {}
        pages: dict[str, Page] = {}
        for name, folder in folders.items():
            held = standing.get(name)
            answer = answers.get(held.asked) if held is not None and held.asked is not None else None
            if held is not None and held.row.get("live") == liveness.DEAD \
                    and answer == liveness.LIVE:
                # The flip, and the one re-ask this poll settles for itself rather than by reading. The
                # number a dead verdict stood on answers live again, and the record that held its silence
                # has not moved since — so nothing came back, and the live answer is not this run's: it
                # is a process the machine has named with the number this run's log stamped. The row
                # keeps the dead verdict the record's silence stands, and grows the number beside it:
                # the reason a reader is owed for a row that stands dead while its number, asked
                # again, answers live.
                workspace, row, page = held.workspace, {**held.row, "reborn": held.asked}, held
            elif held is not None and (answer is None or answer == held.row.get("live")):
                workspace, row, page = held.workspace, held.row, held     # the page stands as it stood
            else:
                workspace, row, page = self._read(folder)     # a moved claim: the record is owed again
            if page is not None:
                pages[name] = page
            if row is None:
                continue
            grouped.setdefault(workspace, []).append(row)
        self.pages = pages
        workspaces = [{"path": path,
                       "runs": sorted(grouped[path], key=lambda row: (row["ts"], row["id"]), reverse=True)}
                      for path in sorted(grouped)]
        return {"workspaces": workspaces}

    def rebirthed(self, run_id: str) -> bool:
        """Whether this run's number answers live while a dead run's silence hangs under it.

        The fact a stop is owed before it ends whatever the number names, and it cannot be read off one
        asking: a live answer is exactly what a process that *is* the run's answers with. What tells the
        two apart is that a verdict was stood on this very number, and the record it was read from has
        been silent ever since — a resurrection writes a line and stamps a number of its own, and a
        number handed to another process writes nothing at all. So this is the poll's to answer, the poll
        being the only reader here that has known the log twice, and it is stood afresh rather than read
        back out of the row last answered: the page still has to stand over the selfsame log it was
        answered from (one `stat`), the verdict it carried has to be the machine's `dead`, and the number
        that verdict stood on has to answer live now (one probe). A page that has moved on — the log
        grew, the folder went, the record already answered working — says nothing about a process this
        server is being asked to end, and a run the record cannot name a number for never had one at
        stake here.

        The answer is a refusal's whole reason: the process standing under the number is not the run's,
        so ending it is not the act that was asked for. What the machine cannot vouch for, the stop
        leaves standing.
        """
        held = self.pages.get(run_id)
        if held is None or held.asked is None or held.row.get("live") != liveness.DEAD:
            return False
        if _log_stamp(os.path.join(self.runs_root, run_id)) != held.stamp:
            return False
        return liveness.probe_pid(held.asked) == liveness.LIVE

    def _read(self, run_dir: str) -> tuple[str, dict | None, Page | None]:
        """One folder read whole, and the page that stands it for the next poll.

        The reading is `describe_run`'s, and so is the objective it is built from — read once here, for
        both: the row needs the ending and the verdict, and the page needs the number the verdict was
        asked of. A folder that names no workspace answers `(“”, None, None)`: no row, and no page,
        because a run that was not answered has nothing worth remembering.
        """
        log_path = os.path.join(run_dir, LOG_NAME)
        opened = _started_step(log_path)
        if opened is None or not opened.get("cwd"):
            return "", None, None
        present = objective(log_path, opened)
        described = describe_run(run_dir, present)
        if described is None:
            return "", None, None
        workspace, row = described
        return workspace, row, Page(_log_stamp(run_dir), _name_stamp(run_dir), workspace, row,
                                    present.asked)


def tree(runs_root: str) -> dict:
    """The two-level tree, read now and remembered nowhere: `Poll.tree`'s answer from a reader that asks
    once and keeps nothing between two asks — which is every caller but the server's own tree, whose
    poll is a `Poll` and whose memory is the server's."""
    return Poll(runs_root).tree()


def stream_lines(log_path: str, poll: float = POLL_SECONDS, on_look=None) -> Iterator[bytes]:
    """The log's lines, then the lines appended after the reader arrived, then stop.

    Each line is yielded as the bytes that hold it: the frame the front is sent is the log line raw, so
    a log written in some encoding the server never inspects arrives as it was written.

    A line is yielded only once it is whole. Half a JSON object is what a reader catches mid-append, and
    a front that parses one sees a broken record rather than a late one, so a short read waits for the
    rest instead of handing it out.

    The stop is the `ended` line that ends the log: the record states when a run is over, and a stream
    that ran past it would poll a file for a run that finished. An ending with whole lines under it is
    not that stop — it is one objective closed and the next one opened, the same log carrying both —
    so it arrives as the step it is and the follow goes on. A log that disappears ends the stream too:
    the record is the only source, and a path that will not come back has nothing further to give.

    Each poll opens the file, reads what has grown, and closes it: a reader that held the log open would
    stand between the run and its record (and between the tree and a log it replaces), and a handle held
    across the follow is what makes a vanished log undetectable on a platform that will not let a held
    file go.

    **`on_look` is this reader's rhythm, lent to a second file.** A caller that follows the run's trace
    alongside the record passes it, and it is called once per poll — after every line that poll found has
    been handed over, before the next poll opens the file. That position is the whole of the merge rule:
    a record line always reaches its reader before the trace fragment that settles under it, and a caller
    that looked at the trace on the record's quiet moments only would starve it while the record was busy.
    The ending round is the one round without the call: this reader stops mid-round there, and the caller
    that has a trace to finish drains its last look before it closes what it is streaming — which is what
    `server`'s stream does, so a fragment written between the last step and the ending line still arrives
    before the frame that says the pane is owed nothing further.
    """
    offset = 0
    while True:
        try:
            with open(log_path, "rb") as handle:
                handle.seek(offset)
                chunk = handle.read()
        except OSError:
            return                                            # gone between the check and the open
        if chunk:
            cut = chunk.rfind(b"\n")
            if cut == -1:
                # no whole line yet: re-read from the same offset
                if on_look is not None:
                    on_look()
                time.sleep(poll)
                continue
            whole, offset = chunk[: cut + 1], offset + cut + 1
            lines = [line.rstrip(b"\r") for line in whole.split(b"\n") if line]
            # Which line of this read ends the log: the last one that bounds an objective, with the
            # session's control lines stepped over exactly as the tree's own reading steps over them. A
            # switch spoken after an objective is the operator talking to the session, not a next
            # objective opening, and a reader that read it that way would stand here polling a log that
            # had already said the last thing it had to say.
            bounds = len(lines) - 1
            while bounds >= 0 and _control(lines[bounds]):
                bounds -= 1
            last = len(lines) - 1
            for where, line in enumerate(lines):
                yield line
                if where == last and bounds >= 0 and is_ending(lines[bounds]):
                    # the ending at the end of what the log holds: the run is over, however far into
                    # the read it fell to notice that nothing came after it. The stop is taken after
                    # the whole read has been handed over, because the lines that stand under that
                    # ending are the session's own control — a switch spoken at a resting run — and a
                    # reader that turned back at the ending would close the stream with the console's
                    # word still in the file, which is the one line the operator just asked for.
                    return
            if on_look is not None:
                on_look()
            continue
        if not os.path.exists(log_path):
            return
        if on_look is not None:
            on_look()
        time.sleep(poll)


def is_ending(line: bytes) -> bool:
    """Whether this raw line is an `ended` step: the line one objective finished on."""
    step = _parse(line)
    return bool(step) and step.get("kind") == "ended"


def live_look(live_path: str, offset: int = 0) -> tuple[list[bytes], int]:
    """One look at the trace: the whole lines that arrived since `offset`, and the offset after them.

    The trace is SAH's own fragment file — `<run-dir>/live.jsonl`, one JSON object per line, the model's
    prose and a streaming tool's output as they arrive — and it is read exactly the way the record is:
    bytes, whole lines only, `\\r` off the end of each, the handle taken up for the look and put down
    again. It is written the same way, one flushed line at a time while a run works, so the two readers
    owe each other the same courtesy about a line still arriving: it waits for the rest of itself, and
    the offset does not move past it.

    **The file may not be there, and that is a state, not a fault.** A run started without SAH's `--live`
    never grows one; a run started with it grows the file only at its first fragment, so a reader that
    arrived before the first word finds nothing and asks again. Absence is the one answer that costs
    nothing to hold: no flag says which case this is, and no reader of the trace needs to know — a look
    that found nothing and a look of a file that is not there are the same nothing, and the record the
    fragments settle stands in either case.
    """
    try:
        with open(live_path, "rb") as handle:
            handle.seek(offset)
            chunk = handle.read()
    except OSError:
        return [], offset
    cut = chunk.rfind(b"\n")
    if cut == -1:
        return [], offset                                     # no whole line yet: look again from here
    whole = chunk[: cut + 1]
    return [line.rstrip(b"\r") for line in whole.split(b"\n") if line], offset + cut + 1


def stream_live(live_path: str, poll: float = POLL_SECONDS) -> Iterator[bytes]:
    """The trace's lines, as they arrive: `live_look` asked again on every poll, and never stopping.

    The tail the record's tail has no line for is an ending. The trace ends where the record ends — every
    fragment it holds is a fact the record's whole step also carries — so the caller that stops asking is
    what stops the following, and a reader that stopped at something else would be inventing a boundary
    the writer never wrote.

    The stream route does *not* follow this tail, and the reason is the record's: a reader parked in here
    waiting for the next fragment has stopped watching the log, and the `ended` line with it — a run whose
    words stop arriving would hold its own stream open and never be told it is over. The route therefore
    drains one `live_look` per poll of the log, which is the same discipline at the same rhythm with no
    waiting in the middle of it. This is the tail for a reader whose only file is the trace: the whole of
    `stream_lines`'s shape — whole lines, open-per-poll — minus the ending, because this
    file is a trace of arrival and not the record.
    """
    offset = 0
    while True:
        lines, offset = live_look(live_path, offset)
        if not lines:
            time.sleep(poll)
            continue
        for line in lines:
            yield line
