# Seguridad, Privacidad de Datos y Git Hooks

Este documento describe la arquitectura de seguridad del repositorio, las políticas de aislamiento de información sensible y la implementación de controles automáticos pre-commit para prevenir fugas accidentales de datos personales o credenciales hacia el control de versiones.

---

## 1. Modelo de Aislamiento de Variables (`.env`)

El archivo `.env` almacena la configuración de identidad del estudiante que se inyecta dinámicamente en las portadas de los documentos y en los nombres de archivo generados.

### Directiva Inviolable:
* El archivo `.env` **nunca se versiona en Git**.
* Su nombre está explícitamente listado en `.gitignore`.
* En su lugar, el repositorio distribuye [.env.example](../../.env.example) como molde estructurado.

```
[Entorno de Trabajo]                   [Control de Versiones (Git)]
├── .env.example (Molde público) ──────► Versionado en Git
└── .env (Configuración local activa) ──► BLOQUEADO por .gitignore y Hook Pre-Commit
```

---

## 2. Hook de Seguridad Pre-Commit (`.githooks/pre-commit`)

Para mitigar el riesgo de que un usuario ejecute `git add -f .env` o intente subir credenciales de forma involuntaria, el repositorio provee un hook de seguridad automatizado en `.githooks/pre-commit`.

### Activación Automática:
Al ejecutar `./setup.sh` o `setup.bat`, se ejecuta la directiva de Git:
```bash
git config core.hooksPath .githooks
```

### Lógica de Inspección del Hook:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Bloquear estrictamente cualquier intento de staging de .env
if git diff --cached --name-only | grep -E '^(\.env|\.env\.local)$' >/dev/null; then
    echo "[ERROR DE SEGURIDAD] Intento de commit del archivo .env detectado." >&2
    echo "                      El archivo .env contiene datos locales protegidos." >&2
    echo "                      Ejecute: git reset HEAD .env" >&2
    exit 1
fi

# 2. Escanear el diff staged en busca de credenciales o secretos obvios
PATRONES_SECRETOS='(BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY|ghp_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9_-]{20}|AKIA[0-9A-Z]{16})'

if git diff --cached -S"PRIVATE KEY" -G"$PATRONES_SECRETOS" --name-only | grep -v 'test' >/dev/null 2>&1; then
    echo "[ERROR DE SEGURIDAD] Se detectó un patrón de clave privada o token en el commit." >&2
    exit 1
fi

exit 0
```

---

## 3. Política de Privacidad del Repositorio

El repositorio está diseñado para operar de forma segura en modalidad **Pública (Open Source)**:

1. **Aislamiento de Workspace y Datos Privados:** `.env`, `materias/*` (conservando solo `materias/.gitkeep`) y `themes/local/` permanecen ignorados en `.gitignore`.
2. **Protección de Propiedad Intelectual:** Los enunciados docentes, entregables personales y logos institucionales propios nunca se versionan en el repositorio público.
