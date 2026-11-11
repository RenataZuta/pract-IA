# Instrucciones para Claude Code — qué hacer ahora

> Dale este archivo a Claude Code junto con el `CLAUDE.md` de la raíz.
> Dile: *"Lee `CLAUDE.md` y `docs/CLAUDE_CODE_NEXT_STEPS.md`, y ejecuta las tareas pendientes en orden."*

El proveedor de IA es **Groq** (gratis): no uses OpenAI ni Anthropic. Detalles en `CLAUDE.md`.

## Setup inicial (una sola vez)

```bash
# 1. Crear virtualenv (Python 3.11)
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
# .venv\Scripts\activate       # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar variables
cp .env.example .env
# Luego editar .env y agregar GROQ_API_KEY (gratis en https://console.groq.com)

# 4. Probar que Streamlit levanta
streamlit run app/main.py
```

## Tarea 1 — Conectar Whisper ✅ hecho

`ai/transcribe.py` usa `whisper-large-v3` de Groq. Los errores se devuelven como
`[ERROR_WHISPER] ...` y se loguean con loguru (sin traceback, para no imprimir
el audio ni la API key).

## Tarea 2 — Conectar el evaluador ✅ hecho

`ai/evaluator.py` llama al LLM de Groq en modo JSON (`openai/gpt-oss-120b` por
defecto, cambiable con `GROQ_LLM_MODEL`), valida con `Feedback` (Pydantic) y
reintenta una vez si el JSON es inválido. Lanza `EvaluationError` si Groq falla.

## Tarea 3 — Flujo end-to-end en Streamlit ✅ hecho (falta probarlo con la API real)

`app/main.py`: grabación → Whisper → transcripción editable → evaluador →
feedback (métrica, criterios, fortaleza, mejoras, red flags, respuesta modelo) y
descarga en PDF (`app/pdf_export.py`). Incluye el modo "Entrevista 1-a-1" (solo
muestra una pregunta de `ai/questions/`).

**Pendiente:** con `GROQ_API_KEY` en `.env`, graba (o sube) un audio corto,
verifica que transcribe y evalúa, y guarda una captura en
`docs/architecture/captura_01_demo_flujo.png`.

## Tarea 4 — Deploy en Streamlit Community Cloud (~15 min)

1. El repo ya es público: `github.com/RenataZuta/pract-IA`.
2. Ve a https://share.streamlit.io → *Create app* → repositorio
   `RenataZuta/pract-IA`, rama `main`, archivo `app/main.py`.
3. En *Advanced settings* elige **Python 3.11** y, en *Secrets*, agrega:
   `GROQ_API_KEY = "gsk_..."`
4. Espera 3-5 min al build. Guarda la URL en el README (sección 6).

## Tarea 5 — Procesar los audios de las entrevistas (~30 min, cuando ReMar los tenga)

ReMar está consiguiendo 3 audios de ~17 min cada uno (banca, FMCG,
consultoría).

1. Cuando los tenga, deben ir a:
   - `data/audios/entrevista_01_banca.m4a`
   - `data/audios/entrevista_02_fmcg.m4a`
   - `data/audios/entrevista_03_consultoria.m4a`
2. Corre `python scripts/transcribe_batch.py`.
3. Lee cada `data/transcripts/entrevista_0X_cruda.txt`.
4. Sintetiza en `docs/research/entrevista-01.md`, `-02.md`, `-03.md`
   usando la plantilla de `docs/research/README.md`.
5. **Importante:** los audios crudos NO se suben al repo (ya está en
   `.gitignore`). Solo las notas sintetizadas.

## Tarea 6 — RAG opcional (~90 min, si hay tiempo)

Archivo: crear `ai/rag_index.py` desde cero.

0. Instala las dependencias del RAG: `pip install -r requirements-rag.txt`
   (están fuera de `requirements.txt` para no alargar el deploy; si el RAG
   se despliega, vuelve a pasarlas a `requirements.txt`).
1. Descarga las memorias anuales listadas en `data/sources.md` a
   `data/corpus/`.
2. Indexa con ChromaDB y `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.
3. En `ai/case_generator.py` (crear nuevo), usa el RAG para generar
   anexos de casos con datos reales en vez de los hardcoded en
   los JSON de `ai/cases/`.
4. Opcional para el demo: generar un caso nuevo en vivo durante
   la presentación.

## Tarea 7 — Video de respaldo (~30 min)

Requerido por la rúbrica como Plan B.

1. Corre el flujo completo localmente.
2. Graba la pantalla con **Loom** o **OBS Studio**: 60-90 segundos.
3. Sube a YouTube (unlisted) o Loom.
4. Pega el link en el README sección 6 (Demo).

## Tarea 8 — Módulo 2: grabar y evaluar la entrevista

Hoy el modo "Entrevista 1-a-1" solo muestra una pregunta. Falta:

1. `ai/interview_evaluator.py`: evalúa la respuesta según el `tipo` de la
   pregunta (STAR / técnica / fit), usando su `hint` como criterio.
2. Rúbrica de entrevista en `ai/rubrics/` y prompts en `ai/prompts/`.
3. En `app/main.py`: grabar la respuesta, transcribir, evaluar y mostrar el
   feedback (reutiliza `feedback_view` si el schema es compatible).

## Checklist final antes del lunes 16 a las 11:59 p.m.

Ver `docs/CHECKLIST_ENTREGA.md`.
