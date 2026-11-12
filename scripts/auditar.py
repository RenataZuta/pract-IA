"""
Agente verificador: audita casos (o un texto) y deja un informe con fuentes.

Uso (desde la raíz del repo, con GROQ_API_KEY en .env):

    python -m scripts.auditar caso ai/cases/fmcg_01_lanzamiento_sku.json
    python -m scripts.auditar caso ai/cases/banca_01_credito_pyme.json --sin-web      # solo cuentas, sin gastar tokens de búsqueda
    python -m scripts.auditar texto README.md --seccion "## 7. Modelo de negocio"
    python -m scripts.auditar hecho "Cocinero es una marca de Alicorp"                  # verifica una afirmación con fuentes
    python -m scripts.auditar evaluar-agente                                           # mide al agente contra defectos conocidos

Cada verificación de un hecho gasta ~7K tokens de los 8K por minuto del plan gratuito de Groq:
el agente espera entre llamadas, así que un caso con 3 hechos tarda unos 3-4 minutos.
Guarda ai/audits/<id>.json (lo lee la app) y ai/audits/<id>.md (para leer).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.verifier import auditar_caso, auditar_texto  # noqa: E402
from ai.verifier.informe import AUDITS_DIR, guardar  # noqa: E402
from ai.verifier.llm import LlmVerificador, VerificadorError  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "casos_con_defectos"


def _seccion(texto: str, encabezado: str) -> str:
    """El texto de una sección de markdown: desde su encabezado hasta el siguiente del mismo nivel."""
    lineas = texto.splitlines()
    inicio = next((i for i, l in enumerate(lineas) if l.strip().startswith(encabezado.strip())), None)
    if inicio is None:
        raise SystemExit(f"No encontré la sección «{encabezado}»")
    nivel = len(encabezado) - len(encabezado.lstrip("#"))
    fin = next((j for j in range(inicio + 1, len(lineas))
                if lineas[j].startswith("#") and len(lineas[j]) - len(lineas[j].lstrip("#")) <= nivel), len(lineas))
    return "\n".join(lineas[inicio:fin])


def _imprimir(informe, rutas=None) -> None:
    r = informe.resumen
    print(f"\n== {informe.caso_id}: {informe.veredicto_global.upper()} ==")
    print(f"cuentas ok {r['chequeos_ok']} · discrepancias {r['discrepancias']} · no evaluables {r['no_evaluables']} · "
          f"descartadas {r['chequeos_descartados']}")
    print(f"hechos: confirmados {r['hechos_confirmados']} · contradichos {r['hechos_contradichos']} · "
          f"no verificables {r['hechos_no_verificables']}")
    for c in informe.chequeos:
        if c.estado == "discrepancia":
            print(f"  ⚠️  [{c.severidad}] {c.descripcion}: calculado {c.calculado:,.4g} vs afirmado {c.afirmado:,.4g}")
    for h in informe.hechos:
        print(f"  {h.veredicto.upper():15} {h.afirmacion}")
        for f in h.fuentes:
            print(f"      {'✓' if f.cita_verificada else '✗'} {f.url}")
    if rutas:
        print("informe:", ", ".join(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p) for p in rutas))


def _detectado(informe, defecto: dict) -> bool:
    """Un hallazgo solo cuenta si habla del defecto real (palabras clave), no por haber marcado cualquier cosa."""
    claves = [k.lower() for k in defecto.get("palabras_clave", [])]
    if defecto["tipo"] == "numerico":
        textos = [f"{c.descripcion} {c.formula} {c.detalle}" for c in informe.chequeos if c.estado == "discrepancia"]
    else:
        textos = [f"{h.afirmacion} {h.resumen} {h.correccion_sugerida or ''}" for h in informe.hechos if h.veredicto == "contradicho"]
    return any(k in texto.lower() for texto in textos for k in claves)


def _evaluar_agente(args, llm) -> None:
    """Corre el agente sobre los casos con defectos conocidos y cuenta cuántos defectos reales detecta."""
    esperados = json.loads((FIXTURES / "esperados.json").read_text(encoding="utf-8"))
    esperados.pop("descripcion", None)
    filas = []
    for archivo, defectos in esperados.items():
        if args.solo and not any(s in archivo for s in args.solo):
            continue
        caso = json.loads((FIXTURES / archivo).read_text(encoding="utf-8"))
        informe = auditar_caso(caso, con_web=not args.sin_web, max_hechos=args.max_hechos, llm=llm, usar_cache=not args.sin_cache)
        guardar(informe, Path(args.salida))
        _imprimir(informe)
        for d in defectos:
            if args.sin_web and d["tipo"] == "hecho_real":
                continue  # sin web no se pueden verificar hechos del mundo real
            filas.append((caso["id"], d["tipo"], d["descripcion"], _detectado(informe, d)))
    detectados = sum(f[3] for f in filas)
    print(f"\nDefectos conocidos detectados: {detectados} de {len(filas)} (un hallazgo cuenta solo si menciona el defecto real)")
    for caso_id, tipo, desc, ok in filas:
        print(f"  {'✓' if ok else '✗'} {caso_id} [{tipo}] {desc}")


def _verificar_un_hecho(args, llm) -> None:
    """Verifica una afirmación suelta con la web y muestra el veredicto con sus fuentes."""
    from ai.verifier.busqueda import verificar_hecho
    from ai.verifier.modelos import HechoReal

    hecho = HechoReal(id="h1", afirmacion=args.afirmacion, tipo="otro", cita_caso=args.afirmacion)
    v = verificar_hecho(hecho, args.contexto, llm, usar_cache=not args.sin_cache)
    print(f"\n{v.veredicto.upper()}: {v.afirmacion}\n{v.resumen}")
    if v.correccion_sugerida:
        print("Corrección sugerida:", v.correccion_sugerida)
    for f in v.fuentes:
        print(f"  {'✓' if f.cita_verificada else '✗'} {f.url}\n      «{f.cita}»")
    if v.nota:
        print("Nota:", v.nota)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--sin-web", action="store_true", help="solo cuentas; no verifica hechos del mundo real")
    comunes.add_argument("--max-hechos", type=int, default=3, help="máximo de hechos a verificar con la web (~7K tokens c/u)")
    comunes.add_argument("--sin-cache", action="store_true", help="ignora la caché de hechos ya verificados")
    comunes.add_argument("--salida", default=str(AUDITS_DIR), help="carpeta de los informes (por defecto ai/audits)")
    p = sub.add_parser("caso", parents=[comunes], help="audita un caso JSON")
    p.add_argument("ruta")
    p = sub.add_parser("texto", parents=[comunes], help="audita un texto o una sección de un .md")
    p.add_argument("ruta")
    p.add_argument("--seccion", help='encabezado exacto, p. ej. "## 7. Modelo de negocio"')
    p = sub.add_parser("evaluar-agente", parents=[comunes], help="mide al agente con los casos de tests/fixtures")
    p.add_argument("--solo", nargs="*", help="solo los fixtures cuyo nombre contenga alguno de estos textos")
    p = sub.add_parser("hecho", parents=[comunes], help="verifica una afirmación suelta con la web")
    p.add_argument("afirmacion")
    p.add_argument("--contexto", default="Afirmación de un caso de práctica de PractIA.")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    llm = LlmVerificador()
    try:
        if args.orden == "hecho":
            _verificar_un_hecho(args, llm)
            return 0
        if args.orden == "evaluar-agente":
            args.salida = args.salida if args.salida != str(AUDITS_DIR) else str(ROOT / "tests" / "fixtures" / "informes")
            _evaluar_agente(args, llm)
            return 0
        ruta = Path(args.ruta)
        if args.orden == "caso":
            informe = auditar_caso(json.loads(ruta.read_text(encoding="utf-8")), con_web=not args.sin_web,
                                   max_hechos=args.max_hechos, llm=llm, usar_cache=not args.sin_cache)
        else:
            texto = ruta.read_text(encoding="utf-8")
            texto = _seccion(texto, args.seccion) if args.seccion else texto
            nombre = ruta.stem.lower() + ("-" + args.seccion.strip("# ").split()[0].strip(".") if args.seccion else "")
            informe = auditar_texto(texto, nombre, con_web=not args.sin_web, max_hechos=args.max_hechos,
                                    llm=llm, usar_cache=not args.sin_cache)
        _imprimir(informe, guardar(informe, Path(args.salida)))
        return 0
    except VerificadorError as exc:
        logger.error("{}", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
