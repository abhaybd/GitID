import argparse
import sys
from typing import List
import os
import yaml
import re
import sys


CONF_PATH = os.path.join(os.environ["HOME"], ".gitid.conf")
# maps shells to startup files (paths relative to home) in decreasing order of priority
SHELL_CONF_PATHS = {
    "bash": [".bash_aliases", ".bashrc", ".bash_profile"],
    "zsh": [".zsh_aliases", ".zshrc", ".zprofile"],
    "sh": [".shrc", ".shinit", ".profile"],
    "fish": [os.path.join(".config", "fish", "config.fish")],
    "csh": [".cshrc"],
    "tcsh": [".tcshrc", ".cshrc"],
    "ksh": [".kshrc", ".profile"]
}
SHELL_CONF_PATHS = {
    shell: [os.path.expanduser(os.path.join("~", p)) for p in paths] for shell, paths in SHELL_CONF_PATHS.items()
}

ALIAS_SNIPPET = f"# >>> gitid initialize >>>\nalias gitid=\"PYTHON_PATH='{sys.executable}' source gitid\"\n# <<< gitid initialize <<<\n\n"
ALIAS_SNIPPET = ALIAS_SNIPPET.replace("\\", "\\\\")  # duplicate backslashes for re.sub
ALIAS_PATTERN = r"# >>> gitid initialize >>>[\s\S]+?# <<< gitid initialize <<<\n{0,2}"


def setup_and_load_conf():
    # perform first time setup, if necessary
    init_conf = {
        "identities": {},
        "shells": []
    }
    if not os.path.isfile(CONF_PATH):
        conf = init_conf
        save_conf(conf)
    else:
        conf = load_conf()
        changed = False
        for k, v in init_conf.items():
            if k not in conf:
                conf[k] = v
                changed = True
        if changed:
            save_conf(conf)
    return conf


def load_conf():
    with open(CONF_PATH) as f:
        conf = yaml.safe_load(f)
    return conf


def save_conf(conf):
    with open(CONF_PATH, "w") as f:
        yaml.dump(conf, f)


def is_active(id_name):
    return "ACTIVE_GITID" in os.environ and os.environ["ACTIVE_GITID"] == id_name


def create_echo(s):
    return f"echo \"{s}\""


def write_dotfile(path, pattern, repl, add_if_absent=True):
    if os.path.isfile(path):
        with open(path) as f:
            contents = f.read()
    else:
        contents = ""
    if re.search(pattern, contents):
        contents = re.sub(pattern, repl, contents)
    elif add_if_absent:
        contents += repl
    with open(path, "w") as f:
        f.write(contents)


def init_shell(conf, args):
    if args.shell not in SHELL_CONF_PATHS:
        print(f"Unsupported shell: {args.shell}", file=sys.stderr)
        sys.exit(1)
    paths = SHELL_CONF_PATHS[args.shell]
    path = next(filter(os.path.isfile, paths), paths[-1])

    print(f"Adding alias to {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_dotfile(path, ALIAS_PATTERN, ALIAS_SNIPPET, add_if_absent=True)
    if args.shell not in conf["shells"]:
        conf["shells"].append(args.shell)
    save_conf(conf)
    print("Shell initialized! Please close and re-open any existing sessions.")
    return []


def uninit(conf, args):
    def uninit_shell(shell):
        paths = SHELL_CONF_PATHS[shell]
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
    commands = [
        f"export ACTIVE_GITID=\"{args.identity}\"",
        f"export GIT_AUTHOR_NAME=\"{entry['name']}\"",
        f"export GIT_AUTHOR_EMAIL=\"{entry['email']}\"",
        f"export GIT_COMMITTER_NAME=\"{entry['name']}\"",
        f"export GIT_COMMITTER_EMAIL=\"{entry['email']}\"",
        create_echo(f"Set active identity: {entry['name']} <{entry['email']}>"),
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
        commands += [
            "unset ACTIVE_GITID",
            "unset GIT_AUTHOR_NAME",
            "unset GIT_AUTHOR_EMAIL",
            "unset GIT_COMMITTER_NAME",
            "unset GIT_COMMITTER_EMAIL"
        ]
    return commands


def clear_ids(conf, _):
    conf["identities"].clear()
    save_conf(conf)
    return [
        "unset ACTIVE_GITID",
        "unset GIT_AUTHOR_NAME",
        "unset GIT_AUTHOR_EMAIL",
        "unset GIT_COMMITTER_NAME",
        "unset GIT_COMMITTER_EMAIL"
    ]


def get_args():
    parser = argparse.ArgumentParser(
        prog="gitid",
        description="Command-line tool for managing multiple git identities on the same machine.")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new shell to work with gitid")
    init_parser.add_argument("shell", help="The name of the POSIX-compliant shell to initialize")
    init_parser.set_defaults(func=init_shell)

    uninit_parser = subparsers.add_parser(
        "uninit", help="Uninitialize a shell, undoing the effects of init")
    uninit_parser.add_argument(
        "shells", nargs="*", help="The names of the shells to uninitialize. If not provided then all initialized shells are uninitialized.")
    uninit_parser.set_defaults(func=uninit)

    set_parser = subparsers.add_parser("set", help="Set the active identity")
    set_parser.add_argument("identity", help="The identity to activate")
    set_parser.set_defaults(func=set_id)

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
