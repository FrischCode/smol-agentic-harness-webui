"""sahw.envfile — the machine-config loader, and the precedence the command line resolves it to.

The .env fills the environment's gaps (setdefault) and never overrides a value the operator already
set, and it is found via $SAHW_ENV_FILE or the tree root. The parser is tiny: KEY=VALUE lines,
whole-line # comments, an optional `export ` prefix, one pair of matching quotes, and a value that is
everything after the first `=`. The precedence the flags use — a flag beats the environment, the
environment beats the file, the file beats the built-in default — is asserted at the one place all four
meet, which is `cli.resolve`; the loader itself is only ever asked to merge.

Every test here names its own env file and clears the keys it reads, because `apply_env_file` writes
into the real environment — that is its whole job — so a value one test merged would otherwise be
another test's ambient truth. `monkeypatch` restores what it deleted, so the write does not outlive the
test that caused it.
"""
import os

import pytest

from sahw import cli, envfile

KEYS = ("SAHW_PORT", "SAHW_RUNS_ROOT", "SAHW_SAH_TREE")


def isolate(monkeypatch, env_file):
    """One env file and no ambient values, for a test about precedence."""
    monkeypatch.setenv("SAHW_ENV_FILE", str(env_file))
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


# --- the parser -------------------------------------------------------------------------

def test_parse_reads_key_value_lines():
    got = envfile.parse_env_file("SAHW_PORT=8321\nSAHW_SAH_TREE=C:/Work/SAH\n")
    assert got == {"SAHW_PORT": "8321", "SAHW_SAH_TREE": "C:/Work/SAH"}


def test_parse_skips_blanks_and_comments():
    text = "\n# a comment\nSAHW_PORT=8321\n   \n# another\nSAHW_SAH_TREE=C:/Work/SAH\n"
    assert envfile.parse_env_file(text) == {"SAHW_PORT": "8321", "SAHW_SAH_TREE": "C:/Work/SAH"}


def test_parse_drops_the_export_prefix():
    assert envfile.parse_env_file("export SAHW_PORT=8321") == {"SAHW_PORT": "8321"}


def test_parse_strips_one_pair_of_matching_quotes():
    assert envfile.parse_env_file("SAHW_RUNS_ROOT=\"C:\\AI\\SAH\\runs\"") == {
        "SAHW_RUNS_ROOT": "C:\\AI\\SAH\\runs"}
    assert envfile.parse_env_file("SAHW_SAH_TREE='C:/Work/SAH'") == {"SAHW_SAH_TREE": "C:/Work/SAH"}


def test_parse_keeps_the_value_after_the_first_equals():
    # no inline-comment stripping: a # stays part of the value, quoted or not
    assert envfile.parse_env_file("SAHW_SAH_TREE=C:/Work/SAH#tree") == {"SAHW_SAH_TREE": "C:/Work/SAH#tree"}


def test_parse_drops_lines_without_an_equals_and_bad_keys():
    text = "not a kv line\nMY KEY=bad\n= novalue\nSAHW_PORT=8321\n"
    assert envfile.parse_env_file(text) == {"SAHW_PORT": "8321"}


def test_load_a_missing_file_is_empty(tmp_path):
    assert envfile.load_env_file(str(tmp_path / "nope.env")) == {}


def test_load_reads_a_file(tmp_path):
    path = tmp_path / "m.env"
    path.write_text("SAHW_PORT=8321\n", encoding="utf-8")
    assert envfile.load_env_file(str(path)) == {"SAHW_PORT": "8321"}


# --- the merge --------------------------------------------------------------------------

def test_apply_fills_gaps_and_returns_the_path(tmp_path, monkeypatch):
    path = tmp_path / "m.env"
    path.write_text("SAHW_PORT=8321\nSAHW_SAH_TREE=C:/Work/SAH\n", encoding="utf-8")
    isolate(monkeypatch, path)
    assert envfile.apply_env_file() == str(path)
    assert os.environ.get("SAHW_PORT") == "8321"
    assert os.environ.get("SAHW_SAH_TREE") == "C:/Work/SAH"


def test_apply_never_overrides_an_existing_value(tmp_path, monkeypatch):
    path = tmp_path / "m.env"
    path.write_text("SAHW_PORT=8321\n", encoding="utf-8")
    isolate(monkeypatch, path)
    monkeypatch.setenv("SAHW_PORT", "9000")       # the operator's shell value wins over the file
    envfile.apply_env_file()
    assert os.environ.get("SAHW_PORT") == "9000"


def test_apply_with_no_file_says_so(tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path / "missing.env")
    assert envfile.apply_env_file() is None


# --- the precedence the command line resolves ---------------------------------------------

def test_resolve_takes_the_flag_over_the_environment(tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path / "missing.env")
    monkeypatch.setenv("SAHW_PORT", "9000")
    monkeypatch.setenv("SAHW_RUNS_ROOT", str(tmp_path / "from-env"))
    args = cli.resolve(["--port", "7777"])
    assert args.port == 7777
    assert args.runs_root == os.path.abspath(str(tmp_path / "from-env"))


def test_resolve_takes_the_environment_over_the_file(tmp_path, monkeypatch):
    path = tmp_path / "m.env"
    path.write_text("SAHW_PORT=8321\nSAHW_RUNS_ROOT=C:/from/file\n", encoding="utf-8")
    isolate(monkeypatch, path)
    monkeypatch.setenv("SAHW_PORT", "9000")
    args = cli.resolve([])
    assert args.port == 9000
    assert args.runs_root == os.path.abspath("C:/from/file")


def test_resolve_takes_the_file_over_the_built_in_default(tmp_path, monkeypatch):
    path = tmp_path / "m.env"
    path.write_text("SAHW_PORT=8642\nSAHW_SAH_TREE=C:/Work/SAH\n", encoding="utf-8")
    isolate(monkeypatch, path)
    args = cli.resolve([])
    assert args.port == 8642
    assert args.sah_tree == os.path.abspath("C:/Work/SAH")


def test_resolve_falls_back_to_the_shipped_defaults(tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path / "missing.env")
    args = cli.resolve([])
    assert args.host == "127.0.0.1"
    assert args.port == cli.DEFAULT_PORT
    assert args.sah_tree == ""
    assert args.runs_root == os.path.join(os.getcwd(), "runs")


def test_resolve_refuses_a_port_that_is_not_a_number(tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path / "missing.env")
    monkeypatch.setenv("SAHW_PORT", "eighty")
    with pytest.raises(ValueError, match="SAHW_PORT"):
        cli.resolve([])
