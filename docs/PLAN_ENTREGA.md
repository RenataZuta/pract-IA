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
- LLM con salidas estructuradas (sesión 8): ai/evaluator.py, ai/interview_evaluator.py, ai/guion.py
- RAG (sesión 8): ai/rag.py
(Además, para auditar los casos: un agente verificador con el patrón de la sesión 11, sin crewAI: ai/verifier/)

Video de respaldo: <PEGA AQUÍ EL LINK DEL VIDEO, o escribe: "lo agrego en este mismo comentario antes del lunes 16, 11:59 p. m.">
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
- feat: agente verificador de casos (cuentas por código, hechos con fuentes verificadas) + ficha en la app + 78 pruebas
- **Esta noche (cuota de Groq repuesta ~19:00 hora de Lima):** `python -m scripts.auditar caso ai/cases/fmcg_04_pricing.json --max-hechos 1 --sin-cache`, leer el informe y commitear `ai/audits/` con `docs: agrego informes de verificación de los casos`

### Vie 13-nov — demo robusto y pruebas: ✅ ADELANTADO el 12-nov
- ✅ `fix: mensajes claros ante el límite de Groq (429), la key inválida y la falta de key`
- ✅ `feat: botón "Usar la respuesta de referencia como ejemplo" como plan B del micrófono`
- ✅ `test: pruebas del evaluador, del RAG y de la coherencia de los 12 casos` (141 pruebas en total)
- ✅ Checklist marcado (`docs/CHECKLIST_ENTREGA.md`)
- **Lo que sí toca el 13 (tuyo):** probar el **micrófono real** en la app pública (es lo único que nunca se ha probado) y anotar qué falla.

### Sáb 14-nov — producto y evidencia: ✅ ADELANTADO el 12-nov
- ✅ `feat: el módulo 2 graba o recibe tu respuesta y la evalúa` (probado con la API real; la duración la mide el código)
- ✅ Guion del demo de 3 minutos (personal, fuera del repo)
- **Lo que sí toca el 14 (tuyo):** ensayar el guion con cronómetro y compartiendo pantalla; completar fecha y canal de las 3 entrevistas y confirmar «AJE» (`docs/research/`, tuyo).

### Dom 15-nov — despliegue final y pruebas con 2 personas
- ✅ `docs: actualizo las capturas con la interfaz final` · ✅ revisión de secretos del historial completo (limpio)
- **Pendiente real (necesita personas):** que **2 personas prueben la URL pública** (una desde el celular), anotar qué falló y arreglarlo (`fix: <qué falló>`, un commit por falla).
- **Pendiente tuyo:** guardar `docs/founder.jpg` y descomentar la línea del README (sección 1) → `docs: agrego la foto del founder`.

### Lun 16-nov — cierre
1. `docs: agrego el link del video de respaldo en el README` — sección 6 (grabarlo es tuyo).
2. `docs: README final` — releer contra el checklist del PDF (sección 9 del PDF).
3. Publicar el comentario en el issue #205 (no es un commit). **Antes de las 23:59.**

> Nota sobre las fechas: lo adelantado el 12-nov quedó fechado el 12-nov. Los commits no se fechan en días que no han llegado: la rúbrica pide commits en varios días y el historial muestra la fecha real. Ya hay 3 días reales (10, 11, 12) y los días 13–16 tendrán commits genuinos con lo que solo puedes hacer tú.

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
