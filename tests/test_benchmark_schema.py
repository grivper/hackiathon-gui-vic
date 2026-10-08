"""Esquema portable del conjunto de consultas de desarrollo TAR-023."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark.jsonl"
MANIFEST = ROOT / "data" / "manifest.json"
FICHAS = ROOT / "data" / "fichas.jsonl"
THEMES = {"economia", "logistica_canal", "turismo", "servicios_publicos", "eventos_naturales", "regulacion"}
CASES = {"supported", "official_context", "abstention", "contradiction", "adversarial"}
RESPONSE_TYPES = {"respuesta", "abstencion", "contradiccion"}
SCOPES = {"titulos_metadatos", "world_bank", "usgs"}


def _records():
    return [json.loads(line) for line in BENCHMARK.read_text(encoding="utf-8").splitlines() if line.strip()]


def _ficha_refs():
    refs = {}
    for line in FICHAS.read_text(encoding="utf-8").splitlines():
        ficha = json.loads(line)
        refs[ficha["id_caso"]] = set(ficha["ids_fuente"])
    return refs


def _local_refs():
    db = ROOT / "data" / "motor.duckdb"
    if not db.exists():
        return None
    duckdb = pytest.importorskip("duckdb")
    con = duckdb.connect(str(db), read_only=True)
    try:
        return {group: set(ids) for group, ids in con.execute(
            "SELECT grupo_id, list(id_noticia) FROM grupo_noticias GROUP BY grupo_id"
        ).fetchall()}
    finally:
        con.close()


def test_benchmark_schema_and_composition():
    records = _records()
    assert len(records) == 40
    assert [r["id"] for r in records] == [f"TAR023-{n:03d}" for n in range(1, 41)]
    assert len({r["id"] for r in records}) == 40

    manifest_hash = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    counts = Counter(r["case"] for r in records)
    assert counts == {"supported": 18, "official_context": 6, "abstention": 6, "contradiction": 6, "adversarial": 4}
    assert Counter(r["theme"] for r in records if r["case"] == "supported") == dict.fromkeys(THEMES, 3)
    assert {r["theme"] for r in records if r["case"] == "abstention"} == THEMES
    assert {r["theme"] for r in records if r["case"] == "adversarial"} == {"economia", "logistica_canal", "servicios_publicos", "regulacion"}

    fichas = _ficha_refs()
    local = _local_refs()
    for record in records:
        assert set(record) == {"id", "theme", "case", "question", "target_group_id", "expected_response_type", "required_evidence_ids", "forbidden_claims", "acceptance_notes", "synthetic", "scope", "snapshot_manifest_sha256"}
        assert record["theme"] in THEMES and record["case"] in CASES
        assert record["expected_response_type"] in RESPONSE_TYPES and record["scope"] in SCOPES
        assert isinstance(record["synthetic"], bool) and record["snapshot_manifest_sha256"] == manifest_hash
        assert isinstance(record["question"], str) and record["question"].strip()
        assert isinstance(record["forbidden_claims"], list) and all(isinstance(v, str) and v.strip() for v in record["forbidden_claims"])
        assert isinstance(record["acceptance_notes"], str) and record["acceptance_notes"].strip()
        assert isinstance(record["required_evidence_ids"], list)
        target = record["target_group_id"]
        assert target.startswith(("G-", "SYN-"))
        assert all(e.startswith(("N-", "IND-", "us", "SYN-")) for e in record["required_evidence_ids"])
        if target.startswith("SYN-"):
            assert record["synthetic"]
        elif target in fichas:
            assert set(record["required_evidence_ids"]) <= fichas[target]
        elif local is not None:
            assert target in local, f"referencia real no disponible: {target}"
            assert set(record["required_evidence_ids"]) <= local[target]
