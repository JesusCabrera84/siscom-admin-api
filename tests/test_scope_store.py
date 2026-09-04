"""
Tests de la materialización del alcance en Valkey.

Se usa un doble de cliente en vez de un Valkey real: lo que hay que fijar aquí es
la forma de las claves, el TTL y —sobre todo— que el índice inverso no revele
identidad, no el comportamiento de Valkey.
"""

import base64
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services import scope_store
from app.services.access_control import Grant, TimeWindow
from app.services.scope_store import (
    RevocationIndexNotConfigured,
    ScopePurpose,
    ScopeStore,
    ScopeStoreUnavailable,
    jti_key,
    owner_key,
    scope_keys,
)

INDEX_SECRET = base64.b64encode(b"index-secret-exactly-32-bytes!!!").decode()


def _grant(internal_id, *, open_window=True):
    """Concesión mínima: ventana abierta salvo que se diga lo contrario."""
    end = None if open_window else datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Grant(internal_id=str(internal_id), windows=(TimeWindow(end=end),))


class FakePipeline:
    def __init__(self, store):
        self.store = store
        self.ops = []

    def sadd(self, key, *values):
        self.ops.append(("sadd", key, values))

    def hset(self, key, mapping=None):
        self.ops.append(("hset", key, mapping))

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))

    def set(self, key, value, ex=None):
        self.ops.append(("set", key, value, ex))

    def execute(self):
        for op in self.ops:
            if op[0] == "sadd":
                self.store.sets.setdefault(op[1], set()).update(op[2])
            elif op[0] == "hset":
                self.store.hashes.setdefault(op[1], {}).update(op[2])
            elif op[0] == "expire":
                self.store.ttls[op[1]] = op[2]
            elif op[0] == "set":
                self.store.strings[op[1]] = op[2]
                self.store.ttls[op[1]] = op[3]
        self.store.executed.append(list(self.ops))
        self.ops = []


class FakeValkey:
    def __init__(self):
        self.sets = {}
        self.hashes = {}
        self.strings = {}
        self.ttls = {}
        self.executed = []

    def pipeline(self):
        return FakePipeline(self)

    def delete(self, *keys):
        removed = 0
        for key in keys:
            gone = self.sets.pop(key, None) is not None
            gone = self.hashes.pop(key, None) is not None or gone
            gone = self.strings.pop(key, None) is not None or gone
            removed += 1 if gone else 0
            self.ttls.pop(key, None)
        return removed

    def get(self, key):
        value = self.strings.get(key)
        return value.encode() if isinstance(value, str) else value

    def hget(self, key, field):
        """Lo que hará siscom-api: autoriza y traduce en una sola operación."""
        value = self.hashes.get(key, {}).get(field)
        return value.encode() if isinstance(value, str) else value

    def smembers(self, key):
        return {v.encode() for v in self.sets.get(key, set())}

    def srem(self, key, *values):
        self.sets.get(key, set()).difference_update(values)
        return len(values)


@pytest.fixture
def fake():
    return FakeValkey()


@pytest.fixture
def store(monkeypatch, fake):
    monkeypatch.setattr(
        "app.services.scope_store.settings.DATA_TOKEN_INDEX_SECRET_B64", INDEX_SECRET
    )
    monkeypatch.setattr(
        "app.services.scope_store.settings.VALKEY_SCOPE_TTL_MARGIN_SECONDS", 300
    )
    return ScopeStore(fake)


def test_writes_devices_and_units_under_the_scope_ref(store, fake):
    scope_ref, subject = uuid4(), uuid4()
    dev, unit = uuid4(), uuid4()
    unit_id = uuid4()

    store.write_scope(
        scope_ref,
        subject_id=subject,
        devices={dev: _grant("123456789012345")},
        units={unit: _grant(unit_id)},
        token_ttl_seconds=600,
    )

    dev_key, unit_key = scope_keys(scope_ref)
    assert json.loads(fake.hashes[dev_key][str(dev)])["id"] == "123456789012345"
    assert json.loads(fake.hashes[unit_key][str(unit)])["id"] == str(unit_id)


