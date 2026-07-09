# Contribuir a este proyecto

Este repo usa **Gitflow** (con soporte de hotfix) + GitHub Actions para CI/CD.
Si no conocés Gitflow, leé primero el modelo original de Vincent Driessen:
https://nvie.com/posts/a-successful-git-branching-model/

Usamos la extensión [git-flow (AVH Edition)](https://github.com/petervanderdoes/gitflow-avh)
para los comandos (`git flow feature start`, `git flow release start`, etc).
Config del repo: `master` está mapeado a `main`.

**`git flow release finish` y `git flow hotfix finish` NO se usan en este repo.** Ambos
mergean localmente y hacen `git push` directo a `main`/`develop`, y el ruleset de esas ramas
("Require a pull request before merging") rechaza ese push. Se usa `start`/`publish` de
git-flow para crear y subir la rama; el cierre real (merge a `main` y a `develop`, tag, borrado
de rama) se hace a mano vía PR — ver el detalle en las secciones 4 y 5.

---

## 1. Ramas y su función

| Rama | Función | Nace de | Se mergea a |
|---|---|---|---|
| `main` | Producción. Cada commit acá (vía merge) dispara el pipeline de promoción. | — | — |
| `develop` | Integración. Todo lo terminado y probado vive acá antes de un release. | `main` (una vez) | — |
| `feature/*` | Una funcionalidad nueva en desarrollo. | `develop` | `develop` (vía PR) |
| `release/*` | Congela una versión para estabilizarla antes de producción. | `develop` | `main` y `develop` |
| `hotfix/*` | Arregla un bug urgente ya en producción, sin esperar el próximo release. | `main` | `main` y `develop` |

---

## 2. Los jobs de CI/CD (`.github/workflows/docker.yml`)

| Job | Tag | Dispara en | Qué hace |
|---|---|---|---|
| `test` | **[CI]** | `pull_request` a `develop`/`main`, y push directo a `develop`/`hotfix/**`/`release/**` | Corre `pytest` sobre `calculadora/`. Gate: si falla, `build`/`build-hotfix`/`build-release` no corren. |
| `build` | **[CI+CD]** | push a `develop` | Build real (`target: prod`) + push a `ghcr.io` con tags `:develop` y `:sha-<short>`. |
| `build-hotfix` | **[CI+CD]** | push a `hotfix/**` | Igual que `build`, pero solo tag `:sha-<short>` (sin tag flotante). |
| `build-release` | **[CI+CD]** | push a `release/**` | Igual que `build-hotfix`, solo tag `:sha-<short>`. Cubre commits hechos directo en la rama release (ej. el changelog) antes de `finish`. |
| `promote` | **[CD]** | push a `main` (merge commit) | Sin rebuild. Copia la imagen correcta (`develop`, hotfix o release, según cuál se mergeó) a `:latest`. Ver detalle abajo. |
| `release` | **[CD]** | evento `release` publicado en GitHub | Sin rebuild. Copia `:latest` a `:vX.Y.Z` y `:X.Y.Z`. |
| `deploy` | **[CD]** | evento `release` publicado, después de `release` | Sin rebuild. En runner self-hosted (`lan-server`), `docker compose pull` + `up -d` del stack en el servidor LAN, usando `docker-compose.prod.yml` con `IMAGE_TAG=<tag del release>` — despliega la versión exacta publicada, nunca `:latest`. |

**Importante:** todo commit hecho directo en `release/x.y.z` (ej. `docs: actualiza changelog para
vX.Y.Z`) pasa por `test` + `build-release` gracias al trigger `release/**`. Sin esa imagen puntual,
`promote` fallaría con `not found` al resolver `HEAD^2` en `main` — es justo el commit del
changelog el que termina siendo la punta de la rama que se mergea.

**Deploy solo pasa con un GitHub Release publicado.** Un push a `main` dispara `promote`
(actualiza `:latest` + `:sha-<merge-commit>` en el registry) pero **no** toca el servidor —
el servidor solo se actualiza cuando corrés `gh release create vX.Y.Z ...` (ver sección 4).
Si necesitás el código en el servidor sin cortar un release formal, no hay atajo automático
todavía; hacelo a mano en el servidor.

### El detalle importante de `promote`

Un hotfix se mergea a `main` **sin pasar por `develop`**. Si `promote` promoviera siempre la
imagen `:develop`, en un hotfix estaría publicando código viejo/incorrecto. Por eso, en vez de
usar un tag fijo, `promote` lee **`HEAD^2`** (el segundo padre del merge commit en `main`), que
siempre es el tip de la rama que se acaba de mergear — sea `develop` o `hotfix/x.y.z` — y
promueve esa imagen puntual. Esto solo funciona porque los merges a `main` son siempre
**merge commits reales** (nunca squash ni rebase).

---

## 3. Flujo: nueva feature

```bash
# Desde develop, crear la rama
git flow feature start nombre-feature

# ... codear, commitear ...
git add <archivos>
git commit -m "feat: descripcion del cambio"

# Publicar la rama (push a origin)
git flow feature publish nombre-feature

# Abrir PR hacia develop — esto dispara el job `test` como check requerido
gh pr create --base develop --head feature/nombre-feature \
  --title "feat: nombre-feature" --body "Descripcion"
```

Ejemplo real de este repo (endpoint `/divide`):

```bash
git flow feature start división
# ... se edita app.py y test_app.py ...
git add calculadora/app.py calculadora/test_app.py
git commit -m "feat: añade endpoint /divide con tests"
git flow feature publish división
gh pr create --base develop --head feature/división --title "feat: división"
```

Una vez que el PR pasa el check `Test (calculadora)` (branch protection lo exige) y se mergea
en GitHub, sincronizá tu local:

```bash
git checkout develop && git pull
git branch -d feature/división
```

---

## 4. Flujo: release (estando en `develop`)

**`main` y `develop` tienen un ruleset con "Require a pull request before merging".** Esto
significa que **`git flow release finish` ya no sirve para publicar** — ese comando mergea
localmente y hace `git push origin main`/`git push origin develop` directo, y ambos pushes van
a ser rechazados por el ruleset. Se usa `git flow release start`/`publish` para crear y subir
la rama, pero el cierre (mergear a `main` y a `develop`) se hace **con PRs**, igual que ya se
hacía con hotfix.

**Antes de arrancar, un requisito que no queda escrito en ningún lado salvo acá:**
el merge de tu PR a `develop` dispara el job `Build & Push (develop)`, que sube la imagen
`:sha-<corto>` a `ghcr.io`. **Ese job tiene que terminar antes** de abrir el PR del release —
si el build de `develop` todavía está corriendo, `promote` va a buscar una imagen
`:sha-<HEAD^2>` que todavía no existe en el registry y falla con `not found`. Andá a la pestaña
**Actions** del repo y confirmá que `Build & Push (develop)` esté en verde antes de seguir.

```bash
# 1. Iniciar release desde develop
git flow release start vX.Y.Z

# 2. Actualizar CHANGELOG.md: mover lo que este bajo [Unreleased] a una
#    seccion nueva [vX.Y.Z] - AAAA-MM-DD (ver seccion 6 para el detalle),
#    commitear ese cambio en la propia rama release/vX.Y.Z
git add CHANGELOG.md
git commit -m "docs: actualiza changelog para vX.Y.Z"

# 3. (opcional) otros ajustes de ultimo minuto en la rama release/vX.Y.Z

# 4. Publicar la rama (push a origin, NO es rama protegida, esto anda directo)
#    Dispara test + build-release: confirmar verde en Actions antes de seguir
git flow release publish vX.Y.Z
```

### Cerrar el release: PR a `main`, tag, PR a `develop`

```bash
# 5. PR hacia main (merge commit obligatorio — squash/rebase estan deshabilitados
#    a nivel repo, asi que --merge es la unica opcion valida)
gh pr create --base main --head release/vX.Y.Z --title "Release vX.Y.Z"
gh pr merge release/vX.Y.Z --merge
# esto dispara `promote` automaticamente al mergear (push a main)

# 6. Tag — los tags no son ramas, no pasan por el ruleset, se pushean directo
git checkout main && git pull
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin --tags

# 7. Back-merge a develop, tambien por PR (antes era push directo)
gh pr create --base develop --head release/vX.Y.Z --title "chore: sincroniza vX.Y.Z en develop"
gh pr merge release/vX.Y.Z --merge

# 8. Limpieza (delete_branch_on_merge esta apagado en el repo, se borra a mano)
git push origin --delete release/vX.Y.Z
git branch -d release/vX.Y.Z
```

### Después del release: crear el GitHub Release

Esto dispara el job `release` (tagea la imagen con el semver) y, a continuación, `deploy`
(despliega ese mismo tag en el servidor LAN):

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes --target main
```

Ejemplo real (v1.5.0, con este flujo ya migrado a PR):

```bash
git flow release start v1.5.0
# ... editar CHANGELOG.md, commitear ...
git add CHANGELOG.md && git commit -m "docs: actualiza changelog para v1.5.0"
git flow release publish v1.5.0
gh pr create --base main --head release/v1.5.0 --title "Release v1.5.0"
gh pr merge release/v1.5.0 --merge
git checkout main && git pull
git tag -a v1.5.0 -m "Release v1.5.0"
git push origin --tags
gh pr create --base develop --head release/v1.5.0 --title "chore: sincroniza v1.5.0 en develop"
gh pr merge release/v1.5.0 --merge
git push origin --delete release/v1.5.0
gh release create v1.5.0 --title "v1.5.0" --generate-notes --target main
```

---

## 5. Flujo: hotfix (bug en producción)

Cuando hay un bug urgente en `main` que no puede esperar al próximo release normal:

```bash
# 1. Crear el hotfix desde main
git flow hotfix start vX.Y.Z

# 2. Arreglar el bug, commitear
git add <archivos>
git commit -m "fix: descripcion del arreglo"

# 2b. Actualizar CHANGELOG.md: agregar seccion [vX.Y.Z] - AAAA-MM-DD con el
#     fix bajo ### Fix (ver seccion 6). Un hotfix nunca lleva ### Features.
git add CHANGELOG.md
git commit -m "docs: actualiza changelog para vX.Y.Z"

# 3. Publicar la rama (esto dispara build-hotfix en CI, sube :sha-<short>)
git flow hotfix publish vX.Y.Z

# 4. PR hacia main — dispara `test` como check requerido antes de mergear
gh pr create --base main --head hotfix/vX.Y.Z \
  --title "hotfix: vX.Y.Z" --body "Descripcion del fix"

# 5. Mergear (merge commit obligatorio, squash/rebase deshabilitados a nivel repo)
gh pr merge hotfix/vX.Y.Z --merge
# esto dispara `promote` automaticamente al mergear (push a main)
```

### Sincronizar el fix de vuelta a develop

Un hotfix arregla `main`, pero si no se propaga a `develop`, el próximo release normal
reintroduciría el mismo bug. `develop` también tiene "Require a pull request before merging"
en el ruleset, así que este back-merge **también va por PR**, no por push directo:

```bash
git checkout main && git pull
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin --tags

# Back-merge a develop por PR (antes era push directo)
gh pr create --base develop --head hotfix/vX.Y.Z --title "chore: sincroniza hotfix vX.Y.Z en develop"
gh pr merge hotfix/vX.Y.Z --merge

# GitHub Release, dispara los jobs `release` + `deploy`
gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes --target main

# Limpieza (delete_branch_on_merge esta apagado, se borra a mano)
git push origin --delete hotfix/vX.Y.Z
git branch -d hotfix/vX.Y.Z
```

Ejemplo real de este repo (`/multiply` tenía `a - b` en vez de `a * b`, hotfix v1.1.1 —
anterior a la migración a PR-only; con el flujo actual sería igual pero con
`gh pr merge hotfix/v1.1.1 --merge` en vez de push directo):

```bash
git flow hotfix start v1.1.1
# ... se corrige app.py, se agregan tests ...
git add calculadora/app.py calculadora/test_app.py
git commit -m "fix: corrige /multiply para usar multiplicacion (a * b) en vez de resta"
git flow hotfix publish v1.1.1
gh pr create --base main --head hotfix/v1.1.1 --title "hotfix: v1.1.1"
gh pr merge hotfix/v1.1.1 --merge
git checkout main && git pull
git tag -a v1.1.1 -m "Release v1.1.1"
git push origin --tags
gh pr create --base develop --head hotfix/v1.1.1 --title "chore: sincroniza hotfix v1.1.1 en develop"
gh pr merge hotfix/v1.1.1 --merge
gh release create v1.1.1 --title "v1.1.1" --generate-notes --target main
git push origin --delete hotfix/v1.1.1
git branch -d hotfix/v1.1.1
```

### Por qué el hotfix garantiza que se promueve la imagen correcta

El PR de un hotfix se mergea directo a `main` (nunca pasa por `develop`). Al pushear ese merge
commit, el job `promote` lee `HEAD^2` — que en este caso es el tip de `hotfix/vX.Y.Z`, la misma
imagen que `build-hotfix` ya subió como `:sha-<ese-commit>` — y la promueve a `:latest`. Es
justo el caso que el fix de `promote` (sección 2) existe para manejar bien.

---

## 6. Changelog (`CHANGELOG.md`)

Cada release (normal u hotfix) tiene que dejar una entrada en `CHANGELOG.md`, en la raíz del
repo. Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/):

```markdown
## [vX.Y.Z] - AAAA-MM-DD

### Features
- Descripcion corta del endpoint/funcionalidad nueva.

### Fix
- Descripcion corta del bug corregido y su causa si es relevante.

### Changed
- Cambios que no son ni feature nueva ni fix (refactors, docs, CI/CD, config).
```

Reglas:
- Entradas en orden descendente (más reciente arriba de todo, debajo de `[Unreleased]`).
- Si una sección no aplica, se omite — no dejar el título vacío.
- Una línea por cambio, corta, sin detalle de implementación ("Añade X", "Corrige Y").
- Un release de **hotfix** siempre lleva `### Fix`, nunca `### Features`.
- Mientras se trabaja en `develop` (features todavía sin release), esos cambios van
  acumulándose bajo `## [Unreleased]`, arriba de todo. Al cortar el release, esa sección se
  vacía y su contenido pasa a la sección `[vX.Y.Z]` nueva.
- Se actualiza **dentro de la rama `release/*` o `hotfix/*`** (ver los pasos 2/2b en las
  secciones 4 y 5), no después — así el commit del changelog queda parte del mismo release.
