# Plan de entrega — PractIA

Fechas del curso (PDF `Proyecto_Final_Startup_UP_2026-II`): link en el issue #205 hasta el **lunes 16-nov 23:59**; presentación **miércoles 18-nov, turno #15, 7:50 AM** (conectarse a las 7:25). Turno de 5 min: 3 de demo en vivo + 2 de comentarios; a los 3:00 se corta.

- **Demo:** https://practia-up.streamlit.app/
- **Repo:** https://github.com/RenataZuta/pract-IA

---

## 1. Qué verificar en la app (checklist del demo, 8 de 20 puntos)

### A. Antes de abrirla (panel de Streamlit Cloud → *Manage app*)
- [ ] Python **3.11** (con 3.14 falla el build) y el build termina sin "Error installing requirements".
- [ ] *Settings → Secrets* tiene `GROQ_API_KEY = "gsk_..."` (con comillas). La key va solo ahí, nunca en el repo.
- [ ] *Logs* sin errores rojos al cargar.
- [ ] La app es **pública**: ábrela en una ventana de incógnito, sin sesión de GitHub ni de Streamlit.

### B. Flujo completo (con micrófono real: es lo único que nunca se ha probado)
- [ ] Los 3 selectores cargan; abre al menos un caso por industria (banca, FMCG, consultoría) y confirma que los anexos se ven como tablas.
- [ ] Cronómetro: *Iniciar* corre solo, cambia de fase y avisa al excederte.
- [ ] **Grabar con el micrófono:** el navegador pide permiso, la grabación se detiene a los 3 s de silencio, y la **transcripción aparece** en el cuadro editable (no queda vacía). Habla 45–60 s.
- [ ] Plan B del micrófono: subir un audio (`.wav`/`.m4a`) por el expander "¿No funciona el micrófono?". Ten un audio de respuesta listo en la laptop.
- [ ] *Evaluar respuesta*: responde en menos de ~30 s, sin error 429. Muestra puntaje total, los 3 subtotales (técnico / blandas / aporte propio), el comparativo con la referencia y "Material recuperado por RAG".
- [ ] *Descargar feedback como PDF*: el archivo abre y las tildes y la ñ se leen bien.
- [ ] Guion final (espera ~1 min después de evaluar por el límite de tokens) y su PDF.
- [ ] "Entrena tu punto más débil" y el historial en un 2.º intento.
- [ ] Modo *Entrevista 1-a-1*: muestra pregunta y pista del entrevistador.

### C. Rendimiento y límites de Groq (plan gratuito: 8K tokens/min)
- [ ] **Arranque en frío:** deja la app sin visitas 15+ min, ábrela y mide cuánto tarda. El día del turno ábrela a las 7:25 y haz una evaluación de calentamiento.
- [ ] Solo cabe **una evaluación por minuto**. En el turno: una sola evaluación, sin repetir y sin pedir el guion antes de que pase 1 min.
- [ ] Revisa en console.groq.com el uso del día y que la key no esté agotada.

### D. Ambiente de la presentación
- [ ] Prueba compartir pantalla **y audio** en la clase virtual (con un compañero). El audio del navegador no sale por defecto en todas las plataformas.
- [ ] Un solo navegador, pestañas cerradas excepto: app, repo y video. Notificaciones apagadas. Zoom del navegador 100–110 %.
- [ ] Plan B local listo: `streamlit run app/main.py` con `.env` configurado, y el video de respaldo abierto en otra pestaña.
- [ ] Prueba con **2 personas** distintas (una desde el celular) y anota qué falló.

### E. Seguridad y datos
- [ ] La key no aparece en la UI, en el PDF ni en los logs.
- [ ] `git log -p | grep -iE "gsk_|api_key|secret|token"` no devuelve claves reales (ya se revisó el 12-nov: limpio).
- [ ] Rotar las dos keys de Groq **después** del miércoles 18 (quedaron expuestas en un chat).

---

## 2. Borrador del comentario para el issue #205

Se publica en el issue #205 del repo del curso (`d2cml-ai/Data-Science-Python`) desde tu cuenta de GitHub. Usa la plantilla del PDF tal cual; vale para los dos días de presentación. Reemplaza el video antes de publicar.

```
Nombre: Ana Renata Zuta Luyo

Startup y one-liner: PractIA — Hacemos simulacros de group case y de entrevista final para estudiantes peruanos que postulan a prácticas y programas trainee, mediante voz (Whisper) y un evaluador con rúbrica (LLM con salida estructurada + RAG) sobre casos y preguntas del proceso peruano.

Link del demo (URL pública, o "corre en local"): https://practia-up.streamlit.app/

Link del repo: https://github.com/RenataZuta/pract-IA

Herramientas del curso que usa:
- Whisper large-v3 (sesión 13): ai/transcribe.py
- LLM con salidas estructuradas (sesión 8): ai/evaluator.py, ai/guion.py
- RAG (sesión 8): ai/rag.py

Video de respaldo: <PEGA AQUÍ EL LINK DEL VIDEO DE 60–90 s>
```

Notas: el PDF permite seguir haciendo commits hasta la presentación, pero **el link debe estar antes del lunes 16 a las 23:59**. Si aún no grabaste el video, publica con el resto y edita tu comentario cuando lo tengas (antes de esa hora). Antes de publicar, abre el repo en una ventana de incógnito y confirma que es público y que el README se ve bien.

