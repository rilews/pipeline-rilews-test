# Contribuir a este proyecto

Este repo usa **Gitflow** (con soporte de hotfix) + GitHub Actions para CI/CD.
Si no conocés Gitflow, leé primero el modelo original de Vincent Driessen:
https://nvie.com/posts/a-successful-git-branching-model/

Usamos la extensión [git-flow (AVH Edition)](https://github.com/petervanderdoes/gitflow-avh)
para los comandos (`git flow feature start`, `git flow release start`, etc).
Config del repo: `master` está mapeado a `main`.

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
| `test` | **[CI]** | `pull_request` a `develop`/`main`, y push directo a `develop`/`hotfix/**` | Corre `pytest` sobre `calculadora/`. Gate: si falla, `build`/`build-hotfix` no corren. |
| `build` | **[CI+CD]** | push a `develop` | Build real (`target: prod`) + push a `ghcr.io` con tags `:develop` y `:sha-<short>`. |
| `build-hotfix` | **[CI+CD]** | push a `hotfix/**` | Igual que `build`, pero solo tag `:sha-<short>` (sin tag flotante). |
| `promote` | **[CD]** | push a `main` (merge commit) | Sin rebuild. Copia la imagen correcta (`develop` o el hotfix, según cuál se mergeó) a `:latest`. Ver detalle abajo. |
| `release` | **[CD]** | evento `release` publicado en GitHub | Sin rebuild. Copia `:latest` a `:vX.Y.Z` y `:X.Y.Z`. |

**Pendiente / no implementado todavía:** no existe un job que corra al pushear una rama `release/**`.
Si commiteás algo directamente en `release/x.y.z` (ej. un ajuste de último minuto), ese commit
**no** pasa por `test` ni se buildea — el `promote` posterior puede fallar porque no va a
encontrar la imagen `:sha-<ese-commit>`. Por ahora, evitar commitear en `release/*`; si hace
falta, se agrega un trigger `push: branches: ['release/**']` más adelante.

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

```bash
# 1. Iniciar release desde develop
git flow release start vX.Y.Z

# 2. (opcional) ajustes de ultimo minuto en la rama release/vX.Y.Z
#    ver la nota en la seccion 2: esos commits no pasan por CI todavia

# 3. Cerrar el release: merge a main + tag + merge de vuelta a develop + borra la rama
git flow release finish -m "Release vX.Y.Z" vX.Y.Z
```

### Cómo pushear el release (el paso que más se presta a confusión)

`git flow release finish` te deja parado en `develop` después de mergear. Un `git push` simple
ahí **solo sube `develop`** — `main` y el tag quedan sin subir si no lo hacés explícito:

```bash
git push origin main
git push origin develop
git push origin --tags
```

El push a `main` dispara automáticamente el job `promote` (evento `push`, sin necesidad de
nada más).

### Después del release: crear el GitHub Release

Esto dispara el job `release`, que tagea la imagen con el semver:

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes --target main
```

Ejemplo real (v1.1.0):

```bash
git flow release start v1.1.0
git flow release finish -m "Release v1.1.0" v1.1.0
git push origin main
git push origin develop
git push origin --tags
gh release create v1.1.0 --title "v1.1.0" --generate-notes --target main
```

Si el `finish` queda a medio camino (pasa a veces: los merges se hacen pero falta el tag o
no borra la rama `release/*`), completalo a mano:

```bash
git checkout main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git branch -d release/vX.Y.Z
git push origin main && git push origin --tags
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

# 3. Publicar la rama (esto dispara build-hotfix en CI, sube :sha-<short>)
git flow hotfix publish vX.Y.Z

# 4. PR hacia main — dispara `test` como check requerido antes de mergear
gh pr create --base main --head hotfix/vX.Y.Z \
  --title "hotfix: vX.Y.Z" --body "Descripcion del fix"
```

### Sincronizar el fix de vuelta a develop

Un hotfix arregla `main`, pero si no se propaga a `develop`, el próximo release normal
reintroduciría el mismo bug. Después de mergear el PR a `main`:

```bash
git checkout main && git pull
git tag -a vX.Y.Z -m "Release vX.Y.Z"

git checkout develop && git pull
git merge main
git push origin develop

git push origin main
git push origin --tags

# GitHub Release, dispara el job `release`
gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes --target main

# Limpieza
git branch -d hotfix/vX.Y.Z
git push origin --delete hotfix/vX.Y.Z
```

Ejemplo real de este repo (`/multiply` tenía `a - b` en vez de `a * b`, hotfix v1.1.1):

```bash
git flow hotfix start v1.1.1
# ... se corrige app.py, se agregan tests ...
git add calculadora/app.py calculadora/test_app.py
git commit -m "fix: corrige /multiply para usar multiplicacion (a * b) en vez de resta"
git flow hotfix publish v1.1.1
gh pr create --base main --head hotfix/v1.1.1 --title "hotfix: v1.1.1"

# despues de mergear el PR:
git checkout main && git pull
git tag -a v1.1.1 -m "Release v1.1.1"
git checkout develop && git pull && git merge main && git push origin develop
git push origin main
git push origin --tags
gh release create v1.1.1 --title "v1.1.1" --generate-notes --target main
git branch -d hotfix/v1.1.1
git push origin --delete hotfix/v1.1.1
```

### Por qué el hotfix garantiza que se promueve la imagen correcta

El PR de un hotfix se mergea directo a `main` (nunca pasa por `develop`). Al pushear ese merge
commit, el job `promote` lee `HEAD^2` — que en este caso es el tip de `hotfix/vX.Y.Z`, la misma
imagen que `build-hotfix` ya subió como `:sha-<ese-commit>` — y la promueve a `:latest`. Es
justo el caso que el fix de `promote` (sección 2) existe para manejar bien.
