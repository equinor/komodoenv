#!/usr/bin/python
"""
This is the update mechanism for komodo.

Note: This script must be kept compatible with Python 2.6 as long as RHEL6 is
alive and kicking. The reason for this is that we wish to use /usr/bin/python
to avoid any dependency on komodo during the update.
"""
import os
import platform
import re
import sys
import shutil
from argparse import ArgumentParser
from textwrap import dedent


ENABLE_BASH = """\
disable_komodo () {{
    if [ -n "${{_PRE_KOMODO_PATH:-}}" ]; then
        export PATH="${{_PRE_KOMODO_PATH}}"
        unset _PRE_KOMODO_PATH
    fi
    if [ -n "${{_PRE_KOMODO_MANPATH:-}}" ]; then
        export MANPATH="${{_PRE_KOMODO_MANPATH}}"
        unset _PRE_KOMODO_MANPATH
    fi
    if [ -n "${{_PRE_KOMODO_LD_LIBRARY_PATH:-}}" ]; then
        export LD_LIBRARY_PATH="${{_PRE_KOMODO_LD_LIBRARY_PATH}}"
        unset _PRE_KOMODO_LD_LIBRARY_PATH
    fi
    if [ -n "${{_PRE_KOMODO_PS1:-}}" ]; then
        export PS1="${{_PRE_KOMODO_PS1}}"
        unset _PRE_KOMODO_PS1
    fi
    if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ]; then
        hash -r
    fi

    unset KOMODO_RELEASE
    unset ERT_LSF_SERVER

    if [ ! "${{1:-}}" = "preserve_disable_komodo" ]; then
        unset -f disable_komodo
    fi
}}

# unset irrelevant variables
disable_komodo preserve_disable_komodo

export KOMODO_RELEASE={komodoenv_prefix}

export _PRE_KOMODO_PATH="$PATH"
export PATH={komodoenv_prefix}/root/bin:{komodoenv_prefix}/root/shims${{PATH:+:${{PATH}}}}

export _PRE_KOMODO_MANPATH="${{MANPATH:-}}"
export MANPATH={komodoenv_prefix}/root/share/man:{komodo_prefix}/root/share/man${{MANPATH:+:${{MANPATH}}}}

export _PRE_KOMODO_LD_LIBRARY_PATH="${{LD_LIBRARY_PATH:-}}"
unset LD_LIBRARY_PATH

export _PRE_KOMODO_PS1="${{PS1:-}}"
export PS1="({komodoenv_release} + {komodo_release}) ${{PS1:-}}"

local_script="{komodo_prefix}/local"
if [ -e "$local_script" ]; then
    source "$local_script"
fi

if [ -n "${{BASH:-}}" -o -n "${{ZSH_VERSION:-}}" ]; then
    hash -r
fi

if [ -d {komodo_prefix}/motd/scripts ]
then
    for f in {komodo_prefix}/motd/scripts/*
    do
        $f
    done
fi

if [ -d {komodo_prefix}/motd/messages ]
then
    cat {komodo_prefix}/motd/messages/*
fi

{komodoenv_prefix}/root/bin/komodoenv-update --check
"""


