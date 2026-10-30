# Publishing this project on GitHub

Repository name: **`water-reach-task-fus-integrated`**
(GitHub does not allow spaces in names.)

## A. One-time preparation

1. **Install Git** — <https://git-scm.com/download/win> → run the installer,
   click *Next* on every page. Close and re-open `cmd`, then check:

   ```cmd
   git --version
   ```

2. **Use GitHub's private e-mail** so your real address is not published:
   GitHub → profile picture → **Settings → Emails** → tick
   **Keep my email addresses private**. Copy the address shown there
   (looks like `12345678+username@users.noreply.github.com`).

3. Tell Git who you are (once per computer):

   ```cmd
   git config --global user.name "Meryem Mine Kurum"
   git config --global user.email "12345678+username@users.noreply.github.com"
   ```

## B. Create the empty repository on GitHub

1. Open <https://github.com/new>.
2. **Repository name:** `water-reach-task-fus-integrated`
3. **Description:** `Water reach task - Tinkerforge rig + Arduino dispenser, fUS integrated`
4. Choose **Private** (recommended for unpublished lab work) or Public.
5. Do **not** tick "Add a README", ".gitignore" or "license" — the project has them.
6. Click **Create repository**.

## C. Upload the project (first time)

Extract the ZIP into a **new, empty folder** (not inside an old project that
already has a `.git` folder). Then in `cmd`:

```cmd
cd %USERPROFILE%\Documents\water-reach-task-fus-integrated
git init
git add .
git status
```

**Check the `git status` list before going on.** It must NOT contain
`config.json`, `.venv`, or any `.xlsx` / `.csv` files. (They are excluded by
`.gitignore`; if you see them, stop and ask.)

```cmd
git commit -m "Water Reach Task v1.0.0"
git branch -M main
git remote add origin https://github.com/mine7minee/water-reach-task-fus-integrated.git
git push -u origin main
```

At the first `push` a **browser window opens** ("Git Credential Manager").
Click **Sign in with your browser** → **Authorize** → come back to `cmd`;
the upload finishes by itself. If `cmd` seems to wait, look for that browser
window — it may be behind other windows.

> **Never** put a token inside the URL (`https://user:TOKEN@github.com/...`):
> Git stores that URL in plain text in `.git\config`. Never paste a token in a
> chat or a screenshot. If that happened, delete the token at
> <https://github.com/settings/tokens> immediately.

## D. Upload later changes

```cmd
cd %USERPROFILE%\Documents\water-reach-task-fus-integrated
git add .
git commit -m "Describe what you changed"
git push
```

## E. Remove an old repository that contained private data

Editing a file on GitHub does **not** remove its old versions — they stay in
the history. If an earlier repository contained IP addresses, device IDs,
personal paths or a Python environment folder, delete that repository:
GitHub → the old repository → **Settings** → scroll to the bottom →
**Delete this repository**.

In the old local folder also remove any token from the saved address:

```cmd
cd <old project folder>
git remote set-url origin https://github.com/mine7minee/<old-repository-name>.git
```
