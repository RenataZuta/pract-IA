"""
Muestra cuánto te queda en Groq con una llamada mínima (~100 tokens).

    python -m scripts.cuota

Lee los encabezados de la respuesta: tokens por minuto y solicitudes por día. El límite de TOKENS POR DÍA (200K en
gpt-oss-120b, plan gratuito) no viene en los encabezados: si ya lo agotaste, Groq responde 429 y el mensaje trae
cuánto usaste. Para el detalle histórico, la consola web: https://console.groq.com (Settings -> Limits, Usage).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, RateLimitError

ROOT = Path(__file__).resolve().parent.parent
MODELO = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not os.getenv("GROQ_API_KEY"):
        print("Falta GROQ_API_KEY en .env")
        return 1
    try:
        crudo = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.with_raw_response.create(
            model=MODELO, messages=[{"role": "user", "content": "ok"}], max_tokens=16,
            extra_body={"reasoning_effort": "low"})
    except RateLimitError as exc:
        print("⛔ Groq está limitando (429). Mensaje:\n", re.sub(r"\s+", " ", str(exc))[:500])
        print("\nSi menciona 'tokens per day (TPD)', agotaste el cupo diario: espera a que se reponga.")
        return 2
    h = crudo.headers
    print(f"Modelo: {MODELO}")
    print(f"Tokens por minuto: {h.get('x-ratelimit-remaining-tokens')} de {h.get('x-ratelimit-limit-tokens')} libres ahora")
    print(f"Solicitudes por día: {h.get('x-ratelimit-remaining-requests')} de {h.get('x-ratelimit-limit-requests')} libres")
    print("Tokens por día: no vienen en los encabezados; mira Usage en https://console.groq.com")
    return 0


if __name__ == "__main__":
    sys.exit(main())
