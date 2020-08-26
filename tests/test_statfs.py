from pathlib import Path
from komodoenv import statfs


def test_statfs():
    """We test with tmpfs because we know it exists on every Linux system. This test
    may be flaky depending on what Ubuntu decides to do in the future.

    """
    assert statfs.is_tmpfs("/") is False
    assert statfs.is_tmpfs("/dev/shm") is True

    # It isn't usual to find NFS on an arbitrary Linux installation, nor is it
    # trivial to fake one. Let's just test that these are *not* NFS and hope for
    # the best.
    assert not statfs.is_nfs("/")
    assert not statfs.is_nfs("/dev/shm")


def test_pathlib():
    assert statfs.is_tmpfs(Path("/dev/shm"))
    assert not statfs.is_nfs(Path("/"))


def test_dir_not_exist():
    assert statfs.is_tmpfs("/dev/shm/this/directory/doesnt/exist/yet")
