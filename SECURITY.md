# Security Policy

## Supported versions

Security fixes are provided for the latest release and the current `main` branch.

## Reporting a vulnerability

Please do not publish credentials, access tokens, personal calendar data, or an exploit in a public issue.

Instead, use GitHub's private vulnerability reporting feature for this repository when available. If private reporting is unavailable, open a minimal public issue that only asks for a private contact channel and does not disclose the vulnerability details.

## Security notes

- Feishu authentication is delegated to `lark-cli`; this project does not ask users to paste app secrets into the UI.
- Personal configuration is stored locally and `config.json` is excluded from version control.
- Release updates are fetched from this repository's GitHub Releases.
- Update archives are validated before files are copied into the installation directory.
- Maintainer credentials never live in the repository or in its Git remotes: `git remote` uses a plain HTTPS URL and authentication is delegated to the `gh` credential helper (`gh auth git-credential`). A token pasted into a remote URL ends up in plaintext in `.git/config`, where backups, sync tools and pasted logs pick it up; `tests/test_repo_hygiene.py` fails the build if that happens. Removing a leaked token from the URL is not enough — revoke it on GitHub and issue a new one.
