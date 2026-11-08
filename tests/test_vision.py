"""sahw.models — the machine's word about its own models, and what the three launches do with it.

Whether a run may be shown a picture is data on this box, not a switch: the SAH tree the launches are made
from holds `data/models.json`, and the profile that names the wire name the launch speaks as is the whole
of the declaration. So every test below puts the tree under its own control — a temp tree with a model file
of its own, and the environment's two links to it (`SAH_MODEL`, `SAH_ENV_FILE`) cleared or named — and reads
back the argv the launch would have started. `spawn.launch` is the standing seam, so no child is ever
started and every argv is read rather than run.

The shape of the answer is what makes this worth pinning down in both directions. A `--vision` the machine
never declared would be this server claiming a capability the box's own file contradicts; a silent `no`
where the file said yes would be a sighted model run blind, with nothing in the record to explain why. And
a file that fails the closed shape is neither: it is a machine that has not said anything, so the launch
goes without the flag and the sentence that says *why* stays available to whoever asks `load_models`.
"""
import json

import pytest

from sahw import channel, models, runs, spawn

# The wire name this box's launches speak as, once a test has named it — and the only name any profile
# below is ever about, so a lookup that reached some other profile would find nothing to answer with.
WIRE = "sighted-model"


def sah_tree(tmp_path, table="none", env=None, name="sah-tree"):
    """A SAH tree of the test's own: the model table it holds, and the `.env` it holds beside it.

    `table="none"` is a tree with no `data/models.json` at all — a fresh copy, which is a machine that
    declares nothing rather than a machine that declared it badly.
    """
    folder = tmp_path / name
    folder.mkdir(parents=True, exist_ok=True)
    if table != "none":
        data = folder / "data"
        data.mkdir(exist_ok=True)
        (data / "models.json").write_text(json.dumps(table), encoding="utf-8")
    if env is not None:
        (folder / ".env").write_text(env, encoding="utf-8")
    return str(folder)


@pytest.fixture
def the_wire(monkeypatch):
    """The environment's own answer to which model a launch speaks as, and no env file to distract it."""
    monkeypatch.setenv("SAH_MODEL", WIRE)
    monkeypatch.delenv("SAH_ENV_FILE", raising=False)
    return WIRE


@pytest.fixture
def launched(monkeypatch):
    """The launch seam, for all three verbs: every argv a launch would have started."""
    calls = []
    monkeypatch.setattr(spawn, "launch", lambda argv, env, cwd: calls.append(argv))
    return calls


def a_run(tmp_path, run_id, workspace):
    """A run folder whose record ended, standing in the workspace the follow and the fork inherit."""
    folder = tmp_path / "runs" / run_id
    folder.mkdir(parents=True, exist_ok=True)
    stamp = "2026-11-03T08:00:00+00:00"
    with open(str(folder / runs.LOG_NAME), "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"id": "000000-started", "kind": "started", "issuer": "core",
                                 "ts": stamp, "cwd": workspace, "model": WIRE, "run_id": run_id,
                                 "root": str(tmp_path / "runs")}) + "\n")
        handle.write(json.dumps({"id": "000001-ended", "kind": "ended", "issuer": "core", "ts": stamp,
                                 "reason": "complete", "exit_code": 0}) + "\n")
    return str(folder)


def spawn_one(tmp_path, tree, launched):
    """One launch of the test's own, in a workspace of its own, and the argv it would have started."""
    workspace = tmp_path / "work"
    workspace.mkdir(exist_ok=True)
    before = len(launched)
    spawn.spawn_run(str(tmp_path / "runs"), tree, str(workspace), "say what this shows",
                    command=["fake-sah"])
    assert len(launched) == before + 1, "one launch, whatever else this test asked for"
    return launched[-1]


# --- the spawn's decision -------------------------------------------------------------------------------

def test_a_profile_that_declares_vision_puts_the_flag_on_the_spawn_argv(tmp_path, the_wire, launched):
    """The flag rides where every other flag rides — before the objective, which stays the last word."""
    tree = sah_tree(tmp_path, {"sight": {"model": WIRE, "vision": True}})
    argv = spawn_one(tmp_path, tree, launched)
    assert "--vision" in argv
    assert argv[-2:] == ["--task", "say what this shows"]


def test_a_profile_that_declares_no_vision_sends_no_flag_at_all(tmp_path, the_wire, launched):
    """A declared `false` and a silent profile are the same launch: no flag, and the child's own default."""
    for table in ({"sight": {"model": WIRE, "vision": False}}, {"sight": {"model": WIRE}}):
        argv = spawn_one(tmp_path, sah_tree(tmp_path, table, name=f"tree-{len(launched)}"), launched)
        assert "--vision" not in argv, table


def test_a_tree_that_names_no_profile_at_all_declares_nothing(tmp_path, the_wire, launched):
    """No file, an empty table, and a table about another model: one answer, and it is the launch today's
    box already gets.

    This machine is in this state — `data/models.json` declares its model with `vision: false` — and the
    sight path opens when the operator writes `true` in that file.
    """
    for table, name in [("none", "tree-nofile"), ({}, "tree-empty"),
                        ({"other": {"model": "another-model", "vision": True}}, "tree-other")]:
        argv = spawn_one(tmp_path, sah_tree(tmp_path, table, name=name), launched)
        assert "--vision" not in argv, table


