---
name: workbench
description: Keep private per-project notes in a workbench git repo outside the app repos. `/workbench help` lists the modes; `setup` creates or connects the workbench and installs the global instructions; `ask` says what to do next; `seed` starts notes for the current repo; `wrap` ends a session (handoff.md, log.md, commit, push). Use before /clear or when the user wants the session saved.
argument-hint: "help | setup | ask | seed | wrap [what the next session is for]"
disable-model-invocation: true
---

The workbench holds per-project notes that don't belong in the app repo: one folder per project, named after the repo's directory name, inside a private git repo. Its README has the rules (intent and procedure only, nothing git already records, dated, no secrets).

## Locating the workbench (every mode but `help` and `setup`)

`$WB` is the path on the `Workbench dir:` line inside the `<!-- workbench:begin -->` block of `~/.claude/CLAUDE.md`. If there is no block or the directory is missing, say so and run `setup` instead. `<repo>` is the git root's directory name. With no argument, show `help`.

## help

Print this table and stop; change nothing.

| Mode | What it does |
|---|---|
| `setup` | Create the workbench (new private GitHub repo, or connect one you already have), and add the workbench rules to `~/.claude/CLAUDE.md`. Run once per machine. |
| `ask` | Read-only. Look at the workbench and the current repo and say what to do next. |
| `seed` | Start notes for the current repo, link it to the workbench, offer to move AI artifacts out of the repo. |
| `wrap [text]` | End of session: overwrite `handoff.md`, append `log.md`, commit and push. Run before `/clear`. |

## setup

Make a workbench exist and tell every session about it. Safe to re-run: it repairs what is missing and never overwrites notes.

1. **State.** Read `~/.claude/CLAUDE.md`: is there a `<!-- workbench:begin -->` block, or an older unmarked "Workbench" section? Does its path exist and is it a git repo with a remote? Report what you found in a line.
2. **GitHub.** `gh auth status`. If not logged in, ask the user to run `! gh auth login`, and continue only after. Note the login as `<owner>`. Without `gh` or an account, offer a local-only workbench (no remote, no push) and say `wrap` will only commit.
3. **Location.** Default to a `workbench` folder beside the user's other repos (the git root's parent when run inside a repo, else `~/workbench`). Ask the user to confirm or change it (AskUserQuestion). If the folder already exists and is a git repo, use it as is.
4. **Repo.** `gh repo view <owner>/workbench --json isPrivate,url`:
   - Exists and private: clone it to the location (or add it as `origin` when the folder exists without a remote). Never overwrite local files.
   - Exists and public: stop. A workbench must be private; ask whether to make it private (`gh repo edit --visibility private`) or use another name.
   - Missing: say you are about to create a **private** repo `<owner>/workbench`, get a yes, then `gh repo create <owner>/workbench --private --source <location> --remote origin` (after `git init` if needed).
   - A different name is fine if the user asks; use it everywhere below.
5. **Scaffold** only what is missing: `README.md` (what it is, the rules: keep intent, procedure and decisions; nothing git already records; date what rots; no secrets; commit at the end of a session; a `Projects:` list), then commit and push the first commit. Never make the repo public.
6. **Global instructions.** Write this block into `~/.claude/CLAUDE.md`, replacing an existing marked block or an older unmarked Workbench section (show the user the diff first and get a yes; keep every other part of the file). Fill in `<WB>` and `<owner>/<name>`:

```
<!-- workbench:begin -->
# Workbench: notes that don't belong in the app repo

Workbench dir: <WB>

`<WB>` is a private repo of per-project notes (plans, decisions, deploy procedures, upstream watchlists), one folder per project named after its repo. Do not put such AI work artifacts in the app repo.

- When starting work in a repo that has a folder there, read `<WB>/<repo>/README.md` first and follow its links as needed. Each project folder has a `handoff.md`: read it first and check it against `git log`.
- When a session produces something not derivable from git or the code (a decision and its why, a procedure, a plan, an unresolved problem), add or update a note there and append to that project's `log.md`. Keep notes short and dated; don't copy what git already records.
- The user-invoked `/workbench` skill does the rest: `help`, `setup`, `ask`, `seed` (new project) and `wrap` (end of session: overwrite `handoff.md` with the current state, what is unverified, open problems and next steps, dated with the commit it describes).
- At the end of the session, commit and push the workbench (`git -C <WB> add -A && git -C <WB> commit && git -C <WB> push`). The user approved pushing it to its private repo (github.com/<owner>/<name>) after each session; that approval covers only this repo. Never make it public.
- No secrets in the workbench.
<!-- workbench:end -->
```

   Say plainly that this block is the standing permission to push that one repo, so the user knows what they are granting.
7. **Finish.** Tell the user in three lines: where the workbench is, its remote, and that `/workbench seed` in a repo starts its notes. Existing projects already in a connected workbench need no seed.

## ask

