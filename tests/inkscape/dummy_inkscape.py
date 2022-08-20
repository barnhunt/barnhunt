import cmd
import shlex


class DummyShellmodeInkscape(cmd.Cmd):
    intro = "DummyShellmodeInkscape"
    prompt = ">"

    def precmd(self, line):
        return " ".join(shlex.split(line))

    def do_true(self, line):
        return False

    def do_echo(self, line):
        print(f"warning: {line}")
        return False

    def do_quit(self, line):
        return True


if __name__ == "__main__":
    DummyShellmodeInkscape().cmdloop()
