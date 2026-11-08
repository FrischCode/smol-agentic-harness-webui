"""sahw.liveness — the machine asked whether a pid is still a process, of real processes only.

Nothing here stands in for the operating system. The pids are the test process's own, a child that ran
and exited, a child that was killed mid-flight, that same child after the last handle to it went, the
processes this box is holding while the battery runs, and values that are not pids at all.

The fresh deaths are held: a pid stays answerable by its exit code until the last handle to its process
object closes, so a fixture that keeps the `Popen` object it was given rules out the one thing that
could make a dead answer a lie — reuse. Holding it makes the answer a fact rather than a race, and it is
the half of the verdict the handle reaches. The other half is a death nobody holds any more, which is
what an operator's snatched terminal actually leaves behind; that case is here too, and it is answered
of the machine's list of what it is holding, not of the exit code.

The last of these is the one that keeps the badge honest: opening a process is refused for most of what
a machine lists (measured on this box: 123 of the 317 rows of its own list), so a refusal has to be told
apart from an absence, and a live run called an orphan is the mistake this battery exists to catch.

The batch — `probe_pids` — is here for the same claim at scale: the tree's poll settles every unfinished
row's verdict on every asking, so what is checked of a batch is that the list behind the refusals is
taken once rather than once per number, and not taken at all when nothing in the batch needs it.
"""
import gc
import os
import subprocess
import sys

import pytest

from sahw import liveness

# A child that does one thing: exit, cleanly or not, on the test's schedule.
EXIT_AT_ONCE = "pass"
RUN_UNTIL_KILLED = "import time; time.sleep(120)"


def spawn(code: str) -> subprocess.Popen:
    """A real child process of this interpreter, on its way and not waited for."""
    return subprocess.Popen([sys.executable, "-c", code])


def machine_pids() -> set[int]:
    """Every pid this machine currently holds, asked of the machine.

    On Windows this is the very list the module falls back to, and that is the point: what is under test
    is whether the probe believes it, since the majority of what a non-admin box lists refuses the
    handle that would otherwise answer for it. On a box with `/proc` the kernel's own directory is the
    same witness; on a box with neither, the caller has nothing to ask.
    """
    if sys.platform == "win32":
        return liveness._running_pids() or set()
    if not os.path.isdir("/proc"):
        return set()
    return {int(name) for name in os.listdir("/proc") if name.isdigit()}


def test_the_running_process_probes_live():
    assert liveness.probe_pid(os.getpid()) == "live"


def test_a_child_that_ran_and_exited_probes_dead():
    child = spawn(EXIT_AT_ONCE)
    child.wait()
    assert liveness.probe_pid(child.pid) == "dead"


def test_a_child_killed_mid_flight_probes_dead():
    """The shape a zombie run leaves: alive while it works, gone the moment it is stopped.

    Both answers are asserted because the pair is the whole point — a verdict that could only ever say
    one thing would pass the second half of this test and still be useless.
    """
    child = spawn(RUN_UNTIL_KILLED)
    assert liveness.probe_pid(child.pid) == "live"
    child.kill()
    child.wait()
    assert liveness.probe_pid(child.pid) == "dead"


