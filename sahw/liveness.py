"""sahw.liveness — whether a pid names a process this machine still holds.

One question, in two hands — `probe_pid` for the one number, `probe_pids` for a reader holding a list of
them: given the `pid` a run stamped in its `started` line, is that process still there? The answer is
read off the operating system and never off the record, because a log cannot say it is still being
written — it can only stop saying so. That silence is exactly what this is for: a run killed, crashed, or
snatched from its terminal leaves a log that will look unfinished forever, and by then the process table
is the only witness left. That witness is named in the record: a run stamps the
`pid` of the process behind it into its `started` line, and a number is what the machine can be asked
about.

**Two questions, in this box's order.** The cheap one opens the process and reads its exit code, which
is exact for what it can reach: the code is `STILL_ACTIVE` while the process runs, and it is the reason
the process died once it has died. It cannot reach everything — measured here, `OpenProcess` refuses
123 of the 317 processes this machine is holding right now, every one of them with access refused — and
it cannot reach a death whose last handle has been closed, because the process object that carries the
exit code is freed with that handle and the number goes with it. So the refusal is asked a second
question, of the machine's list of the processes it holds: a number on that list is running, whether or
not this reader may look inside it, and a number the finished list does not hold is not running here.

**The verdict is one-sided, on purpose.** `"dead"` is a claim the page puts on a run's row, so it is
made only when the machine states it: an exit code that is not the running one, or absence from a list
that was walked to its end. An unfinished list claims nothing, so the list's own failure is the answer
that says nothing — `"unknown"`, which shows no mark. The one way a dead run is misread as live is pid
reuse — the number reborn into another process, answering `STILL_ACTIVE` or turning up on the list —
and that is a false *negative*, the safe direction for a badge: a real orphan may slip past, but a live
run is never called an orphan.

**Reuse is survived here and told apart elsewhere.** This module answers one asking of one number and
remembers nothing about the last one, so it cannot be the hand that says whether a live answer is the
run's own process or a process the machine has just named with the run's number — that needs the record
read twice, and the record is `runs`' to read. The reader that follows a log does hold both askings, and
it is where a live answer standing on a number a dead verdict was stood on becomes a fact the row and
the stop are owed (see `runs.Poll.rebirthed`).

**A verdict is about the machine it was read from.** The pids in a log belong to the box that wrote
them; the same log read on another box is a page of numbers. A number from elsewhere is not running
*here* — the process table this function reads is this box's, and a copied log's process never came with
it — so the honest answer there is the one the list gives, and the only confusion left is reuse, which
answers `"live"` and stays inside the safe direction above.
"""
from __future__ import annotations

import ctypes
import os
import signal
import sys
import time

LIVE = "live"
DEAD = "dead"
UNKNOWN = "unknown"

# `PROCESS_QUERY_LIMITED_INFORMATION` is the least-privileged handle that answers the one question
# asked here, and 259 (`STILL_ACTIVE`) is the code a process reports while it is running. The handle is
# opened, read, and closed in the same breath; nothing else about the process is asked for or kept.
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259

