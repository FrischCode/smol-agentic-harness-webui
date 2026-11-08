"""sahw.files — the three shapes the folder browser, the file preview and the picture route are given.

What is asserted is the ordering rule, the two caps and their flags, and the refusals a route has to be
able to answer with a code: a path that is not there, a folder where a file was asked for, a file that is
not text, and a name that claims no picture kind.
"""
import builtins
import pytest

from sahw import files

# A picture's worth of bytes, as much of one as a reader needs: the eight every png opens with and then
# anything at all, because this reader never looks inside — it hands the bytes back and takes the mime
# from the name, which is the whole of the deal between a route and a browser's image frame.
PICTURE = b"\x89PNG\r\n\x1a\nthe rest of a very small picture"


def test_a_folder_lists_directories_first_and_then_files_each_alphabetical(tmp_path):
    (tmp_path / "zebra").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "apple.txt").write_text("a", encoding="utf-8")
    (tmp_path / "Banana.txt").write_text("b", encoding="utf-8")
    assert files.list_dir(str(tmp_path)) == [
        {"name": "docs", "dir": True},
        {"name": "zebra", "dir": True},
        {"name": "apple.txt", "dir": False},
        {"name": "Banana.txt", "dir": False},
    ]


def test_a_folder_lists_every_entry_it_holds(tmp_path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".env").write_text("SAHW_PORT=8321\n", encoding="utf-8")
    assert [entry["name"] for entry in files.list_dir(str(tmp_path))] == [".venv", ".env"]


def test_an_empty_folder_is_an_empty_listing(tmp_path):
    assert files.list_dir(str(tmp_path)) == []


def test_a_file_reads_as_text_that_was_not_cut(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# hello\n", encoding="utf-8")
    assert files.read_file(str(path)) == ("# hello\n", False)


def test_a_long_file_is_cut_at_the_cap_and_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "READ_CAP", 8)
    path = tmp_path / "digits.txt"
    path.write_text("0123456789", encoding="utf-8")
    assert files.read_file(str(path)) == ("01234567", True)


def test_a_cap_that_lands_inside_a_character_drops_it_rather_than_failing(tmp_path, monkeypatch):
    # "abcdé" is six bytes: the cap falls inside the é, and a preview dies on the cut is no preview.
    monkeypatch.setattr(files, "READ_CAP", 5)
    path = tmp_path / "accent.txt"
    path.write_text("abcdé", encoding="utf-8")
    assert files.read_file(str(path)) == ("abcd", True)


def test_a_file_that_is_exactly_the_cap_is_not_reported_as_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "READ_CAP", 8)
    path = tmp_path / "eight.txt"
    path.write_text("01234567", encoding="utf-8")
    assert files.read_file(str(path)) == ("01234567", False)


def test_a_binary_file_is_refused_rather_than_returned_as_noise(tmp_path):
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\xff\xfe\x00\x00garbage")
    with pytest.raises(files.FileError) as got:
        files.read_file(str(path))
    assert got.value.status == 415


def test_a_binary_file_is_still_refused_when_it_is_longer_than_the_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "READ_CAP", 4)
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\xff\xfe\x00\x00\xfd\xfc")
    with pytest.raises(files.FileError) as got:
        files.read_file(str(path))
    assert got.value.status == 415


def test_a_path_that_is_not_there_is_404_for_both(tmp_path):
    missing = str(tmp_path / "nope")
    for call in (files.list_dir, files.read_file):
        with pytest.raises(files.FileError) as got:
            call(missing)
        assert got.value.status == 404


def test_the_wrong_kind_of_path_is_400_for_both(tmp_path):
    a_file = tmp_path / "f.txt"
    a_file.write_text("x", encoding="utf-8")
    with pytest.raises(files.FileError) as got:
        files.read_file(str(tmp_path))
    assert got.value.status == 400
    with pytest.raises(files.FileError) as got:
        files.list_dir(str(a_file))
    assert got.value.status == 400


# --- the picture reader ---------------------------------------------------------------------------------

