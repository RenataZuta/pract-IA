# PractIA

> Prep de **group case** y de **entrevista final** por voz para estudiantes peruanos que postulan a su primera o segunda práctica en banca, FMCG y consultoría. Dos módulos: un **simulador de group case** (caso con anexos, cronómetro y rúbrica) y una **entrevista individual con el jefe final** (preguntas reales del proceso peruano). En ambos hablas, y recibes feedback contra una rúbrica en menos de 1 minuto.

**One-liner:** Hacemos simulacros por voz de group case y de entrevista final con el jefe para estudiantes peruanos postulando a programas trainee, con casos y preguntas locales y feedback accionable.

---

## 1. Founder

**Ana Renata "ReMar" Zuta** — estudiante de Economía en Universidad del Pacífico (10.º ciclo, graduación dic. 2026), tercio superior. Analista de Planeamiento Financiero en Lima Expresa (OPEX, control presupuestal). Internship previo en Crece Finanzas Estratégicas (crédito privado, modelado financiero, riesgo SME). Preparando CFA Nivel I.

Postulante activa a programas de prácticas (Interbank, Nexa Resources, Repsol), vive el dolor en primera persona.

## 2. Problema

Los estudiantes peruanos que postulan a programas trainee de banca, FMCG y consultoría enfrentan dos pruebas para las que no pueden prepararse solos:

1. **El group case:** por definición requiere 4–6 personas, caso impreso, cronómetro y un evaluador.
2. **La entrevista final con el jefe:** la ronda individual (1-on-1 en Credicorp Capital, jefe directo en Belcorp, entrevistas conductuales en P&G) mezcla preguntas comportamentales (STAR), técnicas de la industria y de fit con la empresa. Para practicarla hace falta saber qué preguntan de verdad y recibir feedback honesto sobre cómo suena tu respuesta.

Hoy:

- Se juntan en grupos de WhatsApp improvisados que nunca cuadran horarios.
- Pagan Preplounge o sesiones de coaching individual (**S/ 150–500**) que no replican la dinámica grupal ni las preguntas del proceso peruano.
- Usan ChatGPT genérico que no conoce el contexto peruano (marcas Alicorp/Belcorp, régimen MYPE, dinámica del BCP) ni lo que realmente preguntan estas empresas.

**Evidencia:** 3 conversaciones con analistas junior (banca, FMCG, consultoría) que pasaron por el proceso en los últimos 24 meses — en `docs/research/`.

## 3. Solución

**PractIA** es una app web con dos módulos que cubren las dos pruebas donde se define una práctica. Comparten el selector de empresa, la transcripción por voz y el evaluador IA contra rúbrica.

### Módulo 1 — Simulador de group case

1. Elige empresa objetivo (BCP, Alicorp, Apoyo Consultoría, etc.) y tipo de case.
2. Recibe el caso: 1 página de contexto + anexos numéricos (sintéticos pero realistas).
3. Cronómetro con las 3 fases estándar: lectura (15 min) → discusión (20 min) → conclusión (5 min).
4. Resuelve por voz; Whisper transcribe en segundos y puedes corregir el texto antes de evaluar.
5. El evaluador IA puntúa contra una rúbrica por industria con tres tipos de criterio: **técnicos (55 %)**, **habilidades blandas (30 %)** (comunicación y seguridad, colaboración y escucha, priorización) y **aporte propio (15 %)**, que compara tu respuesta con una respuesta de referencia del caso preparada con Claude. Devuelve el puntaje total y por tipo, el comparativo con la referencia (en qué coincidiste, qué aportaste y qué te faltó) y red flags. Las habilidades blandas se estiman por lo que dices y no reemplazan una dinámica grupal real. Se puede descargar en PDF.

### Módulo 2 — Prep de entrevista individual con el jefe final

El **jefe final** es el gerente o jefe del área que cierra el proceso. PractIA lo simula:

1. Elige empresa objetivo, industria y rol (mismo selector que el módulo 1).
2. El jefe final te entrevista con una mezcla de tres tipos de pregunta, tomadas del banco `docs/PractIA_Banco_Preguntas.pdf`: **behavioral (STAR)**, **técnicas de tu industria** y **fit con la empresa**. Las preguntas se muestran en pantalla y, opcionalmente, se leen en voz alta con TTS.
3. Responde por voz; Whisper transcribe.
4. El evaluador IA devuelve feedback por respuesta y global, según el tipo de pregunta:

| Eje | Qué evalúa |
|---|---|
| **Behavioral STAR** | ¿Están las 4 partes (Situación, Tarea, Acción, Resultado)? ¿Arranca con una situación concreta, habla en "yo" y no en "nosotros", y cierra con un resultado medible? ¿Cabe en 60–90 s? |
| **Técnica por industria** | Precisión del concepto o framework (EBITDA, 5Cs, 4Ps, MECE…), uso del contexto peruano y estructura del razonamiento. Banca, FMCG o consultoría según la empresa elegida. |
| **Fit** | Motivación específica (un número, una campaña, un reporte leído) en vez de genérica; conocimiento de la empresa; un diferencial concreto frente a otros postulantes. |

