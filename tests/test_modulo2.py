"""Módulo 2 (entrevista 1-a-1): rúbrica por eje, evaluador y flujo en la app."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ai import evaluator
from ai import interview_evaluator as ie
from ai.evaluator import CriterionScore, Feedback
from test_evaluador_rag import GroqFalso, _json_feedback  # noqa: F401  (fixtures y fakes compartidos)

AI = Path(__file__).parent.parent / "ai"
PREGUNTA = {"pregunta": "Cuéntame de una vez que lideraste a un grupo sin tener autoridad formal.",
            "hint": "Buscan si tomas iniciativa aunque nadie te la delegue.", "subtema": "Liderazgo e iniciativa"}


@pytest.mark.parametrize("tipo, eje", [("behavioral_star", "star"), ("fit", "fit"), ("tecnica_banca", "tecnica"),
                                       ("tecnica_fmcg", "tecnica"), ("tecnica_consultoria", "tecnica")])
def test_cada_tipo_de_pregunta_tiene_su_eje_y_su_rubrica_suma_100(tipo, eje):
    assert ie.eje_de(tipo) == eje
    criterios = ie.cargar_rubrica(tipo)["criterios"]
    assert abs(sum(c["peso"] for c in criterios) - 1) < 1e-9 and {c["tipo"] for c in criterios} == {"tecnico", "blando"}


def test_cada_pregunta_del_banco_cae_en_una_rubrica_que_existe_y_las_de_perfil_no_son_star_ni_motivacion():
    for archivo in (AI / "questions").glob("*.json"):
        for q in json.loads(archivo.read_text(encoding="utf-8")):
            rubrica = ie.cargar_rubrica(archivo.stem, q["subtema"])
            assert abs(sum(c["peso"] for c in rubrica["criterios"]) - 1) < 1e-9
    assert ie.eje_de("fit", "Perfil personal") == "perfil" and ie.eje_de("behavioral_star", "Preguntas trampa") == "perfil"
    assert ie.eje_de("tecnica_consultoria", "Fit y motivación") == "fit" and ie.eje_de("fit", "Motivación y fit") == "fit"
    nombres = [c["nombre"] for c in ie.cargar_rubrica("fit", "Perfil personal")["criterios"]]
    assert "Motivación específica" not in nombres and "Autoconocimiento con evidencia" in nombres


def test_tipo_desconocido_da_error_claro():
    with pytest.raises(evaluator.EvaluationError, match="desconocido"):
        ie.eje_de("tecnica_astrologia")


def test_el_prompt_lleva_la_pregunta_la_pista_y_la_longitud():
    prompt = ie._build_user_prompt("yo lideré " * 80, PREGUNTA, "behavioral_star", ie.cargar_rubrica("behavioral_star"))
    assert PREGUNTA["pregunta"] in prompt and PREGUNTA["hint"] in prompt and "160 palabras" in prompt
    assert "Acción propia" in prompt and "60-90 s" in prompt


@pytest.fixture
def groq_falso(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
    monkeypatch.setattr(evaluator, "Groq", GroqFalso)
    GroqFalso.llamadas = 0
    return GroqFalso


def _nombres(tipo):
    return [c["nombre"] for c in ie.cargar_rubrica(tipo)["criterios"]]


def test_el_total_lo_calcula_el_codigo_con_los_pesos_de_la_rubrica(groq_falso):
    nombres = _nombres("behavioral_star")
    groq_falso.respuestas = [_json_feedback([(n, 10 if i < 3 else 0) for i, n in enumerate(nombres)], total=1)]
    fb = ie.evaluate_interview_answer("Lideré a mi grupo. Resultado: 20% menos errores.", PREGUNTA, "behavioral_star")
    assert fb.puntaje_total == 70  # .20 + .25 + .25 con 10 y el resto con 0
    assert fb.puntaje_por_tipo == {"tecnico": 100, "blando": 0} and groq_falso.llamadas == 1


def test_reintenta_si_faltan_criterios(groq_falso):
    nombres = _nombres("fit")
    groq_falso.respuestas = [_json_feedback([(n, 5) for n in nombres[:2]]), _json_feedback([(n, 6) for n in nombres])]
    fb = ie.evaluate_interview_answer("Me interesa la empresa por su campaña X.", {**PREGUNTA, "pregunta": "¿Por qué Belcorp?"}, "fit")
    assert groq_falso.llamadas == 2 and fb.puntaje_total == 60


def test_respuesta_vacia_o_sin_key_no_llaman_a_groq(groq_falso, monkeypatch):
    with pytest.raises(evaluator.EvaluationError, match="vacía"):
        ie.evaluate_interview_answer("  ", PREGUNTA, "behavioral_star")
    monkeypatch.delenv("GROQ_API_KEY")
    with pytest.raises(evaluator.EvaluationError, match="Secrets"):
        ie.evaluate_interview_answer("algo", PREGUNTA, "behavioral_star")
    assert groq_falso.llamadas == 0


def _feedback_falso(*a, **k) -> Feedback:
    return Feedback(puntaje_total=68, criterios=[CriterionScore(nombre="Acción propia", puntaje=7, comentario="Habló en primera persona.", tipo="tecnico", peso=0.25)],
                    fortaleza_principal="Dio un resultado medible.", tres_cosas_a_mejorar=["a", "b", "c"],
                    red_flags_detectados=["Dijo 'nosotros' todo el tiempo"], respuesta_modelo="Ejemplo.", puntaje_por_tipo={"tecnico": 68, "blando": 70})


def test_flujo_en_la_app_escribir_evaluar_y_no_repetir(monkeypatch):
    llamadas = []
    monkeypatch.setattr("ai.interview_evaluator.evaluate_interview_answer", lambda *a, **k: (llamadas.append(a), _feedback_falso())[1])
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("Entrevista 1-a-1").run()
    assert not at.exception and any("Responde la pregunta" in m.value for m in at.markdown)
    at.text_area[0].set_value("Lideré a mi grupo de 4 y entregamos un día antes, con 20% menos errores.").run()
    assert any("palabras" in c.value for c in at.caption)
    evaluar = next(b for b in at.button if b.label == "Evaluar respuesta")
    evaluar.click().run()
    assert not at.exception and len(llamadas) == 1
    assert any(m.value == "68/100" for m in at.metric) and any("Red flags" in e.value for e in at.error)
    next(b for b in at.button if b.label == "Evaluar respuesta").click().run()
    assert len(llamadas) == 1 and any("ya está evaluada" in i.value for i in at.info)
    # otra pregunta: se limpia la respuesta y el feedback
    next(b for b in at.sidebar.button if "Otra pregunta" in b.label).click().run()
    assert not at.exception and at.text_area[0].value == "" and not any(m.value == "68/100" for m in at.metric)


def test_la_duracion_la_decide_el_codigo_no_el_modelo(groq_falso):
    nombres = _nombres("behavioral_star")
    todo_10 = _json_feedback([(n, 10) for n in nombres])
    # ~20 palabras = ~8 s: el modelo dice 10 en duración, el código lo baja a 6
    groq_falso.respuestas = [todo_10]
    corta = ie.evaluate_interview_answer("Lideré a mi grupo y entregamos antes con menos errores que el mes pasado.", PREGUNTA, "behavioral_star")
    dur = next(c for c in corta.criterios if c.nombre == "Estructura y duración")
    assert dur.puntaje == 6 and "muy corta; lo ideal es 60-90 s" in dur.comentario and corta.puntaje_total == 96
    assert "ok" not in dur.comentario  # el comentario del modelo sobre el tiempo se descarta
    # ~170 palabras = ~68 s: en rango, el 10 del modelo se respeta
    groq_falso.respuestas = [todo_10]
    ideal = ie.evaluate_interview_answer("palabra " * 170, PREGUNTA, "behavioral_star")
    assert next(c for c in ideal.criterios if c.nombre == "Estructura y duración").puntaje == 10 and ideal.puntaje_total == 100
    # ~400 palabras = ~160 s: demasiado larga
    groq_falso.respuestas = [todo_10]
    larga = ie.evaluate_interview_answer("palabra " * 400, PREGUNTA, "behavioral_star")
    assert next(c for c in larga.criterios if c.nombre == "Estructura y duración").puntaje == 6
