# Releases and versioning

This repository uses [Conventional Commits](https://www.conventionalcommits.org/)
and `semantic-release`. The [Build and Release workflow](../.github/workflows/release.yml)
runs tests on pull requests and pushes to `main`.

Every successful push to `main` publishes GHCR image tags `main` and
`sha-<commit-sha>`. Commits that require a version bump also create a `vX.Y.Z`
Git tag, GitHub release with generated notes, Python wheel, Helm package, and
image tags `X.Y.Z`, `X.Y`, and `latest`.
The versioned image is built after the Python, lockfile, and chart versions are
updated, so its package metadata matches its image tag.

| Commit | Version impact |
| --- | --- |
| `feat: add a tool` | Minor |
| `fix: handle an empty result` or `perf: reduce indexing work` | Patch |
| `feat!: change tool output` or a `BREAKING CHANGE:` footer | Major |
| Other Conventional Commit types, including `docs:` and `chore:` | Patch |

Release notes show Features, Bug Fixes, Performance, and Refactoring. Routine
documentation, test, CI, build, and chore commits are omitted from the notes.
Normal releases are automatic; do not create or edit version tags manually.
Each push to `main` containing Conventional Commits triggers one release based
on the highest change level among those commits. A release
commit with `[skip ci]` records the new version in `Chart.yaml`,
`pyproject.toml`, and `uv.lock`; it does not trigger another build.

The Helm chart in a source checkout defaults to the image tag in its
`appVersion`. The release workflow updates chart `version` and `appVersion`
together and packages that chart with the matching image tag. To deploy an
unreleased commit, set `image.tag=sha-<commit-sha>` explicitly.
