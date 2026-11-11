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
- Límites del plan gratuito (nov. 2026): LLM 30 RPM, 1K req/día, **8K tokens/min** (una evaluación gasta ~3.5-4.7K tokens: con los casos largos solo cabe una por minuto); Whisper 20 RPM, 2K req/día, 2 h de audio/hora.

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
3. **Al menos 2 herramientas del syllabus dentro del producto** (no solo en desarrollo). Las elegidas: Whisper (sesión 13) + LLMs con RAG (sesión 8). Document AI y TTS son opcionales de refuerzo.
4. **Repo público** con 9 secciones de README (ya están en README.md).
5. **3 conversaciones con usuarios potenciales** en `docs/research/` — las entrevistas están en curso con una analista de banca, una de FMCG y una de consultoría.
6. **No subir claves de API al repo** — usar `.env` (ya en `.gitignore`) y `.env.example`.
7. **Commits en varios días**, no todos el último día.

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
- [x] Rúbricas por industria en `ai/rubrics/*.json`.
- [x] Whisper (`ai/transcribe.py`) y evaluador (`ai/evaluator.py`) conectados a Groq.
- [x] Flujo end-to-end del group case en `app/main.py`: grabación → Whisper → transcripción editable → evaluador → feedback + PDF (`app/pdf_export.py`). Probado con Groq simulado (`streamlit.testing`) y de punta a punta con la API real en Chrome headless subiendo un audio (capturas en `docs/architecture/`). **El micrófono real (`audio_recorder`) no se ha probado.**
- [x] Modo "Entrevista 1-a-1": pregunta aleatoria por tipo, solo lectura. Banco de 75 preguntas en `ai/questions/*.json`: 60 de `docs/PractIA_Banco_Preguntas.pdf` y 15 de las entrevistas de validación (campo `fuente`).
- [x] Diagrama en `docs/architecture/arquitectura.png`.
- [x] Guía de las entrevistas de validación en `docs/PractIA_Guia_Entrevistas.pdf`.

## Estado pendiente (lo que FALTA hacer)

Prioridad descendente:

1. **[CRÍTICO] Probar el micrófono real** — grabar con `audio_recorder` en el navegador y evaluar; el resto del flujo ya se probó con la API real subiendo un audio.
2. **[CRÍTICO] Deploy en Streamlit Community Cloud** — Python 3.11 y `GROQ_API_KEY` en Secrets; poner la URL en el README (sección 6).
3. **[IMPORTANTE] 3 entrevistas transcritas en `docs/research/entrevista-{01,02,03}.md`** — cuando ReMar traiga los audios (~17 min cada uno), usar `scripts/transcribe_batch.py` para procesarlos y luego sintetizar notas con la plantilla ya definida en el PDF de guías. No tocar `docs/research/`: lo llena ReMar.
4. **[IMPORTANTE] Módulo 2: grabar y evaluar** — `ai/interviewer.py`, `ai/interview_evaluator.py`, rúbrica STAR + fit en `ai/rubrics/` y prompts en `ai/prompts/`. Cada pregunta del banco trae su `hint` para usarlo como criterio.
5. **[DESEABLE] RAG con memorias anuales** — descargar memorias de BCP, Alicorp, Credicorp (links en `data/sources.md`) e indexar en ChromaDB. `chromadb` y `sentence-transformers` están en `requirements-rag.txt`, fuera de `requirements.txt`, porque arrastran torch y alargan el build del deploy sin que ningún código las use aún; instálalas con `pip install -r requirements-rag.txt` y, si el RAG se despliega, vuelve a pasarlas a `requirements.txt`.
6. **[DESEABLE] Video de respaldo de 60–90s** — por si falla el deploy en vivo (requerido por la rúbrica).
7. **[DESEABLE] 2 capturas más del flujo** en `docs/architecture/`.

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
