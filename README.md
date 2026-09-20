# GitID

GitID is a command-line tool for managing multiple git identities on the same machine. This is particularly useful for shared machines where multiple people develop in the same workspaces, which is in some cases unavoidable.

With GitID, users can store their git identities and quickly load them in their shell, so their commits are marked with their name and email.

Note that GitID only sets commit authors and committers, and does **not** affect authorization.

## Installation

GitID needs a persistent install so the shell alias can `source` its wrapper. Use pipx or `uv tool install` (not `uvx`):

```bash
pipx install gitid
# or: uv tool install gitid
gitid init bash   # bash, zsh, or ksh
```

If neither tool is available:

```bash
python3 -m pip install --user gitid
gitid init bash
```

> [!NOTE]
> `uvx` and other ephemeral runners will not work: the alias pins the install path, which disappears when the tool exits.

### Installation Issues

Some environments may not place the script on the path. If your shell can't find the `gitid` script, add the pipx/`uv tool`/user-scripts directory to `PATH` in your startup file:

```bash
export PATH="$PATH:<PATH_TO_GITID>"
```

### Unsupported shell

`gitid init` supports bash, zsh, and ksh. For other shells, add an alias that sources the `gitid` wrapper (the script printed by `gitid init bash` on a machine with no startup file is a good template).

## Workflow

Suppose both Frodo Baggins and Samwise Gamgee want to develop on the same computer. They would add their git identities like so:
```bash
gitid add frodo "Frodo Baggins" frodo@shire.com
gitid add sam "Samwise Gamgee" sam@shire.com
```

Now Frodo wants to write some code:
```bash
gitid set frodo
... git commands ...
git commit # This commit is marked with "Frodo Baggins <frodo@shire.com>" as the committer and author
```

To go back to the repository's own `user.name` / `user.email` in this session:
```bash
gitid unset
```

Separately, possibly at the same time (in a different session), Samwise also wants to write code:
```bash
gitid set sam
... git commands ...
git commit # This commit is marked with "Samwise Gamgee <sam@shire.com>" as the committer and author
```

All identities can be viewed:
```bash
gitid list
```

Which outputs: (`*` marks the active identity)
```
Stored identities:
    ( ) frodo: Frodo Baggins <frodo@shire.com>
    (*) sam: Samwise Gamgee <sam@shire.com>
```

Identities can also be removed:
```bash
gitid remove frodo # removes Frodo's identity
gitid clear # removes all stored identities
```
