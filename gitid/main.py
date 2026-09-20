import argparse
import os
import re
import shlex
import shutil
import sys
import sysconfig
import tempfile
from typing import List
import yaml


CONF_PATH = os.path.join(os.path.expanduser("~"), ".gitid.conf")
# maps shells to startup files (paths relative to home) in decreasing order of priority
_SHELL_FILES = {
    "bash": [".bash_aliases", ".bashrc", ".bash_profile"],
    "zsh": [".zsh_aliases", ".zshrc", ".zprofile"],
    "ksh": [".kshrc", ".profile"],
}
# Removed from init; still recognized by uninit so older installs can clean up.
_LEGACY_SHELL_FILES = {
    "sh": [".shrc", ".shinit", ".profile"],
    "fish": [os.path.join(".config", "fish", "config.fish")],
    "csh": [".cshrc"],
    "tcsh": [".tcshrc", ".cshrc"],
}
_SUGGESTED_RC = {
    "bash": "~/.bashrc",
    "zsh": "~/.zshrc",
    "ksh": "~/.kshrc",
}


def _expand_shell_paths(mapping):
    return {
        shell: [os.path.expanduser(os.path.join("~", p)) for p in paths]
        for shell, paths in mapping.items()
    }


SHELL_CONF_PATHS = _expand_shell_paths(_SHELL_FILES)
ALL_SHELL_CONF_PATHS = {**_expand_shell_paths(_LEGACY_SHELL_FILES), **SHELL_CONF_PATHS}

UNSET_ENV_COMMANDS = [
    "unset ACTIVE_GITID",
    "unset GIT_AUTHOR_NAME",
    "unset GIT_AUTHOR_EMAIL",
    "unset GIT_COMMITTER_NAME",
    "unset GIT_COMMITTER_EMAIL",
]


def _gitid_script_path():
    """Absolute path to this install's gitid shell wrapper."""
    installed = os.path.join(sysconfig.get_path("scripts"), "gitid")
    if os.path.isfile(installed):
        return os.path.realpath(installed)
    which = shutil.which("gitid")
    if which:
        return os.path.realpath(which)
    return os.path.realpath(installed)


def _alias_snippet():
    python = shlex.quote(sys.executable)
    script = shlex.quote(_gitid_script_path())
    return (
        "# >>> gitid initialize >>>\n"
        f"alias gitid=\"PYTHON_PATH={python} source {script}\"\n"
        "# <<< gitid initialize <<<\n\n"
    )


ALIAS_PATTERN = r"# >>> gitid initialize >>>[\s\S]+?# <<< gitid initialize <<<\n{0,2}"


def _re_repl(s):
    # re.sub treats backslashes in the replacement as escapes
    return s.replace("\\", "\\\\")


def _atomic_write(path, contents):
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".gitid-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contents)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def setup_and_load_conf():
    # perform first time setup, if necessary
    if not os.path.isfile(CONF_PATH):
        conf = {
            "identities": {},
            "shells": []
        }
        save_conf(conf)
        return conf

    conf = load_conf()
    changed = False
    identities = conf.get("identities", {})
    shells = conf.get("shells", [])
    if identities is None:
        conf["identities"] = {}
        changed = True
    elif not isinstance(identities, dict):
        print(f"Error: {CONF_PATH} field 'identities' must be a mapping.", file=sys.stderr)
        sys.exit(1)
    if shells is None:
        conf["shells"] = []
        changed = True
    elif not isinstance(shells, list):
        print(f"Error: {CONF_PATH} field 'shells' must be a list.", file=sys.stderr)
        sys.exit(1)
    if "identities" not in conf:
        conf["identities"] = {}
        changed = True
    if "shells" not in conf:
        conf["shells"] = []
        changed = True
    if changed:
        save_conf(conf)
    return conf


def load_conf():
    try:
        with open(CONF_PATH, encoding="utf-8") as f:
            conf = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: failed to parse {CONF_PATH}: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: failed to read {CONF_PATH}: {e}", file=sys.stderr)
        sys.exit(1)
    if conf is None:
        return {}
    if not isinstance(conf, dict):
        print(f"Error: {CONF_PATH} is not a valid GitID config file.", file=sys.stderr)
        sys.exit(1)
    return conf


