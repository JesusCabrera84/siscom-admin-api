"""Integridad de la cadena de migraciones de alembic.

Estas pruebas no tocan ninguna base de datos: leen los ficheros de revision.
Existen porque el incidente del 3 de septiembre (ver §18/§19 del documento de
arquitectura y docs/adr) mostro que nada en CI miraba las migraciones. Un PR
podia introducir una cabeza duplicada, un downgrade vacio o una revision
huerfana y la CI seguia en verde: el fallo aparecia en produccion, durante el
despliegue, que es la primera vez que se ejecuta `alembic upgrade head`.
"""

import re
from pathlib import Path

import pytest

VERSIONS_DIR = (
    Path(__file__).resolve().parents[1] / "app" / "db" / "migrations" / "versions"
)

_REVISION_RE = re.compile(r"^revision(?::\s*str)?\s*=\s*[\"'](.+?)[\"']", re.M)
_DOWN_RE = re.compile(r"^down_revision(?::\s*[^=]+)?\s*=\s*(.+)$", re.M)


def _parse(path: Path):
    src = path.read_text()
    rev = _REVISION_RE.search(src)
    down = _DOWN_RE.search(src)
    assert rev, f"{path.name}: no se encontro 'revision ='"
    assert down, f"{path.name}: no se encontro 'down_revision ='"
    raw = down.group(1).strip()
    parent = None if raw in ("None", "None  # noqa") else raw.strip("\"'")
    return rev.group(1), parent, src


@pytest.fixture(scope="module")
def migrations():
    files = sorted(p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py")
    assert files, "no hay migraciones que revisar"
    return [(p,) + _parse(p) for p in files]


def test_revisiones_unicas(migrations):
    """Dos migraciones con el mismo id hacen que alembic ignore una en silencio."""
    seen = {}
    for path, rev, _parent, _src in migrations:
        assert rev not in seen, f"revision duplicada {rev!r}: {path.name} y {seen[rev]}"
        seen[rev] = path.name


def test_una_sola_cabeza(migrations):
    """Dos cabezas es el fallo que produce un PR paralelo sin rebase.

    Alembic aborta con 'Multiple head revisions are present', pero hoy eso solo
    se descubre en el despliegue. Aqui se descubre en el PR.
    """
    revisions = {rev for _p, rev, _parent, _s in migrations}
    parents = {parent for _p, _r, parent, _s in migrations if parent}
    heads = revisions - parents
    assert len(heads) == 1, f"se esperaba una cabeza, hay {len(heads)}: {sorted(heads)}"


def test_una_sola_base(migrations):
    """Una segunda base significa un arbol desconectado que nunca se aplicara."""
    bases = [rev for _p, rev, parent, _s in migrations if parent is None]
    assert len(bases) == 1, f"se esperaba una base, hay {len(bases)}: {sorted(bases)}"


def test_sin_padres_huerfanos(migrations):
    """Un down_revision que apunta a una revision borrada rompe toda la cadena."""
    revisions = {rev for _p, rev, _parent, _s in migrations}
    for path, rev, parent, _src in migrations:
        if parent is not None:
            assert (
                parent in revisions
            ), f"{path.name} ({rev}) desciende de {parent!r}, que no existe"


def test_cadena_recorre_todas_las_migraciones(migrations):
    """Desde la cabeza se debe llegar a la base pasando por todas.

    Detecta ramas laterales: revisiones que existen pero que 'upgrade head'
    nunca aplicaria.
    """
    by_rev = {rev: parent for _p, rev, parent, _s in migrations}
    revisions = set(by_rev)
    head = (revisions - {p for p in by_rev.values() if p}).pop()

    visitadas = set()
    cursor = head
    while cursor is not None:
        assert cursor not in visitadas, f"ciclo en la cadena en {cursor!r}"
        visitadas.add(cursor)
        cursor = by_rev[cursor]

    faltan = revisions - visitadas
    assert not faltan, f"revisiones fuera de la cadena principal: {sorted(faltan)}"


def test_todas_tienen_downgrade_con_cuerpo(migrations):
    """Un downgrade vacio convierte el rollback en una mentira.

    Alembic acepta 'pass' y reporta exito, dejando el esquema intacto y la
    version marcada como revertida: el peor de los dos mundos.
    """
    sin_cuerpo = []
    for path, rev, _parent, src in migrations:
        bloque = re.search(r"def downgrade\(\).*?(?=\ndef |\Z)", src, re.S)
        assert bloque, f"{path.name}: no define downgrade()"
        cuerpo = [
            linea.strip()
            for linea in bloque.group(0).split("\n")[1:]
            if linea.strip()
            and not linea.strip().startswith("#")
            and not linea.strip().startswith('"""')
        ]
        if not cuerpo or cuerpo == ["pass"]:
            sin_cuerpo.append(f"{path.name} ({rev})")
    assert not sin_cuerpo, "downgrade() vacio en: " + ", ".join(sin_cuerpo)


def test_prefijo_del_fichero_coincide_con_el_orden(migrations):
    """El prefijo numerico debe crecer con la cadena.

    Es convencion, no requisito de alembic, pero es lo que hace que el
    directorio se lea en orden. Un fichero 019_x.py que en la cadena va
    despues de 022 es exactamente el tipo de sorpresa que nadie quiere
    descubrir migrando produccion.
    """
    by_rev = {rev: parent for _p, rev, parent, _s in migrations}
    rev_to_prefix = {}
    for path, rev, _parent, _s in migrations:
        prefijo = path.name.split("_", 1)[0]
        assert prefijo.isdigit(), f"{path.name}: el nombre no empieza por un numero"
        rev_to_prefix[rev] = int(prefijo)

    for rev, parent in by_rev.items():
        if parent is not None:
            assert rev_to_prefix[rev] > rev_to_prefix[parent], (
                f"{rev} (prefijo {rev_to_prefix[rev]}) desciende de {parent} "
                f"(prefijo {rev_to_prefix[parent]}): el orden del directorio miente"
            )
