# Plan de entrega — PractIA

- **Demo:** https://practia-up.streamlit.app/
- **Repo:** https://github.com/RenataZuta/pract-IA

---

## 1. Qué verificar en la app (checklist del demo, 8 de 20 puntos)

### A. Antes de abrirla (panel de Streamlit Cloud → *Manage app*)
- [ ] Python **3.11** (con 3.14 falla el build) y el build termina sin "Error installing requirements".
- [ ] *Settings → Secrets* tiene `GROQ_API_KEY = "gsk_..."` (con comillas). La key va solo ahí, nunca en el repo.
- [ ] *Logs* sin errores rojos al cargar.
- [ ] La app es **pública**: ábrela en una ventana de incógnito, sin sesión de GitHub ni de Streamlit.

### B. Flujo completo (con micrófono real)
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
- [ ] **Arranque en frío:** deja la app sin visitas 15+ min, ábrela y mide cuánto tarda. 
- [ ] Solo cabe **una evaluación por minuto**. En el turno: una sola evaluación y sin repetir.
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
