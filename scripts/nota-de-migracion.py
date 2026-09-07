#!/usr/bin/env python3
"""
Genera la nota de migracion y rollback de una liberacion.

Nace de una leccion concreta: `docs/RELEASE.md` decia que revertir era
redesplegar el tag anterior, y eso **falla** si la liberacion trajo una
migracion — alembic aborta con `Can't locate revision identified by ...`.
La instruccion correcta depende de que migraciones lleve cada release, asi que
se deriva del propio repositorio en vez de escribirse a mano.

Uso:
    python scripts/nota-de-migracion.py v1.26.0          # contra un tag
    python scripts/nota-de-migracion.py v1.26.0 --md     # en markdown, para el PR

Pega la salida en el cuerpo del PR, en el mensaje del tag anotado y en el
CHANGELOG de la version.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

VERSIONS = "app/db/migrations/versions"
_REV = re.compile(r"^revision(?::\s*str)?\s*=\s*[\"'](.+?)[\"']", re.M)
_DOWN = re.compile(r"^down_revision(?::\s*[^=]+)?\s*=\s*(.+)$", re.M)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def _revisiones_en(ref: str | None) -> dict[str, str | None]:
    """{revision: down_revision} en un ref de git, o en el árbol de trabajo."""
    fuentes = {}
    if ref is None:
        for p in sorted(Path(VERSIONS).glob("*.py")):
            if p.name != "__init__.py":
                fuentes[p.name] = p.read_text()
    else:
        listado = _git("ls-tree", "--name-only", ref, f"{VERSIONS}/").split("\n")
        for ruta in listado:
            if ruta.endswith(".py") and not ruta.endswith("__init__.py"):
                fuentes[Path(ruta).name] = _git("show", f"{ref}:{ruta}")

    revisiones = {}
    for src in fuentes.values():
        r, d = _REV.search(src), _DOWN.search(src)
        if not r:
            continue
        crudo = d.group(1).strip() if d else "None"
        padre = None if crudo.startswith("None") else crudo.strip("\"'")
        revisiones[r.group(1)] = padre
    return revisiones


def _cabeza(revisiones: dict[str, str | None]) -> str | None:
    if not revisiones:
        return None
    padres = {p for p in revisiones.values() if p}
    cabezas = set(revisiones) - padres
    return sorted(cabezas)[0] if cabezas else None


def _camino(revisiones: dict[str, str | None], desde: str | None, hasta: str) -> list:
    """Revisiones entre `desde` (excluida) y `hasta` (incluida), en orden."""
    camino, cursor = [], hasta
    while cursor is not None and cursor != desde:
        camino.append(cursor)
        cursor = revisiones.get(cursor)
    return list(reversed(camino))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "anterior", help="tag o ref de la liberación anterior (ej. v1.26.0)"
    )
    ap.add_argument("--md", action="store_true", help="salida en markdown")
    args = ap.parse_args()

    try:
        previas = _revisiones_en(args.anterior)
    except subprocess.CalledProcessError:
        print(f"No se pudo leer el ref {args.anterior!r}.", file=sys.stderr)
        return 1

    actuales = _revisiones_en(None)
    cabeza_previa, cabeza_actual = _cabeza(previas), _cabeza(actuales)
    nuevas = _camino(actuales, cabeza_previa, cabeza_actual) if cabeza_actual else []

    b = "**" if args.md else ""
    print(f"{b}Migraciones{b}")
    print()

    if not nuevas:
        print(f"Ninguna. La cabeza sigue en `{cabeza_actual}`.")
        print()
        print(f"{b}Rollback{b}: redesplegar el tag anterior. No toca el esquema.")
        return 0

    for rev in nuevas:
        print(f"- `{rev}`")
    print()
    print(f"Cabeza: `{cabeza_previa}` → `{cabeza_actual}`")
    print()
    print(f"{b}Rollback{b}")
    print()
    print("1. **Casi siempre basta revertir la imagen.** Las migraciones son")
    print("   aditivas (expand/contract), así que el código anterior convive con")
    print("   el esquema nuevo: ignora lo que no conoce. El despliegue ya revierte")
    print("   la imagen solo si el contenedor no levanta.")
    print()
    print("2. **Solo si hace falta revertir también el esquema** — y antes de")
    print("   desplegar el tag viejo, porque el archivo de la migración vive en la")
    print("   imagen nueva:")
    print()
    print("   ```bash")
    print("   docker run --rm --network siscom-network --env-file .env \\")
    print(f"     siscom-admin-api:latest alembic downgrade {cabeza_previa}")
    print("   ```")
    print()
    print("   Sin este paso, desplegar un tag anterior falla con")
    print(f"   `Can't locate revision identified by '{cabeza_actual}'`.")
    print()
    print("   ⚠️ El downgrade **borra** lo que la migración creó. Es seguro poco")
    print("   después de liberar; deja de serlo en cuanto entre dato nuevo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
