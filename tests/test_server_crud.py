"""sahw.server — the spawn pane's mutations: mkdir, rename, delete, upload, and the raw read.

The pane reaches the whole box, so what is judged here is not what a route returns when it works but what
it refuses when it would damage something: five routes, and the guard each one owes is the assertion. Every
test is on the four things a client sees — the status, the body, the error shape, and the disk after the
answer — and the disk is what an act is judged on: a refusal that wrote something is a route that refused
itself with one hand and did the act with the other.

* **`POST /api/fs/mkdir`** stands one folder in a folder that exists, and refuses the name that is already
  taken (409), the parent that is a file (400) or nowhere (404), and every name the box itself would not
  take — a separator, a dot, a device, a drive, a glob, a quote, a space at either end (400, each, with
  nothing on disk afterwards).
* **`POST /api/fs/rename`** moves a thing to a new name in the folder it stands in and nowhere else, and
  refuses the name standing beside it, the runs root, and — the guard this plan exists for — a folder the
  standing tree counts runs in. The refusal names the count, and the count is pinned as the standing
  tree's answer rather than a fresh walk: the poll is warmed, then the record's own reader is taken away,
  and the refusal still arrives.
* **`POST /api/fs/delete`** takes one file or one empty folder off disk, and refuses a folder that holds
  something with the count it holds, the runs root and everything under it, and a workspace holding runs.
* **`POST /api/fs/upload`** streams the request's own bytes into a new file — the bytes on disk compared
  byte for byte against a body larger than the chunk the copy runs on — and refuses a name already
  standing there, a name that is not a name, and the runs root. A refusal is pinned as having read the
  body it refused: the next request on the same pooled connection is answered, and a route that refused
  without draining would answer it with the refused file's bytes as its method line.
* **`GET /api/file/raw`** answers a file's bytes whole — past the preview's cap, including a run's log
  under the runs root, because the read routes are not the guarded ones — with `Content-Disposition`
  naming the file's own name, and refuses a folder (400), a path that is not there (404), and a relative
  path (400, the rule every file route shares).

`spawn.launch` is never reached: no test here starts a run. The runs the fixture's root holds are records
on disk, which is all the tree — and so the guard — reads.
"""
import http.client
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

from sahw import runs, server

TIMEOUT = 15.0

# The run the fixture's root holds: one workspace, and however many records name it. The workspace is what
# the guards are asked about, so its run count is the fact under test rather than a detail of the fixture.
RUN_ONE = "r20261104-080000-first"
RUN_TWO = "r20261104-080100-second"

# Names no act may be given: the separator and the relative dot (a name that is a location), the devices
# this box opens instead of a file (with and without a suffix, upper and lower, because the reservation is
# neither case- nor extension-sensitive), the characters a path, a drive, a glob, a redirect and a quote
# are made of, a control character, a space at either end, and the dot at the end Windows throws away.
BAD_NAMES = ["a/b", "a\\b", ".", "..", "con", "CON", "nul.txt", "COM1", "LPT9", "a:b", "a*b", "a?b",
             'a"b', "a<b", "a>b", "a|b", "a\nb", " lead", "trail ", "trail."]

# A body bigger than the chunk an upload copies on, so the pin is on the whole file rather than on the
# first read of it: one byte of every kind, in a pattern a short file could not tell from a whole one.
BLOB = bytes(bytearray((index * 37 + 11) % 256 for index in range(300 * 1024)))


def get(url):
    """One GET as (status, headers, body bytes): everything a response can be judged on."""
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return response.status, response.headers, response.read()