def test_hget_authorises_and_translates_in_one_step(store, fake):
    """La operación que hará siscom-api: `nil` deniega, el valor traduce."""
    scope_ref, dev = uuid4(), uuid4()
    store.write_scope(
        scope_ref,
        subject_id=uuid4(),
        devices={dev: _grant("864537040123456")},
        units={},
        token_ttl_seconds=600,
    )
    dev_key, _ = scope_keys(scope_ref)

    autorizado = json.loads(fake.hget(dev_key, str(dev)))
    assert autorizado["id"] == "864537040123456"
    # Ventana abierta: también autoriza los datos en vivo
    assert autorizado["windows"] == [{"from": None, "to": None}]
    assert fake.hget(dev_key, str(uuid4())) is None  # ref no autorizada


def test_revoking_makes_every_lookup_deny(store, fake):
    """Tras el DEL no queda ni autorización ni traducción."""
    scope_ref, dev = uuid4(), uuid4()
    store.write_scope(
        scope_ref,
        subject_id=uuid4(),
        devices={dev: _grant("864537040123456")},
        units={},
        token_ttl_seconds=600,
    )
    store.revoke_scope(scope_ref)

    dev_key, _ = scope_keys(scope_ref)
    assert fake.hget(dev_key, str(dev)) is None


def test_scope_outlives_the_token_by_the_configured_margin(store, fake):
    scope_ref = uuid4()
    store.write_scope(
        scope_ref,
        subject_id=uuid4(),
        devices={uuid4(): _grant("123456789012345")},
        units={},
        token_ttl_seconds=600,
    )
    dev_key, _ = scope_keys(scope_ref)
    # El alcance no debe expirar por debajo de un token todavía válido
    assert fake.ttls[dev_key] == 900


def test_everything_is_written_in_a_single_pipeline(store, fake):
    store.write_scope(
        uuid4(),
        subject_id=uuid4(),
        devices={uuid4(): _grant("123456789012345")},
        units={uuid4(): _grant(uuid4())},
        token_ttl_seconds=600,
    )
    assert len(fake.executed) == 1


def test_empty_scope_writes_no_set_but_still_indexes(store, fake):
    """Un usuario sin dispositivos produce un alcance vacío, no un alcance ausente."""
    scope_ref, subject = uuid4(), uuid4()
    store.write_scope(
        scope_ref,
        subject_id=subject,
        devices={},
        units={},
        token_ttl_seconds=600,
    )
    dev_key, unit_key = scope_keys(scope_ref)
    assert dev_key not in fake.hashes and unit_key not in fake.hashes
    assert fake.sets[owner_key(subject)] == {str(scope_ref)}


# ---------------------------------------------------------------------------
# Revocación
# ---------------------------------------------------------------------------


def test_revoking_a_scope_removes_both_sets(store, fake):
    scope_ref = uuid4()
    store.write_scope(
        scope_ref,
        subject_id=uuid4(),
        devices={uuid4(): _grant("123456789012345")},
        units={uuid4(): _grant(uuid4())},
        token_ttl_seconds=600,
    )
    store.revoke_scope(scope_ref)

    dev_key, unit_key = scope_keys(scope_ref)
    assert dev_key not in fake.hashes and unit_key not in fake.hashes


def test_revoking_a_subject_kills_every_live_scope(store, fake):
    """
    Es lo que hace que estrechar permisos surta efecto ya, en vez de dentro de
    diez minutos.
    """
    subject = uuid4()
    refs = [uuid4() for _ in range(3)]
    for ref in refs:
        store.write_scope(
            ref,
            subject_id=subject,
            devices={uuid4(): _grant("123456789012345")},
            units={},
            token_ttl_seconds=600,
        )

    revoked = store.revoke_all_for_subject(subject)

    assert set(revoked) == set(refs)
    for ref in refs:
        assert scope_keys(ref)[0] not in fake.hashes
    assert owner_key(subject) not in fake.sets


def test_revoking_a_subject_without_scopes_is_a_no_op(store):
    assert store.revoke_all_for_subject(uuid4()) == []


def test_revocation_does_not_touch_another_subject(store, fake):
    mine, theirs = uuid4(), uuid4()
    my_ref, their_ref = uuid4(), uuid4()
    for subject, ref in ((mine, my_ref), (theirs, their_ref)):
        store.write_scope(
            ref,
            subject_id=subject,
            devices={uuid4(): _grant("123456789012345")},
            units={},
            token_ttl_seconds=600,
        )

    store.revoke_all_for_subject(mine)

    assert scope_keys(their_ref)[0] in fake.hashes
    assert owner_key(theirs) in fake.sets


