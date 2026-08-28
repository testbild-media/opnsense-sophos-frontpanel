# Publishing this repository on GitHub

This source tree is ready to be used as the root of a GitHub repository.
Recommended repository name:

```text
opnsense-sophos-frontpanel
```

## First push

For the target repository `testbild-media/opnsense-sophos-frontpanel`, start from
this source tree. If the GitHub repository is empty, run:

```sh
git init
git add .
git commit -m "Initial public release v1.0.0"
git branch -M main
git remote add origin git@github.com:testbild-media/opnsense-sophos-frontpanel.git
git push -u origin main
```

HTTPS can be used instead of SSH if preferred.

## Create the v1.0.0 release

```sh
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

Then create a GitHub Release from tag `v1.0.0`. GitHub automatically provides
source `.zip` and `.tar.gz` archives for the tag.

Use [RELEASE_NOTES_1.0.0.md](RELEASE_NOTES_1.0.0.md) as the initial release
text if desired.

## Recommended repository settings

- Default branch: `main`
- Require CI to pass before merging to `main`
- Enable Issues
- Enable private vulnerability reporting / Security Advisories
- Enable automatically generated release notes if desired
- Do not commit locally generated `/packages/` binaries; the directory is in
  `.gitignore`

## Repository metadata

Suggested description:

```text
Native OPNsense plugin for the original Sophos SG/XG 16x2 LCD front panel and chassis buttons.
```

Suggested topics:

```text
opnsense
freebsd
sophos
sg330
lcd
rs232
firewall
plugin
```

## Project URL in locally built packages

`tools/build-package.sh` accepts an optional `PROJECT_URL` environment variable.
Once the repository has a final GitHub URL, use for example:

```sh
PROJECT_URL=https://github.com/testbild-media/opnsense-sophos-frontpanel \
  sh tools/build-package.sh
```

You can also replace the default project URL in the script before publishing.
