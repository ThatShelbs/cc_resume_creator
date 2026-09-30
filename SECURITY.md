# Security and privacy

## What stays on your computer

- The app is a local web page served from `127.0.0.1`. It refuses connections from other
  computers and from other websites, and every request needs a random token created at launch.
- Your profile, resumes, fact bank, job postings, and generated files are stored in your data
  folder (`%LOCALAPPDATA%\ResumeTaylor` by default), outside the code folder and outside git.
- An API key entered in Settings is saved in `secrets.json` in that folder. It is never returned
  by the app's API, never written to logs, and only passed to the Claude tool when you generate.

## What leaves your computer

Only the text of your materials and the job posting, sent to Claude (Anthropic) when you press
Generate, Draft, or Structure. Nothing is sent to the project authors or any other service.

## Keeping personal data out of GitHub

- `.gitignore` excludes `.env`, `secrets.json`, your data folders, and Word/PDF files outside
  `examples/` and `docs/`.
- `python scripts/check_no_personal_data.py --install-hook` installs a pre-commit check that blocks
  resumes, keys, and project folders. CI runs the same check on every push, including all history.
- Never post your data folder or `.env` in an issue. `Doctor.bat` output is safe to share.

## If you already committed something private

Removing a file in a new commit does not remove it from history. Make the repository private,
delete it and start a fresh one, or rewrite history with `git filter-repo`. Rotate any API key
that was ever committed at https://console.anthropic.com/.

## Reporting a vulnerability

Open a private security advisory on the GitHub repository, or email the maintainer.
