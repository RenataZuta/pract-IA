# Agente verificador de casos

Audita un caso de PractIA y deja un informe **con fuentes**: comprueba que las cuentas de los anexos cuadren con lo que dicen la pista y la respuesta de referencia, y verifica con la web los hechos del mundo real (a qué empresa pertenece una marca, fechas, existencia de productos). Nació de un problema real: el 12-nov se corrigieron 10 incongruencias en 8 casos a mano (commit `384710b`), entre ellas dos marcas que no eran de quien el caso decía.

El agente **propone y nunca edita**: toda corrección la decide una persona.

## Cómo funciona

```
caso (JSON)
   │
   ▼
1. EXTRAER (LLM, JSON)  ── "¿qué se puede comprobar?" ──► chequeos numéricos + hechos del mundo real
   │                         no juzga ni calcula                │                    │
   ▼                                                            ▼                    ▼
2. CALCULAR (código)    ◄── fórmula + celdas de las tablas ─────┘                    │
   intérprete aritmético seguro (sin eval)                                           │
   guardarraíles: citas y números deben existir en el caso                           │
   ▼                                                                                 ▼
   ok · discrepancia · no_evaluable · descartado                  3. VERIFICAR (LLM + búsqueda web de Groq)
                                                                     a) investigar → informe en prosa
                                                                     b) estructurar → JSON
                                                                     c) GUARDARRAÍLES EN CÓDIGO:
                                                                        la URL debe haberse consultado de verdad
                                                                        y la cita debe estar en la página abierta
                                                                     confirmado · contradicho · no_verificable
   ▼
4. INFORME  ai/audits/<caso>.json (lo lee la app)  +  <caso>.md (para leer)
```

Archivos (`ai/verifier/`, un archivo = una responsabilidad): `tablas.py` (lee anexos), `calculo.py` (cuentas), `citas.py` y `fuentes.py` (guardarraíles), `llm.py` (Groq, ritmo de tokens), `extraccion.py`, `busqueda.py`, `agente.py` (orquesta), `informe.py`. Prompts en `ai/prompts/verificador_*.md`. La app muestra la ficha en `app/verificacion_view.py` (solo lee el informe, no gasta tokens).

## Decisiones de diseño

| Decisión | Por qué |
|---|---|
| **El LLM propone, el código calcula** | Los modelos se equivocan en aritmética. El LLM solo dice *qué* comparar (celdas + fórmula); `calculo.py` evalúa con un intérprete que solo admite `+ - * / **`, paréntesis y `abs/min/max/round`. |
| **Sin cita verificada no hay veredicto** | La búsqueda de Groq devuelve en `executed_tools` todo lo que consultó. Una fuente solo cuenta si su URL está ahí y su cita textual aparece en una página **abierta**; si no, el veredicto baja a `no_verificable`. Lo impone el código, no el prompt. |
| **Ningún número inventado** | Cada número que el modelo cita debe existir en el caso junto a las palabras de su cita (salvo constantes universales: 12 meses, 100 %…). Si no, el chequeo se descarta y se reporta. |
| **Investigar en prosa y estructurar en un 2.º paso** | Con `tool_choice="required"` el modelo intenta devolver su JSON como si fuera una herramienta llamada `json` y Groq responde 400. Se separó: paso 1 con búsqueda (texto), paso 2 sin herramientas (JSON). |
| **Offline, con informes guardados** | Verificar un hecho cuesta ~9K tokens y el plan gratuito da 8K por minuto: en vivo no cabe. Se corre antes, se guarda el informe y la app solo lo muestra. |
| **Ritmo de tokens y caché** | `llm.py` espera lo justo para no pasar de 8K tokens/min; los hechos y las extracciones ya pagadas se guardan en `ai/audits/.cache/` (ignorada por git). La caché valida la forma de lo que sirve: una vez se guardó una respuesta mala y volvió a fallar; ahora hay una prueba que lo cubre. |
| **Solo lectura, páginas = datos** | El agente no puede escribir ni enviar nada. Lo que dicen las páginas web se trata como información, nunca como instrucciones, y cualquier salida pasa por validación (Pydantic) y guardarraíles. |
| **Bucle propio, no crewAI** | La sesión 11 del curso usa crewAI. **No lo probé aquí.** Elegí un bucle propio para poder explicar cada línea, para no sumar dependencias pesadas al deploy gratuito (el repo fija `groq==0.11.0` y `httpx==0.27.2`; no medí si chocarían) y porque lo importante —las barandillas— no depende del framework. |

## Cómo usarlo

