# Contexto para Claude Code — PractIA

Este archivo es para que **cualquier sesión de Claude Code** retome el proyecto sin que ReMar tenga que explicar todo de nuevo. Léelo primero.

## Qué es PractIA

Prep por voz para estudiantes peruanos postulando a prácticas trainee en banca, FMCG y consultoría, con dos módulos (selector "Modo" en el sidebar):

1. **Group case** — caso + anexos + cronómetro, respuesta por voz, feedback contra rúbrica.
2. **Entrevista 1-a-1 con el jefe final** — preguntas del banco `docs/PractIA_Banco_Preguntas.pdf` (STAR, técnicas por industria, fit). Hoy solo muestra una pregunta aleatoria; falta grabar y evaluar.

Ver `README.md` para el pitch completo.

## Proveedor de IA: Groq (gratis)

- Whisper `whisper-large-v3` y LLM `openai/gpt-oss-120b` (modo JSON) vía el SDK `groq`. Variables: `GROQ_API_KEY`, `GROQ_LLM_MODEL`, `GROQ_WHISPER_MODEL` (ver `.env.example`).
- **No volver a OpenAI/Anthropic**: son de pago y se descartaron.
- `llama-3.3-70b-versatile` ya no está en el plan gratuito (baja el 2026-08-16); por eso el default es gpt-oss-120b.
- `groq==0.11.0` falla con `httpx>=0.28`; por eso `requirements.txt` fija `httpx==0.27.2`.
- Límites del plan gratuito (nov. 2026): LLM 30 RPM, 1K req/día, **8K tokens/min** (una evaluación gasta ~6.0-6.2K tokens con la rúbrica v2 y el RAG: solo cabe una por minuto); Whisper 20 RPM, 2K req/día, 2 h de audio/hora.

## Contexto de la fundadora

- **ReMar** (Ana Renata Zuta), estudiante de Economía en UP, 10.º ciclo, tercio superior.
- Internship actual: Lima Expresa (planeamiento financiero).
- Internship previo: Crece Finanzas Estratégicas (crédito SME).
- Preferencia explícita: **no toques sus archivos Excel sin pedir permiso**. Si detectas que un script podría modificar un `.xlsx` de ella, pregunta antes.
- Idioma: español peruano. Todo el UI, prompts y feedback van en español.

## Restricciones de la tarea del curso

Esto NO es un proyecto libre. Hay restricciones duras:

1. **Deadline:** entrega en issue #205 del repo `d2cml-ai/Data-Science-Python` antes del **lunes 16 nov 2026, 23:59**. Presentación **miércoles 18 nov, 7:50 AM** (turno #15).
2. **Demo en vivo obligatoria:** 3 minutos exactos. El profe corta a los 3:00. El demo vale 8 de 20 puntos: URL pública en vivo = 7–8 pts, laptop = 4–6 pts, solo diapositivas = 0 pts.
3. **Al menos 2 herramientas del syllabus dentro del producto** (no solo en desarrollo). Las elegidas: Whisper (sesión 13) + LLMs con RAG (sesión 8). El RAG hoy es ligero (BM25, `ai/rag.py`); el de memorias anuales con ChromaDB sigue por construir. Document AI y TTS son opcionales de refuerzo.
4. **Repo público** con 9 secciones de README (ya están en README.md).
5. **3 conversaciones con usuarios potenciales** en `docs/research/` — las entrevistas están en curso con una analista de banca, una de FMCG y una de consultoría.
6. **No subir claves de API al repo** — usar `.env` (ya en `.gitignore`) y `.env.example`.
7. **Commits en varios días**, no todos el último día.

## Evaluación del group case (rúbricas v2)

