# GitID

GitID is a command-line tool for managing multiple git identities on the same machine. This is particularly useful for shared machines where multiple people develop in the same workspaces, which is in some cases unavoidable.

With GitID, users can store their git identities and quickly load them in their shell, so their commits are marked with their name and email.

Note that GitID only sets commit authors and committers, and does **not** affect authorization.

## Installation

Installation is easy:
```bash
pip install gitid
gitid init bash # change to your shell of choice
```

### Unsupported shell

If your shell is unsupported by `gitid init`, simply add `alias gitid="source gitid"` to the appropriate startup file of your shell.

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
