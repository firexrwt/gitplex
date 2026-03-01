# GitPlex

A terminal-based Git client built with Python and Textual. Designed to replace
GUI tools like GitHub Desktop while adding features that are only practical in
a terminal environment — primarily the ability to manage and operate on many
repositories simultaneously.

---

## Features

- **Multi-repo dashboard** — all your repositories in one view with branch
  name, ahead/behind counts and dirty-state indicators updated in real time.
- **Auto-detection** — run `gitplex .` from any parent directory and it will
  find every git repository in the immediate subdirectories automatically.
- **Interactive staging** — stage and unstage files individually. Switch to
  hunk mode to stage only specific chunks of a file without touching the rest.
- **Bulk operations** — select any subset of repos with checkboxes, then
  pull, push or fetch all of them concurrently with a single keypress.
- **Commit graph** — visual `git log --graph` output with colour-coded
  branches, plus a structured commit table with author, date and refs.
- **Commit history actions** — select any commit in the Log table and
  cherry-pick, revert, reset (soft / mixed / hard) or amend it directly
  from the TUI. Destructive operations require an explicit confirmation.
- **Commit dialog** — write and apply commit messages without leaving the TUI.
- **Branch management** — list branches, switch between them, create new ones.
- **Force push** — push with `--force-with-lease` after a rebase or reset;
  fails safely if the remote was updated by someone else in the meantime.
- **Stash** — stash dirty changes on the current repository instantly.
- **Create repositories** — run `git init` on a new empty directory or on an
  existing folder full of files, with an optional automatic initial commit.
- **Config persistence** — repository list is saved in
  `~/.config/gitplex/config.json` and restored between sessions.
- **Clone repositories** — clone any remote repository by URL directly from
  the TUI, with automatic destination path suggestion.
- **Remote management** — add, update or remove remotes for the current
  repository without leaving the app.
- **System git** — uses the `git` binary already on your system, inheriting
  your `.gitconfig`, SSH keys, GPG signing and credential helpers with no
  extra configuration.

---

## Requirements

- Python 3.11 or newer
- git (any reasonably recent version)
- Linux or macOS — Windows is not currently supported, but support may be added in the future

---

## Installation

### pip

```
pip install gitplex
```

### Fedora / COPR

```
dnf copr enable firexrwt/gitplex
dnf install gitplex
```

### From source

```
git clone https://github.com/firexrwt/gitplex.git
cd gitplex
pip install .
```

---

## Usage

```
gitplex                 open the TUI, load repos saved in config
gitplex .               scan the current directory for git repos
gitplex ~/projects      scan any directory for git repos
gitplex --help          print usage and key binding reference
gitplex --version       print the version number
```

When a directory is passed, GitPlex scans its immediate children for `.git`
directories and adds every repository it finds to the config automatically.
Repositories that are already tracked are not duplicated.

---

## Interface layout

```
+------------------+--------------------------------------------+
|  REPOS           |  [ Diff ]  [ Graph ]                       |
|                  |                                            |
|  my-app  main  2 |  @@ -14,7 +14,9 @@                        |
|  backend main    |   def process(data):                       |
|  infra   main  1 |  -    return data                          |
|                  |  +    result = transform(data)             |
+------------------+  +    return result                        |
|  [ Unstaged ][ Staged ]                                       |
|                  |                                            |
|  M  src/main.py  |                                            |
|  M  src/utils.py |                                            |
|  ?  scratch.txt  |                                            |
+------------------+--------------------------------------------+
```

The left column is split vertically: the top half lists repositories, the
bottom half lists changed files for the selected repository. The right column
shows either the diff for the selected file or the commit graph, switchable
via tabs at the top.

---

## Key bindings

### Global

| Key          | Action                                              |
|--------------|-----------------------------------------------------|
| `r`          | Refresh all repository statuses                     |
| `q`          | Quit                                                |
| `Tab`        | Move focus to the next panel                        |
| `Shift+Tab`  | Move focus to the previous panel                    |

### Repository management

| Key  | Action                                                         |
|------|----------------------------------------------------------------|
| `n`  | Create a new repository (git init, new or existing folder)     |
| `a`  | Add an existing local repository to the tracked list           |
| `C`  | Clone a remote repository by URL                               |
| `R`  | Manage remotes for the current repo (add / set-url / remove)   |
| `X`  | Remove the currently selected repository from the tracked list |

### Per-repository operations

These act on the repository currently selected in the repo list.

| Key  | Action                                                      |
|------|-------------------------------------------------------------|
| `c`  | Open the commit dialog (requires at least one staged file)  |
| `p`  | Pull (current repo)                                         |
| `P`  | Push (current repo)                                         |
| `F`  | Force push with `--force-with-lease` (requires confirmation)|
| `f`  | Fetch --all --prune (current repo)                          |
| `b`  | Open the branch dialog (switch or create branch)            |
| `S`  | Stash all dirty changes on the current repo                 |

### Bulk operations

Bulk operations run on every repository that has its checkbox ticked. If no
checkboxes are ticked, the operation runs on all tracked repositories.

| Key       | Action                                   |
|-----------|------------------------------------------|
| `Ctrl+A`  | Toggle selection of all repositories     |
| `Ctrl+P`  | Bulk pull (all selected repos)           |
| `Ctrl+U`  | Bulk push (all selected repos)           |
| `Ctrl+F`  | Bulk fetch (all selected repos)          |

Bulk operations run concurrently (up to 4 at a time) and stream output to a
progress dialog as each repository completes.