Cada pregunta del banco trae su pista de evaluación (qué busca el entrevistador y qué es red flag: *"esperé a ver qué pasaba"*, *"no he tenido desacuerdos"*, *"soy muy perfeccionista"*), y el evaluador la usa como criterio. El feedback incluye puntaje por eje, fortaleza principal, tres cosas a mejorar, red flags y una respuesta modelo.

**Corpus de preguntas** (75 en total: 60 del banco `docs/PractIA_Banco_Preguntas.pdf` y 15 que salieron de las entrevistas de validación; un JSON por tipo en `ai/questions/`, con `pregunta`, `hint`, `tipo`, `subtema` y `fuente`):

| Archivo | Preguntas | Subtemas |
|---|---|---|
| `behavioral_star.json` | 18 | Liderazgo e iniciativa · Trabajo en equipo y conflicto · Resolución de problemas y presión · Errores y comunicación · Escucha y humildad · Preguntas trampa |
| `fit.json` | 9 | Motivación y fit · Perfil personal · Criterio y argumentación |
| `tecnica_banca.json` | 17 | Fundamentos financieros · Contexto peruano · Casos y razonamiento · Pricing |
| `tecnica_fmcg.json` | 14 | Marca y marketing · Canal y trade · Consumer insight (el banco incluye el caso Marsella vs P&G) |
| `tecnica_consultoria.json` | 17 | Frameworks · Market sizing · Fit y motivación · Econometría y evaluación de impacto |

**Fuentes del corpus:** Glassdoor PE, Indeed PE, blog BCP, Perú Retail, Wharton Consulting Casebook 2025, PrepLounge, Management Consulted y Case in Point (referencia general, sin reproducir contenido), más las 3 entrevistas de validación (`docs/research/`). Detalle completo del banco en [`docs/PractIA_Banco_Preguntas.pdf`](docs/PractIA_Banco_Preguntas.pdf).

## 4. Insight

El mercado asume que practicar group case **requiere grupo**. Pero buena parte de lo que evalúan los reclutadores es el desempeño individual: cómo estructuras, cómo priorizas, cómo comunicas bajo presión. Eso **sí** se puede practicar solo si tienes el caso, el cronómetro y una rúbrica que refleje cómo evalúan las empresas peruanas.

Con la entrevista final pasa lo mismo: no necesitas a otra persona, necesitas **las preguntas reales del proceso peruano**, un lugar donde responder en voz alta y un evaluador que distinga una respuesta STAR de una anécdota sin resultado. Las dos pruebas se practican con la misma lógica: solo, por voz y con feedback contra un criterio explícito.

## 5. Why now

- **Whisper large-v3 sobre Groq** transcribe voz en español en segundos y con capa gratuita, sin tarjeta.
- **LLMs con salidas estructuradas** (modo JSON + validación Pydantic) permiten rúbricas confiables sin reglas rígidas, tanto para un group case como para una respuesta STAR.
- **Hay decenas de miles de estudiantes de pregrado de economía / admin / ing. industrial** en Lima postulando a prácticas cada ciclo *(estimación; por sustentar con datos de SUNEDU)*.

## 6. Demo

- **URL:** *(pendiente de deploy en Streamlit Cloud)*
- **Capturas:** `docs/architecture/` (`captura_01_demo_flujo.png`, `captura_02_feedback_pdf.png`, `captura_03_modo_entrevista.png`)
- **Diagrama:** `docs/architecture/arquitectura.png`

![Arquitectura de PractIA](docs/architecture/arquitectura.png)

