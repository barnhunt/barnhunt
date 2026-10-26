# SPDX-FileCopyrightText: © 2017 Geoffrey T. Dairiki <dairiki@dairiki.org>
# SPDX-License-Identifier: GPL-3.0-only
import cmd
import shlex


class DummyShellmodeInkscape(cmd.Cmd):
    intro = "DummyShellmodeInkscape"
    prompt = ">"

    def precmd(self, line: str) -> str:
        return " ".join(shlex.split(line))

    def do_true(self, line: str) -> bool:
        return False

    def do_echo(self, line: str) -> bool:
        print(f"warning: {line}")
        return False

    def do_quit(self, line: str) -> bool:
        return True

    def do_EOF(self, line: str) -> bool:
        return True


if __name__ == "__main__":
    DummyShellmodeInkscape().cmdloop()