def save_conf(conf):
    contents = yaml.dump(conf, default_flow_style=False, allow_unicode=True)
    _atomic_write(CONF_PATH, contents)


def is_active(id_name):
    return "ACTIVE_GITID" in os.environ and os.environ["ACTIVE_GITID"] == id_name


def create_echo(s):
    return f"echo {shlex.quote(s)}"


def write_dotfile(path, pattern, repl, add_if_absent=True):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            contents = f.read()
    else:
        contents = ""
    changed = False
    if re.search(pattern, contents):
        contents = re.sub(pattern, repl, contents)
        changed = True
    elif add_if_absent:
        contents += repl
        changed = True
    if changed:
        _atomic_write(path, contents)


def init_shell(conf, args):
    if args.shell in ALL_SHELL_CONF_PATHS and args.shell not in SHELL_CONF_PATHS:
        print(
            f"{args.shell} is no longer supported. GitID requires a bash-compatible "
            f"shell ({', '.join(SHELL_CONF_PATHS)}).",
            file=sys.stderr,
        )
        sys.exit(1)
    if args.shell not in SHELL_CONF_PATHS:
        print(
            f"Unsupported shell: {args.shell}. Supported shells: "
            f"{', '.join(SHELL_CONF_PATHS)}.",
            file=sys.stderr,
        )
        sys.exit(1)
    paths = SHELL_CONF_PATHS[args.shell]
    path = next(filter(os.path.isfile, paths), None)
    snippet = _alias_snippet()
    if path is None:
        suggested = _SUGGESTED_RC[args.shell]
        print(
            f"No existing {args.shell} startup file found. GitID will not create one "
            f"automatically.",
            file=sys.stderr,
        )
        if args.shell == "bash":
            print(
                "Creating ~/.bash_profile would make bash skip ~/.profile and can "
                "drop PATH and other login setup. Add the snippet to ~/.bashrc "
                "instead (sourced by ~/.profile on most Linux systems).",
                file=sys.stderr,
            )
        print(
            f"Add the following to {suggested} (or another startup file your shell "
            f"already reads), then restart the shell:",
            file=sys.stderr,
        )
        print(snippet, end="")
        sys.exit(1)

    print(f"Adding alias to {path}")
    write_dotfile(path, ALIAS_PATTERN, _re_repl(snippet), add_if_absent=True)
    if args.shell not in conf["shells"]:
        conf["shells"].append(args.shell)
    save_conf(conf)
    print("Shell initialized! Please close and re-open any existing sessions.")
    return []


def uninit(conf, args):
    def uninit_shell(shell):
        paths = ALL_SHELL_CONF_PATHS.get(shell)
        if paths is None:
            print(f"Unknown shell: {shell}", file=sys.stderr)
            sys.exit(1)
        for p in filter(os.path.isfile, paths):
            write_dotfile(p, ALIAS_PATTERN, "", add_if_absent=False)
        while shell in conf["shells"]:
            conf["shells"].remove(shell)
        print(f"Uninitialized {shell}")
    if len(args.shells) == 0:
        if len(conf["shells"]) == 0:
            print("No shells to uninitialize.")
        else:
            for shell in conf["shells"].copy():  # copy since we modify in the loop
                uninit_shell(shell)
    else:
        for shell in args.shells:
            uninit_shell(shell)
    save_conf(conf)
    return []


def set_id(conf, args) -> List[str]:
    ids = conf["identities"]
    if args.identity not in ids:
        print(f"Unknown identity {args.identity}", file=sys.stderr)
        sys.exit(1)
    entry = ids[args.identity]
    name = entry["name"]
    email = entry["email"]
    commands = [
        f"export ACTIVE_GITID={shlex.quote(args.identity)}",
        f"export GIT_AUTHOR_NAME={shlex.quote(name)}",
        f"export GIT_AUTHOR_EMAIL={shlex.quote(email)}",
        f"export GIT_COMMITTER_NAME={shlex.quote(name)}",
        f"export GIT_COMMITTER_EMAIL={shlex.quote(email)}",
        create_echo(f"Set active identity: {name} <{email}>"),
    ]
    return commands


