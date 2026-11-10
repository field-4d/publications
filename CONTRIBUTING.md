# Contributing a publication

`main` only changes through pull requests. Lab members need write access to the repository
(ask an org owner of `field-4d`).

## Rules

1. **One folder per publication, named exactly after its title** (as published, or as
   submitted until it is published). Rename the folder if the title changes at acceptance.
2. **You own your folder.** Your GitHub username is listed for it in
   [`.github/CODEOWNERS`](.github/CODEOWNERS). The `folder-guard` check lets you merge
   pull requests that touch only folders you own. A pull request that touches someone
   else's folder, or the files at the top of the repository, needs an approving review
   from that folder's owner (for top-level files, an owner of `*`).
3. **No data or secrets.** No raw datasets, credentials, tokens or cluster account
   details. Put site-specific settings in a gitignored file and commit a template
   (`env.example`).
4. **Self-contained.** Each folder has a `README.md` that maps every figure and table in
   the paper to the script that produces it, its pinned dependencies and a `LICENSE`.
5. **Don't rewrite history.** Force-pushes and deletions of `main` are blocked; fix things
   with new commits.

## Adding a new publication

```bash
git clone https://github.com/field-4d/publications.git && cd publications
git switch -c add-<short-name>
mkdir "<Exact publication title>"      # copy your code into it
git add "<Exact publication title>"
git commit -m "Add code for <short name>"
git push -u origin add-<short-name>
```

Then, in the same pull request:

- add one line to the table in [`README.md`](README.md) (title, status, your username), and
- add your folder to [`.github/CODEOWNERS`](.github/CODEOWNERS), escaping each space with
  a backslash:

  ```
  /My\ publication\ title/ @your-username
  ```

Because this pull request also changes top-level files, it needs one approval from an
owner of `*` in CODEOWNERS. After that, changes to your folder only need you.

To keep an existing project's commit history, import it with `git subtree` instead of
copying files:

```bash
git subtree add --prefix="<Exact publication title>" <path-or-url-of-old-repo> main
```

## Updating your publication

Branch, commit inside your folder, push, open a pull request. Once `folder-guard` passes,
merge it yourself.