- `ai/rubrics/{banca,fmcg,consultoria}.json`: cada criterio tiene `tipo` (`tecnico` 55 %, `blando` 30 %, `innovacion` 15 %), `peso` y, opcional, `aplica_a` (lista de `case_type`; hoy solo "Market sizing / Fermi" en consultoría). El balance salió de las entrevistas de validación: las tres pusieron las habilidades blandas por encima de lo técnico.
- `ai/evaluator.py` filtra los criterios que aplican al caso y reparte el peso de los que no aplican **dentro de su mismo tipo**, para no mover el balance. El LLM puntúa cada criterio (0-10); **el total y los subtotales por tipo los calcula el código**, no el modelo. Si faltan criterios reintenta una vez; si siguen faltando conserva el total del modelo.
- Habilidades blandas: se estiman por señales observables de una respuesta individual (reconoce a otros actores, atiende las restricciones del caso, declara supuestos, prioriza); sin evidencia vale 5.
- Aporte propio: el LLM compara la respuesta con la referencia del caso (`respuesta_referencia` si existe, si no `pista_respuesta_modelo`, preparada con Claude) y devuelve `comparativo_referencia` (coincide / aporta / le faltó). Copia de la referencia = 5; plantilla genérica = 1-2; aportes válidos = 7+.
- RAG ligero (`ai/rag.py`, BM25 en Python puro, sin dependencias): indexa las 75 preguntas (con su hint) y los 12 casos (con su referencia); el evaluador recupera `RAG_K` fragmentos (3 por defecto; 0 lo apaga) parecidos al caso y a la respuesta, los pasa al prompt como material de apoyo y los devuelve en `fuentes_recuperadas` (la UI los muestra). Si falla, se evalúa sin él. Cuesta ~300 tokens.
- Cada caso puede traer `criterios_no_aplican` (lista de nombres) cuando no pide algo que la rúbrica evalúa; hoy `consultoria_01` (no pide recomendación). Su peso se reparte dentro del mismo tipo.
- Los 9 casos originales con pista corta tienen además `respuesta_referencia` (respuesta completa, preparada con Claude y verificada contra los anexos); `consultoria_03`, `banca_04` y `consultoria_04` usan su pista, que ya es completa.
- Guion final (`ai/guion.py`, prompt en `ai/prompts/guion_system.md`): botón aparte tras evaluar (una 2.ª llamada al LLM, ~3.5K tokens, para no cargar la evaluación; si acabas de evaluar hay que esperar ~1 min por el límite de 8K/min). Parte de la respuesta del estudiante e incorpora el contraste (le faltó / aportó / a mejorar); apunta a 400-450 palabras (reintenta si <360 o >470) y calcula el tiempo de cada bloque por palabras (150/min), no por lo que diga el modelo. `app/pdf_export.py::guion_to_pdf` arma el PDF único; normaliza con NFKC los espacios y guiones no separables que escribe el LLM (salían como "?").
- Identidad visual (`app/theme.py`): tema por empresa (`EMPRESAS`, buscado en `case["company"]`), con fallback al de la industria y uno propio para el modo entrevista. Solo genera HTML/CSS (escapado con `html.escape`); `case_view` inyecta el CSS y pinta la franja y la misión. Además del color de la franja, la página y la barra lateral se tiñen con un tinte muy claro de la marca (`fondos()`), los títulos usan su tono oscuro y las tarjetas (anexos, cajas de texto, grabador) quedan en blanco. Eso asume texto oscuro, por eso `.streamlit/config.toml` fija el tema claro (en modo oscuro del sistema sería ilegible). Los colores deben cumplir contraste WCAG AA (texto blanco sobre `oscuro` y texto del monograma sobre `acento`, >= 4.5): hay prueba. La barra de progreso de Streamlit anida 3 capas, el relleno es `[role=progressbar] > div > div > div`.
- Recorrido guiado: `main()` crea un contenedor arriba y lo llena al final (`_paso_actual`), porque el estado de la corrida actual recién está actualizado después de `recording_view`. Historial de intentos en `st.session_state.historial[case_id]` (solo de la sesión, sin base de datos). `punto_debil_view` busca con el RAG (`solo_preguntas=True`) preguntas del banco para el criterio más bajo (<= 7/10), sin llamar al LLM.
- Cronómetro (`app/main.py::timer_view`): cuenta regresiva con `st.fragment(run_every=1)` solo mientras corre; la fase fija el objetivo y no afecta la evaluación (el evaluador solo ve la longitud en palabras).
- El modelo gpt-oss usa `reasoning_effort=low` (`GROQ_REASONING_EFFORT`) para gastar menos tokens.

