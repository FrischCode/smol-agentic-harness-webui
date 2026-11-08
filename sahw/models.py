"""sahw.models — the machine's own word about what the models it names can do.

The SAH tree this server launches runs from is also the machine's, and the machine states its models in
`<sah_tree>/data/models.json`: a table of profile id to profile, each profile an object out of a closed
field set (`model`, `host`, `port`, `base_url`, `api_key`, `think`, `context`, `vision`) in which `model`
is the wire name a request carries and `vision` is whether that model can be shown a picture at all. The
tree ships the shape and not the values, so what is in the file is the operator's statement about this box.

**The declaration is data, and it has one home.** Whether a run may be shown a picture is therefore a
lookup here and not a switch: no flag on this server names it and no request carries it, so the one line
that opens the sight path is the operator's own — `"vision": true` in the profile the machine names — and
it opens it for every launch this box makes at once. A server with a flag of its own would be a second
declaration to disagree with the machine's.

**Read whole or refused.** A file that is not JSON, is not an object of profiles, or holds a field the
closed set does not name is a `ModelError` naming the profile and the key, and never a table half-read:
a half-read profile table is one the operator believes they have. `vision_for` is the forgiving face of
that rule — a machine that declares nothing, or declares it badly, is a machine whose models cannot be
shown a picture, so it answers `False` rather than raising, and the run that starts without `--vision` is
the run the machine asked for. The refusal stays available to anyone who needs to say *why*: it is
`load_models` that raises, and `vision_for` that answers `False`.

**`listed` is the table told to somebody else.** A face that offers the machine's models needs which
profiles exist and what endpoints they name, and it needs that without the one field a profile keeps for
the machine alone: `api_key` signs the box's requests and never leaves it, so the answer carries every
other field and the id that selects the profile. A face reading the table through this function is
reading what the operator declared, with nothing invented beside it — an empty table answers as an empty
list, and a tree that holds no file answers as None, which is the answer a route refuses with.
"""
from __future__ import annotations

import json
import os

from sahw import envfile

# A profile's closed field set: name -> the exact type the field holds. Closed rather than permissive,
# because a declaration that is quietly dropped is a declaration the machine will contradict: a profile
# whose `viison` the reader ignored would run a sighted model as a blind one, or the other way round, with
# nothing in the record to explain the difference. The types are checked as `type is`, not `isinstance`:
# a bool is an int in Python, and a port of `true` is a port of one, which is not what a number means.
PROFILE_FIELDS = {
    "model": str,         # the wire name the request carries — the one required field
    "host": str,
    "port": int,
    "base_url": str,
    "api_key": str,
    "think": str,
    "think_levels": list,   # the level words the profile's server takes: the operator's statement
    "context": int,
    "vision": bool,
}


class ModelError(Exception):
    """A model table that does not hold the shape, naming the profile and the key at fault.

    There is no HTTP code on it because no route reads it: this is a file the operator wrote, and the
    answer a route owes for it is a run started without the capability the file failed to declare. Who
    wants the sentence — a report, a boot line, a test — asks `load_models` and catches this.
    """


def models_path(sah_tree: str) -> str:
    """The table's path under the tree it belongs to."""
    return os.path.join(sah_tree, "data", "models.json")


# The field no answer carries away from the machine. A profile's key is what a request to that endpoint is
# signed with, and a route that echoed the table into a page would be handing the box's credentials to
# whichever browser is open on it. The picker needs no key — it names a profile, and the launch reaches
# the key itself, from the tree it boots in — so what travels is every other field of the profile and
# nothing of this one.
SECRET_FIELDS = ("api_key",)


def listed(sah_tree: str) -> list[dict] | None:
    """The machine's profiles as a face is answered: each named by its id, with its endpoint fields and
    none of its secrets — or None when the tree holds no table at all, which is `load_models`'s own answer
    for that case and the one a caller refuses with.

    The id is the name the face selects by and the name SAH's `--model` takes, so it is carried as a field
    of the entry rather than as a key beside it: an answer a face has to re-key is an answer that can be
    re-keyed wrong. What the id is not is a claim about the wire: the profile's own `model` field is the
    name a request carries, and the two are separate fields exactly as the table holds them.
    """
    profiles = load_models(sah_tree)
    if profiles is None:
        return None
    listed_profiles = []
    for profile_id, profile in profiles.items():
        entry = {"id": profile_id}
        entry.update({key: value for key, value in profile.items() if key not in SECRET_FIELDS})
        listed_profiles.append(entry)
    return listed_profiles