ENABLE_CSH = """\
alias disable_komodo '\\\\
    test $?_PRE_KOMODO_PATH != 0 && setenv PATH "$_PRE_KOMODO_PATH" && unsetenv _PRE_KOMODO_PATH;\\\\
    test $?_PRE_KOMODO_MANPATH != 0 && setenv MANPATH "$_PRE_KOMODO_MANPATH" && unsetenv _PRE_KOMODO_MANPATH;\\\\
    test $?_PRE_KOMODO_LD_PATH != 0 && setenv LD_LIBRARY_PATH "$_PRE_KOMODO_LD_PATH" && unsetenv _PRE_KOMODO_LD_PATH;\\\\
    test $?_KOMODO_OLD_PROMPT != 0 && set prompt="$_KOMODO_OLD_PROMPT" && unsetenv _KOMODO_OLD_PROMPT;\\\\
    test "\\!:*" != "preserve_disable_komodo" && unalias disable_komodo;\\\\
    unsetenv KOMODO_RELEASE;\\\\
    unsetenv ERT_LSF_SERVER;\\\\
    rehash;\\\\
    '
rehash
disable_komodo preserve_disable_komodo

if $?PATH then
    setenv _PRE_KOMODO_PATH "$PATH"
    setenv PATH {komodoenv_prefix}/root/bin:{komodoenv_prefix}/root/shims:$PATH
else
    setenv PATH {komodoenv_prefix}/root/bin:{komodoenv_prefix}/root/shims
endif

if $?MANPATH then
    setenv _PRE_KOMODO_MANPATH "$MANPATH"
    setenv MANPATH {komodoenv_prefix}/root/share/man:{komodo_prefix}/root/share/man:$MANPATH
else
    setenv MANPATH {komodoenv_prefix}/root/share/man:{komodo_prefix}/root/share/man:
endif

if $?LD_LIBRARY_PATH then
    setenv _PRE_KOMODO_LD_PATH "$LD_LIBRARY_PATH"
    unsetenv LD_LIBRARY_PATH
endif

setenv KOMODO_RELEASE {komodoenv_prefix}

set local_script={komodo_prefix}/local.csh
if ( -r $local_script) then
    source $local_script
endif

# Could be in a non-interactive environment,
# in which case, $prompt is undefined and we wouldn't
# care about the prompt anyway.
if ( $?prompt ) then
    setenv _KOMODO_OLD_PROMPT "$prompt"
    set prompt = "[{komodoenv_release} + {komodo_release}] $prompt"
endif

rehash

if ( -d {komodo_prefix}/motd/scripts ) then
    foreach f ({komodo_prefix}/motd/scripts/*)
        $f
    end
endif

if ( -d {komodo_prefix}/motd/messages ) then
    cat {komodo_prefix}/motd/messages/*
endif

{komodoenv_prefix}/root/bin/komodoenv-update --check
"""


if sys.version_info < (3,):
    PY2 = True
    PY3 = False
    text_type = unicode  # noqa
    binary_type = str
else:
    PY2 = False
    PY3 = True
    text_type = str
    binary_type = bytes  # noqa


def ensure_binary(s):
    """A version of six.ensure_binary that is compatible with Python 2.6"""
    if isinstance(s, text_type):
        return s.encode("utf-8", "strict")
    elif isinstance(s, binary_type):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


def ensure_str(s):
    """A version of six.ensure_str that is compatible with Python 2.6"""
    if not isinstance(s, (text_type, binary_type)):
        raise TypeError("not expecting type '%s'" % type(s))
    if PY2 and isinstance(s, text_type):
        s = s.encode("utf-8", "strict")
    elif PY3 and isinstance(s, binary_type):
        s = s.decode("utf-8", "strict")
    return s


def read_config():
    with open(
        os.path.join(os.path.dirname(__file__), "..", "..", "komodoenv.conf")
    ) as f:
        lines = f.readlines()
    config = {}
    for line in lines:
        try:
            split_at = line.index("=")
        except ValueError:
            continue
        else:
            key = line[:split_at].strip()
            val = line[split_at + 1 :].strip()
            config[key] = val

    if "komodo-root" not in config:
        config["komodo-root"] = "/prog/res/komodo"

    return config


def rhel_version():
    """Return the current running RHEL version as "rhelX" where X is the major
    version. "none" if not on RHEL.

    """
    if not hasattr(platform, "dist") or platform.dist()[0] != "redhat":
        return "none"
    return "rhel" + platform.dist()[1].split(".")[0]


def check_same_distro(config):
    """Python might not run properly on a different distro than the one that
    komodoenv was first generated for. Returns True if the distro in the config
    matches ours, False otherwise.

    """
    if not hasattr(platform, "dist"):
        return

    confdist = config.get("linux-dist", "")
    thisdist = "-".join(platform.dist())
    if confdist == thisdist:
        return

    sys.stderr.write(
        "Warning: Current distribution '{current}' doesn't match the one that "
        "was used to generate this environment '{config}'. You might need to "
        "recreate this komodoenv\n".format(current=thisdist, config=confdist)
    )


def get_pkg_version(config, srcpath, package="komodoenv"):
    """Locate `package`'s version in the current komodo distribution. This format is
    defined in PEP 376 "Database of Installed Python Distributions".

    Returns None if package wasn't found.
    """
    pkgdir = os.path.join(
        srcpath, "lib", "python" + config["python-version"], "site-packages"
    )
    pattern = re.compile("^{}-(.+).dist-info".format(package))

    for name in os.listdir(pkgdir):
        match = pattern.match(name)
        if match is not None:
            return match[1]