# The signatures this module asks kernel32 with, declared once at import, on the box that has it.
# They are correctness rather than tuning: a handle is a pointer-sized value and ctypes reads an
# undeclared return as a 32-bit int, so an undeclared `OpenProcess` hands back a truncated handle on a
# 64-bit box and every probe after it fails. `use_last_error` is the same kind of correctness for the
# list below: the walk's end is a failing call, and the code that says *which* failure it was is only
# trustworthy when ctypes captures it at the call rather than after whatever Python did next.
# `ctypes.windll`/`WinDLL` are Windows-only, which is why the block is guarded — the guard is also what
# lets this module import unchanged on a POSIX box.
if sys.platform == "win32":
    _SNAPPROCESS = 0x00000002           # the snapshot's one subject: processes, not their modules
    _NO_MORE_FILES = 18                 # the walk's clean end; any other code left the list short
    _INVALID_HANDLE = ctypes.c_void_p(-1).value

    class _ProcessEntry32(ctypes.Structure):
        """One line of the process list, as PROCESSENTRY32W: `th32ProcessID` is all this module reads,
        and the fields around it are the layout that keeps that number where the kernel writes it.
        `dwSize` is the caller's promise of the size, so the promise and the struct cannot disagree.
        """
        _fields_ = [
            ("dwSize", ctypes.c_ulong),
            ("cntUsage", ctypes.c_ulong),
            ("th32ProcessID", ctypes.c_ulong),
            ("th32DefaultHeapID", ctypes.c_size_t),   # ULONG_PTR: pointer-sized, unlike its neighbours
            ("th32ModuleID", ctypes.c_ulong),
            ("cntThreads", ctypes.c_ulong),
            ("th32ParentProcessID", ctypes.c_ulong),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.OpenProcess.restype = ctypes.c_void_p
    _KERNEL32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    _KERNEL32.GetExitCodeProcess.restype = ctypes.c_bool
    _KERNEL32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    _KERNEL32.CloseHandle.restype = ctypes.c_bool
    _KERNEL32.CloseHandle.argtypes = [ctypes.c_void_p]
    _KERNEL32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    _KERNEL32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
    _KERNEL32.Process32FirstW.restype = ctypes.c_bool
    _KERNEL32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessEntry32)]
    _KERNEL32.Process32NextW.restype = ctypes.c_bool
    _KERNEL32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessEntry32)]


def kill(pid) -> None:
    """End the process this machine holds under `pid`: the box's own termination, asked once.

    The stop act's one syscall, and deliberately a named one — the route that stops a session asks
    `liveness` to end the number it just read as live, so a test stands in for the whole of the operating
    system by replacing this function and asserts the pid it was given. `SIGTERM` through `os.kill` is how
    a win32 box ends a process from outside; there is no gentler grade here, and the session's own log is
    left exactly as the moment of the kill left it, which is the orphan's shape and the resume's own case.

    On the platforms where a process outlives its last signal, the killer also leaves the corpse: a child
    dies into a zombie until its parent reaps it, and a zombie still answers the liveness probe — live, for
    a moment after the kill landed. The waits below close that moment for the children this machine holds:
    the wait asks nothing, a child not yet down answers nothing and is asked again, and the loop's end is
    the same answer as the probe's — the kill was asked, and a corpse that still stands is the machine's to
    settle at the grade it chose. Not a child, or a corpse already collected, is the error the first wait
    raises, and it ends the asking.
    """
    os.kill(pid, signal.SIGTERM)
    if sys.platform != "win32":
        for _ in range(50):
            try:
                reaped, _ = os.waitpid(pid, os.WNOHANG)
            except OSError:
                return
            if reaped:
                return
            time.sleep(0.001)