## Agente verificador de casos (`ai/verifier/`)

Audita un caso y guarda `ai/audits/<id>.json|md` (la app lo muestra en `app/verificacion_view.py`). Detalle, medición y límites en `docs/AGENTE_VERIFICADOR.md`; CLI en `scripts/auditar.py`; pruebas en `tests/` (`pytest`, sin red ni API).

- El LLM propone (qué comprobar, qué buscar); **el código calcula y verifica**. Sin cita textual encontrada en una página abierta no hay veredicto (`fuentes.py`). No editar esas reglas para "que salgan más hallazgos".
- **Cuesta tokens de la cuota de Groq** (200K/día en gpt-oss-120b; ~7K una extracción, ~9K un hecho con web, una llamada por minuto). Antes de correrlo en lote, avisar a ReMar. No lo uses en la demo ni dentro de la app.
- Nunca editar los casos automáticamente a partir de un informe: el agente propone, ReMar decide.
- `tests/fixtures/casos_con_defectos/` son los casos como estaban antes de `384710b`, con sus defectos reales; no "arreglarlos".
- Pendiente: regenerar los informes tras la cuota diaria: `python -m scripts.auditar caso ai/cases/<caso>.json --max-hechos 1 --sin-cache` y commitear `ai/audits/`.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT (app/main.py)                 │
│  Selección empresa → caso → cronómetro → grabación voz     │
└───────────┬──────────────────────────────────┬──────────────┘
            │                                  │
            ▼                                  ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│ ai/case_generator.py     │      │ ai/transcribe.py         │
│ RAG (ChromaDB) +         │      │ Whisper large-v3 (Groq)  │
│ corpus de reportes       │      │ (GROQ_WHISPER_MODEL)     │
│ públicos (data/)         │      │                          │
└──────────────────────────┘      └──────────┬───────────────┘
                                             │
                                             ▼
                                  ┌──────────────────────────┐
                                  │ ai/evaluator.py          │
                                  │ LLM de Groq (modo JSON)  │
                                  │ gpt-oss-120b (por .env)  │
                                  │ + Pydantic (Feedback)    │
                                  │ contra rúbrica           │
                                  └──────────┬───────────────┘
                                             │
                                             ▼
                                        Feedback en UI
