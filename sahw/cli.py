"""sahw.cli — the command line: which machine this server speaks for, and where it listens.

One mode, no subcommands: parse, then listen. The flags are the five a person needs when the box's own
config file is not what they meant — `--port`, `--host`, `--runs-root`, `--sah-tree`, `--stream-poll`
— and each falls back the same way, in one order worth stating: **a flag beats the environment,
the environment beats the machine's config file, and the file beats the built-in default.** The first
two are the same thing here (`envfile.apply_env_file` merges with setdefault, so the environment is
already the file filled in), which leaves the parser's own default as the last voice — the shipped
shape, before anyone said anything about this box.

`resolve` is separated from `build` because those are two questions: what did the invocation mean, and
what happens next. The first is answerable in a test; the second blocks forever on purpose.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

from sahw import envfile, runs, server

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8321


def _port_from_env() -> int:
    """The port the environment names, or the shipped default.

    A value that is not a number is refused with the key that holds it rather than quietly becoming the
    default: an operator who typed `SAHW_PORT=eighty` wants to be told, and a server that came up on
    another port than the file said is the worse mistake of the two.
    """
    raw = os.environ.get("SAHW_PORT", "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"SAHW_PORT is not a number: {raw!r}") from exc


def _stream_poll_from_env() -> float:
    """The stream's own poll, in seconds: the environment's word, or the shipped default.

    A word that is not a positive, finite number of seconds is refused with the key that holds it,
    the way a bad port is: a server that polls at zero spins its reader against a file, and one that
    sleeps an infinity never hands over a second fragment — neither is the pace the operator meant.
    """
    raw = os.environ.get("SAHW_STREAM_POLL", "").strip()
    if not raw:
        return runs.POLL_SECONDS
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"SAHW_STREAM_POLL is not a number of seconds: {raw!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"SAHW_STREAM_POLL must be a positive, finite number of seconds: {raw!r}")
    return value


def resolve(argv: list[str]) -> argparse.Namespace:
    """The invocation, as the server wants it: host, port, and the two absolute paths.

    The machine's config is merged before the parser is built, because every default below consults the
    environment — that ordering is the whole precedence rule, in one line and in the right order. The
    paths are made absolute here, once: the runs root is where the logs are read and written and the SAH
    tree is what a child process is launched with, and neither question is asked of a working directory
    that belongs to whatever called the server.
    """
    envfile.apply_env_file()
    parser = argparse.ArgumentParser(prog="sahw", description="SAHW — SAH's companion web UI")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help="the address to listen on (default 127.0.0.1: this box only)")
    parser.add_argument("--port", type=int, default=_port_from_env(),
                        help=f"the port to listen on (default {DEFAULT_PORT}, or SAHW_PORT)")
    parser.add_argument("--runs-root", dest="runs_root",
                        default=os.environ.get("SAHW_RUNS_ROOT", ""),
                        help="the folder of run folders to list and stream (SAHW_RUNS_ROOT; default "
                             "./runs under the working directory)")
    parser.add_argument("--sah-tree", dest="sah_tree",
                        default=os.environ.get("SAHW_SAH_TREE", ""),
                        help="the SAH tree to launch runs from (SAHW_SAH_TREE); unset, the API lists the "
                             "logs it can read and POST /api/runs refuses")
    parser.add_argument("--no-open", dest="no_open", action="store_true",
                        default=os.environ.get("SAHW_NO_OPEN", "").strip().lower() in ("1", "true", "yes"),
                        help="refuse the open act: the server never opens a window on this machine "
                             "(SAHW_NO_OPEN) — the e2e discipline, that a probe's server never opens "
                             "what an operator would open")
    parser.add_argument("--stream-poll", dest="stream_poll", type=float, default=_stream_poll_from_env(),
                        help=f"how often a followed run's stream asks its log whether it grew, in "
                             f"seconds (SAHW_STREAM_POLL; default {runs.POLL_SECONDS}) — the run's "
                             "trace is drained on that same look, so this is the pace the live pane "
                             "fills")
    args = parser.parse_args(argv)
    args.runs_root = os.path.abspath(os.path.expanduser(args.runs_root or "runs"))
    args.sah_tree = os.path.abspath(os.path.expanduser(args.sah_tree)) if args.sah_tree else ""
    return args


def build(argv: list[str], out, err) -> int:
    """Resolve the invocation, say what is being served, and block on serve_forever."""
    try:
        args = resolve(argv)
    except ValueError as bad:
        print(f"sahw: {bad}", file=err)
        return 2
    try:
        httpd = server.make_server(args.host, args.port, runs_root=args.runs_root,
                                   sah_tree=args.sah_tree, open_paths=not args.no_open,
                                   stream_poll=args.stream_poll)
    except OSError as refused:
        print(f"sahw: cannot listen on {args.host}:{args.port}: {refused}", file=err)
        return 1
    print(f"sahw: http://{args.host}:{args.port}/", file=out)
    print(f"sahw:   runs root {args.runs_root}", file=out)
    print(f"sahw:   sah tree {args.sah_tree or 'none: POST /api/runs will refuse'}", file=out)
    print(f"sahw:   stream poll {args.stream_poll:g}s", file=out)
    print(f"sahw:   web {httpd.site.web_dir}", file=out)
    opened = "refused (--no-open)" if args.no_open else "the machine's own window"
    print(f"sahw:   open {opened}", file=out)
    out.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("sahw: stopped", file=out)
    finally:
        httpd.server_close()
    return 0


def main(argv=None) -> int:
    """The module entry point: hand `sys.argv` (or the argv passed) to `build`."""
    return build(list(sys.argv[1:] if argv is None else argv), sys.stdout, sys.stderr)
