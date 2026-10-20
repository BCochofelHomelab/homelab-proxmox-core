# Contributing

How a change gets from an idea to the homelab, whether you make it or the
AI agent does, and the rules it follows on the way. Setting things up in
the first place is [`docs/SETUP.md`](docs/SETUP.md); this page is the day
to day.

## How a change flows

Every change goes through a pull request, in one of two lanes. The AI
agent proposes changes as its machine user. You propose changes too, and
you're the only one who reviews, merges and applies.

### The AI agent's lane

```mermaid
flowchart TD
  task(["A task from you"]) --> branch["Branches in its own clone<br/>(its devcontainer)"]
  branch --> change["Makes the change and runs the checks<br/>that need no credentials"]
  change --> push["Commits and pushes<br/>as bcochofel-ai-agent"]
  push --> pr["Opens the pull request<br/>(workflow files go in its description)"]
  pr --> ci{"CI passes?"}
  ci -- no --> change
  ci -- yes --> you(["Waits for your review:<br/>your lane"])
```

It works in its devcontainer ([`docs/DEVCONTAINER.md`](docs/DEVCONTAINER.md)),
as its machine user, `bcochofel-ai-agent`, never as you.

- **Its checks:** `mise run lint`, `tofu init -backend=false && tofu
  validate`, `ansible-lint` and `--syntax-check`. It follows CI with `gh
  pr checks` and pushes fixes to the same branch.
- **What it can't do:** push `.github/workflows/` (those files go in the
  pull request's description, for you to add), merge, approve, tag,
  decrypt your secrets, or reach a host.

### Your lane

```mermaid
flowchart TD
  own(["Your change<br/>(your WSL clone, as you)"]) --> pr["Pull request"]
  agent(["The AI agent's<br/>pull request"]) --> pr
  pr --> ci["CI: pre-commit<br/>(GitHub-hosted)"]
  pr --> approve["You approve the<br/>dry-run environment"]
  approve --> dry["Dry-run on runner01:<br/>plan and check, a comment on the PR"]
  ci --> review{"Diff, CI and<br/>dry-run all good?"}
  dry --> review
  review -- no --> fix["Request changes,<br/>or push a fix"]
  fix --> pr
  review -- yes --> merge["Approve and merge"]
  merge --> release["Release: semantic-release<br/>tags main"]
  release --> apply["Apply from main:<br/>tofu:plan, tofu:apply, ansible:site"]
  apply --> verify{"Health check<br/>passes?"}
  verify -- no --> own
```