---

## 3. Plan de commits por día

Reglas: un commit por tarea, mensaje en español (`feat:` `fix:` `docs:` `test:` `chore:`), push a `origin/main` después de cada uno, nada de `git add -A`. Meta: al menos un commit cada día, del 10 al 16-nov (7 días distintos).

### Jue 12-nov — HECHO
- `384710b` fix: corrijo incongruencias entre anexos y respuestas de referencia en 8 casos
- `0b800b0` docs: ajusto el README a la rúbrica de repositorio y de problema
- `7376356` docs: actualizo CLAUDE.md tras la auditoría de cifras de los casos
- docs: agrego el plan de entrega, el borrador del issue y el prompt diario (este archivo)

### Vie 13-nov — demo robusto y pruebas
1. `fix: mensajes claros ante el límite de tasa de Groq (429) y la falta de GROQ_API_KEY` — `ai/evaluator.py`, `app/main.py`. Criterio: en vez de un traceback, la UI dice "espera ~1 minuto" o "falta la clave".
2. `feat: botón "Usar respuesta de ejemplo" como plan B del micrófono` — `app/main.py`. Carga una respuesta de ejemplo en la caja de transcripción, rotulada como ejemplo. Criterio: el flujo evalúa sin micrófono.
3. `test: pruebas del total, del RAG y de la consistencia de los casos` — `tests/` y `requirements-dev.txt` (pytest fuera de `requirements.txt`). Criterio: `pytest` pasa; incluye que el patrimonio de `banca_01` cuadre, que el payback de `consultoria_02` salga de CAPEX y margen, y que cada caso tenga los campos obligatorios.
4. `docs: marco en CHECKLIST_ENTREGA.md lo ya hecho` — `docs/CHECKLIST_ENTREGA.md`.

### Sáb 14-nov — producto y evidencia
1. **Opcional (3–4 h, con tope a las 14:00):** `feat: el módulo 2 graba y evalúa la respuesta (STAR + técnica + fit)` — `ai/interview_evaluator.py`, `ai/prompts/interview_system.md`, `ai/rubrics/entrevista.json`, `app/main.py`. Si no está funcionando a la hora tope, no se sube y se hace el punto 1b.
   - 1b. `docs: dejo el módulo 2 como roadmap en el README, sin promesas` — ajustar README sección 3 y 6.
2. `docs: guion del demo de 3 minutos con tiempos y plan B` — `docs/GUION_DEMO.md`: 0:00–0:30 problema, 0:30–2:30 demo (qué caso, qué clics, qué decir), 2:30–3:00 negocio.
3. `docs: completo fecha y canal de las 3 entrevistas y confirmo "AJE"` — **lo edita ReMar** en `docs/research/` (CLAUDE.md la reserva para ella); también marcar las casillas de `docs/research/README.md`.

### Dom 15-nov — despliegue final y pruebas con 2 personas
1. `fix: <qué falló>` — un commit por cada falla que encuentren las 2 personas.
2. `docs: actualizo las capturas con la interfaz final` — `docs/architecture/captura_0{1,2,3}_*.png` (las actuales son de antes del tema por empresa).
3. `docs: agrego la foto del founder` — guardar `docs/founder.jpg` y descomentar la línea en README sección 1.
4. `chore: congelo versiones y reviso .env.example, .gitignore y secretos` — correr `git log -p | grep -iE "gsk_|api_key|secret|token"`.

### Lun 16-nov — cierre
1. `docs: agrego el link del video de respaldo en el README` — sección 6.
2. `docs: README final` — releer contra el checklist del PDF (sección 9 del PDF).
3. Publicar el comentario en el issue #205 (no es un commit). **Antes de las 23:59.**

---

## 4. Prompt para ejecutar cada día en Claude Code

Pégalo al abrir Claude Code en `~/Downloads/practia`. Cambia solo la fecha.

```
Lee CLAUDE.md y docs/PLAN_ENTREGA.md. Hoy es <FECHA, p. ej. vie 13-nov-2026>.

Ejecuta SOLO el bloque "Plan de commits por día" de esa fecha, en orden, una tarea a la vez:
1. Antes de empezar: git pull, git status y git log --oneline -5. Dime si hay algo sin commitear.
2. Por cada tarea: haz el cambio, verifícalo (python -m compileall ., pytest si existe, y que cada JSON de ai/ cargue) y, si toca la app, pruébala; luego haz UN commit con el mensaje en español del plan y git push origin main.
3. Antes de cada commit: git diff --staged, y busca claves (gsk_, api_key, secret, token). Agrega archivos por nombre, nunca git add -A.
4. Si una tarea es opcional y no está lista para su hora tope, no la subas: haz su alternativa del plan.

Reglas: no cambies el stack (Streamlit + Groq); no escribas, imprimas ni guardes ninguna API key; no toques docs/research/ (dime qué cambiar y lo hago yo); no toques mis archivos Excel; no hagas force push ni reescribas historia; si algo te bloquea o falla dos veces, para y cuéntame en vez de insistir.

Al terminar dime: qué commits hiciste (hash y mensaje), qué quedó pendiente del día y qué debo probar yo a mano (por ejemplo, el micrófono real o el deploy en la nube).
```
