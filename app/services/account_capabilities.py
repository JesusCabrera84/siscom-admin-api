"""
Resolución de capabilities **comerciales**, con techo descendente.

Es el punto único de resolución del nivel de cuenta, hermano de
`app.services.capabilities`, que resuelve el nivel operativo de la organización.
Los dos niveles y su justificación están en §4 del documento de arquitectura.

LA REGLA, EN UNA FRASE
======================
Una cuenta no puede tener más de lo que tiene su ancestro. Mero Mero no puede
darle a Empresa 500 más de lo que Geminis le dio a Mero Mero.

Eso es lo que hace posible la **administración delegada**: dejar que el partner
gestione a sus miles de clientes sin poder regalarse capacidad. Sin ella, la
reventa no es delegable y cada alta tendría que pasar por Geminis.

CÓMO SE CALCULA
===============
Se camina el `account_path` de la raíz a la hoja y se pliegan los valores
**explícitos** que se encuentran:

    int   -> min(...)   un ancestro solo puede bajar el número
    bool  -> AND        un ancestro que dice False lo prohíbe para todo el subárbol
    text  -> el más cercano gana

`text` es la excepción a propósito, y conviene que esté escrito: un texto no
tiene orden, así que «techo» no significa nada sobre él. `self_signup_mode` no
es mayor ni menor que otro modo. Para esos códigos la regla es que el valor más
cercano a la hoja gana, y si eso resulta insuficiente cuando se definan sus
modos, la respuesta es modelarlos como algo ordenable — no inventar aquí un
orden que el tipo no tiene.

QUÉ SIGNIFICA NO TENER FILA — Y POR QUÉ IMPORTA
===============================================
Una cuenta sin fila para una capability **no restringe**: hereda lo que venga de
arriba. No significa cero.

Esa distinción es exactamente la de §17 —«vacío no es sin límite»—, y aquí
aparece en su forma peligrosa: si «sin fila» se tratara como cero, el sistema
denegaría todo hasta configurar cada cuenta una por una; si se tratara como
«sin límite», un descendiente sin fila escaparía del techo de su ancestro. Lo
correcto es la tercera opción: **sin fila no aporta al plegado**, y el resultado
lo determinan las filas que sí existen.

De ahí que el valor por defecto se aplique **solo cuando no hay ninguna fila en
todo el camino**, y nunca como un techo más. Si el default entrara en el
plegado, conceder 5 000 subcuentas a un partner daría `min(default, 5000)` y el
permiso otorgado no serviría de nada.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.capability import AccountCapability, Capability

# Valores cuando NADIE en el camino ha dicho nada. Deliberadamente restrictivos:
# una cuenta recién creada no revende ni tiene marca propia hasta que alguien lo
# conceda explícitamente.
DEFAULT_ACCOUNT_CAPABILITIES: dict[str, Any] = {
    "white_label_enabled": False,
    "max_custom_domains": 0,
    "max_sub_accounts": 0,
    "can_resell": False,
}


class CaminoDeCuentaInvalido(RuntimeError):
    """
    El `account_path` de la cuenta no es utilizable.

    Es un error y no un valor por defecto **a propósito**. Un camino vacío o
    ausente significa que el invariante que sostiene el aislamiento entre
    clientes no se cumple, y en ese estado la respuesta correcta no es «sin
    límite» ni «todo denegado en silencio»: es negarse a responder. Ver §17.
    """


@dataclass
class CapabilidadDeCuenta:
    """
    El resultado de resolver una capability comercial.

    Attributes:
        code: código de la capability
        value: el valor efectivo
        source: 'cuenta' (lo puso ella misma), 'ancestro' (heredado o recortado)
            o 'default' (nadie en el camino dijo nada)
        limitado_por: la cuenta cuyo valor recortó al de la propia cuenta, si
            alguna lo hizo. Es lo que contesta «¿por qué no puedo subirlo?»
            sin tener que leer el árbol a mano.
        aportantes: las cuentas del camino que tenían fila vigente, de la raíz
            a la hoja
    """

    code: str
    value: Union[int, bool, str, None]
    source: str
    limitado_por: Optional[UUID] = None
    aportantes: list[UUID] = field(default_factory=list)

    def as_bool(self) -> bool:
        """El valor como booleano. Un `None` es False, no «sin restricción»."""
        if isinstance(self.value, bool):
            return self.value
        if isinstance(self.value, int):
            return self.value > 0
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "1", "yes", "enabled")
        return False

    def as_int(self) -> int:
        """El valor como entero."""
        if isinstance(self.value, bool):
            return 1 if self.value else 0
        if isinstance(self.value, int):
            return self.value
        if isinstance(self.value, str) and self.value.isdigit():
            return int(self.value)
        return 0


def _recortar(acumulado: Any, nuevo: Any) -> Any:
    """
    Pliega el valor de un descendiente contra lo que traía de sus ancestros.

    No decide por el tipo declarado de la capability sino por el del valor real,
    porque es el que está en la fila y el que no puede mentir.
    """
    if isinstance(acumulado, bool) or isinstance(nuevo, bool):
        # AND: basta que un ancestro lo prohíba.
        return bool(acumulado) and bool(nuevo)
    if isinstance(acumulado, int) and isinstance(nuevo, int):
        return min(acumulado, nuevo)
    # Texto (o tipos mezclados, que solo pasa si alguien cambió el value_type
    # con filas ya escritas): gana el más cercano a la hoja.
    return nuevo


def resolver(
    db: Session,
    account_id: UUID,
    code: str,
) -> CapabilidadDeCuenta:
    """
    Resuelve una capability comercial para una cuenta, aplicando el techo de
    todos sus ancestros.

    Raises:
        CaminoDeCuentaInvalido: si la cuenta no existe o su camino está vacío.
    """
    cuenta = db.query(Account).filter(Account.id == account_id).first()
    if cuenta is None:
        raise CaminoDeCuentaInvalido(f"La cuenta {account_id} no existe")

    camino = list(cuenta.account_path or [])
    if not camino:
        raise CaminoDeCuentaInvalido(
            f"La cuenta {account_id} no tiene account_path. Lo mantienen dos "
            "triggers en la base: si falta, el esquema está en un estado que "
            "no permite decidir permisos."
        )

    capability = db.query(Capability).filter(Capability.code == code).first()
    if capability is None:
        # La capability no está definida en la base. `self_signup_mode` es hoy
        # el caso real: la 027 no la siembra porque sus modos siguen sin
        # acordarse.
        return CapabilidadDeCuenta(
            code=code, value=DEFAULT_ACCOUNT_CAPABILITIES.get(code), source="default"
        )

    filas = (
        db.query(AccountCapability)
        .filter(
            AccountCapability.account_id.in_(camino),
            AccountCapability.capability_id == capability.id,
        )
        .all()
    )

    # Un límite caducado no restringe ni concede: se ignora igual que si no
    # existiera la fila.
    por_cuenta = {f.account_id: f for f in filas if not f.is_expired()}

    valor: Any = None
    aportantes: list[UUID] = []

    # De la raíz a la hoja: el orden del camino ya es ése.
    for id_en_camino in camino:
        fila = por_cuenta.get(id_en_camino)
        if fila is None:
            continue  # no aporta: hereda lo que venga de arriba
        aportantes.append(id_en_camino)
        nuevo = fila.get_value()
        valor = nuevo if valor is None else _recortar(valor, nuevo)

    if valor is None:
        return CapabilidadDeCuenta(
            code=code, value=DEFAULT_ACCOUNT_CAPABILITIES.get(code), source="default"
        )

    # ¿Pidió la cuenta más de lo que le dejaron? Se compara su propio valor
    # contra el efectivo, no el orden en que se plegaron: con un camino
    # A(5) -> B(10) -> C(3) quien manda al final es C, aunque B fuera recortado
    # por A en el camino. Atribuir el recorte al primero que ocurrió daría una
    # explicación falsa.
    propia = por_cuenta.get(account_id)
    valor_propio = propia.get_value() if propia is not None else None

    limitado_por: Optional[UUID] = None
    if valor_propio is not None and valor != valor_propio:
        # El techo lo impone el ancestro cuyo valor es el que quedó. Si hay
        # varios iguales manda el más cercano a la hoja, que es el que el
        # partner puede entender sin ver todo el árbol.
        for id_ancestro in reversed(camino[:-1]):
            fila = por_cuenta.get(id_ancestro)
            if fila is not None and fila.get_value() == valor:
                limitado_por = id_ancestro
                break

    if valor_propio is not None and limitado_por is None:
        origen = "cuenta"
    else:
        origen = "ancestro"

    return CapabilidadDeCuenta(
        code=code,
        value=valor,
        source=origen,
        limitado_por=limitado_por,
        aportantes=aportantes,
    )


def puede(db: Session, account_id: UUID, code: str) -> bool:
    """Si una capability booleana está concedida a lo largo de todo el camino."""
    return resolver(db, account_id, code).as_bool()


def limite(db: Session, account_id: UUID, code: str) -> int:
    """El límite numérico efectivo, ya recortado por los ancestros."""
    return resolver(db, account_id, code).as_int()


def validar_limite(db: Session, account_id: UUID, code: str, actual: int) -> bool:
    """
    Si cabe uno más sin pasarse del límite.

    Un límite de 0 es **cero**, no «ilimitado» — al contrario que en
    `app.services.capabilities`, donde `limit <= 0` se interpreta como sin
    tope. La diferencia es deliberada y es la razón por la que este servicio
    existe aparte: los defaults de aquí son 0 precisamente para que una cuenta
    sin permiso explícito no pueda revender ni reclamar dominios. Si 0
    significara «ilimitado», el valor por defecto concedería todo.
    """
    tope = limite(db, account_id, code)
    if tope < 0:
        return True
    return actual < tope


def resolver_todas(db: Session, account_id: UUID) -> dict[str, CapabilidadDeCuenta]:
    """
    Todas las capabilities **comerciales**, resueltas para la cuenta.

    No recorre la tabla `capabilities` entera: ahí conviven los códigos
    operativos —`max_devices`, `history_days`— que se resuelven por
    organización y nunca tendrán fila a nivel de cuenta. Devolverlos aquí en
    `default` sugeriría que este servicio opina sobre ellos, y no opina.

    El conjunto comercial son los códigos que este módulo conoce, más
    cualquiera que de hecho tenga una fila en `account_capabilities` — de modo
    que una capability comercial nueva sembrada en la base aparezca en cuanto
    se use, sin esperar a que alguien la añada a la constante.
    """
    codigos = set(DEFAULT_ACCOUNT_CAPABILITIES)
    en_uso = (
        db.query(Capability.code)
        .join(AccountCapability, AccountCapability.capability_id == Capability.id)
        .distinct()
        .all()
    )
    codigos.update(code for (code,) in en_uso)
    return {code: resolver(db, account_id, code) for code in sorted(codigos)}
