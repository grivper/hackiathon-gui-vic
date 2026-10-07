.PHONY: instalar datos procesar test sync db arrancar

instalar:
	pip install -r requirements.txt

datos:          ## descarga todas las fuentes y genera el snapshot
	python ingesta/descargar_snapshot.py

procesar:       ## regenera processed/ desde raw/ sin internet
	python ingesta/descargar_snapshot.py --solo-procesar

test:
	python -m pytest -q tests

sync:           ## sincroniza la bitácora con Notion
	python notion_sync.py

db:             ## carga data/processed/* en DuckDB y genera el reporte de calidad
	python motor/cargar_db.py

arrancar: instalar db  ## instala dependencias y carga la base DuckDB (setup en un comando)

