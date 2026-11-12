# Guion del demo — 3 minutos + 2 de comentarios

Turno **#15, miércoles 18-nov, 7:50 AM** (conectarse a las 7:25). A los **3:00 el profe corta**: ensaya con cronómetro, compartiendo pantalla y audio. Sin diapositivas.

Caso de la demo: **Banca → BCP — Línea de capital de trabajo para una PYME importadora** (`banca_01`). Es el que tiene los números más claros para decir en voz alta.

## Antes de conectarte (7:25–7:45)

- [ ] Una sola ventana de Chrome con 3 pestañas: **la app** (https://practia-up.streamlit.app/), **el repo** y **el video de respaldo**. Cierra todo lo demás y apaga notificaciones.
- [ ] Abre la app a las 7:25: si estaba dormida, tarda en despertar. Deja elegido **Group case → Banca → BCP**.
- [ ] Prueba compartir pantalla **y audio** en la clase virtual. El audio del navegador no sale por defecto en todas las plataformas.
- [ ] Haz **una** evaluación de calentamiento al menos 3 minutos antes de tu turno (el plan gratuito de Groq da 8K tokens por minuto y una evaluación gasta ~6K). Después, recarga la página para empezar limpia.
- [ ] Ten abierto un plan B (ver abajo) y el micrófono ya autorizado en el navegador.

## Minuto a minuto

| Tiempo | Qué muestras | Qué dices |
|---|---|---|
| **0:00–0:30** El problema | Nada en pantalla, o la app abierta en el caso | "Para entrar a un programa trainee de banca, consumo masivo o consultoría pasas dos pruebas que no puedes practicar solo: el **group case**, que pide 4 a 6 personas, un caso y un evaluador, y la **entrevista final con el jefe**. Hoy se practica por WhatsApp, con coaching de S/ 150 a 500, o con un ChatGPT que no conoce lo que preguntan en Perú. En las 3 entrevistas que hice, la fase que más temen es la final." |
| **0:30–0:45** El caso | Franja de BCP, contexto y **Anexo 1** abierto (5 s) | "Esto es PractIA. Elijo BCP: una PYME pide S/ 1.2 millones. Cada caso trae anexos con cifras." |
| **0:45–1:30** Responde por voz | Clic en el micrófono y hablas **45–60 s** | Di tu recomendación: aprobar condicional, línea de S/ 900 mil; **tres números** (EBITDA de 730 a 560 mil, deuda +34 %, 85 % de importaciones en dólares sin cobertura); cuatro condiciones; riesgo principal. |
| **1:30–1:40** Transcribe | Aparece la transcripción editable | "Whisper la transcribe en segundos y puedo corregirla antes de evaluar." Clic en **Evaluar respuesta**. |
| **1:40–2:15** Feedback | Puntaje total y los tres subtotales; un criterio con su comentario; **Comparativo con la respuesta de referencia**; "Material recuperado por RAG" | "Evalúa contra una rúbrica 55 % técnico, 30 % habilidades blandas y 15 % aporte propio. **El total lo calcula el código, no el modelo.** Compara con una respuesta de referencia y usa RAG sobre un banco de 75 preguntas reales. Y revisa que las cifras del feedback salgan de los anexos." |
| **2:15–2:30** Módulo 2 | Clic en **Entrevista 1-a-1** → una pregunta y la **pista del entrevistador** | "El segundo módulo es la entrevista con el jefe final: preguntas reales del proceso peruano, y cada una trae lo que busca el entrevistador." *(No evalúes en vivo: ver nota abajo.)* |
| **2:30–3:00** El negocio | Nada, o el README | "Free con 2 sesiones al mes; **Pro S/ 29 al mes**; **Teams S/ 500 al mes** para universidades, 50 usuarios. Una sesión cuesta unos S/ 0.03, así que el margen por usuario Pro es de ~S/ 28. Las entrevistas mostraron que los estudiantes pagan poco, por eso la primera apuesta es vender a universidades." |

> **Por qué no evaluar el módulo 2 en vivo:** una evaluación del group case gasta ~6K tokens y la del módulo 2 ~3K; juntas en el mismo minuto pasan de los 8K por minuto y Groq responde 429. En la demo, **una sola evaluación en vivo**. No uses el "Guion final": pide esperar un minuto después de evaluar.

## Si algo falla (plan B)

| Falla | Qué haces |
|---|---|
| El micrófono no funciona | Expande **"¿No funciona el micrófono?"** y pulsa **"Usar la respuesta de referencia como ejemplo"** (carga una respuesta lista, rotulada como ejemplo), o sube un audio ya grabado. |
| Sale un error de Groq (límite) | El mensaje dice cuántos segundos esperar. Mientras tanto sigue con el módulo 2 o el negocio, y vuelve a evaluar. |
| La app no carga o se cae el internet | Pasa al **video de respaldo** (60–90 s): cuenta como demo en vivo si el código que lo produce está en el repo. |
| La transcripción sale rara | Corrígela a mano en el cuadro; es editable. |

## Preguntas que pueden hacerte (2 minutos de comentarios)

- **¿Dónde está el evaluador?** `ai/evaluator.py`. Filtra los criterios que aplican al caso, llama al LLM con la rúbrica y el RAG, valida con Pydantic y **recalcula el total**.
- **¿Por qué recalcular el total?** Porque el modelo se equivoca en la aritmética. El LLM puntúa cada criterio; el código aplica los pesos.
- **¿Qué es el RAG?** `ai/rag.py`: BM25 en Python puro sobre 87 documentos (75 preguntas y 12 casos). Sin dependencias pesadas, cabe en el plan gratuito de Streamlit Cloud.
- **¿Qué hizo el agente de IA?** Escribió la mayor parte del código; yo decidí el problema, las rúbricas (salieron de las entrevistas) y revisé las cifras de los casos. Hay una tabla en la sección 9 del README.
- **¿Cómo sabes que las cifras de los casos están bien?** Un agente verificador (`ai/verifier/`) recalcula los anexos con código y verifica hechos reales con fuentes; y `tests/` protege las cuentas corregidas. Está documentado, con sus límites, en `docs/AGENTE_VERIFICADOR.md`.
- **¿Qué falta?** Validar quién paga (las entrevistas mostraron baja disposición a pagar), probar con estudiantes y medir si el feedback mejora su desempeño.
