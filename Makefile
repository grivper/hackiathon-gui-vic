.PHONY: instalar datos procesar test sync

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
