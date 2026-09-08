## ¿Qué hace este PR?

<!-- Descripción clara y concisa del cambio -->

## Tipo de cambio

- [ ] Bug fix (cambio que corrige un error sin romper nada)
- [ ] Nueva funcionalidad (cambio que agrega funcionalidad)
- [ ] Breaking change (fix o feature que rompe comportamiento existente)
- [ ] Refactor / mejora interna
- [ ] Documentación
- [ ] Tests
- [ ] Actualización de dependencias

## Migraciones y rollback

<!--
OBLIGATORIO. Pega aquí la salida de:

    python scripts/nota-de-migracion.py <tag-o-rama-anterior> --md

Si el PR no toca `app/db/migrations/versions/`, el script lo dirá y con eso
basta. No lo escribas a mano: se deriva del repositorio para que no envejezca.

Existe porque `docs/RELEASE.md` decía que revertir era redesplegar el tag
anterior, y eso FALLA cuando la liberación trae una migración: alembic aborta
con `Can't locate revision identified by ...`.
-->

## Checklist

- [ ] **Base branch:** `develop` (no `master`)
- [ ] Mi código sigue las convenciones del proyecto
- [ ] Corrí `make validate` (lint + format-check + test + docker build)
- [ ] Actualicé `CHANGELOG.md` en `[Unreleased]` (si aplica)
- [ ] **Pegué la nota de migración y rollback** (sección de arriba), aunque sea para decir que no hay migraciones
- [ ] Actualicé documentación relevante (si aplica)

## Issues relacionados

Closes #<!-- número de issue -->
