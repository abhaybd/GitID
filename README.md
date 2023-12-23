# GitID

Command-line tool for managing multiple git identities on the same machine. This is particularly useful for shared machines where multiple people develop in the same workspaces, which is in some cases unavoidable.

With GitID, users can store their git identities and quickly load them in their shell, so their commits are marked with their name and email.

Note that GitID only sets commit authors and committers, and does **not** affect authorization.

## Installation

Installation is easy:
```bash
pip install gitid
gitid init bash # substitute with your shell of choice
```

### Unsupported shell

If your shell is unsupported by `gitid init`, simply add `alias gitid="source gitid"` to the appropriate startup file of your shell.

## Workflow

To add a new identity:
```bash
gitid add idname username email
```

The added identity can now be activated:
```bash
gitid set idname
... git commands ...
git commit # This commit is marked with "username <email>" as the committer and author
```

All identities can be viewed:
```bash
gitid list
```

Which outputs: (`*` marks the active identity)
```
Stored identities:
    (*) idname: username <email>
```

Identities can also be removed:
```bash
gitid remove idname # removes the identity named 'idname'
gitid clear # removes all stored identities
```