Modelos y APIs (todo sobre [Groq](https://console.groq.com), capa gratuita):
- **Whisper large-v3** → transcripción de la voz del estudiante, en ambos módulos.
- **openai/gpt-oss-120b** (modo JSON, configurable con `GROQ_LLM_MODEL`) → evaluador contra rúbrica, con salida validada con Pydantic: rúbricas por industria para el group case; rúbrica STAR + técnica + fit para la entrevista *(por construir)*.
- **RAG ligero** (BM25 en Python puro, `ai/rag.py`) → recupera del corpus (75 preguntas de entrevista con lo que busca el entrevistador y 12 casos con su respuesta de referencia) los fragmentos más parecidos al caso y a tu respuesta, y se los da al evaluador como material de apoyo; el feedback los muestra. *Ampliación por construir:* RAG con memorias anuales (BCP, Alicorp, Credicorp) y ChromaDB (`requirements-rag.txt`).

**Estado (nov. 2026):** *Módulo 1* — flujo de voz conectado (grabación → Whisper → transcripción editable → evaluador → feedback y PDF), evaluación por rúbrica v2 y un RAG ligero que le da material de apoyo al evaluador, probado de punta a punta con la API real de Groq (ver capturas); falta desplegarlo. *Módulo 2* — banco de 75 preguntas en `ai/questions/` y modo de práctica que muestra una pregunta aleatoria por tipo; falta grabar la respuesta y evaluarla (STAR + técnica + fit). Detalle en `CLAUDE.md`.

## 7. Modelo de negocio

| Plan | Precio | Qué incluye |
|---|---|---|
| Free | S/ 0 | 2 sesiones/mes (group case o entrevista), feedback básico |
| Pro | **S/ 29/mes** | Group cases y entrevistas ilimitados, feedback detallado (STAR + técnica + fit), biblioteca por empresa |
| Teams (universidades) | **S/ 500/mes** | 50 usuarios, dashboard del profesor, cases y preguntas personalizados |

**Margen de contribución por usuario Pro:** ~S/ 28/mes (costo API ~S/ 1 con 40 sesiones al mes). Una sesión cuesta ~S/ 0.03 a precios de Groq (gpt-oss-120b: US$ 0.15 / 0.60 por millón de tokens de entrada / salida; Whisper large-v3: US$ 0.111 por hora; tipo de cambio S/ 3.7; respuesta de 3 min y ~6K tokens por evaluación). Estimación sin comisiones de pasarela de pago; la capa gratuita de Groq no sirve para producción y se pasaría al plan Developer.

## 8. Herramientas del curso

Al menos dos del syllabus están dentro del producto (no solo en el desarrollo):

| Herramienta | Sesión | Módulo | Dónde está en el repo |
|---|---|---|---|
| **Whisper (voz a texto)** | 13 | 1 y 2 | `ai/transcribe.py` (Groq) |
| **LLMs con salidas estructuradas + RAG** | 8 | 1 y 2 | `ai/evaluator.py` (M1, Groq) y `ai/rag.py` (RAG ligero, BM25). Por construir: `ai/interviewer.py` y `ai/interview_evaluator.py` (M2), `ai/case_generator.py` y `ai/rag_index.py` (RAG con memorias anuales) |
| **Document AI / OCR** (opcional) | 10 | 1 y 2 | `ai/cv_parser.py` — para personalizar casos y preguntas de entrevista con el CV del estudiante |
| **Texto a voz** (opcional) | 15 | 1 y 2 | `ai/tts.py` — el jefe final formula las preguntas en voz alta y el evaluador "habla" el feedback |

## 9. Qué hizo el agente

El 90% del código fue escrito con Claude Code (Claude Opus 4.7). Las decisiones de producto, la selección de empresas objetivo, la rúbrica y la validación con usuarios son de ReMar. Ver `CLAUDE.md` para el contexto que recibió el agente.

---

## Estructura del repo

Los archivos marcados *(por construir)* aún no existen en el repo.

```
practia/
├── README.md              # Este archivo
├── LICENSE                # MIT
├── .env.example           # Variables (nunca el .env real)
├── .gitignore
├── requirements.txt
├── requirements-rag.txt   # Dependencias del RAG (por construir); aparte para no alargar el deploy
├── CLAUDE.md              # Contexto para Claude Code
├── app/
│   ├── main.py            # Streamlit app (selector de modo: group case / entrevista 1-a-1)
│   ├── pdf_export.py      # Feedback a PDF (reportlab)
│   └── components.py      # (por construir)
├── ai/
│   ├── prompts/           # System prompt del evaluador de group case; jefe final y evaluador de entrevista (por construir)
│   ├── cases/             # 12 casos semilla (JSON, 4 por industria) — Módulo 1
│   ├── questions/         # Banco de 75 preguntas (JSON, uno por tipo) — Módulo 2
│   ├── rubrics/           # Rúbricas por industria (M1); rúbrica de entrevista STAR + fit (por construir, M2)
│   ├── transcribe.py      # Whisper large-v3 (Groq) — ambos módulos
│   ├── evaluator.py       # LLM de Groq en modo JSON + Pydantic — evaluador de group case (M1)
│   ├── interviewer.py     # (por construir) Jefe final: arma y conduce la entrevista (M2)
│   ├── interview_evaluator.py  # (por construir) Feedback STAR + técnica + fit (M2)
│   ├── rag.py             # RAG ligero: recuperación BM25 sobre preguntas y casos (lo usa el evaluador)
│   ├── case_generator.py  # (por construir) RAG sobre memorias anuales
│   └── rag_index.py       # (por construir) Indexado ChromaDB
├── data/                  # Datos públicos de memorias anuales
├── docs/
│   ├── PractIA_Banco_Preguntas.pdf   # Fuente del corpus de preguntas (M2)
│   ├── PractIA_Guia_Entrevistas.pdf  # Guía de las 3 entrevistas de validación
│   ├── research/          # 3 entrevistas de validación
│   └── architecture/      # Diagrama + capturas del flujo
└── scripts/
    └── transcribe_batch.py  # Procesamiento de audios
```

## Cómo correrlo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # agrega tu GROQ_API_KEY (gratis en https://console.groq.com)
streamlit run app/main.py
```

## Deploy

[Streamlit Community Cloud](https://streamlit.io/cloud) — conecta este repo, apunta a `app/main.py`, elige Python 3.11 y agrega `GROQ_API_KEY` en Settings → Secrets.

---

*Hecho en Lima, noviembre 2026, para el curso Data Science con Python de UP.*
