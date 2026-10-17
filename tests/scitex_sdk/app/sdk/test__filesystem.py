#!/usr/bin/env python3
# Timestamp: 2026-03-13
# File: tests/test__filesystem.py

"""Tests for FileSystemBackend."""

import pytest

from scitex_sdk.app.sdk._filesystem import FileSystemBackend


@pytest.fixture
def backend(tmp_path):
    """Create a FileSystemBackend rooted at a temp directory."""
    return FileSystemBackend(tmp_path)


class TestRead:
    def test_read_text_backend_read_hello_txt_world(self, backend, tmp_path):
        # Arrange
        # Act
        (tmp_path / "hello.txt").write_text("world", encoding="utf-8")
        # Assert
        assert backend.read("hello.txt") == "world"

    def test_read_binary_backend_read_data_bin_binary_true_b_x00_x01_x02(self, backend, tmp_path):
        # Arrange
        # Act
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
        # Assert
        assert backend.read("data.bin", binary=True) == b"\x00\x01\x02"

    def test_read_missing_raises(self, backend):
        # Arrange
        # Act
        # Assert
        with pytest.raises(FileNotFoundError):
            backend.read("nonexistent.txt")


class TestWrite:
    def test_write_text_tmp_path_out_txt_read_text_encoding_utf_8_hello(self, backend, tmp_path):
        # Arrange
        # Act
        backend.write("out.txt", "hello")
        # Assert
        assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hello"

    def test_write_binary_tmp_path_out_bin_read_bytes_b_xff_xfe(self, backend, tmp_path):
        # Arrange
        # Act
        backend.write("out.bin", b"\xff\xfe")
        # Assert
        assert (tmp_path / "out.bin").read_bytes() == b"\xff\xfe"

    def test_write_creates_parents(self, backend, tmp_path):
        # Arrange
        # Act
        backend.write("sub/dir/file.txt", "nested")
        # Assert
        assert (tmp_path / "sub" / "dir" / "file.txt").exists()


