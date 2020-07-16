from komodoenv import update
from textwrap import dedent
import sys
import time


def test_rewrite_executable_python():
    pip = dedent("""\
    #!/usr/bin/python2
    # EASY-INSTALL-ENTRY-SCRIPT: 'pip==8.1.2','console_scripts','pip'
    __requires__ = 'pip==8.1.2'
    import sys
    from pkg_resources import load_entry_point

    if __name__ == '__main__':
        sys.exit(
            load_entry_point('pip==8.1.2', 'console_scripts', 'pip')()
        )""")

    lines = pip.splitlines()
    lines[0] = "#!/prog/res/komodo/bin/python"

    assert "\n".join(lines) == update.rewrite_executable("/prog/res/komodo/bin/pip", pip)


def test_rewrite_executable_binary():
    with open("/bin/sh", "rb") as f:
        sh = f.read()

    expect = dedent("""\
    #!/bin/bash
    export LD_LIBRARY_PATH=/prog/res/komodo/lib:/prog/res/komodo/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
    /prog/res/komodo/bin/bash "$@"
    """)

    assert expect == update.rewrite_executable("/prog/res/komodo/bin/bash", sh)


def test_rewrite_executable_other_shebang():
    gem = dedent("""\
    #!/prog/res/komodo/bin/ruby
    #--
    # Copyright 2006 by Chad Fowler, Rich Kilmer, Jim Weirich and others.
    # All rights reserved.
    # See LICENSE.txt for permissions.
    #++

    require 'rubygems'
    require 'rubygems/gem_runner'
    require 'rubygems/exceptions'

    required_version = Gem::Requirement.new ">= 1.8.7"

    unless required_version.satisfied_by? Gem.ruby_version then
      abort "Expected Ruby Version #{required_version}, is #{Gem.ruby_version}"
    end

    args = ARGV.clone

    begin
      Gem::GemRunner.new.run args
    rescue Gem::SystemExitException => e
      exit e.exit_code
    end""")

    expect = dedent("""\
    #!/bin/bash
    export LD_LIBRARY_PATH=/prog/res/komodo/lib:/prog/res/komodo/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
    /prog/res/komodo/bin/gem "$@"
    """)

    assert expect == update.rewrite_executable("/prog/res/komodo/bin/gem", gem)


def test_track(tmpdir):
    update.KOMODO_ROOT = str(tmpdir)
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()

        actual = update.current_track("bleeding")
        assert actual["tracked-release"] == "bleeding"
        assert actual["current-release"] == "bleeding"
        assert abs(actual["mtime-release"] - time.time()) <= 1.0  # This *could* cause false-negatives if for


def test_track_symlink(tmpdir):
    update.KOMODO_ROOT = str(tmpdir)
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()
        (tmpdir / "stable").mksymlinkto("bleeding")

        actual = update.current_track("stable")
        assert actual["tracked-release"] == "stable"
        assert actual["current-release"] == "bleeding"
        assert abs(actual["mtime-release"] - time.time()) <= 1.0  # This *could* cause false-negatives if for


def test_should_update_trivial(tmpdir):
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()

        update.KOMODO_ROOT = str(tmpdir)
        config = update.current_track("bleeding")
        assert not update.should_update(config)


def test_should_update_time(tmpdir):
    update.KOMODO_ROOT = str(tmpdir)
    with tmpdir.as_cwd():
        (tmpdir / "bleeding").mkdir()

        config = update.current_track("bleeding")

        (tmpdir / "bleeding").remove()
        (tmpdir / "bleeding").mkdir()
        assert update.should_update(config)


def test_should_update_symlink(tmpdir):
    update.KOMODO_ROOT = str(tmpdir)
    with tmpdir.as_cwd():
        (tmpdir / "a").mkdir()
        (tmpdir / "b").mkdir()
        (tmpdir / "stable").mksymlinkto("a")

        config = update.current_track("stable")

        (tmpdir / "stable").remove()
        (tmpdir / "stable").mksymlinkto("b")
        assert update.should_update(config)
