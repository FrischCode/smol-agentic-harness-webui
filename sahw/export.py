"""sahw.export — one run's log as Markdown: the projection a download carries.

A projection, not a second record. It reads the same `log.jsonl` the tree lists and the stream replays and
renders it, so the file an operator downloads says what the record says; nothing here keeps state, writes a
file, or re-derives a verdict. The log is the record and this is one way of showing it — which is also why
the answer is rendered on every request rather than cached beside the log: a report left in the run's folder
would be a second thing a later act could forget to refresh.

**The shape is the record's, not the page's.** The transcript pane arranges steps into rows, folds a
speaker's turns, and decorates them with the machine's verdicts; that is the face's business. This renders
the fields: the run's opening and its bounds, then every step in the order it was written, one purpose-built
line per kind, then the ending. A kind this reader does not know is printed from the fields it carries rather
than dropped — a projection that silently omits a step type is how a refusal disappears from a report — and a
kind it does know is rendered even when the line it produces is empty (an allowed operation, which the call
above it already told the reader about).

**Two divergences from the harness's own projection are this reader's, and both are its limits.** The
harness holds the step taxonomy and this tree does not import it, so it cannot tell a field a *known* kind
carries that its own build predates: those stay unprinted here, where the harness prints them crudely. And
the italic line an allowed operation may carry comes from the policy that wrote it, a sentence this tree
cannot enumerate without copying it and going stale quietly, so any reason the record carries on an allowed
operation is shown as the record words it. A kind that is wholly unknown already prints all its fields, so
the one thing the taxonomy would be needed for — a step nobody can render — stays covered.

**Tolerance is the same bargain the tree's other readers strike.** A log is written while it is read, so a
line that is not a whole step is dropped and counted, and the count is printed above the report rather than
left for the reader to notice by its absence. A step whose fields are of a type no writer would have stamped
still renders (as `?`, or with the figure left out), because a download that raises is worth less than a
download with one figure wrong. And there is no size cap: a preview pane clips to a screen, a download is
asked for the whole transcript.
"""
from __future__ import annotations

import json

# The stamped columns: an id, a time and a voice are metadata about the step, not its content, so they do
# not appear in a line of prose — and the unknown-kind fallback excludes them for the same reason.
META_FIELDS = ("id", "ts", "issuer", "kind")

# The outcomes that state nothing beyond the act itself. A verdict outside this set is a fact the reader
# needs before the numbers, so the turn's footer leads with it.
CLEAN_OUTCOMES = ("", "ok", "allowed", "accepted")


# --- the reader ---------------------------------------------------------------------------------------

