# Research — Validación con usuarios

Esta carpeta contiene las **3 conversaciones con usuarios potenciales** que exige el proyecto final (rúbrica: criterio "Problema y usuario", 3 puntos).

## Estado

- [ ] Entrevista 01 — Banca (analista junior BCP / Interbank / Credicorp Capital)
- [ ] Entrevista 02 — FMCG (practicante o analista Alicorp / Belcorp / P&G)
- [ ] Entrevista 03 — Consultoría (analista Apoyo / Deloitte / EY Advisory)

## Flujo

1. **Agendar** → mensaje de WhatsApp en el PDF de guías.
2. **Conducir** → usar el PDF `guia-entrevistas.pdf` (20 min, grabada).
3. **Transcribir** → correr `python scripts/transcribe_batch.py` después de poner el audio en `data/audios/entrevista_XX_industria.m4a`.
4. **Sintetizar** → llenar la plantilla abajo en `entrevista-01.md`, `-02.md`, `-03.md`.

**Importante:** los audios NO van al repo (están en `.gitignore`). Solo las notas sintetizadas.

## Plantilla por entrevista

Copia este contenido a `entrevista-01.md` (y 02, 03) y rellena:

```markdown
# Entrevista 01 — Banca

**Fecha:** 2026-11-XX
**Entrevistado:** [Inicial]
**Empresa actual:** [Empresa]
**Cargo actual:** [Cargo] · [Años en la empresa]
**Práctica inicial:** [Cuándo y dónde]
**Duración:** XX min
**Canal:** Zoom / WhatsApp / presencial

## Perfil en una línea
[Una frase]

## Problema confirmado (con citas literales)
- "..."
- "..."

## Cómo se preparó para su group case
- Horas invertidas: XX
- Materiales: [HBR, Preplounge, YouTube de X, grupo]
- Plata invertida: S/ XX
- Qué le hubiera ahorrado tiempo: "..."

## Casos específicos que mencionó
1. [Empresa] — [tipo] — [duración] — [qué pedían]

## Qué ven ahora desde el otro lado
- Buen vs mal performance: ...
- Red flags: ...

## Objeciones a la idea (cuando la mencioné al final)
- "..."

## Qué cambiaría en mi idea después de esta conversación
- [Insight 1]
- [Insight 2]

## Referidos
- [Nombre] — [contacto]
```
