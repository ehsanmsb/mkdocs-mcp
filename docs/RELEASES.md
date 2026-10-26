# Releases and versioning

This repository uses [Conventional Commits](https://www.conventionalcommits.org/)
and `semantic-release`. The [Build and Release workflow](../.github/workflows/release.yml)
runs tests on pull requests and pushes to `main`.

Every successful push to `main` publishes GHCR image tags `main` and
`sha-<commit-sha>`. Commits that require a version bump also create a `vX.Y.Z`
Git tag, GitHub release with generated notes, Python wheel, Helm package, and
image tags `X.Y.Z`, `X.Y`, and `latest`.

| Commit | Version impact |
| --- | --- |
| `feat: add a tool` | Minor |
| `fix: handle an empty result` or `perf: reduce indexing work` | Patch |
| `feat!: change tool output` or a `BREAKING CHANGE:` footer | Major |
| `docs:`, `test:`, `ci:`, `chore:`, `build:`, `refactor:` | No release unless marked breaking |

Release notes show Features, Bug Fixes, Performance, and Refactoring. Routine
documentation, test, CI, build, and chore commits are omitted from the notes.
Normal releases are automatic; do not create or edit version tags manually.

The Helm chart in a source checkout defaults to the moving `main` image. A
versioned Helm package from a GitHub release defaults to its matching versioned
image. For a repeatable deployment from a checkout, set
`image.tag=sha-<commit-sha>`.