def test_a_picture_reads_as_the_bytes_it_was_written_with_the_mime_its_name_claims(tmp_path):
    """The bytes, never a decoding: a browser paints the file as written, and text is the other reader's.

    The pair is the contract one response is built from — body and `Content-Type` — so both are read here
    from one path, and the read is the file on disk: the whole bytes, which is what the frame owes.
    """
    path = tmp_path / "shot.png"
    path.write_bytes(PICTURE)
    assert files.read_image(str(path)) == PICTURE
    assert files.picture_type(str(path)) == "image/png"


def test_every_kind_the_record_can_name_is_answered_and_the_name_is_only_a_claim():
    """The kinds a `read` receipt and a browser agree on, both spellings of one of them, any casing.

    `picture_type` reads the extension and nothing else, which is the point: deciding whether the bytes are
    what the name says belongs to a reader holding the bytes, and this answer only chooses the mime a
    browser paints from. `.jpg` and `.jpeg` are one kind on the wire, so both spellings answer `image/jpeg`.
    """
    for name, kind in (("a.png", "image/png"), ("a.jpg", "image/jpeg"), ("a.jpeg", "image/jpeg"),
                       ("a.gif", "image/gif"), ("a.bmp", "image/bmp"), ("a.webp", "image/webp"),
                       (r"C:\shots\SHOT.PNG", "image/png"), ("shot.WebP", "image/webp")):
        assert files.picture_type(name) == kind
    for name in ("notes.md", "no-extension", "archive.tar.gz", "shot.pn", "folder.png/"):
        assert files.picture_type(name) == ""


def test_a_name_that_claims_no_picture_kind_is_the_text_readers_own_refusal(tmp_path):
    """415 — the code the text reader gives a file that is not text, for the same reason.

    The caller picked the wrong reader; the file is not the kind the route asked for. A picture's own
    bytes in a file whose name claims none still get the refusal, because the claim is what the name is:
    a route that guessed a kind from the bytes would answer with a mime the caller never asked for.
    """
    path = tmp_path / "notes.md"
    path.write_bytes(PICTURE)
    with pytest.raises(files.FileError) as got:
        files.read_image(str(path))
    assert got.value.status == 415


def test_a_picture_reads_whole_regardless_of_the_cap_the_text_reader_keeps(tmp_path, monkeypatch):
    """The cap is the text reader's, and the frame owes the whole file: a body that stops halfway is a
    picture a browser paints as a broken frame, and the clipping the text reader's flag names has no seam
    to land in a body the browser paints. The cap shrinks to nothing and the read goes to the end.
    """
    monkeypatch.setattr(files, "READ_CAP", 16)
    path = tmp_path / "shot.png"
    path.write_bytes(PICTURE)
    assert files.read_image(str(path)) == PICTURE


def test_a_picture_refuses_the_same_paths_the_text_reader_refuses(tmp_path):
    """404 a path that is not there, whatever it is called, and 400 a folder asked of the reader.

    The missing check comes first, so a name that claims nothing under a path that is not there is simply
    a path that is not there — the answer a caller needs is the one about the path, not about the name.
    """
    for missing in (str(tmp_path / "gone.png"), str(tmp_path / "gone.txt")):
        with pytest.raises(files.FileError) as got:
            files.read_image(missing)
        assert got.value.status == 404
    with pytest.raises(files.FileError) as got:
        files.read_image(str(tmp_path))
    assert got.value.status == 400


def test_a_picture_the_box_will_not_open_is_the_code_the_operating_systems_no_owes(tmp_path, monkeypatch):
    """403 — the text reader's own answer to the same `OSError`, pinned because no Windows `chmod` can
    produce it for real: clearing a file's read attribute on this box clears a flag the reader may still
    read past, so the failure is induced at the one call the reader makes rather than pretended at.
    """
    path = tmp_path / "shot.png"
    path.write_bytes(PICTURE)

    def denied(*_args, **_kwargs):
        raise PermissionError(13, "the box said no", str(path))

    monkeypatch.setattr(builtins, "open", denied)
    with pytest.raises(files.FileError) as got:
        files.read_image(str(path))
    assert got.value.status == 403
