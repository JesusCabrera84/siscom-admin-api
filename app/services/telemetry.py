"""
Servicio de Telemetría Agregada.

Responsabilidades:
  1. Validar que el usuario tenga acceso a los dispositivos solicitados.
  2. Construir y ejecutar queries SQL parametrizadas sobre telemetry_hourly_stats.
  3. Mapear filas de DB a schemas semánticos sin exponer sum_* ni count_*.

La tabla telemetry_hourly_stats tiene PRIMARY KEY (device_id, bucket) y un índice
compuesto que hace eficientes los filtros por (device_id, bucket) en ese orden.

Rango semiabierto: [from_ts, to_ts) para evitar doble conteo en consultas contiguas.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.telemetry import (
    AlertsOut,
    AvgMinMaxOut,
    BatchMetricName,
    BatteryOut,
    CommQualityOut,
    Granularity,
    MetricName,
    OdometerOut,
    SamplesOut,
    SpeedOut,
    TelemetryDeviceItemOut,
    TelemetryPointOut,
)
from app.services.access_control import (
    accessible_refs,
    subject_for_user,
)

BASE_METRICS = {
    "speed",
    "main_battery",
    "backup_battery",
    "alerts",
    "comm_quality",
    "samples",
    "signal",
    "satellites",
    "odometer",
}

INTELLIGENCE_METRICS = {
    "fuel_consumed_liters",
    "moving_minutes",
    "idle_minutes",
}

# ---------------------------------------------------------------------------
# Control de acceso
# ---------------------------------------------------------------------------


def authorized_ranges(
    db: Session,
    user: User,
    device_id: str,
    from_ts: datetime,
    to_ts: datetime,
) -> List[tuple]:
    """
    Sub-rangos de `[from_ts, to_ts)` que el usuario puede ver de ese dispositivo.

    **Se recorta, no se rechaza**: pedir enero–diciembre habiendo tenido el equipo
    hasta marzo devuelve enero–marzo. No hay oráculo de pertenencia que proteger
    —el usuario ya conoce los límites de su propia ventana—, al contrario que con
    un dispositivo ajeno, que se rechaza entero.

    Lista vacía significa que no hubo permiso en ningún momento del rango, y el
    llamante responde 404 sin distinguir "no existe" de "no es tuyo".
    """
    refs = accessible_refs(db, subject_for_user(user))
    for grant in refs.devices.values():
        if grant.internal_id == device_id:
            return grant.clip(from_ts, to_ts)
    return []


def validate_device_access(
    db: Session,
    user: User,
    device_id: str,
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
) -> List[tuple]:
    """
    Lanza HTTPException 404 si el usuario no puede ver el dispositivo en el rango.

    Se usa 404 (en lugar de 403) para no filtrar existencia. Devuelve los
    sub-rangos autorizados para que el llamante consulte solo esos.
    """
    ranges = authorized_ranges(db, user, device_id, from_ts, to_ts)
    if not ranges:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    return ranges


# ---------------------------------------------------------------------------
# Construcción de SELECT dinámico
# ---------------------------------------------------------------------------


def _build_select_columns(metrics: Sequence[MetricName], prefix: str = "") -> str:
    """
    Construye los fragmentos SELECT calculados según las métricas pedidas.
    Para granularity=day se espera que prefix='SUM' y se pase con el grupo correcto.
    Este método devuelve solo las columnas de métricas, sin bucket ni device_id.
    """
    cols: List[str] = []

    if "speed" in metrics:
        cols += [
            "SUM(sum_speed) / NULLIF(SUM(count_speed), 0) AS avg_speed",
            "MIN(min_speed) AS min_speed",
            "MAX(max_speed) AS max_speed",
        ]

    if "main_battery" in metrics:
        cols += [
            "SUM(sum_main_voltage) / NULLIF(SUM(count_main_voltage), 0) AS avg_main_voltage",
            "MIN(min_main_voltage) AS min_main_voltage",
            "MAX(max_main_voltage) AS max_main_voltage",
        ]

    if "backup_battery" in metrics:
        cols += [
            "SUM(sum_backup_voltage) / NULLIF(SUM(count_backup_voltage), 0) AS avg_backup_voltage",
            "MIN(min_backup_voltage) AS min_backup_voltage",
            "MAX(max_backup_voltage) AS max_backup_voltage",
        ]

    if "alerts" in metrics:
        cols.append("SUM(count_alerts) AS count_alerts")

    if "comm_quality" in metrics:
        cols += [
            "SUM(count_comm_fixable) AS count_comm_fixable",
            "SUM(count_comm_with_fix) AS count_comm_with_fix",
        ]

    if "samples" in metrics:
        cols.append("SUM(samples) AS samples")

    if "signal" in metrics:
        cols += [
            "SUM(sum_rx_lvl) / NULLIF(SUM(count_rx_lvl), 0) AS avg_rx_lvl",
            "MIN(min_rx_lvl) AS min_rx_lvl",
            "MAX(max_rx_lvl) AS max_rx_lvl",
        ]

    if "satellites" in metrics:
        cols += [
            "SUM(sum_satellites) / NULLIF(SUM(count_satellites), 0) AS avg_satellites",
            "MIN(min_satellites) AS min_satellites",
            "MAX(max_satellites) AS max_satellites",
        ]

    if "odometer" in metrics:
        cols += [
            "MIN(first_odometer) AS first_odometer",
            "MAX(last_odometer) AS last_odometer",
        ]

    return ",\n    ".join(cols)


# ---------------------------------------------------------------------------
# Queries por dispositivo único
# ---------------------------------------------------------------------------


def _query_single_hour(
    db: Session,
    device_id: str,
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[MetricName],
) -> List[TelemetryPointOut]:
    """Query para granularity=hour sobre un único dispositivo."""
    metric_cols = _build_select_columns(metrics)
    if not metric_cols:
        return []

    sql = text(f"""
        SELECT
            bucket,
            {metric_cols}
        FROM telemetry_hourly_stats
        WHERE device_id = :device_id
          AND bucket >= :from_ts
          AND bucket < :to_ts
        GROUP BY bucket
        ORDER BY bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_id": device_id, "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return [_map_row_to_point(row, metrics) for row in rows]


