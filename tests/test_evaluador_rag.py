"""Evaluador: el total lo calcula el código con los pesos de la rúbrica. RAG: recupera lo parecido."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai import evaluator, rag
from ai.evaluator import CriterionScore, Feedback, criterios_aplicables

AI = Path(__file__).parent.parent / "ai"
RUBRICAS = {n: json.loads((AI / "rubrics" / f"{n}.json").read_text(encoding="utf-8")) for n in ("banca", "fmcg", "consultoria")}


def caso(nombre: str) -> dict:
    return json.loads((AI / "cases" / f"{nombre}.json").read_text(encoding="utf-8"))


def peso_por_tipo(criterios: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for c in criterios:
        out[c["tipo"]] = round(out.get(c["tipo"], 0) + c["peso"], 6)
    return out


@pytest.mark.parametrize("industria", RUBRICAS)
def test_cada_rubrica_suma_100_y_reparte_55_30_15(industria):
    todos = [{**c, "tipo": c.get("tipo", "tecnico")} for c in RUBRICAS[industria]["criterios"]]
    assert peso_por_tipo(todos) == {"tecnico": 0.55, "blando": 0.30, "innovacion": 0.15}


def test_el_peso_de_un_criterio_que_no_aplica_se_reparte_dentro_de_su_tipo():
    r = RUBRICAS["consultoria"]
    sin_fermi = criterios_aplicables(r, caso("consultoria_01_profitability"))  # Profitability: no es Market entry/sizing
    assert "Recomendación y riesgos" not in {c["nombre"] for c in sin_fermi}  # el caso lo excluye
    assert peso_por_tipo(sin_fermi) == {"tecnico": 0.55, "blando": 0.30, "innovacion": 0.15}
    con_fermi = criterios_aplicables(r, caso("consultoria_03_market_sizing"))
    assert len(con_fermi) == len(sin_fermi) + 2 and abs(sum(c["peso"] for c in con_fermi) - 1) < 1e-9


def test_promedio_ponderado_redondea_medio_hacia_arriba():
    cs = [CriterionScore(nombre="a", puntaje=7, comentario="", peso=0.5), CriterionScore(nombre="b", puntaje=8, comentario="", peso=0.5)]
    assert evaluator._promedio(cs) == 75  # 7.5 -> 75 (round() de Python daría el par)
    assert evaluator._promedio([CriterionScore(nombre="a", puntaje=7, comentario="", peso=0.3),
                                CriterionScore(nombre="b", puntaje=8, comentario="", peso=0.7)]) == 77


def _json_feedback(criterios: list[tuple[str, int]], total: int = 99) -> str:
    return json.dumps({
        "puntaje_total": total, "criterios": [{"nombre": n, "puntaje": p, "comentario": "ok"} for n, p in criterios],
        "comparativo_referencia": {"coincide": [], "aporta": [], "le_falto": []}, "fortaleza_principal": "x",
        "tres_cosas_a_mejorar": ["a", "b", "c"], "red_flags_detectados": [], "respuesta_modelo": "m"})


class GroqFalso:
    """Devuelve, en orden, los textos que se le den; anota cuántas veces lo llamaron."""
    respuestas: list[str] = []
    llamadas = 0

    def __init__(self, **kw):
        self.chat = type("C", (), {"completions": self})()

    def create(self, **kw):
        type(self).llamadas += 1
        contenido = type(self).respuestas.pop(0)
        mensaje = type("M", (), {"content": contenido})()
        return type("R", (), {"choices": [type("Ch", (), {"message": mensaje})()]})()


@pytest.fixture
def groq_falso(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
    monkeypatch.setenv("RAG_K", "0")
    monkeypatch.setattr(evaluator, "Groq", GroqFalso)
    GroqFalso.llamadas = 0
    return GroqFalso


def _nombres_banca():
    return [c["nombre"] for c in criterios_aplicables(RUBRICAS["banca"], caso("banca_01_credito_pyme"))]


def test_el_total_y_los_subtotales_los_calcula_el_codigo_no_el_modelo(groq_falso):
    groq_falso.respuestas = [_json_feedback([(n, 10) for n in _nombres_banca()], total=3)]  # el modelo dice 3: miente
    fb = evaluator.evaluate_response("Recomiendo aprobar con condiciones.", caso("banca_01_credito_pyme"), RUBRICAS["banca"])
    assert fb.puntaje_total == 100 and fb.puntaje_por_tipo == {"tecnico": 100, "blando": 100, "innovacion": 100}
    assert abs(sum(c.peso for c in fb.criterios) - 1) < 1e-9 and groq_falso.llamadas == 1


def test_si_faltan_criterios_reintenta_una_vez_y_completa(groq_falso):
    nombres = _nombres_banca()
    groq_falso.respuestas = [_json_feedback([(n, 5) for n in nombres[:-2]]), _json_feedback([(n, 6) for n in nombres])]
    fb = evaluator.evaluate_response("Recomiendo aprobar.", caso("banca_01_credito_pyme"), RUBRICAS["banca"])
    assert groq_falso.llamadas == 2 and len(fb.criterios) == len(nombres) and fb.puntaje_total == 60


def test_tolera_tildes_y_mayusculas_en_los_nombres_de_criterios(groq_falso):
    nombres = _nombres_banca()
    cambiados = [(n.upper().replace("Á", "A"), 8) for n in nombres]
    groq_falso.respuestas = [_json_feedback(cambiados)]
    fb = evaluator.evaluate_response("Texto.", caso("banca_01_credito_pyme"), RUBRICAS["banca"])
    assert [c.nombre for c in fb.criterios] == nombres and fb.puntaje_total == 80


def test_transcripcion_vacia_no_llama_a_groq(groq_falso):
    with pytest.raises(evaluator.EvaluationError, match="vacía"):
        evaluator.evaluate_response("   ", caso("banca_01_credito_pyme"), RUBRICAS["banca"])
    assert groq_falso.llamadas == 0


# ---------- RAG ----------
def test_el_corpus_tiene_las_75_preguntas_y_los_12_casos():
    preguntas = sum(len(json.loads(p.read_text(encoding="utf-8"))) for p in (AI / "questions").glob("*.json"))
    assert preguntas == 75 and len(rag.corpus()) == 75 + 12


def test_recupera_el_caso_parecido_y_excluye_el_propio():
    consulta = "subir el precio del chocolate por el costo del cacao: elasticidad, bodegas y gramaje"
    assert "caso:fmcg_04" in [d.id for d, _ in rag.recuperar(consulta, k=3)]
    assert "caso:fmcg_04" not in [d.id for d, _ in rag.recuperar(consulta, k=5, excluir_caso="fmcg_04")]


def test_una_consulta_sin_palabras_utiles_no_rompe():
    assert rag.recuperar("", k=3) == []
