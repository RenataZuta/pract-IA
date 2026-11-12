"""Orquestador: extraer qué comprobar -> calcular con código -> verificar hechos con fuentes -> informe."""
from __future__ import annotations

from datetime import date

from loguru import logger

from ai.verifier.busqueda import verificar_hecho
from ai.verifier.calculo import evaluar_chequeo
from ai.verifier.citas import cita_en_texto
from ai.verifier.extraccion import extraer, texto_de_afirmaciones, texto_del_caso
from ai.verifier.llm import LlmVerificador
from ai.verifier.modelos import Informe
from ai.verifier.tablas import parsear_tablas

LIMITACIONES = [
    "El agente propone y no edita: toda corrección la decide una persona.",
    "Un chequeo «ok» prueba coherencia aritmética, no que el supuesto del caso sea realista.",
    "Las cifras de los anexos son sintéticas: solo se verifican hechos del mundo real y la coherencia interna.",
    "«No verificable» no significa falso: significa que no hubo una cita textual en una página abierta.",
    "Las fuentes son las que devuelve la búsqueda de Groq; una página puede estar desactualizada.",
    "El modelo elige qué comprobar y puede omitir cosas: el informe no garantiza que el caso esté libre de errores.",
]


def auditar_caso(case: dict, *, con_web: bool = True, max_hechos: int = 3, llm: LlmVerificador | None = None,
                 usar_cache: bool = True) -> Informe:
    """Audita un caso (dict con el formato de ai/cases/*.json) y devuelve un Informe con fuentes."""
    llm = llm or LlmVerificador()
    tablas = parsear_tablas(case)
    texto = texto_del_caso(case)

    chequeos, hechos, descartados = extraer(case, tablas, llm, usar_cache=usar_cache)
    logger.info("{}: {} chequeos y {} hechos propuestos", case["id"], len(chequeos), len(hechos))
    afirmaciones = texto_de_afirmaciones(case)
    resultados = [evaluar_chequeo(c, tablas, texto, afirmaciones) for c in chequeos]

    veredictos = []
    if con_web:
        contexto = f"Caso de práctica «{case['title']}» sobre {case['company']}."
        for h in hechos[:max_hechos]:
            if h.cita_caso and not cita_en_texto(h.cita_caso, texto):
                descartados.append(f"hecho {h.id}: su cita no aparece en el caso")
                continue
            veredictos.append(verificar_hecho(h, contexto, llm, usar_cache=usar_cache))

    resumen = {
        "chequeos_ok": sum(r.estado == "ok" for r in resultados),
        "discrepancias": sum(r.estado == "discrepancia" for r in resultados),
        "no_evaluables": sum(r.estado == "no_evaluable" for r in resultados),
        "chequeos_descartados": sum(r.estado == "descartado" for r in resultados),
        "hechos_confirmados": sum(v.veredicto == "confirmado" for v in veredictos),
        "hechos_contradichos": sum(v.veredicto == "contradicho" for v in veredictos),
        "hechos_no_verificables": sum(v.veredicto == "no_verificable" for v in veredictos),
    }
    revisar = resumen["discrepancias"] or resumen["hechos_contradichos"]
    return Informe(
        caso_id=case["id"], titulo=case["title"], generado=date.today().isoformat(), modelo=llm.modelo,
        veredicto_global="revisar" if revisar else "sin_hallazgos", resumen=resumen,
        chequeos=resultados, hechos=veredictos, descartados=descartados,
        limitaciones=LIMITACIONES if con_web else LIMITACIONES + ["Esta corrida fue sin web: no se verificaron hechos del mundo real."],
    )


def auditar_texto(texto: str, nombre: str, *, con_web: bool = True, max_hechos: int = 3,
                  llm: LlmVerificador | None = None, usar_cache: bool = True) -> Informe:
    """Audita un texto libre (p. ej. una sección del README): sus cuentas y sus hechos reales."""
    pseudo_caso = {"id": nombre, "title": nombre, "company": "PractIA", "industry": "", "context": texto,
                   "prompt": "Audita este texto.", "exhibits": []}
    return auditar_caso(pseudo_caso, con_web=con_web, max_hechos=max_hechos, llm=llm, usar_cache=usar_cache)