def test_a_model_file_that_fails_the_shape_is_no_declaration_and_no_crash(tmp_path, the_wire, launched):
    """The launch goes without the flag, and the reason stays available to whoever asks for it.

    A field the closed set does not name — `viison` is the one that would be mistyped into a yes and read
    as nothing — is refused by `load_models` naming the profile and the key, because a half-read table is
    one the operator believes they have. `vision_for_launch` is the forgiving face of the same rule: it
    answers no, and the run starts.
    """
    broken = sah_tree(tmp_path, {"sight": {"model": WIRE, "viison": True}}, name="tree-typo")
    assert "--vision" not in spawn_one(tmp_path, broken, launched)
    with pytest.raises(models.ModelError) as raised:
        models.load_models(broken)
    assert "sight" in str(raised.value) and "viison" in str(raised.value), raised.value

    not_json = tmp_path / "tree-notjson"
    (not_json / "data").mkdir(parents=True)
    (not_json / "data" / "models.json").write_text("{vision: ", encoding="utf-8")
    assert "--vision" not in spawn_one(tmp_path, str(not_json), launched)


# --- which profile is asked, and by what name -------------------------------------------------------------

def test_the_profile_that_decides_is_the_one_that_names_the_wire_either_way(tmp_path, the_wire, launched):
    """Reached by the profile's own id or by the `model` field: either agreement is the same statement.

    The table is keyed by the id the operator selects and each profile names the wire it stands for, and in
    the shape this tree ships the two are one string — so a lookup that only understood one spelling would
    answer for a machine that happened to spell it the other way.
    """
    by_field = sah_tree(tmp_path, {"sight": {"model": WIRE, "vision": True}}, name="tree-field")
    assert "--vision" in spawn_one(tmp_path, by_field, launched)
    by_id = sah_tree(tmp_path, {WIRE: {"model": "another-model", "vision": True}}, name="tree-id")
    assert "--vision" in spawn_one(tmp_path, by_id, launched)


def test_the_wire_a_launch_speaks_as_is_read_from_the_environment_then_the_trees_own_file(tmp_path,
                                                                                           monkeypatch):
    """The chain the child's own boot reads, in the order it reads it.

    The environment this server passes down beats the tree's `.env`, which beats the built-in default the
    child would fall to: the profile that decides is the one the *launch's* wire name names, so a tree with
    a `vision: true` profile for a model the launch does not speak as says nothing about this launch.
    """
    monkeypatch.delenv("SAH_MODEL", raising=False)
    monkeypatch.delenv("SAH_ENV_FILE", raising=False)
    tree = sah_tree(tmp_path, {"sight": {"model": WIRE, "vision": True}},
                    env=f"SAH_MODEL={WIRE}\n# a comment, and nothing else\n")
    assert models.vision_for_launch(tree) is True, "the tree's own .env names the wire"

    monkeypatch.setenv("SAH_MODEL", "another-model")
    assert models.vision_for_launch(tree) is False, "the environment beats the file, as it does for the child"

    # The named file is the file, wherever it stands: a tree with no `.env` of its own still speaks a wire,
    # and it is that wire the profile has to be reached by.
    monkeypatch.delenv("SAH_MODEL")
    other = tmp_path / "elsewhere.env"
    other.write_text(f"SAH_MODEL={WIRE}\n", encoding="utf-8")
    monkeypatch.setenv("SAH_ENV_FILE", str(other))
    without_env = sah_tree(tmp_path, {"sight": {"model": WIRE, "vision": True}}, name="tree-no-env")
    assert models.vision_for_launch(without_env) is True, "SAH_ENV_FILE names the file, as the child reads it"


# --- the same decision on the other two verbs -------------------------------------------------------------

def test_the_fork_and_the_follow_carry_the_decision_the_spawn_carried(tmp_path, the_wire, launched):
    """One declaration, three verbs: a branch and a continued objective ride the machine's word too.

    A `--vision` read from the tree the launch is made from, on all three command lines — the fork because
    a branch runs on this box's model as much as a fresh run does, the follow because a run that could see
    its first objective sees its second and one that could not is not made able by arriving as a follow.
    """
    workspace = tmp_path / "work"
    workspace.mkdir()
    source = a_run(tmp_path, "r20261103-080000-source", str(workspace))
    for tree, expected in [(sah_tree(tmp_path, {"sight": {"model": WIRE, "vision": True}},
                                         name="tree-sees"), True),
                           (sah_tree(tmp_path, {"sight": {"model": WIRE, "vision": False}},
                                     name="tree-blind"), False)]:
        launched.clear()
        run_dir = a_run(tmp_path, f"r20261103-080100-follow{int(expected)}", str(workspace))
        spawn.spawn_fork(str(tmp_path / "runs"), tree, source, "0", "the branch", command=["fake-sah"])
        assert ("--vision" in launched[-1]) is expected
        assert channel.post_message(str(tmp_path / "runs"), tree, run_dir, "onward",
                                    command=["fake-sah"]) == channel.FOLLOW
        assert ("--vision" in launched[-1]) is expected
        assert launched[-1][-2:] == ["--task", "onward"]