You work in your own WSL clone, as you. The branch, commit and pull
request steps are the same as the AI agent's; you can also run `mise run
tofu:plan` for an early look. Yours is the only lane that can change
`.github/workflows/`, and the only one that reviews, merges and applies.

**On the pull request:**

| Workflow | Runs on | When | What |
| --- | --- | --- | --- |
| `ci.yml` | GitHub-hosted | every push | pre-commit on every file, gitleaks on the full history; no credentials |
| `dry-run.yml` | `runner01` | after you approve the `dry-run` environment (*Review deployments → Approve and deploy*) | `tofu plan` if `terraform/` changed, `ansible-playbook --check --diff` if `ansible/` changed; the summary as a comment on the pull request, the full output as an encrypted artifact ([`docs/SETUP.md`](docs/SETUP.md#stage-8-the-dry-run-runner-optional)) |

A new push needs a new approval, of the pull request and of its dry-run,
and cancels the pull request's previous dry-run. A fork's pull request
never reaches the runner.

**Review and merge.** Read the diff and the dry-run's comment, then
approve. Every pull request needs one approval from a code owner, the
`sre-lead` team, and every review conversation resolved
([`docs/SETUP.md`](docs/SETUP.md#rulesets)). **Merge right after you
approve:** once approved, GitHub would let any user with Write merge, the
machine user included. GitHub never lets you approve your own pull
request, nor one whose last push was yours: merge those with the ruleset's
admin bypass, which works only through a pull request. Squash or rebase
merges only (linear history).

**Release.** `release.yml` runs semantic-release on the merge to `main`
(below). Nothing is deployed at this step.

**Apply**, from your WSL clone only:

```bash
git switch main && git pull
mise run tofu:plan        # saves terraform/tfplan; compare it with the pull request's dry-run
mise run tofu:apply       # applies exactly that plan, and writes hosts.ini
mise run ansible:site     # --limit <host or group> to touch only what changed
```

If your plan differs from the pull request's dry-run (a change by hand,
another merge), stop and find out why before applying. Always OpenTofu
first (VMs and inventory), then Ansible.

**Verify.** `site.yml` ends with the health check (`99-healthcheck.yml`):
what this repo deploys fails the run, external dependencies are reported.
A problem means a new pull request, never a live edit on a host.

## Branches

[Trunk-based development](https://trunkbaseddevelopment.com/): `main` is
the trunk, always deployable; work happens on short-lived branches,
deleted after merge. Names follow
[Conventional Branch](https://conventionalbranch.org/) 1.1.0,
`<prefix>/<description>`:

| Prefix | For |
| --- | --- |
| `feature/` (or `feat/`) | new capability |
| `bugfix/` (or `fix/`) | bug fix |
| `hotfix/` | urgent fix |
| `release/` | release preparation |
| `chore/` | non-code work: dependencies, docs, tooling |

Lowercase letters, numbers and hyphens only; dots only in release versions
(`release/v5.1.0`). An AI agent may use the spec's agent prefixes (e.g.
`claude/`). Keep the prefix and the commit type in line: a `feature/`
branch carries `feat:` commits. Keep each pull request to one logical
change.

## Commits and releases

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/),
checked by commitlint ([`commitlint.config.js`](commitlint.config.js)):
`<type>(optional scope): <subject>`, with type `feat`, `fix`, `docs`,
`style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` or `revert`,
lowercase: anything else is refused, `Fix:` included (the release reads
only `fix` and `feat`, so a capital silently skips the release).
`git commit` without `-m` opens the repo's template.

[semantic-release](https://semantic-release.gitbook.io/)
([`.releaserc.js`](.releaserc.js)) computes each version from them, on
`main` only:

- `fix:` → patch; `feat:` → minor; `!` after the type or a
  `BREAKING CHANGE:` footer → major;
- `docs:`, `chore:`, `style:` and the rest → no release on their own.

It publishes a GitHub Release with generated notes and a tag, with the
workflow's own token: no `CHANGELOG.md`, nothing pushed to `main`.

Pull requests are squash-merged, with the pull request's title as the
whole commit (single-commit pull requests too): that title is the only
thing semantic-release reads, so:

- **The title takes the highest type of its commits, lowercase:** `feat`
  if any commit is a feature, else `fix` if any is a fix, else the rest.
  A pull request titled `refactor:` that adds a feature releases nothing.
- **A breaking change goes in the title** (`feat!:`): commit bodies,
  `BREAKING CHANGE:` footers included, don't reach `main`.
- CI checks the title with the same commitlint rules.

## Checks

`mise install` installs the git hooks, so `git commit` runs
[`.pre-commit-config.yaml`](.pre-commit-config.yaml): file hygiene, Packer,
OpenTofu (fmt, validate, terraform-docs, TFLint, Trivy, Checkov),
markdownlint, ansible-lint, ShellCheck, gitleaks, SOPS files encrypted,
actionlint and zizmor on workflows, and commitlint. CI runs the same.

```bash
mise run lint      # every hook on every file
mise run check     # the above + gitleaks on the full history (what CI runs)
```

Three repo-specific rules the hooks enforce:

- **Every `check_mode: false`** says why it's safe on the same line
  (`check_mode: false # read-only: ...`): it runs for real in the CI
  dry-run.
- **Every action in a workflow** is pinned to a commit SHA, with its
  version in a comment.