def read_steps(log_path: str) -> tuple[list[dict], str]:
    """The log's steps, and one sentence about the lines that were not steps.

    A step is a whole JSON object carrying a string `kind` — the test the record itself makes, asked here
    without the record's vocabulary so a step type or a field this tree predates arrives rather than being
    refused. Lines that fail it are dropped and counted: a log is appended to while it is read, and the one
    reading of a half-line that is not damage is that it has not finished. A log that cannot be opened at
    all is an empty history with nothing to report, the same answer the tree gives a runs root that is not
    there.
    """
    try:
        with open(log_path, "rb") as handle:
            blob = handle.read()
    except OSError:
        return [], ""
    steps: list[dict] = []
    dropped: list[str] = []
    for number, raw in enumerate(blob.decode("utf-8", "replace").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            step = json.loads(raw)
        except ValueError:
            dropped.append(f"line {number}")
            continue
        if not isinstance(step, dict) or not isinstance(step.get("kind"), str):
            dropped.append(f"line {number}")
            continue
        steps.append(step)
    if not dropped:
        return steps, ""
    named = ", ".join(dropped[:3]) + (f" (+{len(dropped) - 3} more)" if len(dropped) > 3 else "")
    return steps, (f"{len(dropped)} line(s) were not whole steps and were dropped — {named}; "
                   "a log read while it is written holds one mid-append")


def lineage(steps: list[dict]) -> tuple[list[dict], str]:
    """The steps with every cut applied — the conversation in force — and a sentence when a cut cannot be.

    A `cut` step is an instruction to the reader rather than a turn of the conversation: the conversation is
    the prefix ending at the step it names, and everything the file held after that step is detached. The cut
    itself is an operator act, so it does not survive into the answer either: what a report of a cut run shows
    is the conversation as it now stands, which is what the operator who cut it is continuing.

    Walking in file order and truncating at each cut composes, because a later cut may aim at a step of a
    lineage an earlier one made and a detached step never re-enters. A cut whose target is not in the list is
    corruption, not a gap: nothing can honestly be projected from it, so the steps come back whole and the
    sentence says the report is uncut — the file stays the record either way.
    """
    in_force: list[dict] = []
    for step in steps:
        if step.get("kind") != "cut":
            in_force.append(step)
            continue
        target = step.get("to", "")
        where = next((i for i, prior in enumerate(in_force) if prior.get("id") == target), None)
        if where is None:
            return steps, (f"the cut {step.get('id', '?')} names {target!r}, which is not in the "
                           "conversation it detaches a tail from; the run is shown uncut")
        in_force = in_force[: where + 1]
    return in_force, ""


def markdown(log_path: str) -> str:
    """One log as the Markdown the run's export downloads: the conversation in force, rendered.

    Read, projected, rendered — three steps, each of them answerable on its own and none of them writing a
    thing. The one addition is the line above the report saying what the reader had to leave out: a
    projection must not look intact when it is not.
    """
    steps, damage = read_steps(log_path)
    steps, cut_note = lineage(steps)
    text = render(steps)
    note = "; ".join(part for part in (damage, cut_note) if part)
    return f"(note: the log is damaged — {note})\n\n{text}" if note else text


def json_document(log_path: str) -> str:
    """One log as the JSON its export downloads: the record's own lines, one document.

    The same reading `markdown` makes — the log's steps in the order they were written — but the
    projection stops at the shape the record already stands in: an array of the record's own lines,
    nothing derived, nothing arranged, no cut for the reader's convenience. The transcript is a
    conversation in force; the document is the record, which the reader may not tidy.
    """
    steps, _ = read_steps(log_path)
    return json.dumps(steps, indent=2, ensure_ascii=False)


# --- the lines ---------------------------------------------------------------------------------------

def _number(value):
    """The figure, if it is one: a number that arrived as text is no figure and prints nothing.

    Nothing in a projection of a record this tree does not validate may raise, and a footer is the one place
    the record's fields are put through arithmetic rather than through `str`.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _args(step: dict) -> str:
    return json.dumps(step.get("args", {}), ensure_ascii=False, sort_keys=True)


def _indented(text: str) -> str:
    return "\n".join("    " + line for line in text.splitlines()) or "    (empty)"


def _speaker(step: dict) -> str:
    """Who spoke a message, as the one word a reader of the report needs.

    The author, not the role: the harness puts words in the user's seat on its own account — a nudge, a
    wrap-up, a future word — and a report that said `you` said them is a report that misremembers who spoke.
    The role is the shape the wire carries; the issuer is who spoke.
    """
    role = step.get("role", "")
    if step.get("issuer") == "core":
        return "core"
    return {"user": "you", "assistant": "agent"}.get(role, role)


def _trailer(step: dict) -> str:
    """The status footer of an assistant's turn, as one line: the window, the tokens, the wall time.

    The window pair first and unmarked, because it is the number being watched — how full the model's window
    is decides whether the next step is possible, which no token count says on its own. Then the token group:
    `¤` what the server served from its own cache, `›` what came out, `↑` prefill and `↓` decode as the rates
    the server measured for itself (`/s` on the last, covering both), and `TOK` to name the group. The wall
    time last. A rate reported as zero is a server that measured nothing, so it prints no arrow; a cache count
    of zero is a fact, so it prints.

    The arrows mark rates and nothing else, and `›` is the only mark a count gets: a count wearing an arrow is
    read as a speed by anyone who has seen this line. Nothing is divided out of `ms`, which spans the whole
    request, and an outcome that is not one of the clean ones leads the line, because a turn that failed is
    the fact a footer exists to put first.
    """
    bits = []
    tokens_in = _number(step.get("tokens_in"))
    if tokens_in is not None:
        ceiling = _number(step.get("context_max"))
        bits.append(f"{tokens_in}/{ceiling} CTX" if ceiling else f"{tokens_in} CTX")
    group = []
    cached = _number(step.get("tokens_cached"))
    if cached is not None:
        group.append(f"¤{cached}")
    tokens_out = _number(step.get("tokens_out"))
    if tokens_out is not None:
        group.append(f"›{tokens_out}")
    prefill = _number(step.get("prefill_tps"))
    if prefill:
        group.append(f"↑{prefill:.0f}")
    decode = _number(step.get("tps"))
    if decode:
        group.append(f"↓{decode:.0f}/s")
    if group:
        bits.append(" ".join(group) + " TOK")
    ms = _number(step.get("ms"))
    if ms is not None:
        bits.append(f"{ms / 1000:.1f}s")
    outcome = step.get("outcome")
    if outcome and outcome not in CLEAN_OUTCOMES:
        bits.insert(0, str(outcome))
    return " · ".join(bits)


def _message(step: dict) -> list[str]:
    """One turn of prose, or the warning that stands in for the turn that did not happen."""
    if step.get("outcome") == "failed" or step.get("error"):
        return [f"> ⚠ turn failed: {step.get('error', '')}"]
    text = (step.get("text") or "").strip()
    lines = [f"**{_speaker(step)}:** {text}"] if text else []
    trailer = _trailer(step)
    if trailer:
        lines.append(f"*{trailer}*")
    return lines


def _call(step: dict) -> list[str]:
    return [f"▶ `{step.get('name', '')}` {_args(step)}"]


def _result(step: dict, names: dict) -> list[str]:
    """One tool's answer, under the name of the call it answers.

    A result carries no name of its own — the name belongs to the call, reached through `refs` — and
    labelling every one of them `output:` throws away the only heading a reader has to work with.
    """
    mark = "✓" if step.get("ok") else "✗"
    label = names.get(step.get("refs", ""), "output")
    content = (step.get("content") or "").rstrip()
    return [f"{mark} {label}:", _indented(content)] if content else [f"{mark} {label} (no output)"]


def _operation(step: dict) -> list[str]:
    """A refusal, and the policy's own sentence when an allowance carries one.

    The routine allowance draws nothing: the call it stands for is already on the screen. What a reason on an
    allowed act says is the policy's business, and this tree cannot enumerate those sentences — see the
    module's note on the italic line — so whichever one the record holds is shown as the record words it.
    """
    if step.get("outcome") == "refused":
        return [f"! refused `{step.get('op', '')}` — {step.get('reason', '')}"]
    reason = str(step.get("reason") or "")
    return [f"  _{reason}_"] if reason else []


def _request(step: dict) -> list[str]:
    return [f"? asked ({step.get('subject', '')}) `{step.get('item', '')}` — {step.get('why', '')}"]


def _decision(step: dict) -> list[str]:
    return [f"↳ decided `{step.get('outcome', '')}` — {step.get('reason', '')}"]


def _notice(step: dict) -> list[str]:
    return [f"• {step.get('subject', 'notice')}: {step.get('text', '')}"]


def _summary(step: dict) -> list[str]:
    """A compaction: its verdict and its arithmetic in the heading, its text below.

    The heading carries a blank line of its own, because a Markdown heading glued to the paragraph under it is
    the paragraph's second sentence to a renderer.
    """
    verdict = f"{step.get('outcome', '')}" + (f": {step['reason']}" if step.get("reason") else "")
    head = (f"### summary ({verdict}, kept {step.get('kept', '?')}, dropped "
            f"{step.get('dropped', '?')})")
    return [head, "", (step.get("text") or "").strip()]


def _fields(step: dict) -> str:
    """What a step declared, as the crude line a kind this reader has no words for prints.

    Crude beats invisible: the step is in the record and a report that dropped it would leave the reader
    looking for a gap in a transcript that has none.
    """
    return ", ".join(f"{k}={v!r}" for k, v in step.items() if k not in META_FIELDS)


_HANDLERS = {
    "message": _message, "call": _call, "operation": _operation,
    "request": _request, "decision": _decision, "notice": _notice, "summary": _summary,
}


# --- the report ---------------------------------------------------------------------------------------

def render(steps: list[dict]) -> str:
    """The steps as Markdown: the run's opening, every step in the order it was written, the ending.

    Pure — same steps, same text, nothing written. Consecutive blocks are separated by exactly one blank
    line, never inside a block and never doubled: that is the turn seam a reader needs, and it is also what
    keeps a rule line from landing directly under a text line, where Markdown would read it as a heading
    underline rather than as the boundary between two objectives.
    """
    openings = [step for step in steps if step.get("kind") == "started"]
    started = openings[0] if openings else {}
    endings = [step for step in steps if step.get("kind") == "ended"]
    ended = endings[-1] if endings else None
    # A log that holds several objectives holds one opening and one ending per objective, and the boundaries
    # between them are content the reader needs: showing only the first start and the last end would render a
    # followed-up session as one run that ended once.
    session = len(openings) > 1
    names = {step["id"]: step.get("name", "") for step in steps
             if step.get("kind") == "call" and "id" in step}

    lines = [f"# run {started.get('run_id', 'run')}", ""]
    meta = []
    if started.get("model"):
        meta.append(f"model: {started['model']}")
    if started.get("resumed_from"):
        meta.append(f"resumed from: {started['resumed_from']}")
    if started.get("grants"):
        meta.append(f"grants: {json.dumps(started['grants'], ensure_ascii=False)}")
    if ended is not None and not session:
        meta.append(f"ended: {ended.get('reason', '')} (exit {ended.get('exit_code', '?')})")
    if meta:
        lines.append(" · ".join(str(item) for item in meta))
        lines.append("")

    for step in steps:
        kind = step.get("kind")
        if kind == "started":
            if not (session and step is not started):
                continue
            block = [f"*run {step.get('run_id', 'run')} begins"
                     + (f" · model {step['model']}" if step.get("model") else "") + "*"]
        elif kind == "ended":
            if not session:
                continue
            block = ["---", f"*ended: {step.get('reason', '')} (exit {step.get('exit_code', '?')})*"]
        elif kind == "result":
            block = _result(step, names)
        else:
            handler = _HANDLERS.get(kind)
            block = handler(step) if handler else [f"· {kind}: {_fields(step)}"]
        if block and lines and lines[-1] != "":
            lines.append("")
        lines.extend(block)

    return "\n".join(lines).rstrip() + "\n"
