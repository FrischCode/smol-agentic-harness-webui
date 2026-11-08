"""sahw.spawn — start one SAH run and leave it to its objective.

The command line is the one an operator types, assembled here from four facts: the workspace the run
stands in, the objective it was given, the SAH tree whose package runs it, and the runs root it writes
into. Everything else — the backend, the endpoints, the credentials — belongs to the machine, and the
child reads them from its own tree's config, exactly as it does when a person launches it. The two dials
the face turns are the exception, and they are flags and nothing more: the model the picker stands on
rides to `--model` and the reasoning level to `--think`, each sent only when it is named, so a launch the
face left alone is a launch the machine answers for itself.

**A run started here is one objective, not a conversation waiting for its next word.** The argv carries
no `-i`, so the child works the objective it was given, writes its ending, and exits. Its stdin is the
null device and the launch keeps no handle on it: there is no prompt left to read a word from. The
process that continues a run later is a new one on the same log (see `channel`), so the run's lifecycle
is its objective's, and which page is looking at it moves nothing.

**The folder is taken before the child starts.** `--run-dir` names a folder this module creates and
nothing else has written to, which is the contract the run asks for: it refuses a folder that already
holds a run, so a fresh empty folder is what a started run needs, and taking it here is what lets the
API answer with a run id whose folder already exists. Minting and taking are a race between two
spawners, so a folder that turns out to be taken is drawn again rather than shared.

**The child's environment is two keys set on the server's own.** PYTHONPATH, because the SAH package
is a source tree and the child's working directory is the workspace, not the tree that holds it.
SAH_EXTENSION set to a single space — not empty, not removed: an absent or empty value lets the
machine's own config fill the key from that box's default, which is a path relative to a different
workspace, and a run whose extension cannot be loaded refuses at boot before it does anything. A space
is present, so nothing is filled in, and the run's command line drops whitespace-only entries from the
extension list.

**A forked run is started the same way, from another run's record.** `spawn_fork` launches `sah fork`
with the source's folder and the branch step the route settled against the source's log, and claims the
fresh folder here so the id is answerable before the child has seeded it. Two things differ, and both are
the source's doing rather than the request's: the branch stands in the workspace the source's newest
`started` stamped, and it carries the source's reach because `sah fork` reads that same line and inherits
it — so the fork argv names no `--grant` and no `--write`, and the face that asks for a fork grants nothing.

**Nothing is waited for, and nothing is held.** The child has its own log, and the log is the record: it
is what the tree lists, what the stream follows, and what an operator audits. A parent that waited would
hold an HTTP connection open for the length of a run, and a browser is not a supervisor. The child is not
kept either — the process is found again by the `pid` its own log stamps, the way `liveness` finds it —
so what a launch answers is an id and nothing else. Both outputs go to the null device because nobody is
reading them — a run holding a pipe nobody drains is a run that blocks on its own stdout and never
finishes — and stdin goes there for the same reason in the other direction: a run with an objective has
nothing to read.
"""
from __future__ import annotations

import os
import subprocess
import sys

from sahw import models, runs

DEFAULT_MAX_TURNS = 90
DEFAULT_MAX_RUNTIME = 10800

# Present, and meaning "none of these". Empty is the case this exists to avoid — see `child_env`.
EXTENSION_OFF = " "

# CREATE_NEW_PROCESS_GROUP: the child leads its own process group, so a Ctrl+C at the server is not a
# Ctrl+C at every run that server started.
_NEW_PROCESS_GROUP = 0x00000200


