# Contexto para Claude Code — PractIA

Este archivo es para que **cualquier sesión de Claude Code** retome el proyecto sin que ReMar tenga que explicar todo de nuevo. Léelo primero.

## Qué es PractIA

Simulador de **group case** por voz para estudiantes peruanos postulando a prácticas trainee en banca, FMCG y consultoría. Ver `README.md` para el pitch completo.

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
│ RAG (ChromaDB) +         │      │ Whisper large-v3-turbo   │
│ corpus de reportes       │      │ (HF o OpenAI API)        │
│ públicos (data/)         │      │                          │
└──────────────────────────┘      └──────────┬───────────────┘
                                             │
                                             ▼
                                  ┌──────────────────────────┐
                                  │ ai/evaluator.py          │
                                  │ LLM (GPT-4o-mini o       │
                                  │ Claude Haiku) con        │
                                  │ structured output JSON   │
                                  │ contra rúbrica           │
                                  └──────────┬───────────────┘
                                             │
                                             ▼
                                        Feedback en UI
```

## Estado actual (lo que YA está hecho)

- [x] Idea validada conceptualmente (3 iteraciones en chat).
- [x] Estructura del repo creada.
- [x] README.md con las 9 secciones.
- [x] 10 casos semilla en `ai/cases/*.json` (3 banca, 4 FMCG, 3 consultoría).
- [x] Rúbricas por industria en `ai/rubrics/*.json`.
- [x] Esqueleto de app Streamlit en `app/main.py`.
- [x] Guías de entrevista en `docs/research/guia-entrevistas.pdf`.

## Estado pendiente (lo que FALTA hacer)

Prioridad descendente:

1. **[CRÍTICO] Conectar Whisper real** — hoy `ai/transcribe.py` tiene un stub. Usar la API de OpenAI (`openai-whisper-large-v3-turbo`) o Hugging Face Inference Endpoints.
2. **[CRÍTICO] Conectar el evaluador real** — `ai/evaluator.py` tiene el prompt listo pero falta el cliente API y el parsing JSON.
3. **[CRÍTICO] Flujo end-to-end en Streamlit** — hoy la UI muestra el caso y el cronómetro; falta conectar grabación → Whisper → evaluador → mostrar feedback.
4. **[IMPORTANTE] 3 entrevistas transcritas en `docs/research/entrevista-{01,02,03}.md`** — cuando ReMar traiga los audios (~17 min cada uno), usar `scripts/transcribe_batch.py` para procesarlos y luego sintetizar notas con la plantilla ya definida en el PDF de guías.
5. **[IMPORTANTE] Deploy en Streamlit Community Cloud** — con `OPENAI_API_KEY` en Secrets.
6. **[DESEABLE] RAG con memorias anuales** — descargar memorias de BCP, Alicorp, Credicorp (links en `data/sources.md`) e indexar en ChromaDB.
7. **[DESEABLE] Video de respaldo de 60–90s** — por si falla el deploy en vivo (requerido por la rúbrica).
8. **[DESEABLE] Diagrama de arquitectura y 3 capturas** en `docs/architecture/`.

## Convenciones de código

- Python 3.11+.
- Type hints en todo lo que toque el modelo (inputs, outputs).
- Un archivo = una responsabilidad. No metas lógica de LLM dentro de `app/main.py`.
- Variables de entorno via `python-dotenv`.
- Logging con `loguru`, no `print`.
- Si agregas una dependencia, actualiza `requirements.txt` con versión pinned.

## Cuando hagas commits

- Mensajes en español, imperativo: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`.
- Un commit por cambio lógico, no "WIP" monolíticos.
- **Nunca** hagas `git add -A` sin revisar `.env`, `*.wav`, `*.mp3`, `__pycache__`, `.venv`. Todos están en `.gitignore` pero más vale confirmar.

## Qué NO hacer

- No cambiar el stack (Streamlit → Next.js) sin discutirlo con ReMar primero. 7 días no alcanzan.
- No agregar login/base de datos salvo que esté explícitamente pedido.
- No usar casos reales con nombres de empresas sin verificar que sean datos públicos.
- No subir audios de las entrevistas al repo público (son conversaciones privadas).
- No pitchear ChatGPT genérico como competidor principal en el README — la diferenciación es contexto peruano.