# ---------------------------------------------------------------------------
# El índice inverso no debe revelar identidad
# ---------------------------------------------------------------------------


def test_owner_key_does_not_contain_the_subject_id(store):
    subject = uuid4()
    key = owner_key(subject)

    assert str(subject) not in key
    assert str(subject).replace("-", "") not in key


def test_owner_key_is_stable_for_the_same_subject(store):
    subject = uuid4()
    assert owner_key(subject) == owner_key(subject)


def test_owner_key_changes_with_the_secret(monkeypatch, store):
    subject = uuid4()
    first = owner_key(subject)

    monkeypatch.setattr(
        "app.services.scope_store.settings.DATA_TOKEN_INDEX_SECRET_B64",
        base64.b64encode(b"a-different-secret-of-32-bytes!!").decode(),
    )
    assert owner_key(subject) != first


def test_without_the_index_secret_nothing_can_be_issued(monkeypatch, fake):
    """
    Emitir credenciales que no se pueden revocar es peor que no emitirlas, así
    que la falta del secreto bloquea la emisión en lugar de degradarla.
    """
    monkeypatch.setattr(
        "app.services.scope_store.settings.DATA_TOKEN_INDEX_SECRET_B64", None
    )
    with pytest.raises(RevocationIndexNotConfigured):
        ScopeStore(fake).write_scope(
            uuid4(),
            subject_id=uuid4(),
            devices={},
            units={},
            token_ttl_seconds=600,
        )


def test_without_valkey_the_store_reports_unavailable():
    unconfigured = ScopeStore(None)
    assert not unconfigured.is_configured
    with pytest.raises(ScopeStoreUnavailable):
        unconfigured.revoke_scope(uuid4())


def test_build_client_returns_none_without_url(monkeypatch):
    monkeypatch.setattr("app.services.scope_store.settings.VALKEY_URL", None)
    assert scope_store.build_client() is None


# ---------------------------------------------------------------------------
# Rastro forense por `jti`
# ---------------------------------------------------------------------------


def test_jti_trail_points_at_the_hashed_owner(store, fake):
    """
    siscom-api registra el `jti` sin saber de quién es; el cruce con este rastro
    reconstruye a quién pertenecía el acceso. El valor guardado es la clave HMAC,
    así que el rastro tampoco identifica a nadie por sí solo.
    """
    subject, jti = uuid4(), uuid4()
    store.write_scope(
        uuid4(),
        subject_id=subject,
        devices={uuid4(): _grant("123456789012345")},
        units={},
        token_ttl_seconds=600,
        jti=jti,
    )

    assert fake.strings[jti_key(jti)] == owner_key(subject)
    assert str(subject) not in fake.strings[jti_key(jti)]


def test_jti_trail_expires_with_the_scope(store, fake):
    jti = uuid4()
    store.write_scope(
        uuid4(),
        subject_id=uuid4(),
        devices={},
        units={},
        token_ttl_seconds=600,
        jti=jti,
    )
    assert fake.ttls[jti_key(jti)] == 900


def test_no_jti_means_no_trail(store, fake):
    store.write_scope(
        uuid4(),
        subject_id=uuid4(),
        devices={},
        units={},
        token_ttl_seconds=600,
    )
    assert fake.strings == {}


def test_revoking_keeps_the_jti_trail(store, fake):
    """
    Conservarlo permite investigar el uso de un token *después* de revocarlo,
    que es justo cuando interesa. Caduca solo.
    """
    subject, jti, scope_ref = uuid4(), uuid4(), uuid4()
    store.write_scope(
        scope_ref,
        subject_id=subject,
        devices={uuid4(): _grant("123456789012345")},
        units={},
        token_ttl_seconds=600,
        jti=jti,
    )
    store.revoke_all_for_subject(subject)

    assert scope_keys(scope_ref)[0] not in fake.hashes
    assert jti_key(jti) in fake.strings


# ---------------------------------------------------------------------------
# Propósito: sesión y enlaces compartidos no se revocan juntos
# ---------------------------------------------------------------------------