def get_json(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def post_body(url, blob):
    """One POST whose body is bytes rather than a document: the upload's own shape."""
    request = urllib.request.Request(url, data=blob, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, json.loads(response.read())


def refused(url, status, body=None):
    """The JSON body of an error response, having checked it is one error of that status and no other.

    The status is asserted exactly: a route that answered 200 with a reason in the body, or 500 with the
    sentence it was supposed to build itself, has not refused the act — it has failed at it. A body rides as
    the bytes it is (a dict spelled as JSON, anything else posted whole), because the upload route's body is
    the file and no caller of this helper should have to know which of the two a route reads.
    """
    if isinstance(body, dict):
        body = json.dumps(body).encode("utf-8")
    target = url if body is None else urllib.request.Request(url, data=body, method="POST")
    with pytest.raises(urllib.error.HTTPError) as raised:
        urllib.request.urlopen(target, timeout=TIMEOUT)
    assert raised.value.code == status
    error = json.loads(raised.value.read().decode("utf-8"))
    assert set(error) == {"error"} and error["error"]
    return error["error"]


def query(**values):
    return urllib.parse.urlencode(values)


def tree_of(base):
    return get_json(f"{base}/api/runs")[1]


def listing_of(base, path):
    return get_json(f"{base}/api/fs?{query(path=path)}")[1]["entries"]


def make_log(run_dir, cwd, ts):
    """One run's record, ended: a row the tree holds and no process stands behind."""
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, runs.LOG_NAME), "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"id": "000000-started", "kind": "started", "issuer": "core",
                                 "ts": ts, "cwd": cwd, "model": "flash-next",
                                 "run_id": "run", "root": "root"}) + "\n")
        handle.write(json.dumps({"id": "000009-ended", "kind": "ended", "issuer": "core",
                                 "ts": ts.replace("08:0", "09:0"), "reason": "complete",
                                 "exit_code": 0}) + "\n")


def touch(path, text="a file, and the whole of it\n"):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


@pytest.fixture
def workspace(tmp_path):
    """The folder the fixture's runs stand in, holding one file and one folder to work with."""
    folder = tmp_path / "workspace"
    folder.mkdir()
    touch(str(folder / "notes.md"))
    (folder / "deep").mkdir()
    touch(str(folder / "deep" / "inside.txt"))
    return str(folder)


@pytest.fixture
def box(tmp_path, workspace):
    """A runs root holding two records over that workspace, and a front of one file."""
    make_log(str(tmp_path / "runs" / RUN_ONE), workspace, "2026-11-04T08:00:00+00:00")
    make_log(str(tmp_path / "runs" / RUN_TWO), workspace, "2026-11-04T08:01:00+00:00")
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<!doctype html><title>SAHW</title>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def serve(box):
    """`serve(**overrides)` — the server on a free port over the fixture's folders, and its base URL."""
    started_servers = []

    def start(**overrides):
        options = {"runs_root": str(box / "runs"), "sah_tree": str(box / "sah-tree"),
                   "web_dir": str(box / "web")}
        options.update(overrides)
        httpd = server.make_server("127.0.0.1", 0, **options)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started_servers.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for httpd in started_servers:
        httpd.shutdown()
        httpd.server_close()


# --- mkdir -----------------------------------------------------------------------------------------------

def test_mkdir_stands_a_folder(serve, workspace):
    base = serve()
    status, answer = post_json(f"{base}/api/fs/mkdir", {"path": workspace, "name": "fresh"})
    assert status == 200
    assert answer == {"ok": True, "path": os.path.join(workspace, "fresh")}
    assert os.path.isdir(os.path.join(workspace, "fresh"))
    assert {"name": "fresh", "dir": True} in listing_of(base, workspace)


def test_mkdir_refuses_a_name_already_standing(serve, workspace):
    base = serve()
    sentence = refused(f"{base}/api/fs/mkdir", 409, {"path": workspace, "name": "deep"})
    assert "taken" in sentence and "deep" in sentence
    assert os.path.isfile(os.path.join(workspace, "deep", "inside.txt")), "the folder was overwritten"


def test_mkdir_refuses_a_parent_that_is_not_a_folder(serve, workspace):
    base = serve()
    assert "not a folder" in refused(f"{base}/api/fs/mkdir", 400,
                                     {"path": os.path.join(workspace, "notes.md"), "name": "x"})
    assert "no such folder" in refused(f"{base}/api/fs/mkdir", 404,
                                       {"path": os.path.join(workspace, "nowhere"), "name": "x"})


@pytest.mark.parametrize("name", BAD_NAMES)
def test_mkdir_refuses_a_name_the_machine_will_not_take(serve, workspace, name):
    base = serve()
    sentence = refused(f"{base}/api/fs/mkdir", 400, {"path": workspace, "name": name})
    assert "bare name" in sentence or "device" in sentence, sentence
    assert sorted(os.listdir(workspace)) == ["deep", "notes.md"], "the refused folder was made"