def exit_code_reachable(pid: int) -> bool:
    """Whether a handle still keeps this pid's exit code answerable — the probe's first question, asked
    here plainly so the battery can say which of its two questions answered.

    A dead process can be opened only while somebody holds a handle to its object, so on this box "opens"
    and "has an exit code left to read" are one fact. The module's own call is what is reached for: the
    point is the reach of that call, not a second opinion about the death.
    """
    handle = liveness._KERNEL32.OpenProcess(liveness._PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    liveness._KERNEL32.CloseHandle(handle)
    return True


def test_dropping_the_spawner_closes_the_route_the_exit_code_travels():
    """The premise of the test below, checked rather than assumed: nothing holds a dead child once the
    object that spawned it goes, and on this box that means nothing can open the number at all.

    POSIX has no such handle to lose — its signal reaches a number that is simply gone — so the premise
    is this box's, and the test says so instead of passing for a reason it cannot claim.
    """
    if sys.platform != "win32":
        pytest.skip("the handle and the exit code behind it are this box's way of remembering a death")
    child = spawn(RUN_UNTIL_KILLED)
    child.kill()
    child.wait()
    gone = child.pid
    assert exit_code_reachable(gone), "the spawner still holds the handle it opened with"

    del child
    gc.collect()
    assert not exit_code_reachable(gone), "the object went, and the handle and the code went with it"


def test_a_death_nobody_holds_a_handle_for_still_probes_dead():
    """The orphan as the machine really keeps it, once the last handle to the child has gone.

    A spawner that drops the process object closes the handle it opened with, and the exit code goes with
    it: the number cannot be opened at all any more, which is the same answer a live-but-private process
    gives. This is the state a run whose terminal was snatched settles into — nothing above it left alive
    to remember it — so this is the verdict the page's mark is built on, and it is the verdict the second
    question exists to give. The premise that the handle really is gone is the test above's.
    """
    child = spawn(RUN_UNTIL_KILLED)
    child.kill()
    child.wait()
    gone = child.pid
    assert liveness.probe_pid(gone) == "dead", "the exit code, or the list: dead either way"

    del child
    gc.collect()
    assert liveness.probe_pid(gone) == "dead", "and the verdict outlives the handle"


def test_no_process_the_machine_still_lists_is_called_dead():
    """The one-sided rule, asked of every process on the box instead of of a stand-in for one.

    Most of what a machine lists refuses the handle the exit code is read from, and a probe that read a
    refusal as a death would put the orphan word on a live run — `System`, half of `svchost`, the
    security authorities. So every pid on the machine's own list must answer anything but `dead`. A
    process that left between the listing and the probe is not a wrong answer, so a `dead` is only held
    against the claim if a fresh listing still holds the number.
    """
    listed = machine_pids()
    if not listed:
        pytest.skip("this box gives no list of its processes to ask")

    called_dead = sorted(pid for pid in listed if liveness.probe_pid(pid) == liveness.DEAD)
    still_listed = machine_pids()
    assert [pid for pid in called_dead if pid in still_listed] == []


def test_a_value_that_is_not_a_pid_probes_unknown():
    for not_a_pid in (None, "", "4242", 0, -1, 1.5, True, [], liveness):
        assert liveness.probe_pid(not_a_pid) == "unknown", repr(not_a_pid)


def count_lists(monkeypatch):
    """The machine's list, wrapped in a tally of how many times it was taken. The batch's whole claim is
    about that count, so the count is what the battery reads rather than infers."""
    took = []
    real = liveness._running_pids

    def counting():
        took.append(1)
        return real()

    monkeypatch.setattr(liveness, "_running_pids", counting)
    return took


def unheld_death() -> int:
    """A process this battery spawned, killed, waited for, and forgot: the death the handle can no longer
    reach, which is the only kind answered of the machine's list.

    The spawner's object is what holds the handle the exit code is read through, so dropping it — and the
    collection that takes the object with it — is what leaves a number that refuses to open at all.
    """
    child = spawn(RUN_UNTIL_KILLED)
    child.kill()
    child.wait()
    gone = child.pid
    del child
    gc.collect()
    return gone


def test_a_batch_settles_many_deaths_out_of_one_look_at_the_machine(monkeypatch):
    """Several numbers, one process list.

    The batch exists because a tree of unfinished rows asks about a dozen dead numbers in one breath, and
    the machine's list is the same list for all of them. Taken per number it is a dozen looks at a machine
    that said the same thing each time; taken once it settles every number that refused the handle, which
    is what this counts. POSIX has no list to share — its signal asks both questions at once — so the
    claim is this box's, and the test says so rather than passing for a reason it cannot make.
    """
    if sys.platform != "win32":
        pytest.skip("the shared list is this box's second question; the signal needs no second question")
    deaths = [unheld_death() for _ in range(3)]
    took = count_lists(monkeypatch)
    answers = liveness.probe_pids([os.getpid()] + deaths)
    assert answers[os.getpid()] == "live", "the number that opened is answered without the list"
    assert [answers[pid] for pid in deaths] == ["dead", "dead", "dead"]
    assert len(took) == 1, "three refusals settled out of one list, not three"


def test_a_batch_asks_no_list_for_what_cannot_need_it(monkeypatch):
    """The batch's other half: a list is taken only when some number needs one.

    Live numbers open and answer themselves, values that are not pids are answered without the machine
    being looked at, and an empty batch asks nothing at all — so the ordinary poll of a tree with one run
    working costs no process list, and the tree with none costs nothing whatsoever.
    """
    took = count_lists(monkeypatch)
    assert liveness.probe_pids([]) == {}
    assert liveness.probe_pids([os.getpid()]) == {os.getpid(): "live"}
    assert liveness.probe_pids([None, 0, "7", True]) == {None: "unknown", 0: "unknown",
                                                         "7": "unknown", True: "unknown"}
    assert took == [], "nothing here is a death the list would have to settle"