class TestList:
    def test_list_root_a_txt_in_result(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.yaml").touch()
        # Act
        result = backend.list()
        # Act
        # Assert
        # Assert
        assert "a.txt" in result

    def test_list_root_b_yaml_in_result(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.yaml").touch()
        # Act
        result = backend.list()
        # Act
        # Assert
        # Assert
        assert "b.yaml" in result


    def test_list_with_extension_filter_b_yaml_in_result(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.yaml").touch()
        # Act
        result = backend.list(extensions=[".yaml"])
        # Act
        # Assert
        # Assert
        assert "b.yaml" in result

    def test_list_with_extension_filter_a_txt_not_in_result(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.yaml").touch()
        # Act
        result = backend.list(extensions=[".yaml"])
        # Act
        # Assert
        # Assert
        assert "a.txt" not in result


    def test_list_empty_dir(self, backend):
        # Arrange
        # Act
        result = backend.list("nonexistent")
        # Assert
        assert result == []


class TestExists:
    def test_exists_true_backend_exists_present_txt_is_true(self, backend, tmp_path):
        # Arrange
        # Act
        (tmp_path / "present.txt").touch()
        # Assert
        assert backend.exists("present.txt") is True

    def test_exists_false_backend_exists_absent_txt_is_false(self, backend):
        # Arrange
        # Act
        # Assert
        assert backend.exists("absent.txt") is False


class TestDelete:
    def test_delete_file_not_tmp_path_doomed_txt_exists(self, backend, tmp_path):
        # Arrange
        (tmp_path / "doomed.txt").write_text("bye", encoding="utf-8")
        # Act
        backend.delete("doomed.txt")
        # Assert
        assert not (tmp_path / "doomed.txt").exists()

    def test_delete_missing_raises(self, backend):
        # Arrange
        # Act
        # Assert
        with pytest.raises(FileNotFoundError):
            backend.delete("ghost.txt")


class TestRename:
    def test_rename_not_tmp_path_old_txt_exists(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "old.txt").write_text("content", encoding="utf-8")
        # Act
        backend.rename("old.txt", "new.txt")
        # Act
        # Assert
        # Assert
        assert not (tmp_path / "old.txt").exists()

    def test_rename_tmp_path_new_txt_read_text_encoding_utf_8_content(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "old.txt").write_text("content", encoding="utf-8")
        # Act
        backend.rename("old.txt", "new.txt")
        # Act
        # Assert
        # Assert
        assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "content"


    def test_rename_missing_raises(self, backend):
        # Arrange
        # Act
        # Assert
        with pytest.raises(FileNotFoundError):
            backend.rename("nope.txt", "dest.txt")

    def test_rename_exists_raises(self, backend, tmp_path):
        # Arrange
        (tmp_path / "a.txt").touch()
        # Act
        (tmp_path / "b.txt").touch()
        # Assert
        with pytest.raises(FileExistsError):
            backend.rename("a.txt", "b.txt")


class TestCopy:
    def test_copy_tmp_path_src_txt_exists(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "src.txt").write_text("data", encoding="utf-8")
        # Act
        backend.copy("src.txt", "dst.txt")
        # Act
        # Assert
        # Assert
        assert (tmp_path / "src.txt").exists()

    def test_copy_tmp_path_dst_txt_read_text_encoding_utf_8_data(self, backend, tmp_path):
        # Arrange
        # Arrange
        (tmp_path / "src.txt").write_text("data", encoding="utf-8")
        # Act
        backend.copy("src.txt", "dst.txt")
        # Act
        # Assert
        # Assert
        assert (tmp_path / "dst.txt").read_text(encoding="utf-8") == "data"


    def test_copy_missing_raises(self, backend):
        # Arrange
        # Act
        # Assert
        with pytest.raises(FileNotFoundError):
            backend.copy("missing.txt", "dst.txt")


class TestPathTraversal:
    def test_traversal_blocked_raises_valueerror(self, backend):
        # Arrange
        # Act
        # Assert
        with pytest.raises(ValueError, match="Path traversal"):
            backend.read("../../etc/passwd")


class TestProtocolCompliance:
    def test_implements_protocol_backend_is_filesbackend(self, backend):
        # Arrange
        # Act
        from scitex_sdk.app.sdk._protocol import FilesBackend

        # Assert
        assert isinstance(backend, FilesBackend)


class TestSiblingRootContainment:
    """Two sibling owned roots: ``project`` vs ``project-other``.

    The old string-prefix check let ``../project-other/sentinel.txt`` escape
    (``<root>-other`` shares the prefix). Component containment refuses it on
    read/write/list/resolve while valid in-root requests keep working, and a
    symlink inside root pointing outside stays refused (resolve-first policy).
    """

    @pytest.fixture
    def siblings(self, tmp_path):
        (tmp_path / "project").mkdir()
        (tmp_path / "project-other").mkdir()
        (tmp_path / "project-other" / "sentinel.txt").write_text("secret")
        return tmp_path

    def test_read_sibling_escape_refused(self, siblings):
        fs = FileSystemBackend(siblings / "project")
        with pytest.raises(ValueError, match="Path traversal"):
            fs.read("../project-other/sentinel.txt")

    def test_write_sibling_escape_refused(self, siblings):
        fs = FileSystemBackend(siblings / "project")
        with pytest.raises(ValueError, match="Path traversal"):
            fs.write("../project-other/evil.txt", "x")
        assert not (siblings / "project-other" / "evil.txt").exists()

    def test_list_sibling_escape_refused(self, siblings):
        fs = FileSystemBackend(siblings / "project")
        with pytest.raises(ValueError, match="Path traversal"):
            fs.list("../project-other")

    def test_delete_rename_copy_sibling_escape_refused(self, siblings):
        fs = FileSystemBackend(siblings / "project")
        (siblings / "project" / "own.txt").write_text("own")
        with pytest.raises(ValueError, match="Path traversal"):
            fs.delete("../project-other/sentinel.txt")
        with pytest.raises(ValueError, match="Path traversal"):
            fs.rename("own.txt", "../project-other/moved.txt")
        with pytest.raises(ValueError, match="Path traversal"):
            fs.copy("own.txt", "../project-other/copied.txt")
        assert (siblings / "project" / "own.txt").exists()

    def test_valid_root_requests_still_work(self, siblings):
        fs = FileSystemBackend(siblings / "project")
        fs.write("sub/ok.txt", "fine")
        assert fs.read("sub/ok.txt") == "fine"
        assert fs.exists("sub/ok.txt")
        assert fs.list("sub") == ["sub/ok.txt"]
        assert fs.list("") == ["sub"] or "sub/ok.txt" in fs.list("sub")

    def test_symlink_pointing_outside_stays_refused(self, siblings):
        import os
        target = siblings / "project-other" / "sentinel.txt"
        link = siblings / "project" / "link.txt"
        try:
            os.symlink(target, link)
        except OSError:
            pytest.skip("symlinks unavailable")
        fs = FileSystemBackend(siblings / "project")
        with pytest.raises(ValueError, match="Path traversal"):
            fs.read("link.txt")