def can_update(config):
    """Compares the version of komodoenv that built the release with the one in the
    one we want to update to. If the major versions are the same, we know the
    layout is identical, and can be safely updated with this script.

    """
    version = get_pkg_version(
        config, os.path.join(config["komodo-root"], config["tracked-release"], "root")
    )
    if "komodoenv-version" not in config or version is None:
        return False

    current_maj = int(config["komodoenv-version"].split(".")[0])
    updated_maj = int(version.split(".")[0])

    return current_maj == updated_maj


def write_config(config):
    with open(
        os.path.join(os.path.dirname(__file__), "..", "..", "komodoenv.conf"), "w"
    ) as f:
        for key, val in config.items():
            f.write("{key} = {val}\n".format(key=key, val=val))


def current_track(config):
    path = os.path.join(config["komodo-root"], config["tracked-release"])

    rp = os.path.realpath(path)
    st = os.stat(path)

    config = {
        "tracked-release": config["tracked-release"],
        "current-release": os.path.basename(rp),
        "mtime-release": str(st.st_mtime),
    }

    return config


def should_update(config, current):
    return any(
        [
            config[x] != current[x]
            for x in ("tracked-release", "current-release", "mtime-release")
        ]
    )


def enable_script(fmt, komodo_prefix, komodoenv_prefix):
    return fmt.format(
        komodo_prefix=komodo_prefix,
        komodo_release=os.path.basename(komodo_prefix),
        komodoenv_prefix=komodoenv_prefix,
        komodoenv_release=os.path.basename(komodoenv_prefix),
    )


def update_enable_script(komodo_prefix, komodoenv_prefix):
    with open(os.path.join(komodoenv_prefix, "enable"), "w") as f:
        f.write(enable_script(ENABLE_BASH, komodo_prefix, komodoenv_prefix))
    with open(os.path.join(komodoenv_prefix, "enable.csh"), "w") as f:
        f.write(enable_script(ENABLE_CSH, komodo_prefix, komodoenv_prefix))


def rewrite_executable(path, python, text):
    path = os.path.realpath(path)
    root = os.path.realpath(os.path.join(path, "..", ".."))
    libs = os.pathsep.join((os.path.join(root, "lib"), os.path.join(root, "lib64")))

    newline_pos = text.find(b"\n")
    if (
        text[:2] == b"#!"
        and newline_pos >= 0
        and text[:newline_pos].find(b"python") >= 0
    ):
        return ensure_binary(
            "#!{python}{rest}".format(
                python=python, rest=ensure_str(text[newline_pos:])
            )
        )

    return ensure_binary(
        dedent(
            """\
    #!/bin/bash
    export LD_LIBRARY_PATH={libs}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}
    exec -a "$0" "{prog}" "$@"
    """
        ).format(libs=libs, prog=path)
    )


def update_bins(srcpath, dstpath):
    python = os.path.join(dstpath, "root", "bin", "python")
    shimdir = os.path.join(dstpath, "root", "shims")
    if os.path.isdir(shimdir):
        shutil.rmtree(shimdir)

    os.mkdir(shimdir)
    for name in os.listdir(os.path.join(srcpath, "root", "bin")):
        shimpath = os.path.join(dstpath, "root", "shims", name)
        path = os.path.join(srcpath, "root", "libexec", name)
        if not os.path.isfile(path):
            path = os.path.join(srcpath, "root", "bin", name)
        if not os.path.isfile(path):  # if folder, ignore
            continue

        with open(path) as f:
            text = f.read()
        with open(shimpath, "w") as f:
            f.write(rewrite_executable(path, python, text))
        os.chmod(shimpath, 0o755)


def parse_args(args):
    if args is None:
        args = sys.argv[1:]

    ap = ArgumentParser()
    ap.add_argument(
        "--check",
        action="store_true",
        default=False,
        help="Check if this komodoenv can be updated",
    )

    return ap.parse_args(args)


def main(args=None):
    args = parse_args(args)

    config = read_config()
    current = current_track(config)
    if not should_update(config, current):
        return

    check_same_distro(config)

    if args.check and not can_update(config):
        sys.exit("Warning: Your komodoenv is out of date. You will need to recreate komodo")

    elif args.check:
        sys.exit(
            dedent(
                """\
        Warning: Your komodoenv is out of date. To update to the latest komodo release ({rel}), run the following command:

        \tkomodoenv-update

        """.format(
                    rel=os.path.basename(current["current-release"])
                )
            )
        )

    config.update(current)
    write_config(config)

    srcpath = os.path.join(config["komodo-root"], config["current-release"])
    dstpath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    update_bins(srcpath, dstpath)
    update_enable_script(srcpath, dstpath)


if __name__ == "__main__":
    main()