def test_mkdir_refuses_inside_the_runs_root(serve, box):
    base = serve()
    root = str(box / "runs")
    for parent in (root, os.path.join(root, RUN_ONE), os.path.join(root, "estate")):
        sentence = refused(f"{base}/api/fs/mkdir", 409, {"path": parent, "name": "sneak"})
        assert "record" in sentence, sentence
    assert sorted(os.listdir(root)) == [RUN_ONE, RUN_TWO], "the refused folder was made"


# --- rename -----------------------------------------------------------------------------------------------

def test_rename_a_folder_and_a_file(serve, workspace):
    base = serve()
    status, answer = post_json(f"{base}/api/fs/rename",
                               {"path": os.path.join(workspace, "deep"), "name": "deeper"})
    assert status == 200
    assert answer["path"] == os.path.join(workspace, "deeper")
    assert answer["was"] == os.path.join(workspace, "deep")
    assert open(os.path.join(workspace, "deeper", "inside.txt"), encoding="utf-8").read()
    status, answer = post_json(f"{base}/api/fs/rename",
                               {"path": os.path.join(workspace, "notes.md"), "name": "notes-v2.md"})
    assert answer["path"] == os.path.join(workspace, "notes-v2.md")
    assert sorted(os.listdir(workspace)) == ["deeper", "notes-v2.md"]


def test_rename_refuses_a_name_standing_beside_it(serve, workspace):
    base = serve()
    sentence = refused(f"{base}/api/fs/rename", 409,
                       {"path": os.path.join(workspace, "notes.md"), "name": "deep"})
    assert "taken" in sentence
    assert sorted(os.listdir(workspace)) == ["deep", "notes.md"]


@pytest.mark.parametrize("name", ["a/b", "..", "con"])
def test_rename_refuses_a_name_the_machine_will_not_take(serve, workspace, name):
    base = serve()
    refused(f"{base}/api/fs/rename", 400, {"path": os.path.join(workspace, "notes.md"), "name": name})
    assert os.path.isfile(os.path.join(workspace, "notes.md"))


def test_rename_refuses_the_runs_root(serve, box):
    base = serve()
    sentence = refused(f"{base}/api/fs/rename", 409,
                       {"path": str(box / "runs"), "name": "elsewhere"})
    assert "record" in sentence
    assert os.path.isdir(str(box / "runs"))


def test_rename_refuses_a_workspace_holding_runs_naming_the_count(serve, workspace):
    base = serve()
    sentence = refused(f"{base}/api/fs/rename", 409, {"path": workspace, "name": "renamed"})
    assert "workspace of 2 run(s)" in sentence, sentence
    assert os.path.isdir(workspace)


def test_the_count_is_answered_from_the_standing_tree_not_a_walk(serve, workspace, monkeypatch):
    """The guard reads the tree the server already holds: with the record's reader taken away, still 409.

    A 500 here would say the route went and looked — a second walk over the logs to answer a question the
    rows already hold, and one that could answer differently from the page standing above it.
    """
    base = serve()
    assert len(tree_of(base)["workspaces"][0]["runs"]) == 2      # the poll is standing
    monkeypatch.setattr(runs, "describe_run",
                        lambda *args, **kwargs: pytest.fail("the guard walked the record again"))
    sentence = refused(f"{base}/api/fs/rename", 409, {"path": workspace, "name": "renamed"})
    assert "workspace of 2 run(s)" in sentence


def test_rename_stands_a_folder_the_tree_no_longer_counts(serve, box, tmp_path):
    """A folder whose runs are gone from the record is an ordinary folder again: the count decides.

    The guard is asked of the standing tree, which is the one thing that can answer it wrongly — so the
    record is moved first and the tree asked afterwards, and the rename is allowed on the answer the page
    would be shown.
    """
    base = serve()
    standing = tmp_path / "was-a-workspace"
    standing.mkdir()
    holder = str(box / "runs" / "r20261104-080200-third")
    make_log(holder, str(standing), "2026-11-04T08:02:00+00:00")
    assert "workspace of 1 run(s)" in refused(f"{base}/api/fs/rename", 409,
                                              {"path": str(standing), "name": "moved"})
    os.remove(os.path.join(holder, runs.LOG_NAME))
    status, answer = post_json(f"{base}/api/fs/rename", {"path": str(standing), "name": "now-a-folder"})
    assert status == 200
    assert answer["path"] == str(tmp_path / "now-a-folder")
    assert os.path.isdir(str(tmp_path / "now-a-folder"))