### File list

The file list shows either unstaged or staged files depending on which tab is
active. Press `Space` on a file to toggle its staged state.

| Key    | Action                                        |
|--------|-----------------------------------------------|
| `Space`| Stage the highlighted file / unstage it       |
| `A`    | Stage all unstaged files at once              |
| `U`    | Unstage all staged files at once              |
| `d`    | Discard unstaged changes in the highlighted file |

### Commit log

The Log tab inside the Graph panel shows a structured commit table.

| Key     | Action                                                       |
|---------|--------------------------------------------------------------|
| `Enter` | Open the commit actions dialog for the highlighted commit    |

**Commit actions** available per commit:

| Action       | Description                                                        |
|--------------|--------------------------------------------------------------------|
| Cherry-pick  | Apply this commit on top of the current branch                     |
| Revert       | Create a new commit that undoes the changes                        |
| Reset soft   | Move HEAD here; keep changes staged                                |
| Reset mixed  | Move HEAD here; keep changes unstaged                              |
| Reset hard   | Move HEAD here and discard all changes (requires confirmation)     |
| Amend        | Edit the commit message (available only for the HEAD commit)       |

### Diff view

| Key  | Action                                                          |
|------|-----------------------------------------------------------------|
| `h`  | Toggle hunk mode (split the diff into individual hunks)         |
| `s`  | Stage the currently highlighted hunk (hunk mode only)           |
| `j`  | Scroll down                                                     |
| `k`  | Scroll up                                                       |
| `g`  | Scroll to the top                                               |
| `G`  | Scroll to the bottom                                            |

#### Hunk mode

When hunk mode is active the diff panel splits into two sections: a list of
hunks at the top and the content of the highlighted hunk below. Navigate the
hunk list with the arrow keys, press `s` to stage the selected hunk. After
staging, the diff reloads automatically so the line numbers remain correct for
any remaining hunks.

---

## Workflow examples

### Daily driver — multiple repositories

```
cd ~/projects          # parent directory containing all your repos
gitplex .                # GitPlex scans and adds every repo it finds
```

Once inside the TUI:

1. Scroll the repo list to get an overview of what is dirty and what is
   ahead or behind remote.
2. Press `Ctrl+F` to fetch all repos at once and update the ahead/behind
   counters.
3. Press `Ctrl+P` to pull everything that is behind.
4. Select a repo, browse changed files, stage what you want, write a commit
   message with `c`.
5. Push with `P` or do a final `Ctrl+U` for everything.

### Staging a partial change

1. Select the repository in the left panel.
2. Select the file in the Unstaged tab.
3. Press `h` in the diff panel to enter hunk mode.
4. Navigate to the hunk you want and press `s`.
5. Switch to the Staged tab to confirm only that hunk moved across.
6. Press `c` to commit.

### Pushing an existing project to GitHub for the first time

1. On GitHub, create a new empty repository (no README, no .gitignore).
2. In GitPlex, select your repository in the repo list.
3. Press `R` to open the remotes dialog.
4. Enter name `origin` and the URL GitHub gave you
   (`https://github.com/you/repo.git` or `git@github.com:you/repo.git`).
5. Press "Add".
6. Back in the main view, press `P` to push.
   On the first push git may reject it if the remote and local histories
   diverge — in that case run `git push -u origin main` once from the
   terminal; subsequent pushes will work from GitPlex normally.

### Cloning a repository

1. Press `C` from anywhere in the TUI.
2. Paste the remote URL. GitPlex suggests a destination path automatically
   based on the repository name under your home directory.
3. Optionally change the destination path.
4. Confirm. The clone runs in the background and the repository appears in
   the list when it finishes.

### Initialising a new project

1. Press `n` anywhere in the TUI.
2. Enter the path to the new directory (it does not have to exist yet) or the
   path to an existing folder that is not yet a repository.
3. Set a branch name if you want something other than `main`.
4. Tick "Make initial commit" if the folder already contains files you want to
   track from the start, and optionally edit the commit message.
5. Confirm. The repository is initialised and added to the tracked list
   immediately.

---

## Configuration

The config file lives at `~/.config/gitplex/config.json`. It is created
automatically on first run and updated whenever you add or remove a repository.
You can edit it directly if needed — the format is plain JSON:

```json
{
  "repos": [
    "/home/user/projects/my-app",
    "/home/user/projects/backend",
    "/home/user/projects/infra"
  ],
  "max_log_entries": 80,
  "auto_fetch_interval": 0
}
```

| Field                | Default | Description                                         |
|----------------------|---------|-----------------------------------------------------|
| `repos`              | `[]`    | Absolute paths to tracked repositories              |
| `max_log_entries`    | `80`    | Maximum commits shown in the graph and log table    |
| `auto_fetch_interval`| `0`     | Seconds between automatic fetches (0 = disabled)    |

---

## Project structure

```
src/gitplex/
  app.py            main application class and all key binding handlers
  app.tcss          Textual CSS stylesheet
  config.py         config file read/write
  main.py           CLI entry point
  git/
    repo.py         GitRepo wrapper around subprocess git calls
    diff.py         unified diff parser and Rich markup renderer
  widgets/
    repo_list.py    repository panel (left top)
    file_list.py    staged / unstaged file panel (left bottom)
    diff_view.py    diff viewer with hunk mode (right)
    graph_view.py   commit graph and log table (right)
    modals.py       all modal dialogs
```

---

## License

MIT