def parse_profile(profile_id: str, value) -> dict:
    """One profile, checked against the closed field set and returned as the file held it.

    `model` is the one required field — a profile that names no model selects nothing — and every field
    the shape names is optional, its absence meaningful: a field a profile leaves silent says nothing
    about that axis, and a default filled in here would be this module declaring what the machine left
    open. Nothing is defaulted, then: the dict handed back holds exactly the keys the file held.
    """
    if not profile_id:
        raise ModelError("data/models.json: a profile needs a name — an empty id selects nothing")
    if not isinstance(value, dict):
        raise ModelError(f"data/models.json: profile {profile_id!r} must be an object of fields, "
                         f"not a {type(value).__name__}")
    for key in value:
        if key not in PROFILE_FIELDS:
            raise ModelError(f"data/models.json: profile {profile_id!r} holds field {key!r}, which "
                             f"the shape does not name ({', '.join(sorted(PROFILE_FIELDS))})")
    if not isinstance(value.get("model"), str) or not value["model"]:
        raise ModelError(f"data/models.json: profile {profile_id!r} needs a non-empty model — the "
                         "wire name the request carries")
    out = {}
    for key, expected in PROFILE_FIELDS.items():
        if key not in value:
            continue
        got = value[key]
        if type(got) is not expected:
            raise ModelError(f"data/models.json: profile {profile_id!r} field {key!r} must be a "
                             f"{expected.__name__}, not a {type(got).__name__}")
        if key == "port" and not 1 <= got <= 65535:
            raise ModelError(f"data/models.json: profile {profile_id!r} port {got} is not a port "
                             "(1-65535)")
        if key == "context" and got <= 0:
            raise ModelError(f"data/models.json: profile {profile_id!r} context {got} is not a window "
                             "(a positive token count)")
        if key == "think_levels" and any(type(word) is not str for word in got):
            bad = next(word for word in got if type(word) is not str)
            raise ModelError(f"data/models.json: profile {profile_id!r} field {key!r} holds {bad!r}, "
                             f"which is not a level word (a string)")
        out[key] = got
    return out


def load_models(sah_tree: str) -> dict | None:
    """The tree's model table as `{profile id: profile}`, or None when the tree declares no file at all.

    Read whole: every profile is checked before the table is handed back, so a table that names one
    mistyped key is refused rather than selected from. A tree with no `data/models.json` is not a fault —
    it is a machine that declares nothing about its models, which is what a fresh copy of the tree is.
    """
    path = models_path(sah_tree)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            table = json.load(handle)
    except (OSError, UnicodeDecodeError) as exc:
        raise ModelError(f"data/models.json cannot be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ModelError(f"data/models.json is not JSON: {exc}") from exc
    if not isinstance(table, dict):
        raise ModelError("data/models.json must hold an object: profile id -> profile")
    return {profile_id: parse_profile(profile_id, value) for profile_id, value in table.items()}


def vision_for(wire_name: str, sah_tree: str) -> bool:
    """Whether the model this box names is one that can be shown a picture: the declaration, or False.

    The profile that answers is the one this wire name is the machine's model of — the table holds a
    profile by the id the operator selects and names the wire it stands for in its `model` field, and in
    the shipped shape the two are the same string. Either agreement is the same statement, so a profile
    reached either way is the one that decides, and any one of them declaring `vision` is enough: the
    question is what the machine said, not which spelling of its saying this caller reached.

    False is the answer for every way a machine can fail to say yes, and each is silent because none of
    them is a caller's mistake: no tree named, no file, a file that fails the shape, a wire name no
    profile names, and a profile that names the wire and leaves `vision` out or sets it false. A run
    started without `--vision` is the run such a machine asked for, and the sentence the record owes about
    a picture it could not see is SAH's to write, not this lookup's.
    """
    if not wire_name or not sah_tree:
        return False
    try:
        profiles = load_models(sah_tree)
    except ModelError:
        return False
    for profile_id, profile in (profiles or {}).items():
        if profile_id == wire_name or profile.get("model") == wire_name:
            if profile.get("vision"):
                return True
    return False


def model_reference(sah_tree: str, env: dict | None = None) -> str:
    """The wire name a run launched from this tree speaks as: `SAH_MODEL`, or "" when nothing names one.

    The chain is the launched child's own, read from where each link stands — the environment this server
    passes down beats the tree's `.env`, and the `.env` the tree holds beats the built-in default the
    child would fall to. `SAH_ENV_FILE`, when the environment names one, is the file, exactly as the
    child reads it. Nothing here resolves a profile or an endpoint: this answers which model the spawn's
    word has to ask about, which is the whole of what `vision_for` needs.
    """
    values = dict(os.environ if env is None else env)
    path = values.get("SAH_ENV_FILE") or (os.path.join(sah_tree, ".env") if sah_tree else "")
    return values.get("SAH_MODEL") or (envfile.load_env_file(path).get("SAH_MODEL", "") if path else "")


def vision_for_launch(sah_tree: str, env: dict | None = None, named: str = "") -> bool:
    """Whether to start a run from this tree with `--vision`: the two questions the launch has, in order.

    Which model the launch speaks as, and what the machine says that model can do. The pair is one
    question to a caller — `spawn`, `spawn_fork`, and the follow's relaunch each want the yes or the no and
    none of them cares which link in the chain answered — and the order is the one that cannot be got
    wrong: the model has to be named before its record can be asked.

    `named` is the model the caller is launching as, and it answers the first question before the chain
    does: a launch that was pointed at a model by the face's picker speaks as *that* model, and the
    machine's own default — `model_reference`, which is what the launch would fall to — only answers when
    none was named. Asking the default about a run that will not speak as it would be asking after the
    wrong record: the picker's model is the one the child carries in its `--model`, and sight is a fact
    about the model a run speaks as.
    """
    return vision_for(named or model_reference(sah_tree, env), sah_tree)
