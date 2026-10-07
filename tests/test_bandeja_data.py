from __future__ import annotations

from datetime import date, datetime

import duckdb
import pytest

from app.data import fetch_inbox_groups, open_inbox_repository


def _create_databases(tmp_path):
    motor_path = tmp_path / "motor.duckdb"
    signals_path = tmp_path / "senales.duckdb"

    motor = duckdb.connect(str(motor_path))
    try:
        motor.execute("""
            CREATE TABLE grupos (
                grupo_id TEXT,
                n_noticias INTEGER,
                n_procedencias INTEGER,
                procedencias TEXT,
                fecha_min TIMESTAMP,
                fecha_max TIMESTAMP,
                titulo_representativo TEXT,
                corroboracion INTEGER,
                es_repeticion BOOLEAN
            )
        """)
        motor.execute("""
            CREATE TABLE grupo_noticias (
                grupo_id TEXT,
                id_noticia TEXT,
                procedencia TEXT,
                similitud_al_centroide DOUBLE
            )
        """)
        motor.execute("""
            CREATE TABLE clasificacion (
                id_noticia TEXT,
                metodo TEXT,
                tema TEXT,
                score DOUBLE,
                segundo_tema TEXT,
                margen DOUBLE,
                modelo TEXT,
                contraste TEXT
            )
        """)
        groups = [
            ("G-NUEVO", 5, 1, "tvn", datetime(2026, 1, 5), datetime(2026, 1, 5, 12), "Titular nuevo", 1, True),
            ("G-FUENTES", 2, 3, "tvn,efe,ap", datetime(2026, 1, 4), datetime(2026, 1, 4, 12), "Titular con fuentes", 3, False),
            ("G-ALFA", 1, 2, "tvn,efe", datetime(2026, 1, 3), datetime(2026, 1, 3, 12), "Titular alfa", 2, False),
            ("G-BETA", 1, 2, "tvn,ap", datetime(2026, 1, 3), datetime(2026, 1, 3, 12), "Titular beta", 2, False),
            ("G-OTROS", 3, 4, "tvn,efe,ap,afp", datetime(2026, 1, 6), datetime(2026, 1, 6, 12), "Titular otros", 4, False),
        ]
        motor.executemany("INSERT INTO grupos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", groups)
        classifications = []
        for group_id, topics in {
            "G-NUEVO": ["economia", "economia", "otros"],
            "G-FUENTES": ["salud"],
            "G-ALFA": ["educacion"],
            "G-BETA": ["educacion"],
            "G-OTROS": ["otros", "otros", "economia"],
        }.items():
            for index, topic in enumerate(topics):
                news_id = f"{group_id}-{index}"
                motor.execute(
                    "INSERT INTO grupo_noticias VALUES (?, ?, ?, ?)",
                    [group_id, news_id, "medio", 0.9],
                )
                classifications.append((news_id, "embeddings", topic, 0.8, None, None, "modelo", None))
        motor.executemany("INSERT INTO clasificacion VALUES (?, ?, ?, ?, ?, ?, ?, ?)", classifications)
    finally:
        motor.close()

    signals = duckdb.connect(str(signals_path))
    signals.close()
    return motor_path, signals_path


def test_fetch_inbox_groups_uses_one_dominant_embeddings_topic_per_group_and_orders(tmp_path):
    motor_path, signals_path = _create_databases(tmp_path)

    rows = fetch_inbox_groups(motor_path, signals_path)

    assert [row.grupo_id for row in rows] == ["G-NUEVO", "G-FUENTES", "G-ALFA", "G-BETA"]
    assert [row.tema for row in rows] == ["economia", "salud", "educacion", "educacion"]
    assert rows[0].n_noticias == 5
    assert rows[0].n_procedencias == 1
    assert rows[0].corroboracion == 1
    assert rows[0].es_repeticion is True


def test_fetch_inbox_groups_filters_dates_topic_and_limit_inclusively(tmp_path):
    motor_path, signals_path = _create_databases(tmp_path)

    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, topic="educacion")] == ["G-ALFA", "G-BETA"]
    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, start_date=date(2026, 1, 4))] == ["G-NUEVO", "G-FUENTES"]
    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, end_date=date(2026, 1, 4))] == ["G-FUENTES", "G-ALFA", "G-BETA"]
    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, limit=2)] == ["G-NUEVO", "G-FUENTES"]


def test_open_inbox_repository_keeps_motor_database_read_only(tmp_path):
    motor_path, signals_path = _create_databases(tmp_path)

    with (
        open_inbox_repository(motor_path, signals_path) as connection,
        pytest.raises(duckdb.InvalidInputException),
    ):
        connection.execute("INSERT INTO grupos VALUES ('G-NUEVO', 1, 1, '', NOW(), NOW(), '', 1, FALSE)")