```

## Estado actual (lo que YA está hecho)

- [x] Idea validada conceptualmente (3 iteraciones en chat).
- [x] Estructura del repo creada.
- [x] README.md con las 9 secciones y los dos módulos.
- [x] 12 casos semilla en `ai/cases/*.json` (4 banca, 4 FMCG, 4 consultoría); `banca_04` (pricing) y `consultoria_04` (evaluación de impacto) salieron de las entrevistas de validación.
- [x] Rúbricas por industria en `ai/rubrics/*.json` (v2: 55 % técnico, 30 % habilidades blandas, 15 % aporte propio frente a la referencia).
- [x] Whisper (`ai/transcribe.py`) y evaluador (`ai/evaluator.py`) conectados a Groq.
- [x] Flujo end-to-end del group case en `app/main.py`: grabación → Whisper → transcripción editable → evaluador → feedback + PDF (`app/pdf_export.py`). Probado con Groq simulado (`streamlit.testing`) y de punta a punta con la API real en Chrome headless subiendo un audio (capturas en `docs/architecture/`). **El micrófono real (`audio_recorder`) no se ha probado.**
- [x] Modo "Entrevista 1-a-1": pregunta aleatoria por tipo, solo lectura. Banco de 75 preguntas en `ai/questions/*.json`: 60 de `docs/PractIA_Banco_Preguntas.pdf` y 15 de las entrevistas de validación (campo `fuente`).
- [x] Diagrama en `docs/architecture/arquitectura.png`.
- [x] Guía de las entrevistas de validación en `docs/PractIA_Guia_Entrevistas.pdf`.

## Estado pendiente (lo que FALTA hacer)

Prioridad descendente:

1. **[CRÍTICO] Probar el micrófono real** — grabar con `audio_recorder` en el navegador y evaluar; el resto del flujo ya se probó con la API real subiendo un audio.
2. **[HECHO] Deploy en Streamlit Community Cloud** — https://practia-up.streamlit.app/ (Python 3.11, secret `GROQ_API_KEY`). Probado de punta a punta en la URL pública. Ábrela unos minutos antes de la demo: la app se duerme tras un tiempo sin visitas.
3. **[IMPORTANTE] 3 entrevistas transcritas en `docs/research/entrevista-{01,02,03}.md`** — cuando ReMar traiga los audios (~17 min cada uno), usar `scripts/transcribe_batch.py` para procesarlos y luego sintetizar notas con la plantilla ya definida en el PDF de guías. No tocar `docs/research/`: lo llena ReMar.
4. **[IMPORTANTE] Módulo 2: grabar y evaluar** — `ai/interviewer.py`, `ai/interview_evaluator.py`, rúbrica STAR + fit en `ai/rubrics/` y prompts en `ai/prompts/`. Cada pregunta del banco trae su `hint` para usarlo como criterio.
5. **[HECHO 2026-11-12] Auditoría de cifras de los 12 casos** (commit `384710b`): se recalcularon los anexos contra las pistas y referencias y se corrigieron 10 incongruencias en 8 casos (balance de `banca_01`, payback de `consultoria_02` = CAPEX ÷ (venta anual × margen) con margen 8% / 7.5%, break-even de `fmcg_01`, la referencia de `fmcg_04` decía "no recupero nada" cuando la cuenta sí recupera margen, etc.). Antes ya estaban corregidos `banca_01` (deuda +34%), `consultoria_01` (nota "wait"), `consultoria_02` (8% era una tienda) y `fmcg_01` (Sao 28%). Los competidores "Marca B/C" de `fmcg_01` y `fmcg_04` son ficticios a propósito: Cocinero, Princesa, Triángulo y Costa son marcas de Alicorp y Nestlé. Si se editan anexos, recalcular con los números del anexo antes de tocar la referencia, y mantener las referencias en un largo parecido (el plan gratuito de Groq permite 8K tokens/min).
6. **[DESEABLE] RAG con memorias anuales** — descargar memorias de BCP, Alicorp, Credicorp (links en `data/sources.md`) e indexar en ChromaDB. `chromadb` y `sentence-transformers` están en `requirements-rag.txt`, fuera de `requirements.txt`, porque arrastran torch y alargan el build del deploy sin que ningún código las use aún; instálalas con `pip install -r requirements-rag.txt` y, si el RAG se despliega, vuelve a pasarlas a `requirements.txt`.
7. **[DESEABLE] Video de respaldo de 60–90s** — por si falla el deploy en vivo (requerido por la rúbrica).
8. **[DESEABLE] 2 capturas más del flujo** en `docs/architecture/`.

## Convenciones de código

- Python 3.11+.
- Type hints en todo lo que toque el modelo (inputs, outputs).
- Un archivo = una responsabilidad. No metas lógica de LLM dentro de `app/main.py`.
- Variables de entorno via `python-dotenv`.
- Logging con `loguru`, no `print`.
- Si agregas una dependencia, actualiza `requirements.txt` con versión pinned.
- Streamlit: no fijes el valor de un widget con clave fija vía `st.session_state` tras trabajo lento (no se pinta en el navegador); usa `value=` y una clave nueva por entrada. Las pruebas con `streamlit.testing` no detectan esto: verifica en un navegador.

## Cuando hagas commits

- Mensajes en español, imperativo: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`.
- Un commit por cambio lógico, no "WIP" monolíticos.
- **Nunca** hagas `git add -A` sin revisar `.env`, `*.wav`, `*.mp3`, `__pycache__`, `.venv`. Todos están en `.gitignore` pero más vale confirmar.

## Qué NO hacer

- No cambiar el stack (Streamlit → Next.js) sin discutirlo con ReMar primero. 7 días no alcanzan.
- No agregar login/base de datos salvo que esté explícitamente pedido.
- No usar casos reales con nombres de empresas sin verificar que sean datos públicos.
- No subir audios de las entrevistas al repo público (son conversaciones privadas).
- No volver a OpenAI/Anthropic: el proveedor es Groq (gratis).
- No pitchear ChatGPT genérico como competidor principal en el README — la diferenciación es contexto peruano.