Necesita `GROQ_API_KEY` en `.env`. Cada comando gasta tokens de tu cuota (**200K por día** en `gpt-oss-120b`, plan gratuito).

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m scripts.auditar hecho "Cocinero es una marca de Alicorp"          # ~9K tokens, ~1 min
python -m scripts.auditar caso ai/cases/fmcg_04_pricing.json --sin-web      # solo cuentas, ~7K tokens
python -m scripts.auditar caso ai/cases/fmcg_04_pricing.json --max-hechos 1 # cuentas + 1 hecho con web, ~16K tokens
python -m scripts.auditar texto README.md --seccion "## 7. Modelo de negocio"
python -m scripts.auditar evaluar-agente --sin-web                          # mide al agente contra defectos conocidos
pytest                                                                      # 78 pruebas, sin red ni API
```

Cada llamada al modelo pesa ~6–9K tokens y el ritmo es de una por minuto: un caso con 3 hechos tarda unos 4–5 minutos.

## Qué se midió (y qué no)

Conjunto de prueba: las versiones de 4 casos **anteriores** al commit `384710b` (`tests/fixtures/casos_con_defectos/`, con la lista de defectos reales en `esperados.json`).

| Prueba | Resultado |
|---|---|
| **Motor determinista** (tests): detecta el patrimonio incoherente de `banca_01`, el payback de `consultoria_02` y el break-even de `fmcg_01` cuando se le da el chequeo, y rechaza citas inventadas, números ajenos, fórmulas peligrosas y diferencias de unidades | ✅ 3 de 3, 78 pruebas pasan |
| **Verificación web aislada**: «Cocinero es una marca local e independiente, no de Alicorp» | ✅ `contradicho`, con 2 citas verificadas de `alicorp.com.pe` (la fuente primaria) |
| **Agente completo, extracción por LLM** sobre los 3 defectos numéricos | ❌ **0 de 3** en la última corrida. El modelo casi nunca *propone* las relaciones sutiles; cuando propone un chequeo, el código lo evalúa bien |
| Hallazgos reales del agente en casos | `banca_01`: 110.9 días de inventario frente a «110»; el resto de cuentas de `fmcg_04` (11) cuadran |

Cómo leer esto con honestidad:

- **La parte confiable es la verificación** (guardarraíles, cálculo, citas). **La parte débil es la recuperación**: qué decide revisar el LLM varía entre corridas: para el mismo caso (`fmcg_01`) propuso 11, 3, 2 y 8 chequeos en cuatro corridas.
- Una versión anterior del marcador contaba como «detectado» cualquier discrepancia y daba 2 de 5; era engañoso (eran falsos positivos de signo). Ahora un hallazgo solo cuenta si menciona el defecto real.
- **Contaminación:** las relaciones que nombra el prompt (break-even, payback, patrimonio) las escribí sabiendo estos defectos. La cifra sobre este conjunto es optimista y aun así es baja.
- La muestra es muy pequeña (4 casos, pocas corridas): no es una estimación estadística.
- Falsos positivos que aparecieron y se corrigieron: signo de gastos entre paréntesis, «~S/ 3M» comparado a nivel de soles, chequeos tautológicos («lecturas» de una celda).

## Límites

- «Cita verificada» significa que la cita **existe en la página abierta**, no que **demuestre** el veredicto. La prueba de Cocinero usa una página de términos de una promoción: es evidencia indirecta. Una persona debe leer la cita.
- Las cifras de los anexos son sintéticas: solo se verifica su coherencia interna y los hechos reales.
- El modelo elige qué comprobar: un informe sin hallazgos no garantiza un caso sin errores.
- La búsqueda de Groq depende de lo que devuelva su motor; una página puede estar desactualizada.

## Próximos pasos (en orden de valor)

1. Dos pasadas de extracción y unir los chequeos (aumenta la recuperación; duplica el costo en tokens).
2. Chequeos estructurales deterministas sin LLM (totales = suma de componentes, balance, filas «% margen» recalculables).
3. Más casos con defectos conocidos y un conjunto aparte para no ajustar el prompt sobre lo que se mide.
4. Un modelo de pago o con más contexto para la extracción.

## Si el profe pregunta

- **¿Qué hace el agente y qué hace el código?** El LLM decide qué mirar y redacta el informe; el código calcula, valida y verifica las fuentes.
- **¿Cómo evitas alucinaciones?** No confío en el modelo: sus números deben existir en el caso, sus URLs deben haberse consultado y sus citas deben estar en una página abierta; si no, el veredicto baja a `no_verificable`.
- **¿Por qué no corre en vivo?** Cada verificación cuesta ~9K tokens y el límite gratuito es 8K por minuto; por eso se corre antes y la app muestra el informe.
- **¿Qué no hace?** No corrige casos, no garantiza ausencia de errores y no demuestra que una cita implique el veredicto.
- **¿Lo mediste?** Sí, y la recuperación del LLM es baja (0 de 3 en la última corrida); el motor determinista sí detecta los 3 defectos cuando se le da el chequeo.
