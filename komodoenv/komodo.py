from subprocess import Popen, PIPE


def get_komodoenv_version(root):
    script = "/usr/bin/env>1;source {}/enable 1>&2 2>/dev/null;/usr/bin/env>2".format(
        root
    )

    proc = Popen(["/usr/bin/bash", "-c", script], stdout=PIPE)

    pre_env, post_env = proc.communicate()

    pre_env = pre_env.decode("utf-8", "ignore").split("\n")

    return stdout.decode("utf-8", "ignore").split("\n")