class SpawnError(Exception):
    """A run that cannot be started, carrying the HTTP code that says who to blame: 400 when the request
    named a folder that is not there or gave no objective, 503 when this server was never pointed at the
    SAH tree it would have to launch from. The reason and the code are one decision, so they travel
    together and a route stays one `except` wide.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def venv_python(sah_tree: str) -> str:
    """The interpreter to launch a run with: the SAH tree's own virtualenv.

    That venv holds the tools the tree was built with and nothing the UI needs, and the run is the
    tree's, so it runs on its interpreter. The name is the box's layout — a Windows venv keeps its
    scripts under Scripts/ — because the box this server launches runs is this box.
    """
    return os.path.join(sah_tree, ".venv", "Scripts", "python.exe")


def child_command(sah_tree: str) -> list[str]:
    """The command prefix that starts a SAH run: the tree's python, running the package as a module.

    A parameter of `spawn_run` rather than a constant buried in its body, so a test can hold the launch
    steady by naming a different child — the same seam the run's own loop takes its clock. What the seam
    replaces is the program; the flags after it are what is being asserted, so they are built the same
    way whoever runs them.
    """
    return [venv_python(sah_tree), "-m", "sah"]


def build_argv(prefix: list[str], *, run_dir: str, runs_root: str, sah_tree: str, workspace: str,
               task: str, max_turns: int, max_runtime: int, think: str = "", model: str = "",
               vision: bool = False) -> list[str]:
    """The child's argv. Keyword-only, because six strings in a row are not a contract.

    The run works the one objective `--task` names and then exits: no `-i` is sent, because a process left
    at a prompt is a process waiting for a word this server does not have, and a run that has ended and is
    spoken to again is relaunched rather than kept open. `--view off` keeps the console silent: the
    record is the log, and a run whose output nobody reads is a run with nowhere to put a word.
    `--project-notes` loads the workspace's own instruction file, which is why the child is started *in*
    the workspace: the notes are read from the working directory. `--grant` replaces the default read root
    rather than adding to it, so both folders the run needs are named — the workspace it stands in, and the
    SAH tree whose conventions a companion's run reads — while `--write` keeps the workspace the only
    folder it can change.

    `--think` is sent only when a level is named: an empty one is the machine's own default (the .env's
    SAH_THINK, then the server's), and a run started with the machine's default carries no flag that
    names it. A named one is sent verbatim, because the level is the server's own word.

    `--model` rides the same seam for the same reason, and it is the composer's picker that names one:
    the word sent is the word the machine's registry answers under (a profile id), sent verbatim because
    the face names what the machine answered and nothing between the two gets to re-resolve it. SAH's own
    precedence is flag > profile > `.env`, so the flag is what the run speaks as; an empty one sends no
    flag and the machine's default stands, which is what a picker nobody moved says about a spawn on a box
    whose registry names nothing. The sight decision follows the named model rather than the default it
    replaced (see `spawn_run`), because `--vision` is a fact about the model the child carries.

    `--vision` is sent only when the machine has said yes to it, and `models.vision_for` is where that yes
    is read from — this module does not decide what a model can do, it passes on what the machine declared
    about the model it is launching. A `False` sends no flag and the child's own default (no sight) stands,
    exactly as before the flag existed.

    `--ask-timeout inf` is the promise to answer from somewhere else, and somewhere else is the face: the
    operator who started the run reads the log and types the answer, so the run is attended — a prose turn
    completes rather than being nudged, and `verify_objective` is never offered. `inf` is the attended
    default with no fuse: the question is answered when the operator looks, not decided by the clock.
    Without the flag a run with a `--task` and no witness is unattended, and would end before the operator
    has said anything.

    `--live` is the other half of the same promise: an attended run is a run whose words somebody is
    watching arrive. SAH then writes the run's fragments to `<run-dir>/live.jsonl` as they come — the
    model's prose and a streaming tool's output, one line each — and the stream route reads that file
    beside the log, which is what lets the pane show a long turn being written instead of landed. It is a
    flag and not a claim: the file is created at the run's first fragment, a run that streams nothing
    leaves no file, and the record stays the whole of what the run said.
    """
    argv = (list(prefix)
            + ["run",
               "--run-dir", run_dir,
               "--runs-root", runs_root,
               "--view", "off",
               "--project-notes",
               "--grant", workspace,
               "--grant", sah_tree,
               "--write", workspace,
               "--max-turns", str(max_turns),
               "--max-runtime", str(max_runtime)])
    if think:
        argv += ["--think", str(think)]
    if model:
        argv += ["--model", str(model)]
    if vision:
        argv += ["--vision"]
    return argv + ["--live", "--ask-timeout", "inf", "--task", task]


def child_env(sah_tree: str, base: dict[str, str] | None = None) -> dict[str, str]:
    """The child's environment: the server's own, with the two keys this module owns set over it.

    PYTHONPATH names the SAH tree because the package runs from source and the child's working directory
    is the workspace, where the package is not. SAH_EXTENSION is set to a single space rather than
    cleared, because clearing it is the failure: the machine's config merges with setdefault, so a key
    that is missing (or empty, which a shell drops on the way through) is filled with that box's default
    extension — a path relative to some other workspace, which the run cannot load, and its boot gate
    refuses a run whose extension is unreadable. A space beats the merge, and whitespace-only entries
    are filtered out of the extension list, so the run loads no extension and says nothing about it.
    """
    env = dict(os.environ if base is None else base)
    env["PYTHONPATH"] = sah_tree
    env["SAH_EXTENSION"] = EXTENSION_OFF
    return env


def detach_kwargs() -> dict:
    """`Popen` kwargs that put the child in a process group of its own.

    The point is the separation of lifetimes: a run started from the UI outlives a Ctrl+C at the
    server, and stopping the UI is not stopping the work. The console itself is deliberately left
    attached — a new group is what separates the two lifetimes, and the flag that claims to remove the
    console does not deliver a windowless child.
    """
    if sys.platform == "win32":
        return {"creationflags": _NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def launch(argv: list[str], env: dict[str, str], cwd: str):
    """Start the child and do not wait for it.

    The one place this module asks the operating system for a process, so a test can stand in for the
    whole of it without touching the argv that would run or the folder that was claimed. All three streams
    are the null device: the child has an objective rather than a prompt, so there is nothing for it to
    read and nobody to read what it writes — and a pipe nobody drains is a run that blocks on its own
    stdout. The handle that comes back is a `Popen` this module hands to its caller and forgets; the
    process is found again by the `pid` its own log stamps.
    """
    return subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            **detach_kwargs())


def claim_run_dir(runs_root: str) -> str:
    """Mint a run id and take the folder it names, in one step, creating the folder empty.

    `runs.fresh_run_dir` answers which name is free; this answers that the name is now spoken for, which
    is the promise the run's own refusal is written against — it will not append to a history it did not
    begin. Two spawners can reach the same free name between the check and the taking, and the answer is
    to draw again: an id is cheap and a shared folder is two runs writing one log.
    """
    while True:
        path = runs.fresh_run_dir(runs_root)
        try:
            os.makedirs(path)
            return path
        except FileExistsError:
            continue


def fork_argv(prefix: list[str], *, source_dir: str, run_dir: str, runs_root: str, step: str,
              task: str, max_turns: int, max_runtime: int, think: str = "", model: str = "",
              vision: bool = False) -> list[str]:
    """The argv that branches a run: `fork`, the source, the branch step, then the fresh folder.

    `spawn_run`'s shape, with the objective swapped for the conversation it diverges from: the same runs
    root, the same `--view off`, the same budgets, no `-i`, because a fork is a run like any other — it
    works the objective `--task` names, writes its ending, and exits. **No `--grant` and no `--write` are
    sent, and that is the whole of the reach story**: `sah fork` reads the source's newest `started` and
    begins the branch with the reach the source began with, so the face that asks for a fork grants
    nothing — the record the source already holds is what the fork stands on.

    The step is named always, not only when the page named one: `sah fork` requires a branch step, and a
    fork of a whole conversation has one too — the last step of the conversation in force, which is what
    the route resolved before it got here (see `runs.fork_branch`).

    The composer's two dials ride it as they ride the spawn and the follow — `--think` when a level is
    named, `--model` when the picker stands on one — because a branch is a new objective and its bounds are
    the composer's: a face that showed a model and sent the branch to the machine's default instead would
    be a face describing a run it did not start.

    `--vision` rides the same decision the spawn's and the follow's ride: a branch runs on the model the
    machine names, and the machine's word about that model is one answer for all three verbs.

    `--ask-timeout inf` rides the same decision the spawn rides: a fork the operator branches at the face
    is attended, for the reason the spawn's docstring states.

    `--live` rides it too, for the same second reason: a branch is a run the face is watching from its
    first word, and the trace it writes is what lets the pane show those words arriving. The branch's own
    folder is where the file stands — the source's trace is nobody else's fragment file.
    """
    argv = (list(prefix)
            + ["fork", source_dir,
               "--run-dir", run_dir,
               "--runs-root", runs_root,
               "--view", "off",
               "--project-notes",
               "--step", str(step),
               "--max-turns", str(max_turns),
               "--max-runtime", str(max_runtime)])
    if think:
        argv += ["--think", str(think)]
    if model:
        argv += ["--model", str(model)]
    if vision:
        argv += ["--vision"]
    return argv + ["--live", "--ask-timeout", "inf", "--task", task]


def spawn_fork(runs_root: str, sah_tree: str, source_dir: str, step: str, task: str,
               max_turns: int = DEFAULT_MAX_TURNS, max_runtime: int = DEFAULT_MAX_RUNTIME,
               think: str = "", model: str = "", *, command: list[str] | None = None) -> str:
    """Branch the run whose folder this is into a new run, and answer the new run's id.

    Three things are checked before anything is written, in the same order `spawn_run` checks them: an
    objective for the branch (a fork with no task is a run with nothing to do), a source whose log is
    there to carry, and a SAH tree to launch from. Then the workspace: the branch stands where its source
    stood, because a fork is the same run on a different path — the folder the source's newest `started`
    stamped, with the same refusal the follow owes it when that folder is gone.

    The new run's folder is claimed here and named with `--run-dir`, so the id is in the response before
    the child has seeded anything — the same promise the spawn route makes, and the reason the front can
    open a fork the moment it asks for one. The child is not kept: the log it writes is the record, and
    every later question about the branch is answered from it.
    """
    if not str(task).strip():
        raise SpawnError("a fork is started with an objective: task is empty")
    if not sah_tree:
        raise SpawnError("this server names no SAH tree: pass --sah-tree or set SAHW_SAH_TREE", 503)
    source_log = os.path.join(source_dir, runs.LOG_NAME)
    if not os.path.isfile(source_log):
        raise SpawnError(f"the run to fork has no log to carry: {source_dir}")
    workspace = str((runs.latest_started(source_log) or {}).get("cwd") or "")
    if not workspace or not os.path.isdir(workspace):
        named = workspace or "(no workspace stamped)"
        raise SpawnError(f"the workspace the source stands in is not a folder: {named}")
    tree_dir = os.path.abspath(os.path.expanduser(sah_tree))
    run_dir = claim_run_dir(runs_root)
    prefix = list(command) if command else child_command(tree_dir)
    argv = fork_argv(prefix, source_dir=os.path.abspath(source_dir), run_dir=run_dir,
                     runs_root=os.path.abspath(runs_root), step=step, task=task,
                     max_turns=int(max_turns), max_runtime=int(max_runtime), think=think,
                     model=model, vision=models.vision_for_launch(tree_dir, named=model))
    launch(argv, child_env(tree_dir), cwd=os.path.abspath(workspace))
    return os.path.basename(run_dir)


def spawn_run(runs_root: str, sah_tree: str, workspace: str, task: str,
              max_turns: int = DEFAULT_MAX_TURNS, max_runtime: int = DEFAULT_MAX_RUNTIME,
              think: str = "", model: str = "", *, command: list[str] | None = None):
    """Start one run in `workspace` and answer its id while it is still starting.

    Three things are checked before anything is written, because each is a request that cannot be
    honoured and the answer is a sentence, not a child that dies: an objective (a run with no task is a
    run with nothing to do), a workspace that is a folder (it is the run's working directory, the first
    thing it was launched into, and the folder whose notes it loads), and a SAH tree to launch from. The
    budgets arrive as they were typed and are turned into integers here, so the argv holds numbers and
    the refusal for a non-number is the caller's 400. The thinking level, when named, rides to the
    child's `--think` verbatim; an empty one is not sent, and the machine's own default applies. The
    model, when named, rides to `--model` at that same seam, and it changes what the next question is
    asked about: a launch pointed at a model is sighted or blind as *that* model's declaration says, so
    the named model — not the `.env` default the flag replaces — is what `models.vision_for_launch` is
    given. Whether
    the child may be shown a picture is not the request's business either: it is read from the tree the
    launch is made from (`models.vision_for_launch`), so the machine's own model data is what opens the
    sight path and no caller can ask for a capability this box has not declared.

    The id is the whole answer. The launched child is not returned and nothing about it is kept: the
    process is found again by the `pid` its own log stamps, the same way `liveness` finds it, and a run
    holds no word for the server beside that number.
    """
    if not str(task).strip():
        raise SpawnError("a run is started with an objective: task is empty")
    if not workspace or not os.path.isdir(workspace):
        raise SpawnError(f"cwd is not a folder: {workspace}")
    if not sah_tree:
        raise SpawnError("this server names no SAH tree: pass --sah-tree or set SAHW_SAH_TREE", 503)
    run_dir = claim_run_dir(runs_root)
    workspace_dir = os.path.abspath(os.path.expanduser(workspace))
    tree_dir = os.path.abspath(os.path.expanduser(sah_tree))
    prefix = list(command) if command else child_command(tree_dir)
    argv = build_argv(prefix, run_dir=run_dir, runs_root=os.path.abspath(runs_root), sah_tree=tree_dir,
                      workspace=workspace_dir, task=task,
                      max_turns=int(max_turns), max_runtime=int(max_runtime), think=think,
                      model=model, vision=models.vision_for_launch(tree_dir, named=model))
    launch(argv, child_env(tree_dir), cwd=workspace_dir)
    return os.path.basename(run_dir)