def test_renewing_a_session_does_not_kill_shared_links(store, fake):
    """
    Compartir un enlace es un acto deliberado; renovar el token de sesión —que
    revoca lo anterior del mismo dueño— no debe apagarlo.
    """
    subject = uuid4()
    share_ref, session_ref = uuid4(), uuid4()

    store.write_scope(
        share_ref,
        subject_id=subject,
        devices={uuid4(): _grant("111111111111111")},
        units={},
        token_ttl_seconds=1800,
        purpose=ScopePurpose.SHARE,
    )
    store.write_scope(
        session_ref,
        subject_id=subject,
        devices={uuid4(): _grant("222222222222222")},
        units={},
        token_ttl_seconds=600,
    )

    store.revoke_all_for_subject(subject)  # propósito SESSION por defecto

    assert scope_keys(session_ref)[0] not in fake.hashes
    assert scope_keys(share_ref)[0] in fake.hashes


def test_stopping_sharing_does_not_log_the_user_out(store, fake):
    """Y la simétrica: revocar los enlaces no toca la sesión."""
    subject = uuid4()
    share_ref, session_ref = uuid4(), uuid4()

    store.write_scope(
        share_ref,
        subject_id=subject,
        devices={uuid4(): _grant("111111111111111")},
        units={},
        token_ttl_seconds=1800,
        purpose=ScopePurpose.SHARE,
    )
    store.write_scope(
        session_ref,
        subject_id=subject,
        devices={uuid4(): _grant("222222222222222")},
        units={},
        token_ttl_seconds=600,
    )

    revoked = store.revoke_all_for_subject(subject, ScopePurpose.SHARE)

    assert revoked == [share_ref]
    assert scope_keys(session_ref)[0] in fake.hashes


def test_the_two_purposes_use_different_index_keys(store):
    subject = uuid4()
    assert owner_key(subject, ScopePurpose.SESSION) != owner_key(
        subject, ScopePurpose.SHARE
    )


def test_the_purpose_key_still_hides_the_subject(store):
    subject = uuid4()
    for purpose in ScopePurpose:
        assert str(subject) not in owner_key(subject, purpose)


# ---------------------------------------------------------------------------
# Formato de cable: la ventana viaja con la referencia
# ---------------------------------------------------------------------------


def test_wire_format_carries_the_windows(store, fake):
    """
    siscom-api no puede deducir la vigencia: hacerlo exigiría conocer el modelo
    de unidades y asignaciones, que es lo que no debe aprender. Por eso la
    ventana viaja con la referencia.
    """
    scope_ref, dev = uuid4(), uuid4()
    grant = Grant(
        internal_id="864537040123456",
        windows=(
            TimeWindow(
                start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ),
            TimeWindow(start=datetime(2026, 6, 1, tzinfo=timezone.utc), end=None),
        ),
    )
    store.write_scope(
        scope_ref,
        subject_id=uuid4(),
        devices={dev: grant},
        units={},
        token_ttl_seconds=600,
    )

    dev_key, _ = scope_keys(scope_ref)
    value = json.loads(fake.hget(dev_key, str(dev)))

    assert value["id"] == "864537040123456"
    assert value["windows"] == [
        {"from": "2026-01-01T00:00:00+00:00", "to": "2026-03-01T00:00:00+00:00"},
        {"from": "2026-06-01T00:00:00+00:00", "to": None},
    ]


def test_a_closed_window_is_distinguishable_from_an_open_one(store, fake):
    """
    El dispositivo que se fue sigue en el alcance —su histórico es legítimo—
    pero sin ventana abierta, que es lo único que autoriza los datos en vivo.
    """
    scope_ref, se_fue, sigue = uuid4(), uuid4(), uuid4()
    store.write_scope(
        scope_ref,
        subject_id=uuid4(),
        devices={
            se_fue: _grant("111111111111111", open_window=False),
            sigue: _grant("222222222222222"),
        },
        units={},
        token_ttl_seconds=600,
    )

    dev_key, _ = scope_keys(scope_ref)
    cerrado = json.loads(fake.hget(dev_key, str(se_fue)))
    abierto = json.loads(fake.hget(dev_key, str(sigue)))

    assert cerrado["windows"][0]["to"] is not None
    assert abierto["windows"][0]["to"] is None
