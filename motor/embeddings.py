#!/usr/bin/env python3
"""Embeddings de titulares con cache incremental en disco (data/embeddings/*.npy).

Carga el modelo desde la caché local `modelos/` cuando existe (offline, sin red en
inferencia). El cache de embeddings está indexado por nombre de modelo y guarda los
`id_noticia` junto con sus vectores (float32, normalizados L2) para que una nueva
ejecución solo tenga que calcular los titulares nuevos (idempotente e incremental).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

MODELOS_DIR = Path(__file__).resolve().parent.parent / "modelos"
EMBEDDINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "embeddings"


def _nombre_archivo_seguro(modelo: str) -> str:
    """Convierte un id de modelo (puede traer '/') en un nombre de archivo seguro."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", modelo)


def _rutas_cache(modelo: str, cache_dir: Path) -> tuple[Path, Path]:
    base = _nombre_archivo_seguro(modelo)
    return cache_dir / f"{base}.ids.npy", cache_dir / f"{base}.vectores.npy"


def cargar_modelo(modelo: str, modelos_dir: Path = MODELOS_DIR):
    """Carga un SentenceTransformer desde la caché local si existe; si no, desde el hub."""
    from sentence_transformers import SentenceTransformer

    if modelos_dir.exists() and any(modelos_dir.iterdir()):
        return SentenceTransformer(modelo, cache_folder=str(modelos_dir))
    return SentenceTransformer(modelo)


def cargar_cache(
    modelo: str, cache_dir: Path = EMBEDDINGS_DIR
) -> tuple[list[str], np.ndarray]:
    """Devuelve (ids, vectores) ya guardados para este modelo, o listas/arrays vacíos."""
    ruta_ids, ruta_vectores = _rutas_cache(modelo, cache_dir)
    if not ruta_ids.exists() or not ruta_vectores.exists():
        return [], np.zeros((0, 0), dtype=np.float32)
    ids = list(np.load(ruta_ids, allow_pickle=False))
    vectores = np.load(ruta_vectores)
    return ids, vectores


def guardar_cache(
    modelo: str, ids: list[str], vectores: np.ndarray, cache_dir: Path = EMBEDDINGS_DIR
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    ruta_ids, ruta_vectores = _rutas_cache(modelo, cache_dir)
    np.save(ruta_ids, np.array(ids, dtype=str))
    np.save(ruta_vectores, vectores.astype(np.float32))


def _normalizar_l2(vectores: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return vectores / normas


def codificar(encoder, textos: list[str]) -> np.ndarray:
    """Codifica una lista de textos en vectores float32 normalizados L2. Orden determinista."""
    if not textos:
        return np.zeros((0, 0), dtype=np.float32)
    vectores = encoder.encode(
        list(textos),
        batch_size=64,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return _normalizar_l2(np.asarray(vectores, dtype=np.float32))


def embeddings_incrementales(
    encoder,
    modelo: str,
    ids: list[str],
    textos: list[str],
    cache_dir: Path = EMBEDDINGS_DIR,
) -> dict[str, np.ndarray]:
    """Devuelve {id_noticia: vector} para todos los `ids`, calculando solo los que falten
    en la caché de disco y actualizándola (idempotente: una segunda ejecución no recalcula
    nada si los ids no cambiaron).
    """
    ids_cacheados, vectores_cacheados = cargar_cache(modelo, cache_dir)
    indice_cache = {id_: i for i, id_ in enumerate(ids_cacheados)}

    faltantes_ids: list[str] = []
    faltantes_textos: list[str] = []
    for id_, texto in zip(ids, textos):
        if id_ not in indice_cache:
            faltantes_ids.append(id_)
            faltantes_textos.append(texto)

    if faltantes_ids:
        nuevos_vectores = codificar(encoder, faltantes_textos)
        dim = nuevos_vectores.shape[1] if nuevos_vectores.size else (
            vectores_cacheados.shape[1] if vectores_cacheados.size else 0
        )
        if vectores_cacheados.size == 0:
            vectores_cacheados = np.zeros((0, dim), dtype=np.float32)
        ids_cacheados = list(ids_cacheados) + faltantes_ids
        vectores_cacheados = np.vstack([vectores_cacheados, nuevos_vectores])
        indice_cache = {id_: i for i, id_ in enumerate(ids_cacheados)}
        guardar_cache(modelo, ids_cacheados, vectores_cacheados, cache_dir)

    return {id_: vectores_cacheados[indice_cache[id_]] for id_ in ids}
