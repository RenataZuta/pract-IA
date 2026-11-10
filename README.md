# PractIA

> Simulador de **group case** por voz para estudiantes peruanos que postulan a su primera o segunda práctica en banca, FMCG y consultoría. Les damos un caso real con anexos, lo resuelven por voz, y reciben feedback contra una rúbrica en menos de 1 minuto.

**One-liner:** Hacemos simulacros de group case por voz para estudiantes peruanos postulando a programas trainee, con casos locales y feedback accionable.

---

## 1. Founder

**Ana Renata "ReMar" Zuta** — estudiante de Economía en Universidad del Pacífico (10.º ciclo, graduación dic. 2026), tercio superior. Analista de Planeamiento Financiero en Lima Expresa (OPEX, control presupuestal). Internship previo en Crece Finanzas Estratégicas (crédito privado, modelado financiero, riesgo SME). Preparando CFA Nivel I.

Postulante activa a programas de prácticas (Interbank, Nexa Resources, Repsol), vive el dolor en primera persona.

## 2. Problema

Los estudiantes peruanos que postulan a programas trainee de banca, FMCG y consultoría enfrentan un **group case** al que no se pueden preparar solos: por definición requiere 4–6 personas, caso impreso, cronómetro y un evaluador. Hoy:

- Se juntan en grupos de WhatsApp improvisados que nunca cuadran horarios.
- Pagan Preplounge o sesiones de coaching individual (**S/ 150–500**) que no replican la dinámica grupal.
- Usan ChatGPT genérico que no conoce el contexto peruano (marcas Alicorp/Belcorp, régimen MYPE, dinámica del BCP).

**Evidencia:** 3 conversaciones con analistas junior (banca, FMCG, consultoría) que pasaron por el proceso en los últimos 24 meses — en `docs/research/`.

## 3. Solución

**PractIA** es una app web donde el estudiante:

1. Elige empresa objetivo (BCP, Alicorp, Apoyo Consultoría, etc.) y tipo de case.
2. Recibe el caso: 1 página de contexto + anexos numéricos (sintéticos pero realistas, con RAG sobre reportes públicos).
3. Cronómetro con las 3 fases estándar: lectura (15 min) → discusión (20 min) → conclusión (5 min).
4. Resuelve por voz; Whisper transcribe en tiempo real.
5. El evaluador IA devuelve feedback estructurado: framework usado, estructura numérica, claridad de recomendación, uso del tiempo, red flags.

## 4. Insight

El mercado asume que practicar group case **requiere grupo**. Pero el 80% de lo que evalúan los reclutadores es el desempeño individual: cómo estructuras, cómo priorizas, cómo comunicas bajo presión. Eso **sí** se puede practicar solo si tienes el caso, el cronómetro y una rúbrica que refleje cómo evalúan las empresas peruanas.

## 5. Why now

- **Whisper large-v3-turbo** (ago. 2024) hace la transcripción por voz en español peruano prácticamente gratis.
- **LLMs con salidas estructuradas** permiten rúbricas confiables sin reglas rígidas.
- **Hay 40.000+ estudiantes de pregrado de economía / admin / ing. industrial** en Lima postulando a prácticas cada ciclo (SUNEDU).

## 6. Demo

- **URL:** *(pendiente de deploy en Streamlit Cloud)*
- **Capturas:** `docs/architecture/`
- **Diagrama:** `docs/architecture/arquitectura.png`

Modelos y APIs:
- **Whisper large-v3-turbo** (OpenAI o Hugging Face) → transcripción de la voz del estudiante.
- **GPT-4o-mini / Claude Haiku 4.5** → evaluador contra rúbrica (JSON estructurado).
- **RAG con ChromaDB** → corpus de memorias anuales (BCP, Alicorp, Credicorp) y casos semilla.

## 7. Modelo de negocio

| Plan | Precio | Qué incluye |
|---|---|---|
| Free | S/ 0 | 2 group cases/mes, feedback básico |
| Pro | **S/ 29/mes** | Cases ilimitados, feedback detallado, biblioteca por empresa |
| Teams (universidades) | **S/ 500/mes** | 50 usuarios, dashboard del profesor, cases personalizados |

**Margen de contribución por usuario Pro:** ~S/ 23/mes (costo API ~S/ 6).

## 8. Herramientas del curso

Al menos dos del syllabus están dentro del producto (no solo en el desarrollo):

| Herramienta | Sesión | Dónde está en el repo |
|---|---|---|
| **Whisper (voz a texto)** | 13 | `ai/transcribe.py` |
| **LLMs con salidas estructuradas + RAG** | 8 | `ai/evaluator.py`, `ai/case_generator.py` |
| **Document AI / OCR** (opcional) | 10 | `ai/cv_parser.py` — para personalizar casos con el CV del estudiante |
| **Texto a voz** (opcional) | 15 | `ai/tts.py` — el evaluador "habla" el feedback |

## 9. Qué hizo el agente

El 90% del código fue escrito con Claude Code (Claude Opus 4.7). Las decisiones de producto, la selección de empresas objetivo, la rúbrica y la validación con usuarios son de ReMar. Ver `docs/CLAUDE.md` para el contexto que recibió el agente.

---

## Estructura del repo

```
practia/
├── README.md              # Este archivo
├── LICENSE                # MIT
├── .env.example           # Variables (nunca el .env real)
├── .gitignore
├── requirements.txt
├── CLAUDE.md              # Contexto para Claude Code
├── app/
│   ├── main.py            # Streamlit app
│   └── components.py
├── ai/
│   ├── prompts/           # System prompts de evaluador y generador
│   ├── cases/             # 10 casos semilla (JSON)
│   ├── rubrics/           # Rúbricas por industria
│   ├── transcribe.py      # Whisper
│   ├── evaluator.py       # LLM con salidas estructuradas
│   ├── case_generator.py  # RAG sobre memorias anuales
│   └── rag_index.py       # Indexado ChromaDB
├── data/                  # Datos públicos de memorias anuales
├── docs/
│   ├── research/          # 3 entrevistas de validación
│   └── architecture/      # Diagrama + 3 capturas
├── scripts/
│   └── transcribe_batch.py  # Procesamiento de audios
└── notebooks/             # Exploración
```

## Cómo correrlo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # agrega tu OPENAI_API_KEY
streamlit run app/main.py
```

## Deploy

[Streamlit Community Cloud](https://streamlit.io/cloud) — conecta este repo, apunta a `app/main.py`, agrega los secretos del `.env` en la UI.

---

*Hecho en Lima, noviembre 2026, para el curso Data Science con Python de UP.*
