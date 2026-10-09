# Segunda opinión humana

Una segunda persona del equipo (Guille, que construyó el motor) revisó las mismas salidas del sistema de forma independiente de la evaluación principal (`evaluacion-humana-final.md`, Víctor). No es una revisión ciega ni externa: los dos revisores pertenecen al equipo. Se publica para que se vea dónde coinciden y dónde no.

## Validez del sustento

- Alcance: 23 afirmaciones reales (12 de las fichas finales, 7 de borradores previos de esas fichas y 4 de fichas generadas desde la app). Todavía no llegan a las 30 que pide el reto.
- Criterio: la afirmación debe decir lo mismo que la fuente citada; si agrega una cifra, causa o fecha que la fuente no dice, no está respaldada.
- Resultado: **19 / 23 = 82,6 %** (2 ambiguas y 2 no respaldadas). Sin contar las ambiguas: 90,5 %.
- Tiempo: 15 min 21 s para las 23 afirmaciones (unos 40 s por afirmación).
- Detalle fila por fila: `data/revision/validez_sustento.csv`.

| Fila | Veredicto de la segunda opinión | Veredicto de la evaluación principal | Comentario |
|---|---|---|---|
| 1 (Encuentro Mulino, diaadia.com.pa) | no respaldada | respaldada | La segunda opinión comparó con la página original, que no mostraba el nombre de Sheinbaum; el titular guardado en la base sí lo trae. |
| 7 (inflación 2024, Banco Mundial) | no respaldada | no respaldada | Coinciden. Es un indicador oficial, no un titular; el valor redondeado coincide con el indicador. |
| 10 (reunión sobre economía y neutralidad) | ambigua | respaldada | Se dudó por el tiempo futuro "serán temas". |
| 11 (Sheinbaum apoya la neutralidad) | ambigua | respaldada | Se dudó de que el titular afirme apoyo. |

## Precision@5

Sobre los mismos cinco grupos del ranking (G-0fee038b990b, G-9d6c477049d9, G-9f2630b6d7d1, G-b4cdd9db855e, G-cfe160debe8e):

- Segunda opinión: **2 / 5 = 40 %** (relevantes: G-0fee038b990b y G-b4cdd9db855e).
- Evaluación principal: **4 / 5 = 80 %**.
- Método de la segunda opinión: se evaluaron a ciegas 20 grupos candidatos (los cinco del ranking más 15 siguientes, en orden aleatorio y sin puntaje). Se eligieron cinco como top propio y se marcó relevancia en los 20. Coincidieron 2 de los 5 del sistema.
- Hay muchos grupos empatados en 90 puntos, por lo que el top 5 depende del criterio de desempate (puntaje, U, id).

## Cómo leer la diferencia

Las dos revisiones dan resultados distintos con criterios de relevancia distintos. La métrica de Precision@5 es sensible al criterio editorial y la muestra es de solo cinco registros, así que no debe leerse como una medida estable. La meta del 90 % de validez del sustento no se cumple con ninguna de las dos revisiones.
