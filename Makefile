.PHONY: instalar datos procesar test sync db arrancar modelos clasificar agrupar motor muestra evaluar

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

modelos:        ## descarga el modelo de embeddings a una caché local (modelos/) para uso offline
	SENTENCE_TRANSFORMERS_HOME=modelos python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', cache_folder='modelos')"

clasificar:     ## clasifica las noticias por tema (embeddings + baseline TF-IDF) en data/motor.duckdb
	python motor/clasificar.py

agrupar:        ## agrupa titulares del mismo evento y cuenta procedencias en data/motor.duckdb
	python motor/agrupar.py

muestra:        ## genera una muestra estratificada por mes para etiquetar a ciegas (data/etiquetas/)
	python motor/muestra_etiquetado.py

evaluar:        ## evalua embeddings/tfidf contra las etiquetas humanas (macro-F1, precision/recall, confusion)
	python motor/evaluar.py

motor:          ## modelo (si falta) + clasificación + agrupación; idempotente
	@test -d modelos || $(MAKE) modelos
	$(MAKE) clasificar
	$(MAKE) agrupar
