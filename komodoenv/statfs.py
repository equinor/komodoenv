import sys
from ctypes import (
    CDLL,
    Structure,
    byref,
    c_int64,
    c_uint64,
    create_string_buffer,
)
from pathlib import Path

# From /usr/include/linux/magic.h
_TMPFS_MAGIC = 0x01021994
_NFS_SUPER_MAGIC = 0x00006969


class _Statfs(Structure):
    """Based on Linux' `struct statfs`. Read: man 2 statfs"""

    fsblkcnt_t = c_uint64
    fsfilcnt_t = c_uint64
    fsid_t = c_uint64

    _fields_ = (
        ("f_type", c_int64),
        ("f_bsize", c_uint64),
        ("f_blocks", fsblkcnt_t),
        ("f_bfree", fsblkcnt_t),
        ("f_bavail", fsblkcnt_t),
        ("f_files", fsfilcnt_t),
        ("f_ffree", fsfilcnt_t),
        ("f_fsid", fsid_t),
        ("f_namelen", c_int64),
        ("f_frsize", c_uint64),
        ("f_spare", c_int64 * 5),
    )


def _test_fs_type(path, f_type):
    if sys.platform != "linux":
        return

    path = Path(path)
    while not path.is_dir():
        path = path.parent

    libc = CDLL(None)
    stat = _Statfs()

    libc.statfs(create_string_buffer(str(path).encode("utf-8")), byref(stat))

    return stat.f_type == f_type


def is_tmpfs(path):
    """Test if `path` is on a `tmpfs` filesystem."""
    return _test_fs_type(path, _TMPFS_MAGIC)


def is_nfs(path):
    """Test if `path` is on a `nfs` filesystem."""
    return _test_fs_type(path, _NFS_SUPER_MAGIC)
