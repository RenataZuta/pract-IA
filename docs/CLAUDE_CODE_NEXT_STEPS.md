# Instrucciones para Claude Code — qué hacer ahora

> Dale este archivo a Claude Code junto con el `CLAUDE.md` de la raíz.
> Dile: *"Lee `CLAUDE.md` y `docs/CLAUDE_CODE_NEXT_STEPS.md`, y ejecuta las tareas en orden."*

## Setup inicial (una sola vez)

```bash
# 1. Crear virtualenv
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
# .venv\Scripts\activate       # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar variables
cp .env.example .env
# Luego editar .env y agregar OPENAI_API_KEY

# 4. Probar que Streamlit levanta
streamlit run app/main.py
```

## Tarea 1 — Conectar Whisper (~30 min)

Archivo: `ai/transcribe.py`. Hoy es stub.

**Qué hacer:**
1. Instala la dependencia si falta: `pip install openai`.
2. En `_transcribe_openai`, reemplaza el `TODO` por la llamada real a
   `client.audio.transcriptions.create` con modelo `whisper-1`.
3. Maneja errores: si falla (red, rate limit), devuelve string con prefijo
   `[ERROR_WHISPER]` y loggea con `logger.exception`.
4. Test manual: graba un audio corto en `.webm` en Streamlit y verifica
   que la transcripción llega.

## Tarea 2 — Conectar el evaluador (~45 min)

Archivo: `ai/evaluator.py`.

**Qué hacer:**
1. En `_evaluate_openai`, usa `client.beta.chat.completions.parse` con
   `response_format=Feedback` (OpenAI structured outputs).
2. El system prompt ya está en `ai/prompts/evaluator_system.md`. El
   user prompt lo arma `_build_user_prompt`.
3. Si OpenAI structured outputs rechaza el schema (`strict=true` lo
   requiere), puede que necesites simplificar: quita los `Field(ge=0,le=10)`
   y valida después con Pydantic.
4. Test manual: usa el primer caso de `ai/cases/banca_01_credito_pyme.json`,
   un transcript stub de 2 oraciones, y verifica que devuelve un `Feedback`
   válido.

## Tarea 3 — Conectar el flujo end-to-end en Streamlit (~60 min)

Archivo: `app/main.py`.

**Qué hacer:**
1. Instala `audio-recorder-streamlit` (ya en requirements) y úsalo en
   `recording_view` para grabar en el navegador.
2. Al clickear "Evaluar":
   - Llama `transcribe_audio(audio_bytes)`.
   - Muestra la transcripción en un `st.text_area` editable (por si
     Whisper comete errores).
   - Llama `evaluate_response(transcript, case, rubric)`.
   - Renderiza el `Feedback` con `st.metric` para el puntaje total y
     `st.expander` para cada criterio.
3. Agrega un botón "Descargar feedback como PDF" (opcional, con
   `reportlab`).

## Tarea 4 — Deploy en Streamlit Community Cloud (~15 min)

1. Crea el repo en GitHub (público): `github.com/renatazuta/practia`.
2. `git init && git add . && git commit -m "feat: estructura inicial del repo"`.
3. `git push -u origin main`.
4. Ve a https://share.streamlit.io, autoriza el repo, elige `app/main.py`.
5. En Settings > Secrets agrega `OPENAI_API_KEY`.
6. Espera 3-5 min al build. Guarda la URL en el README.

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

## Checklist final antes del lunes 16 a las 11:59 p.m.

Ver `docs/CHECKLIST_ENTREGA.md`.
