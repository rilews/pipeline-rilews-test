# Changelog

Todos los cambios notables de este proyecto se documentan acá.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
versionado según [Semantic Versioning](https://semver.org/lang/es/).

## Cómo agregar una entrada

Cada release nueva agrega una sección arriba de todo (orden descendente, más reciente primero),
usando este esqueleto:

```markdown
## [vX.Y.Z] - AAAA-MM-DD

### Features
- Descripcion corta del endpoint/funcionalidad nueva.

### Fix
- Descripcion corta del bug corregido y su causa si es relevante.

### Changed
- Cambios que no son ni feature nueva ni fix (refactors, docs, CI/CD, config).
```

Reglas simples:
- Si una sección no aplica (ej. un release sin fixes), se omite — no dejar el título vacío.
- Una línea por cambio, en pasado/imperativo corto ("Añade X", "Corrige Y"), sin detalle de implementación.
- El release que viene de un **hotfix** siempre lleva `### Fix`, nunca `### Features`.
- Completar esta sección **al momento de hacer `git flow release start`**, antes de `finish`
  (o justo después, como parte del PR/commit de cierre), para no tener que reconstruir el
  historial de memoria más adelante.

---

## [Unreleased]

_(cambios ya en `develop` que todavía no salieron en un release)_

---

## [v1.4.0] - 2026-07-09

### Changed
- Añade job `build-release` (push a `release/**`): cierra el gap donde un commit directo en
  una rama release (ej. el propio changelog) no tenía imagen construida y `promote` fallaba
  con `not found` al resolver `HEAD^2`.
  
---

## [v1.3.0] - 2026-07-09

### Changed
- Añade job `deploy` al pipeline (`.github/workflows/docker.yml`): tras `promote`, corre en
  runner self-hosted (`lan-server`) y hace `docker compose pull` + `up -d` contra el servidor
  en red local, usando `docker-compose.prod.yml` (imagen `:latest` desde `ghcr.io`, sin rebuild).

---

## [v1.2.1] - 2026-07-09

### Changed
- Corrige documentación (CONTRIBUTING.md: orden correcto push develop → esperar build → release).

---

## [v1.2.0] - 2026-07-09

### Features
- Añade endpoint `/mod` (resto).

### Fix
- Corrige `/mod` para usar módulo (`a % b`) en vez de resta — bug intencional para validar que
  el job `test` bloquea el PR cuando un test falla.

### Changed
- Añade documentación de contribución (CONTRIBUTING.md).

---

## [v1.2.2] - 2026-07-09

### Fix
- Corrige contributing para especificar changelod

---

## [v1.1.1] - 2026-07-08

### Fix
- Corrige `/multiply` para usar multiplicación (`a * b`) en vez de resta — hotfix sobre bug
  introducido en v1.1.0.

---

## [v1.1.0] - 2026-07-08

### Features
- Añade endpoint `/divide` con manejo de división por cero y tests.

---

## [v1.0.1] - 2026-07-08

### Fix
- Corrige `/multiply` para usar resta en vez de multiplicación *(nota: este fix quedó mal —
  ver v1.1.1, que lo corrige de nuevo)*.

---

## [v1.0.0] - 2026-07-08

### Features
- Primera versión: calculadora Flask con `/sum`, `/subtract`, `/health`.
- Añade endpoint `/multiply` (sin tests).
- Pipeline CI/CD con Gitflow + soporte de hotfix (`.github/workflows/docker.yml`).
- Tests automatizados (`pytest`) como gate previo al build.
- Documentación de restricciones/CONTRIBUTING inicial.
