"""sahw.purge — the one act that takes a run's record off disk, and the guard that says when it may not.

Delete is the only thing this server does that cannot be undone, so the whole module is written on one side
of one question: **is a process still writing this log?** The page asks for a delete behind its own
confirmation, and that consent is not the guard — the modal is the operator meaning it, and this is the
machine refusing anyway when the record is still being written. The two are kept different on purpose: what
the modal allows, the probe still declines.

**The folder is the record, so the folder is what goes.** A run's log, its report, and whatever files the run
left beside them are one folder under the runs root, and deleting means that folder and everything in it. The
guard is the only check on *which* folder; resolving the name to a folder under the runs root and nothing else
is the route's, and it is the same `_run_folder` every other per-run route stands on, so delete cannot reach a
path the stream could not.

**A batch is one act or it is not an act.** Deleting a workspace's runs — or every workspace's, which is the
batch the tree's head asks for — either removes all of them or none: a half-run batch leaves an operator
counting runs they did not delete, and the refusal names the live ids so the batch can be re-asked once they
are stopped. Nothing is deleted while any member is still being written.

**The guard reads the record first and the machine second, exactly as the tree's rows do.** An `ended` line
is the objective's own word that it is over; only a log that never ended asks the machine about the pid its
newest objective stamped. `unknown` — the answer the machine gives when it cannot name the process — is not
working, and the rule this module serves is that a run with no live process is dead. A guard that refused on
`unknown` would refuse to delete every run whose log was written on another box.
"""
from __future__ import annotations

import os
import shutil

from sahw import liveness, runs


def is_working(run_dir: str) -> bool:
    """Whether a process this machine still holds is behind this run's log.

    One call into the module that owns the reading — `runs.objective`, which is what the tree's rows are
    built from — so a row that carries no orphan mark and a delete that refuses cannot disagree about the
    same log.
    """
    present = runs.objective(os.path.join(run_dir, runs.LOG_NAME))
    return not present.ended and present.verdict == liveness.LIVE


def delete_run(run_dir: str) -> dict:
    """Remove one run's folder, or refuse it by name.

    The answer is the act's own shape — `{"ok": true, "deleted": id}`, or `{"ok": false, "reason": ...}` —
    rather than the tree's error shape, because a live run is not a bad request: the request was understood
    and the machine declined the act. A folder that cannot be removed (a file held open, a permission the
    server does not have) is not that: it raises, and the route says so as a fault.
    """
    run_id = os.path.basename(run_dir)
    if is_working(run_dir):
        return {"ok": False,
                "reason": f"{run_id} is still working — nothing was deleted; stop the run before deleting it"}
    shutil.rmtree(run_dir)
    return {"ok": True, "deleted": run_id}


def workspace_runs(runs_root: str, cwd: str) -> list[tuple[str, dict]]:
    """Every run under this root whose `started` stamps this workspace, as (id, the row the tree shows).

    The workspace is matched as the tree matches it: the string the run stamped, exactly. The page sends back
    the path the tree gave it, and a path differing in case or separator spelling is a different workspace to
    the record — an answer of "nothing was deleted" is then the honest one, and the safe side of a mistake.

    A run whose log names no workspace is not in any workspace, so it is not in the batch; a run whose row
    says the process is live carries that in the row, which is why this returns rows rather than names.
    """
    found = []
    for name in runs.run_dirs(runs_root):
        described = runs.describe_run(os.path.join(runs_root, name))
        if described is not None and described[0] == cwd:
            found.append((name, described[1]))
    return found


def all_runs(runs_root: str) -> list[tuple[str, dict]]:
    """Every run under this root that stands in some workspace, as (id, the row the tree shows).

    The same reading `workspace_runs` makes, over every workspace at once: the batch the tree's head asks
    for is the batch the operator could count, so its members are exactly the rows the tree lists. A run
    whose log names no workspace stands in no workspace, and is swept with none of them.
    """
    found = []
    for name in runs.run_dirs(runs_root):
        described = runs.describe_run(os.path.join(runs_root, name))
        if described is not None:
            found.append((name, described[1]))
    return found


def delete_batch(runs_root: str, found: list[tuple[str, dict]], batch: str) -> dict:
    """Remove one batch of runs, or refuse the whole batch with the live ids named.

    The guard is asked of every member before anything is removed, so the batch never half-happens; the
    ids come back in the order the folders sort, which is the order they were minted. An empty batch is an
    act that succeeds having deleted nothing — the act asked for was "leave none of these", and that is now
    true. `batch` is what the batch is called in the refusal's sentence: the workspace's path, or the words
    saying it was every workspace, so one sentence describes either batch.
    """
    live = sorted(name for name, row in found if row.get("live") == liveness.LIVE)
    if live:
        return {"ok": False,
                "reason": (f"{len(live)} run(s) {batch} still hold a process — nothing was deleted; "
                           f"the live run(s): {', '.join(live)}"),
                "live": live}
    deleted = []
    for name, _ in sorted(found, key=lambda one: one[0]):
        shutil.rmtree(os.path.join(runs_root, name))
        deleted.append(name)
    return {"ok": True, "deleted": deleted}


def delete_workspace(runs_root: str, cwd: str) -> dict:
    """Remove every run of one workspace, or refuse the whole batch with the live ids named.

    The members are `workspace_runs`' — matched as the tree matches them, string for string — and a
    workspace with no runs is the empty batch, which succeeds.
    """
    return delete_batch(runs_root, workspace_runs(runs_root, cwd), f"of {cwd}")


def delete_every_workspace(runs_root: str) -> dict:
    """Remove every run of every workspace, or refuse the whole batch with the live ids named.

    One act over the whole root, and the same act the per-workspace batch is: every member is asked of the
    guard before the first folder goes, and the answer names every folder it took. A run the tree does not
    list — one whose log names no workspace — is not a member, so the sweep that was asked for as "every
    run I can see" cannot reach past what it could see.
    """
    return delete_batch(runs_root, all_runs(runs_root), "of every workspace")
