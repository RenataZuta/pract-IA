# Checklist final — entrega lunes 16 nov, 23:59

Basado en el PDF del proyecto final (`Proyecto_Final_Startup_UP_2026-II.pdf`,
sección 9).

## Obligatorio

- [ ] Repo público en GitHub con el README de 9 secciones.
- [ ] `LICENSE` (MIT) en la raíz.
- [ ] `.env.example` con nombres de variables (sin valores reales).
- [ ] `.gitignore` que incluya `.env` y audios.
- [ ] Demo funcionando: idealmente URL pública en Streamlit Cloud; mínimo,
      corre en laptop con `streamlit run app/main.py`.
- [ ] Video de respaldo de 60-90 segundos con link en el README.
- [ ] Diagrama de arquitectura en `docs/architecture/arquitectura.png`.
- [ ] 3 capturas del flujo principal en `docs/architecture/`.
- [ ] 3 notas de entrevistas en `docs/research/entrevista-{01,02,03}.md`.
- [ ] Sección en el README que diga qué 2+ herramientas del curso están
      dentro del producto (Whisper + RAG) y en qué archivos están.
- [ ] Commits en varios días, no todo el domingo. Mínimo 6 commits en
      días distintos.
- [ ] Revisar con `git log -p` que no hay `api_key`, `secret`, `token`
      pegados en el código.
- [ ] Link del repo en el issue #205 antes del lunes 16 a las 11:59 p.m.
      con la plantilla:
      ```
      Nombre:
      Startup y one-liner:
      Link del demo (URL pública, o "corre en local"):
      Link del repo:
      Herramientas del curso que usa:
      Video de respaldo:
      ```

## Preparación de la presentación (martes 17 y miércoles 18)

- [ ] Ensayo con cronómetro: 3 minutos exactos. El profe corta a los 3:00.
- [ ] Guion del demo (segundos):
      - 0:00–0:30 El problema (quién lo sufre, cuánto le cuesta).
      - 0:30–2:30 Demo en vivo (un flujo completo, de verdad).
      - 2:30–3:00 El negocio (quién paga, cuánto, qué sigue).
- [ ] Preparar laptop con todo cerrado excepto el navegador.
- [ ] Tener la URL pública abierta en una pestaña y el repo en otra.
- [ ] Tener el video de respaldo listo por si cae internet.
- [ ] Conectarse 5 min antes de la hora (7:25 a.m.), con audio y pantalla
      compartida ya probados.

## Rúbrica — en qué pesan los puntos

| Criterio | Puntos | Qué apunto a maximizar |
|---|---|---|
| Demo funcionando | 8 | URL pública en vivo con datos reales → 7-8 pts |
| Problema y usuario | 3 | Las 3 entrevistas transcritas con citas literales |
| Solución e insight | 2 | El insight de "80% del desempeño es individual" |
| Modelo de negocio | 2 | Precio concreto (S/ 29 Pro, S/ 500 Teams) + unit economics |
| Herramientas del curso | 2 | Whisper + RAG explícitos en el código y README |
| Repositorio | 2 | README 9 secciones + commits distribuidos + sin secretos |
| Presentación | 1 | Clara, dentro de 3 min, buenas respuestas en comentarios |
| **Total** | **20** | **Target: 18-20** |