def _query_single_day(
    db: Session,
    device_id: str,
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[MetricName],
) -> List[TelemetryPointOut]:
    """Query para granularity=day sobre un único dispositivo."""
    metric_cols = _build_select_columns(metrics)
    if not metric_cols:
        return []

    sql = text(f"""
        SELECT
            date_trunc('day', bucket) AS bucket,
            {metric_cols}
        FROM telemetry_hourly_stats
        WHERE device_id = :device_id
          AND bucket >= :from_ts
          AND bucket < :to_ts
        GROUP BY date_trunc('day', bucket)
        ORDER BY bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_id": device_id, "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return [_map_row_to_point(row, metrics) for row in rows]


def _query_single_hour_intelligence(
    db: Session,
    device_id: str,
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[BatchMetricName],
) -> List[TelemetryPointOut]:
    """Query para granularity=hour sobre un único dispositivo en tabla intelligence."""
    metric_cols = _build_intelligence_select_columns(metrics)
    if not metric_cols:
        return []

    sql = text(f"""
        SELECT
            bucket,
            {metric_cols}
        FROM telemetry_intelligence_hourly_stats
        WHERE device_id = :device_id
          AND bucket >= :from_ts
          AND bucket < :to_ts
        GROUP BY bucket
        ORDER BY bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_id": device_id, "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return [_map_row_to_point(row, metrics) for row in rows]


def _query_single_day_intelligence(
    db: Session,
    device_id: str,
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[BatchMetricName],
) -> List[TelemetryPointOut]:
    """Query para granularity=day sobre un único dispositivo en tabla intelligence."""
    metric_cols = _build_intelligence_select_columns(metrics)
    if not metric_cols:
        return []

    sql = text(f"""
        SELECT
            date_trunc('day', bucket) AS bucket,
            {metric_cols}
        FROM telemetry_intelligence_hourly_stats
        WHERE device_id = :device_id
          AND bucket >= :from_ts
          AND bucket < :to_ts
        GROUP BY date_trunc('day', bucket)
        ORDER BY bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_id": device_id, "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return [_map_row_to_point(row, metrics) for row in rows]


# ---------------------------------------------------------------------------
# Queries multi-dispositivo
# ---------------------------------------------------------------------------


def _query_multi_hour(
    db: Session,
    device_ids: Sequence[str],
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[MetricName],
) -> Dict[str, List[TelemetryPointOut]]:
    """Query batch para granularity=hour."""
    metric_cols = _build_select_columns(metrics)
    if not metric_cols:
        return {d: [] for d in device_ids}

    # Usar ANY con array de PostgreSQL para IN eficiente
    sql = text(f"""
        SELECT
            device_id,
            bucket,
            {metric_cols}
        FROM telemetry_hourly_stats
        WHERE device_id = ANY(:device_ids)
          AND bucket >= :from_ts
          AND bucket < :to_ts
                GROUP BY device_id, bucket
        ORDER BY device_id ASC, bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_ids": list(device_ids), "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return _group_rows_by_device(rows, device_ids, metrics)


def _build_intelligence_select_columns(metrics: Sequence[BatchMetricName]) -> str:
    cols: List[str] = []

    if "fuel_consumed_liters" in metrics:
        cols.append("SUM(fuel_consumed_liters) AS fuel_consumed_liters")

    if "moving_minutes" in metrics:
        cols.append("SUM(moving_minutes) AS moving_minutes")

    if "idle_minutes" in metrics:
        cols.append("SUM(idle_minutes) AS idle_minutes")

    return ",\n            ".join(cols)


def _query_multi_hour_intelligence(
    db: Session,
    device_ids: Sequence[str],
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[BatchMetricName],
) -> Dict[str, List[TelemetryPointOut]]:
    """Query batch para métricas de telemetry_intelligence_hourly_stats con granularity=hour."""
    metric_cols = _build_intelligence_select_columns(metrics)
    if not metric_cols:
        return {d: [] for d in device_ids}

    sql = text(f"""
        SELECT
            device_id,
            bucket,
            {metric_cols}
        FROM telemetry_intelligence_hourly_stats
        WHERE device_id = ANY(:device_ids)
          AND bucket >= :from_ts
          AND bucket < :to_ts
        GROUP BY device_id, bucket
        ORDER BY device_id ASC, bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_ids": list(device_ids), "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return _group_rows_by_device(rows, device_ids, metrics)


def _query_multi_day(
    db: Session,
    device_ids: Sequence[str],
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[MetricName],
) -> Dict[str, List[TelemetryPointOut]]:
    """Query batch para granularity=day."""
    metric_cols = _build_select_columns(metrics)
    if not metric_cols:
        return {d: [] for d in device_ids}

    sql = text(f"""
        SELECT
            device_id,
            date_trunc('day', bucket) AS bucket,
            {metric_cols}
        FROM telemetry_hourly_stats
        WHERE device_id = ANY(:device_ids)
          AND bucket >= :from_ts
          AND bucket < :to_ts
        GROUP BY device_id, date_trunc('day', bucket)
        ORDER BY device_id ASC, bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_ids": list(device_ids), "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return _group_rows_by_device(rows, device_ids, metrics)


def _query_multi_day_intelligence(
    db: Session,
    device_ids: Sequence[str],
    from_ts: datetime,
    to_ts: datetime,
    metrics: Sequence[BatchMetricName],
) -> Dict[str, List[TelemetryPointOut]]:
    """Query batch para métricas de telemetry_intelligence_hourly_stats con granularity=day."""
    metric_cols = _build_intelligence_select_columns(metrics)
    if not metric_cols:
        return {d: [] for d in device_ids}

    sql = text(f"""
        SELECT
            device_id,
            date_trunc('day', bucket) AS bucket,
            {metric_cols}
        FROM telemetry_intelligence_hourly_stats
        WHERE device_id = ANY(:device_ids)
          AND bucket >= :from_ts
          AND bucket < :to_ts
        GROUP BY device_id, date_trunc('day', bucket)
        ORDER BY device_id ASC, bucket ASC
        """)

    rows = db.execute(
        sql,
        {"device_ids": list(device_ids), "from_ts": from_ts, "to_ts": to_ts},
    ).fetchall()

    return _group_rows_by_device(rows, device_ids, metrics)


# ---------------------------------------------------------------------------
# Mapeo de filas a schemas semánticos
# ---------------------------------------------------------------------------


def _map_row_to_point(row, metrics: Sequence[str]) -> TelemetryPointOut:
    """
    Convierte una fila de resultado SQL a TelemetryPointOut.
    Los campos de métricas no pedidas quedan como None (excluídos en la respuesta
    con response_model_exclude_none=True en el endpoint).
    """
    mapping = row._mapping

    speed_out: Optional[SpeedOut] = None
    main_battery_out: Optional[BatteryOut] = None
    backup_battery_out: Optional[BatteryOut] = None
    alerts_out: Optional[AlertsOut] = None
    comm_out: Optional[CommQualityOut] = None
    samples_out: Optional[SamplesOut] = None
    signal_out: Optional[AvgMinMaxOut] = None
    satellites_out: Optional[AvgMinMaxOut] = None
    odometer_out: Optional[OdometerOut] = None

    if "speed" in metrics:
        speed_out = SpeedOut(
            avg_speed=mapping.get("avg_speed"),
            min_speed=mapping.get("min_speed"),
            max_speed=mapping.get("max_speed"),
        )

    if "main_battery" in metrics:
        main_battery_out = BatteryOut(
            avg_voltage=mapping.get("avg_main_voltage"),
            min_voltage=mapping.get("min_main_voltage"),
            max_voltage=mapping.get("max_main_voltage"),
        )

    if "backup_battery" in metrics:
        backup_battery_out = BatteryOut(
            avg_voltage=mapping.get("avg_backup_voltage"),
            min_voltage=mapping.get("min_backup_voltage"),
            max_voltage=mapping.get("max_backup_voltage"),
        )

    if "alerts" in metrics:
        alerts_out = AlertsOut(count=mapping.get("count_alerts") or 0)

    if "comm_quality" in metrics:
        comm_out = CommQualityOut(
            count_comm_fixable=mapping.get("count_comm_fixable") or 0,
            count_comm_with_fix=mapping.get("count_comm_with_fix") or 0,
        )

    if "samples" in metrics:
        samples_out = SamplesOut(total=mapping.get("samples") or 0)

    if "signal" in metrics:
        signal_out = AvgMinMaxOut(
            avg=mapping.get("avg_rx_lvl"),
            min=mapping.get("min_rx_lvl"),
            max=mapping.get("max_rx_lvl"),
        )

    if "satellites" in metrics:
        satellites_out = AvgMinMaxOut(
            avg=mapping.get("avg_satellites"),
            min=mapping.get("min_satellites"),
            max=mapping.get("max_satellites"),
        )

    if "odometer" in metrics:
        first_odometer = mapping.get("first_odometer")
        last_odometer = mapping.get("last_odometer")
        total_distance_mt = None
        if first_odometer is not None and last_odometer is not None:
            total_distance_mt = last_odometer - first_odometer
        odometer_out = OdometerOut(total_distance_mt=total_distance_mt)

    fuel_consumed_liters: Optional[float] = None
    moving_minutes: Optional[float] = None
    idle_minutes: Optional[float] = None

    if "fuel_consumed_liters" in metrics:
        fuel_consumed_liters = mapping.get("fuel_consumed_liters")

    if "moving_minutes" in metrics:
        moving_minutes = mapping.get("moving_minutes")

    if "idle_minutes" in metrics:
        idle_minutes = mapping.get("idle_minutes")

    return TelemetryPointOut(
        bucket=mapping["bucket"],
        speed=speed_out,
        main_battery=main_battery_out,
        backup_battery=backup_battery_out,
        alerts=alerts_out,
        comm_quality=comm_out,
        samples=samples_out,
        signal=signal_out,
        satellites=satellites_out,
        odometer=odometer_out,
        fuel_consumed_liters=fuel_consumed_liters,
        moving_minutes=moving_minutes,
        idle_minutes=idle_minutes,
    )


def _merge_series_by_bucket(
    base_series: List[TelemetryPointOut],
    extra_series: List[TelemetryPointOut],
) -> List[TelemetryPointOut]:
    """Fusiona dos series por bucket sin perder métricas ya calculadas."""
    merged: Dict[datetime, TelemetryPointOut] = {p.bucket: p for p in base_series}

    for extra in extra_series:
        current = merged.get(extra.bucket)
        if current is None:
            merged[extra.bucket] = extra
            continue

        if extra.fuel_consumed_liters is not None:
            current.fuel_consumed_liters = extra.fuel_consumed_liters
        if extra.moving_minutes is not None:
            current.moving_minutes = extra.moving_minutes
        if extra.idle_minutes is not None:
            current.idle_minutes = extra.idle_minutes

    return sorted(merged.values(), key=lambda p: p.bucket)


def _group_rows_by_device(
    rows,
    device_ids: Sequence[str],
    metrics: Sequence[str],
) -> Dict[str, List[TelemetryPointOut]]:
    """Agrupa filas por device_id, preservando orden original de device_ids."""
    result: Dict[str, List[TelemetryPointOut]] = {d: [] for d in device_ids}
    for row in rows:
        dev_id = row._mapping["device_id"]
        if dev_id in result:
            result[dev_id].append(_map_row_to_point(row, metrics))
    return result


# ---------------------------------------------------------------------------
# API pública del servicio
# ---------------------------------------------------------------------------


def get_telemetry_single(
    db: Session,
    user: User,
    device_id: str,
    from_ts: datetime,
    to_ts: datetime,
    granularity: Granularity,
    metrics: List[BatchMetricName],
) -> List[TelemetryPointOut]:
    """
    Retorna la serie temporal de telemetría para un dispositivo.

    El acceso es **temporal**: se consulta únicamente en los sub-rangos en que el
    usuario tuvo el dispositivo. Un equipo reasignado a otra organización deja de
    aportar datos posteriores a su marcha sin que la petición falle.
    """
    ranges = validate_device_access(db, user, device_id, from_ts, to_ts)

    base_metrics = [m for m in metrics if m in BASE_METRICS]
    intelligence_metrics = [m for m in metrics if m in INTELLIGENCE_METRICS]

    series: List[TelemetryPointOut] = []
    for desde, hasta in ranges:
        series.extend(
            _query_one_range(
                db,
                device_id,
                desde,
                hasta,
                granularity,
                base_metrics,
                intelligence_metrics,
            )
        )

    # Los sub-rangos son disjuntos y vienen ordenados, pero se reordena por
    # bucket de todos modos: la propiedad de salida es "ordenado por bucket", y
    # no debe depender de cómo estén ordenadas las ventanas de entrada.
    return sorted(series, key=lambda p: p.bucket)


def _query_one_range(
    db: Session,
    device_id: str,
    from_ts: Optional[datetime],
    to_ts: Optional[datetime],
    granularity: Granularity,
    base_metrics: List[str],
    intelligence_metrics: List[str],
) -> List[TelemetryPointOut]:
    """Consulta un único sub-rango autorizado."""
    if granularity == "hour":
        base_series = (
            _query_single_hour(db, device_id, from_ts, to_ts, base_metrics)
            if base_metrics
            else []
        )
        intelligence_series = (
            _query_single_hour_intelligence(
                db, device_id, from_ts, to_ts, intelligence_metrics
            )
            if intelligence_metrics
            else []
        )
    else:
        base_series = (
            _query_single_day(db, device_id, from_ts, to_ts, base_metrics)
            if base_metrics
            else []
        )
        intelligence_series = (
            _query_single_day_intelligence(
                db, device_id, from_ts, to_ts, intelligence_metrics
            )
            if intelligence_metrics
            else []
        )

    return _merge_series_by_bucket(base_series, intelligence_series)


def get_telemetry_batch(
    db: Session,
    user: User,
    device_ids: List[str],
    from_ts: datetime,
    to_ts: datetime,
    granularity: Granularity,
    metrics: List[BatchMetricName],
) -> List[TelemetryDeviceItemOut]:
    """
    Retorna la serie temporal agrupada por dispositivo, con acceso **temporal**.

    Dos reglas distintas, y la diferencia es deliberada:

    - Un dispositivo sin ningún permiso en el rango **rechaza la petición entera**
      con 404. Devolver el subconjunto permitido convertiría el endpoint en un
      oráculo de pertenencia: pidiendo de uno en uno se averigua de quién es cada
      equipo.
    - Un dispositivo con permiso **parcial** se recorta a su ventana. Ahí no hay
      nada que proteger, porque quien pregunta ya conoce los límites de su propia
      ventana.
    """
    ranges_by_device = _authorized_ranges_for_batch(
        db, user, device_ids, from_ts, to_ts
    )

    base_metrics = [m for m in metrics if m in BASE_METRICS]
    intelligence_metrics = [m for m in metrics if m in INTELLIGENCE_METRICS]

    # Los dispositivos que comparten ventanas se consultan juntos. En el caso
    # habitual —todos asignados y cubriendo el rango entero— hay un solo grupo y
    # un solo rango, así que la consulta es exactamente la de antes.
    grupos: Dict[tuple, List[str]] = defaultdict(list)
    for dev_id in device_ids:
        grupos[tuple(ranges_by_device[dev_id])].append(dev_id)

    grouped: Dict[str, List[TelemetryPointOut]] = {d: [] for d in device_ids}

    for rangos, ids in grupos.items():
        for desde, hasta in rangos:
            parcial = _query_batch_one_range(
                db, ids, desde, hasta, granularity, base_metrics, intelligence_metrics
            )
            for dev_id in ids:
                grouped[dev_id].extend(parcial.get(dev_id, []))

    # Preservar orden original del request; la serie, ordenada por bucket.
    return [
        TelemetryDeviceItemOut(
            device_id=dev_id, series=sorted(grouped[dev_id], key=lambda p: p.bucket)
        )
        for dev_id in device_ids
    ]


def _authorized_ranges_for_batch(
    db: Session,
    user: User,
    device_ids: Sequence[str],
    from_ts: datetime,
    to_ts: datetime,
) -> Dict[str, List[tuple]]:
    """
    Ventanas autorizadas de cada dispositivo pedido, en una sola resolución.

    Lanza 404 genérico —sin decir cuál falla— si alguno no tiene permiso alguno
    en el rango.
    """
    refs = accessible_refs(db, subject_for_user(user))
    por_id = {grant.internal_id: grant for grant in refs.devices.values()}

    resultado: Dict[str, List[tuple]] = {}
    for dev_id in device_ids:
        grant = por_id.get(dev_id)
        rangos = grant.clip(from_ts, to_ts) if grant else []
        if not rangos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uno o más dispositivos no encontrados",
            )
        resultado[dev_id] = rangos

    return resultado


def _query_batch_one_range(
    db: Session,
    device_ids: List[str],
    from_ts: Optional[datetime],
    to_ts: Optional[datetime],
    granularity: Granularity,
    base_metrics: List[str],
    intelligence_metrics: List[str],
) -> Dict[str, List[TelemetryPointOut]]:
    """Consulta un único sub-rango para un grupo de dispositivos."""
    vacio = {d: [] for d in device_ids}

    if granularity == "hour":
        grouped_base = (
            _query_multi_hour(db, device_ids, from_ts, to_ts, base_metrics)
            if base_metrics
            else vacio
        )
        grouped_intelligence = (
            _query_multi_hour_intelligence(
                db, device_ids, from_ts, to_ts, intelligence_metrics
            )
            if intelligence_metrics
            else vacio
        )
    else:
        grouped_base = (
            _query_multi_day(db, device_ids, from_ts, to_ts, base_metrics)
            if base_metrics
            else vacio
        )
        grouped_intelligence = (
            _query_multi_day_intelligence(
                db, device_ids, from_ts, to_ts, intelligence_metrics
            )
            if intelligence_metrics
            else vacio
        )

    return {
        dev_id: _merge_series_by_bucket(
            grouped_base.get(dev_id, []), grouped_intelligence.get(dev_id, [])
        )
        for dev_id in device_ids
    }