- **A secret-named OpenTofu or Packer variable** (token, secret,
  password, hash, private key, API key) has no default and is
  `sensitive = true` ([`docs/CREDENTIALS.md`](docs/CREDENTIALS.md#secret-tiers)).
  A name that only looks secret goes in the allowlist of
  [`scripts/check_secret_variables.py`](scripts/check_secret_variables.py),
  with the reason.

Silence a ShellCheck finding only with a `# shellcheck disable=SCxxxx`
comment that says why.

## Toolchain

Every command-line tool is pinned in [`mise.toml`](mise.toml), with each
download's checksum in `mise.lock`: your workstation, CI and the
devcontainer run the same versions (CI and the devcontainer install in
locked mode). `mise tasks` lists the repo's commands; `mise run doctor`
shows what's installed.

The tasks are named `<namespace>:<action>`:

| Namespace | For |
| --- | --- |
| `setup:` | Installing: hooks, TFLint plugins, `.venv/`, the MCP servers. |
| `lint`, `lint:secrets`, `check` | The checks that need no credentials; `check` is both, what CI runs. |
| `check:` | Verifying the credentials, the AI agent's boundary and the runner. |
| `packer:`, `tofu:`, `ansible:`, `secrets:` | Your credentialed commands, one namespace per tool. |
| `ci:` | The dry-run, as the `ci` identity. |

| Tool | For |
| --- | --- |
| Packer | The VM template ([`docs/PACKER.md`](docs/PACKER.md)). |
| OpenTofu (`tofu`) | The VMs and the inventory ([`docs/TERRAFORM.md`](docs/TERRAFORM.md)); `terraform` is pinned only as a rollback path. |
| Ansible, ansible-lint | Configuring the hosts ([`docs/ANSIBLE.md`](docs/ANSIBLE.md)); in `.venv/`, from `requirements.txt`. |
| Terramate | Unused here for now. |
| TFLint, terraform-docs, Trivy, Checkov | Linting, docs and policy for the OpenTofu code. |
| ShellCheck, markdownlint-cli2, actionlint, zizmor | Shell scripts, Markdown, and GitHub workflows (lint and security). |
| gitleaks | No secret committed: staged changes, and the full history in CI. |
| SOPS, age | The encrypted secret files and their keys ([`docs/CREDENTIALS.md`](docs/CREDENTIALS.md)). |
| pre-commit, commitlint, semantic-release | Hooks, commit messages, releases. |
| GitHub CLI (`gh`) | Pull requests and runs; the machine user's in the devcontainer. |
| Python, uv, Node.js | The runtimes for `.venv/` and the Node-based hooks. |
| github-mcp-server, terraform-mcp-server, mcp-proxmox | The AI agent's read-only MCP servers ([`docs/CREDENTIALS.md`](docs/CREDENTIALS.md) step 8). |

Pinned elsewhere, in their own ecosystem's file: Ansible and ansible-lint
(`requirements.txt`, ranges), the Ansible collections
(`ansible/requirements.yml`, minimums), the pre-commit hook repositories
(`.pre-commit-config.yaml`), semantic-release (`package-lock.json`), the
OpenTofu providers (`.terraform.lock.hcl`), Packer's Proxmox plugin
(`versions.pkr.hcl`, minimum), the devcontainer image
(`devcontainer.json`), and the workflows' actions (commit SHAs).

**Bumping a version.** Nothing updates on its own: no Dependabot, no
Renovate.

1. `mise run outdated` lists newer versions of the pinned tools and hooks.
2. Edit the pin in `mise.toml` (or the file above), then `mise lock` and
   `MISE_LOCKED=1 mise install`.
3. Read the release notes, run `mise run lint`, and commit the pin with its
   lockfiles.

mise itself is pinned as `MISE_VERSION` in `.devcontainer/post-create.sh`,
which [`docs/SETUP.md`](docs/SETUP.md#stage-1-workstation)'s install
command reads, and as `version:` in every workflow's `jdx/mise-action`
step, so CI runs the same mise. A pre-commit check
([`scripts/check_mise_version.py`](scripts/check_mise_version.py)) fails
when they differ. To bump it, change both: `post-create.sh` in your pull
request, the workflows as a commit of yours (the AI agent can't push
workflows). Read the release notes, and check that a locked install still
works and `mise lock` leaves `mise.lock` unchanged, before you merge.
`terraform-mcp-server`'s entry spells out its URL and
checksum, so its bump updates all three.
