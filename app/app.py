"""Minimal Streamlit entry point for the editorial inbox."""

from __future__ import annotations

from pathlib import Path

import duckdb
import streamlit as st
from app.data import fetch_inbox_groups


ROOT_DIR = Path(__file__).resolve().parents[1]
MOTOR_PATH = ROOT_DIR / "data" / "motor.duckdb"
SIGNALS_PATH = ROOT_DIR / "data" / "senales.duckdb"


@st.cache_data
def load_inbox(motor_path: str, signals_path: str):
    """Cache the pure read-only query at the UI boundary."""

    return fetch_inbox_groups(motor_path, signals_path)


def main() -> None:
    """Render the availability state while SIB-02 owns inbox controls and cards."""

    st.set_page_config(page_title="Bandeja editorial")
    st.title("Bandeja editorial")
    st.caption("La priorización temporal usa fecha y corroboración entre procedencias.")

    try:
        groups = load_inbox(str(MOTOR_PATH), str(SIGNALS_PATH))
    except (duckdb.Error, OSError):
        st.warning("Los datos no están disponibles. Ejecute el motor antes de consultar la bandeja.")
        return

    if not groups:
        st.info("No hay grupos disponibles para revisión.")
        return

    st.info("Hay grupos disponibles. Los controles y las fichas se incorporarán próximamente.")


if __name__ == "__main__":
    main()