Read-only: change nothing, commit nothing. Work out one best next step and say it.

1. `git -C $WB status -sb` (uncommitted or unpushed notes), the `Projects:` list, and `git -C $WB fetch` to see if the remote is ahead.
2. If inside a git repo: does `$WB/<repo>/` exist? If not, the answer is `/workbench seed`. If it does, read its `handoff.md`, compare the commit and date it names with `git log --oneline -10` and `git status -sb`, and note whether it is stale, plus any notes the handoff calls unverified or open.
3. Reply in at most six lines: where things stand, the single next step (which skill or command to run, e.g. `/workbench wrap`, `/workbench seed`, `git pull` in the workbench, or the first "Next" item of the handoff), and anything stale or unpushed. Don't dump the handoff.

## wrap

Run this before the user types `/clear`.

1. Read the project's existing `handoff.md`, `log.md` and the notes the session touched, so you edit instead of duplicating. Run `git log --oneline -10` and `git status -sb` in the app repo for the real state.
2. **Overwrite** `<repo>/handoff.md` (never append) with: the date and the commit it describes; the state; what is unverified; open problems; next steps. If the user passed text after `wrap`, tailor "Next" to it. Name the skills the next session should call, if any.
3. Update the reference notes only for things learned this session that git and the code can't tell: a decision and why, a changed procedure, a new gotcha. Fix notes that turned out wrong. Don't list merged PRs or file layouts.
4. Append a short dated entry to `<repo>/log.md`.
   **Notes for other projects.** If the session learned something that belongs to a different project (a decision, gotcha or procedure about another repo, a dependency's upstream change, a task for a repo other than this one), put it in that project's folder, not this one. Only for facts the session actually established, written so they make sense alone and dated, and never a guess about which project they belong to (ask if unsure).
   - Folder exists (`$WB/<other>/`): add to the matching reference note, or append a dated entry to its `log.md`; if it is something the next session there must act on, add one line under "Next" in its `handoff.md` (never overwrite that file). Don't touch the other app repo.
   - No folder yet: create `$WB/<other>/inbox.md` with the dated notes and nothing else, so `seed` picks them up later.
   - List each addition in the final summary, by project.
5. Redact secrets and personal data. Host names are fine; keys, tokens and passwords are not.
6. Commit and push the workbench: `git -C $WB add -A && git -C $WB commit -m "<repo>: <what changed>" && git -C $WB push`. End the commit message with the attribution trailer the session was given. If the push fails, say so; don't force it.
7. Tell the user what changed in two or three lines, including any notes added to other projects, and that it is safe to `/clear`.

## seed

Start notes for a repo that has no folder yet.

1. If `<repo>/` already exists in the workbench and holds more than `inbox.md`, say so and stop; offer `wrap` instead. If it holds only `inbox.md`, carry on: notes from other sessions are waiting there. Fold each into the new notes (README, reference notes, handoff "Next", `log.md` as fits), then delete `inbox.md`.
2. Read the app repo's README, CLAUDE.md or AGENTS.md, `git log --oneline -20`, branches, and any docs on build and deploy. Don't read everything: enough to describe how to work there.
3. Create `<repo>/README.md` (index: what the repo is, its path and remote, links to the files below), `handoff.md` (current state from git, next steps unknown if not stated), `log.md`, and only the reference notes you can fill with something real (for example `deploy.md` when the repo has a build and install procedure, `branches.md` when the user keeps an integration branch). Ask the user for anything that only they know rather than guessing; leave a section out instead of inventing one.
4. Add `<repo>` to the Projects list in the workbench `README.md`.
5. In the app repo, write `CLAUDE.local.md` containing (with `$WB` written out as the absolute path): `Private project notes live outside this repo: read $WB/<repo>/README.md before working here, and update them as described in the global instructions.` Then add `CLAUDE.local.md` to `.git/info/exclude` if absent. Never add either to the app repo's tracked files or its .gitignore.
6. **Migrate** (only when the app repo already tracks AI artifacts): look for planning docs, scratch notes, session summaries and agent files that are not real project documentation (`PLAN*.md`, `NOTES*.md`, `docs/plans/`, `TODO` scratch files, `.claude/` content, handoff or summary files). Check `git ls-files` and `git log` for each so you know who wrote it and whether anything else links to it.
   - Show the user the list with one line on why each looks like an artifact, and ask which to move. Files that other people or docs rely on, and the repo's own `CLAUDE.md` or `AGENTS.md`, stay unless the user says otherwise.
   - Copy the chosen files into `<repo>/migrated/` in the workbench (keep their relative paths) and mention them in the index. Don't edit them.
   - Do not delete, commit or push anything in the app repo. Instead, print the exact `git rm` commands (and a suggested commit message) for the user to run and review. Note that history keeps the files either way.
7. Commit and push the workbench as in `wrap` step 6, then summarize what was created and what is left for the user to do in the app repo.