def test_rename_refuses_what_is_not_there(serve, workspace):
    base = serve()
    assert "no such file or folder" in refused(
        f"{base}/api/fs/rename", 404, {"path": os.path.join(workspace, "gone"), "name": "x"})


# --- delete -----------------------------------------------------------------------------------------------

def test_delete_a_file_and_an_empty_folder(serve, workspace):
    base = serve()
    empty = os.path.join(workspace, "empty")
    os.mkdir(empty)
    status, answer = post_json(f"{base}/api/fs/delete", {"path": os.path.join(workspace, "notes.md")})
    assert status == 200 and answer == {"ok": True, "path": os.path.join(workspace, "notes.md"),
                                        "kind": "file"}
    status, answer = post_json(f"{base}/api/fs/delete", {"path": empty})
    assert answer["kind"] == "folder"
    assert sorted(os.listdir(workspace)) == ["deep"]


def test_delete_refuses_a_folder_that_holds_something_with_its_count(serve, workspace):
    base = serve()
    sentence = refused(f"{base}/api/fs/delete", 409, {"path": os.path.join(workspace, "deep")})
    assert "not empty" in sentence and "holds 1 entry" in sentence, sentence
    assert os.path.isfile(os.path.join(workspace, "deep", "inside.txt"))
    touch(os.path.join(workspace, "deep", "second.txt"))
    sentence = refused(f"{base}/api/fs/delete", 409, {"path": os.path.join(workspace, "deep")})
    assert "holds 2 entries" in sentence, sentence


def test_delete_refuses_the_runs_root_and_everything_under_it(serve, box):
    base = serve()
    root = str(box / "runs")
    for path in (root, os.path.join(root, RUN_ONE, runs.LOG_NAME)):
        sentence = refused(f"{base}/api/fs/delete", 409, {"path": path})
        assert "record" in sentence, sentence
    assert os.path.isfile(os.path.join(root, RUN_ONE, runs.LOG_NAME))


def test_delete_refuses_a_workspace_holding_runs(serve, workspace):
    base = serve()
    sentence = refused(f"{base}/api/fs/delete", 409, {"path": workspace})
    assert "workspace of 2 run(s)" in sentence, sentence
    assert os.path.isdir(workspace)


def test_delete_refuses_what_is_not_there(serve, workspace):
    base = serve()
    assert "no such file or folder" in refused(
        f"{base}/api/fs/delete", 404, {"path": os.path.join(workspace, "gone")})


# --- upload -----------------------------------------------------------------------------------------------

def test_upload_lands_the_bytes_whole(serve, workspace):
    base = serve()
    status, answer = post_body(f"{base}/api/fs/upload?{query(path=workspace, name='blob.bin')}", BLOB)
    assert status == 200
    assert answer == {"ok": True, "path": os.path.join(workspace, "blob.bin"), "bytes": len(BLOB)}
    assert open(os.path.join(workspace, "blob.bin"), "rb").read() == BLOB


def test_upload_refuses_a_name_already_standing(serve, workspace):
    base = serve()
    before = open(os.path.join(workspace, "notes.md"), "rb").read()
    sentence = refused(f"{base}/api/fs/upload?{query(path=workspace, name='notes.md')}", 409,
                       body=b"the bytes that were not wanted\n")
    assert "taken" in sentence
    assert open(os.path.join(workspace, "notes.md"), "rb").read() == before


def test_upload_refuses_the_runs_root(serve, box):
    base = serve()
    sentence = refused(f"{base}/api/fs/upload?{query(path=str(box / 'runs'), name='drop.bin')}", 409,
                       body=b"nothing of mine belongs in the record\n")
    assert "record" in sentence
    assert sorted(os.listdir(str(box / "runs"))) == [RUN_ONE, RUN_TWO]


@pytest.mark.parametrize("name", ["a/b", "..", "con", "trail."])
def test_upload_refuses_a_name_the_machine_will_not_take(serve, workspace, name):
    base = serve()
    refused(f"{base}/api/fs/upload?{query(path=workspace, name=name)}", 400, body=b"posted\n")
    assert sorted(os.listdir(workspace)) == ["deep", "notes.md"], "the refused file was written"