def is_pid(value) -> bool:
    """Whether this is a number the machine can be asked about: a positive integer, and not a bool.

    The record's `started` line holds whatever the writer put under `pid` — a log from before the fact
    existed holds nothing, and a hand-written line holds anything — so this is the one place that word is
    settled, and `probe_pid` answers through it. A reader that keeps numbers for later (the tree's poll,
    holding the number it asked of) asks this before keeping one, since a value that cannot be a key
    cannot be asked about either.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def probe_pid(pid) -> str:
    """Whether this machine still holds `pid`: `"live"`, `"dead"`, or `"unknown"`.

    The argument is whatever the record's `started` line held for `pid`, and deciding whether it is a pid
    at all is this function's own work — see `is_pid`. A pid that is not a positive integer answers
    `"unknown"`: a missing number is not evidence of a death.

    One number, then, and `probe_pids` the same question asked of several. The answer is the same in
    both hands because there is one asking underneath them; a reader with a list of numbers to settle
    should hand over the list, and pay for the machine's one look at itself once.
    """
    if not is_pid(pid):
        return UNKNOWN
    return probe_pids([pid])[pid]


def probe_pids(pids) -> dict:
    """Each of these pids answered — `{pid: verdict}` — from one look at the machine.

    The same question `probe_pid` asks, in the hand that holds several numbers: every one of them is
    first asked of exactly, by opening the process and reading its exit code, and only the numbers that
    refused the handle are settled from the machine's list of what it holds. That list is the batch's
    whole point and its one shared cost: taken once for all of them instead of once per number, since
    it is the same list either way — order ten milliseconds a take, and a reader with thirty runs on
    its record has thirty numbers to settle and one machine.

    A list is taken only when some number needs it, so a batch of live pids — the ordinary batch of a
    tree with one run working — costs no list at all. A value that is not a pid is answered `"unknown"`
    without the machine being asked, the way `probe_pid` answers it; a reader holding values that cannot
    even be keys settles them with `is_pid` first, since an answer is a mapping and they could not be
    read back out of it. A reader that asks about nothing is given nothing, and on the platforms where
    one signal asks both questions at once there is no list to share, and every number is answered on
    its own.
    """
    answers: dict = {}
    refused = []
    for pid in pids:
        if not is_pid(pid):
            answers[pid] = UNKNOWN              # not a pid at all: no question to ask about it
        elif sys.platform == "win32":
            exact = _probe_handle(pid)
            if exact is None:
                refused.append(pid)             # the handle was refused: the list is the witness
            else:
                answers[pid] = exact
        else:
            answers[pid] = _probe_posix(pid)
    if refused:
        listed = _running_pids()
        for pid in refused:
            answers[pid] = UNKNOWN if listed is None else (LIVE if pid in listed else DEAD)
    return answers


def _probe_posix(pid: int) -> str:
    """`kill(pid, 0)` — the signal no handler ever sees, asked only for the error it raises.

    Success means the process is there. `ProcessLookupError` is the only answer that says it is not.
    `PermissionError` means it is there and belongs to somebody else: the claim being made is liveness,
    not ownership, and a reader without leave does not make another user's process dead. Any other
    refusal says nothing either way.

    The signal asks both of the questions the Windows branch splits in two, and asks them in one: on
    this platform a number that is no longer a process is simply not found, handle or no handle, so the
    dead run whose last handle closed years ago is answered the same as one that died a moment ago.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return DEAD
    except PermissionError:
        return LIVE
    except OSError:
        return UNKNOWN
    return LIVE


def _probe_handle(pid: int) -> str | None:
    """The exact answer for `pid` — open it, read its exit code — or None when the handle is refused.

    A handle in hand is the exact answer: the code is `STILL_ACTIVE` while the process runs, and a dead
    process object keeps reporting the code it died at — for as long as some handle is open, which is
    what the run's own spawner may or may not still be holding. A refusal is not an answer about the
    process, it is an answer about the reader's leave, and the same refusal covers a number nobody holds
    any more; the two are told apart by the list, which is why a refusal is handed back rather than
    settled here. `probe_pids` keeps the refusal and the list apart for the same reason: the list is one
    look at the machine, and several numbers are settled out of the one look.
    """
    handle = _KERNEL32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle and handle != _INVALID_HANDLE:
        try:
            code = ctypes.c_ulong()
            if not _KERNEL32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return UNKNOWN                        # a handle is not a promise; the code is the fact
            return LIVE if code.value == _STILL_ACTIVE else DEAD
        finally:
            _KERNEL32.CloseHandle(handle)
    return None


def _running_pids() -> set[int] | None:
    """Every pid this machine currently holds, or None when that list cannot be had whole.

    None is the careful half of the design: the claim built on this set is a claim about what is *not*
    in it, and a list the walk left short — the snapshot refused, the walk ending on anything but the
    clean end-of-list code — says nothing about what it missed. An empty list is treated the same way,
    because a machine with no processes is not a machine: an empty walk is a failed one, not evidence
    that every run on the record died.

    The cost is a snapshot of every process on the box, walked once (order ten milliseconds for a few
    hundred of them here), and it is paid only for a pid that refused the handle: a live run and a run
    whose spawner still holds its process are answered without it.
    """
    snapshot = _KERNEL32.CreateToolhelp32Snapshot(_SNAPPROCESS, 0)
    if not snapshot or snapshot == _INVALID_HANDLE:
        return None
    try:
        entry = _ProcessEntry32()
        entry.dwSize = ctypes.sizeof(_ProcessEntry32)
        found = set()
        stepping = _KERNEL32.Process32FirstW(snapshot, ctypes.byref(entry))
        while stepping:
            found.add(entry.th32ProcessID)
            stepping = _KERNEL32.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != _NO_MORE_FILES:
            return None
        return found or None
    finally:
        _KERNEL32.CloseHandle(snapshot)
