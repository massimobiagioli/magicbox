# How to Create a New App

Checklist: from nothing to an app deployed by Jenkins at
`https://magicbox.local/<app>` on every push to `main` (ADR-0016, ADR-0017).
Replace `<app>` (lowercase letters, digits, hyphens; e.g. `orders-api`).
`controller$` = on your workstation, in the `magicbox` repository.

## 0. Prerequisites (once)

- [ ] MagicBox running: `make deploy`, `make stacks`.
- [ ] Jenkins with credentials `github` and `portainer-api-token`
      (installation guide 4.1): `make ci-cd`.
- [ ] API gateway: `make api-gateway` (installation guide 4.2).
- [ ] `stacks_jenkins_github_user` set in `inventory/hosts.yml`.
- [ ] GitHub token of Jenkins with access to **All repositories** (Contents:
      Read-only, Commit statuses: Read and write), so new repositories need
      no token change. Otherwise add each new repository to the token.
- [ ] GitHub CLI logged in, for `--create-repo`: `gh auth status`.

## 1. Create the app

```text
controller$ uv run tools/new_app.py <app> --create-repo
```

- [ ] Output ends with `Registered <app>: port 180xx` and the push to
      `https://github.com/<github-user>/<app>`.

What it did: project `../<app>` from `templates/python-fastapi-app` (renamed,
`uv lock`, first commit), private GitHub repository with `main` pushed, entry
in the apps registry `inventory/group_vars/magicbox/apps.yml` (first free
port). Without `--create-repo`: create the private repository on GitHub, then
`git -C ../<app> push -u origin main`.

Existing repository (already pushed, with the template's `Jenkinsfile` and
`deploy/`): add the entry by hand instead (template:
`inventory/apps.example.yml`). The gateway route `/<app>` is derived from
`name` and `port`; there is no separate route setting.

```yaml
magicbox_apps:
  - name: <app>          # job, stack, container, path /<app>
    port: 180xx          # unique, 18000-18999
    repo: https://github.com/<github-user>/<repository>
```

- [ ] Everything the pipeline needs is committed and pushed to `main`:
      Jenkins builds from GitHub, not from the local folder.

## 2. Register it on MagicBox

```text
controller$ make apps
```

- [ ] Ends with `failed=0`; the report lists `<app>: registered, not deployed yet`.
- [ ] Jenkins (`https://magicbox.local/jenkins/`) shows the job `<app>`; its
      first scan starts the build of `main`.

## 3. First deployment

- [ ] Build `<app> > main > #1`: Prepare, Lint, Test, Build, Deploy, Verify
      green (the first build is slower: base image pull).
- [ ] Deploy log: `Created stack '<app>'`.
- [ ] `https://magicbox.local/<app>/health` answers `{"status":"ok"}`.
- [ ] Optional: `make apps` reports `<app>: deployed`.

## 4. Develop

```text
controller$ cd ../<app>
controller$ uv sync && uv run uvicorn app.main:app --reload    # http://127.0.0.1:8000/
controller$ uv run ruff check . && uv run ruff format --check . && uv run pytest
```

- [ ] Write routes in `app/` and a unit test for each in `tests/`.
- [ ] Routes are served from `/` (Kong strips `/<app>`); use relative links.
- [ ] Push to `main`: deployed within 5 minutes. Other branches: Lint and
      Test only. A failing lint or test stops before the deploy.
- [ ] Do not edit `Jenkinsfile` or `deploy/`: they are generic. Container
      port other than 8000: change it in `Dockerfile` and `deploy/stack.yml`.
- [ ] `README.md` of `magicbox`, table "Addresses": add the app URL.

## 5. Remove an app

- [ ] Delete its entry from `inventory/group_vars/magicbox/apps.yml`, then
      `make apps` (removes the route and the port).
- [ ] Jenkins: delete the job `<app>`. Portainer: delete the stack `<app>`.

## 6. Test an app again from scratch

Keep the registry entry; only the job and the stack are reset.

- [ ] Portainer (`https://magicbox.local:9443/`), environment `homelab`: delete
      the stack `<app>` (removes the container).
- [ ] Jenkins: delete the job `<app>` (with its builds).
- [ ] `controller$ make apps`: recreates the job and starts its first scan,
      even when the registry is unchanged.
- [ ] Steps 2 and 3 again; Deploy log `Created stack '<app>'` (without the
      stack reset: `Updated stack`).

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `new_app.py`: "set stacks_jenkins_github_user" | Set it in `inventory/hosts.yml` or pass `--repo` |
| `new_app.py`: "already exists" | Pick another name or delete the folder |
| `gh` fails | `gh auth login`, then create the repository and push by hand (step 1) |
| `make apps`: "run `make ci-cd` first" | Jenkins predates the apps support: `make ci-cd` |
| `make apps`: assertion on `<app>` | Name or port duplicated or reserved, or bad `repo` URL |
| Job scan: no branches / 401 | GitHub token cannot read the repository: prerequisite 0 |
| Lint or Test fails | Run step 4 commands locally; nothing is deployed |
| Deploy: HTTP 401 | `vault_jenkins_portainer_token` (installation guide 4.1), `make ci-cd` |
| Deploy: "not in the MagicBox apps registry" | Run `make apps` |
| Verify fails | `HEALTHCHECK` in `Dockerfile`; `sudo docker logs <app>` on MagicBox |
| `/<app>` returns 404 | `make apps` not run since the app was added |
| `/<app>` returns 502 | Not deployed yet: check the Jenkins build |