def list_ids(conf, _):
    ids = conf["identities"]
    if len(ids) == 0:
        print("No stored identities to display.")
    else:
        print("Stored identities:")
        for id_name, entry in sorted(ids.items()):
            active = '*' if is_active(id_name) else ' '
            print(f"\t({active}) {id_name}: {entry['name']} <{entry['email']}>")
    return []


def add_id(conf, args):
    ids = conf["identities"]
    if args.identity in ids:
        print(
            f"Identity already exists: {args.identity}. To update an identity, remove it and re-add it.", file=sys.stderr)
        sys.exit(1)
    ids[args.identity] = {
        "name": args.name,
        "email": args.email
    }
    save_conf(conf)
    return []


def remove_id(conf, args) -> List[str]:
    ids = conf["identities"]
    if args.identity not in ids:
        print(f"Unknown identity {args.identity}", file=sys.stderr)
        sys.exit(1)
    entry = ids[args.identity]
    del ids[args.identity]
    save_conf(conf)
    commands = [create_echo(f"Removed identity: {entry['name']} <{entry['email']}>")]
    if is_active(args.identity):
        commands += UNSET_ENV_COMMANDS
    return commands


def clear_ids(conf, _):
    conf["identities"].clear()
    save_conf(conf)
    return list(UNSET_ENV_COMMANDS)


def unset_id(_, __) -> List[str]:
    if "ACTIVE_GITID" in os.environ:
        message = "Unset active identity."
    else:
        message = "No active identity."
    return UNSET_ENV_COMMANDS + [create_echo(message)]


def get_args():
    parser = argparse.ArgumentParser(
        prog="gitid",
        description="Command-line tool for managing multiple git identities on the same machine.")
    subparsers = parser.add_subparsers(required=True, dest="command")

    init_parser = subparsers.add_parser("init", help="Initialize a new shell to work with gitid")
    init_parser.add_argument(
        "shell", help="The shell to initialize (bash, zsh, or ksh)")
    init_parser.set_defaults(func=init_shell)

    uninit_parser = subparsers.add_parser(
        "uninit", help="Uninitialize a shell, undoing the effects of init")
    uninit_parser.add_argument(
        "shells", nargs="*", help="The names of the shells to uninitialize. If not provided then all initialized shells are uninitialized.")
    uninit_parser.set_defaults(func=uninit)

    set_parser = subparsers.add_parser("set", help="Set the active identity")
    set_parser.add_argument("identity", help="The identity to activate")
    set_parser.set_defaults(func=set_id)

    unset_parser = subparsers.add_parser(
        "unset", help="Clear the active identity for this shell session")
    unset_parser.set_defaults(func=unset_id)

    list_parser = subparsers.add_parser("list", help="List the stored identities")
    list_parser.set_defaults(func=list_ids)

    add_parser = subparsers.add_parser("add", help="Add a new identity")
    add_parser.add_argument("identity", help="The nickname of the identity to add")
    add_parser.add_argument(
        "name", help="The name of the identity to add, which will be associated with git commits")
    add_parser.add_argument(
        "email", help="The email of the identity to add, which will be associated with git commits")
    add_parser.set_defaults(func=add_id)

    remove_parser = subparsers.add_parser("remove", help="Remove an existing identity")
    remove_parser.add_argument("identity", help="The identity to remove")
    remove_parser.set_defaults(func=remove_id)

    clear_parser = subparsers.add_parser("clear", help="Clear all stored identities")
    clear_parser.set_defaults(func=clear_ids)

    return parser.parse_args()


def main():
    args = get_args()

    conf = setup_and_load_conf()
    commands = args.func(conf, args)

    if commands:
        print("\n".join(commands))
        # return code 99 signals the caller to execute the contents of stdout
        sys.exit(99)


if __name__ == "__main__":
    main()