def test_upload_refuses_a_target_that_is_not_a_folder(serve, workspace):
    base = serve()
    assert "not a folder" in refused(
        f"{base}/api/fs/upload?{query(path=os.path.join(workspace, 'notes.md'), name='x.bin')}",
        400, body=b"posted\n")
    assert "no such folder" in refused(
        f"{base}/api/fs/upload?{query(path=os.path.join(workspace, 'nowhere'), name='x.bin')}",
        404, body=b"posted\n")


def test_a_refused_upload_still_owes_the_connection_its_bytes(serve, workspace, box):
    """After a 409 the pooled connection answers the next request: the refused body was read, not left."""
    base = serve()
    host, port = base.split("//")[1].split(":")
    connection = http.client.HTTPConnection(host, int(port), timeout=TIMEOUT)
    try:
        connection.request("POST", f"/api/fs/upload?{query(path=workspace, name='notes.md')}",
                           body=BLOB)
        response = connection.getresponse()
        assert response.status == 409
        json.loads(response.read())
        connection.request("GET", f"/api/fs?{query(path=workspace)}")
        response = connection.getresponse()
        assert response.status == 200, "the refused body was read as the next request"
        assert [entry["name"] for entry in json.loads(response.read())["entries"]] == ["deep",
                                                                                        "notes.md"]
    finally:
        connection.close()


# --- the raw read ---------------------------------------------------------------------------------------

def test_raw_answers_the_bytes_with_the_attachment_headers(serve, workspace):
    base = serve()
    big = os.path.join(workspace, "big.txt")
    with open(big, "wb") as handle:
        handle.write(BLOB)
    status, headers, body = get(f"{base}/api/file/raw?{query(path=big)}")
    assert status == 200
    assert headers.get("Content-Type") == "application/octet-stream"
    assert headers.get("Content-Length") == str(len(BLOB))
    assert headers.get("Content-Disposition") == 'attachment; filename="big.txt"'
    assert body == BLOB, "the raw route clipped, or rewrote, what the disk holds"


def test_the_attachment_names_the_file_the_disk_holds(serve, workspace):
    """The name the browser keeps the bytes as, spelled from the file: spaces, accents and all.

    A quote in a name is the case the escaping exists for, and this box will not let a test write one — so
    the rule is pinned where it can be seen, on the names that survive the disk to reach the header, and
    `_download_name`'s docstring carries the rest.
    """
    base = serve()
    odd = touch(os.path.join(workspace, "the one - café 7.txt"))
    _status, headers, _body = get(f"{base}/api/file/raw?{query(path=odd)}")
    assert headers.get("Content-Disposition") == 'attachment; filename="the one - café 7.txt"'


def test_raw_refuses_a_folder_and_a_path_that_is_not_there(serve, workspace):
    base = serve()
    assert "not a file" in refused(f"{base}/api/file/raw?{query(path=workspace)}", 400)
    assert "no such file" in refused(
        f"{base}/api/file/raw?{query(path=os.path.join(workspace, 'gone.txt'))}", 404)


def test_raw_refuses_a_path_that_names_no_root(serve, workspace):
    base = serve()
    assert "absolute path" in refused(f"{base}/api/file/raw?{query(path='notes.md')}", 400)


def test_raw_reads_the_record_the_mutations_may_not_touch(serve, box):
    """The read routes are not guarded: the pane may look at the runs root, it may not manage it."""
    base = serve()
    log = os.path.join(str(box / "runs"), RUN_ONE, runs.LOG_NAME)
    status, _headers, body = get(f"{base}/api/file/raw?{query(path=log)}")
    assert status == 200
    assert json.loads(body.decode("utf-8").splitlines()[0])["kind"] == "started"


# --- the listing, unchanged -------------------------------------------------------------------------------

def test_the_listing_answers_what_it_always_did(serve, workspace):
    """Five routes added, one answer untouched: dirs first, then files, each alphabetical, dots and all."""
    base = serve()
    os.mkdir(os.path.join(workspace, ".hidden"))
    touch(os.path.join(workspace, "Beta.md"))
    assert listing_of(base, workspace) == [
        {"name": ".hidden", "dir": True},
        {"name": "deep", "dir": True},
        {"name": "Beta.md", "dir": False},
        {"name": "notes.md", "dir": False},
    ]
