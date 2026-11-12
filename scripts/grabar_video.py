"""
Graba el video de respaldo (60-90 s) de la app real, con subtítulos, de forma automática.

Es una grabación AUTOMATIZADA de la app pública funcionando: un navegador (Playwright + Google Chrome) recorre el
flujo completo contra la URL real y usa la API real de Groq. La "voz" es un audio sintético (texto en
docs/video/respuesta_demo.txt) que se SUBE por el cargador de audio; el video no tiene sonido.

Dos grabaciones separadas (módulo 1 y módulo 2) que se unen: así cada evaluación respeta el límite del plan
gratuito de Groq (8K tokens por minuto) y el video no muestra las esperas.

Uso (solo desarrollo; no hace falta para correr la app):

    pip install playwright imageio-ffmpeg        # y tener Google Chrome instalado; la síntesis de voz usa `say` (macOS)
    python -m scripts.grabar_video                               # graba la app pública
    python -m scripts.grabar_video --url http://localhost:8501   # o una app local

Cada corrida gasta ~9K tokens de la cuota de Groq (una evaluación de cada módulo).

ESTADO: probado hasta pulsar «Evaluar» del módulo 1 contra la app pública (12-nov); la corrida completa quedó pendiente
porque se agotó el cupo diario de Groq. Correrlo de nuevo cuando la cuota esté repuesta y revisar el mp4 resultante.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXTO_VOZ = ROOT / "docs" / "video" / "respuesta_demo.txt"
SALIDA = ROOT / "docs" / "video" / "PractIA_demo_respaldo.mp4"
URL_PUBLICA = "https://practia-up.streamlit.app/"
TAMANO = {"width": 1280, "height": 800}
PAUSA_ENTRE_EVALUACIONES_S = 70  # el plan gratuito de Groq da 8K tokens/min; una evaluación del módulo 1 gasta ~6K

RESPUESTA_ENTREVISTA = (
    "En mi práctica en planeamiento financiero, durante el cierre de octubre, había tres cuentas por conciliar antes del viernes "
    "y nadie lo había asignado. Como yo era quien mejor conocía el modelo, propuse repartir el trabajo por área y armé una hoja de "
    "control con fechas. Yo conciliaba las diferencias y le pedía a cada compañero su parte con un plazo claro, y cada mañana "
    "revisábamos juntos qué faltaba. Hubo una cuenta que nadie entendía y me quedé una tarde con la contadora para resolverla. "
    "Entregamos un día antes y bajamos las partidas sin conciliar de doce a dos. Lo que aprendí es que avisar temprano de los "
    "pendientes evita correr al final, y desde entonces armo el control desde el primer día."
)


def sintetizar_voz(destino: Path) -> Path:
    """Audio sintético (macOS `say`) del texto de docs/video/respuesta_demo.txt, en WAV de 16 kHz."""
    aiff = destino.with_suffix(".aiff")
    subprocess.run(["say", "-v", "Flo (Español (México))", "-o", str(aiff), "-f", str(TEXTO_VOZ)], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", str(aiff), str(destino)], check=True)
    return destino


def subtitulo(page, texto: str) -> None:
    """Subtítulo fijo abajo, en la página exterior (persiste aunque la app, dentro de un iframe, se recargue)."""
    page.evaluate(
        """(t) => {
          let d = document.getElementById('pr-sub');
          if (!d) { d = document.createElement('div'); d.id = 'pr-sub';
            d.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:2147483647;max-width:84%;' +
              'background:rgba(17,24,39,.92);color:#fff;padding:12px 22px;border-radius:12px;font:600 20px/1.35 system-ui,sans-serif;' +
              'text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.35)'; document.body.appendChild(d); }
          d.textContent = t; }""",
        texto,
    )


def marco_de_la_app(page, esperar: str, intentos: int = 30):
    """El iframe de la app (Streamlit Cloud la sirve dentro de uno); en local es la propia página."""
    for _ in range(intentos):
        for f in [page.main_frame, *page.frames]:
            try:
                if f.query_selector("body") and esperar in f.inner_text("body"):
                    return f
            except Exception:  # el marco puede estar recargándose
                pass
        time.sleep(3)
    raise RuntimeError(f"la app no mostró «{esperar}»")


def desplazar(fr, y: int) -> None:
    fr.evaluate("(y) => { const m = document.querySelector('[data-testid=stMain]') || document.scrollingElement;"
                " m.scrollTo({top: y, behavior: 'smooth'}); }", y)


def grabar_modulo_1(p, url: str, voz: Path, carpeta: Path) -> Path:
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport=TAMANO, record_video_dir=str(carpeta), record_video_size=TAMANO)
    page = ctx.new_page()
    page.goto(url, timeout=90000)
    fr = marco_de_la_app(page, "Graba tu respuesta")
    subtitulo(page, "PractIA · simulador de group case y de entrevista por voz · demo grabada de la app pública")
    time.sleep(4)
    subtitulo(page, "1 · Eliges un caso (aquí, BCP) y lees el contexto y los anexos con cifras")
    fr.get_by_text("Anexo 1:").first.click()
    time.sleep(4.5)
    subtitulo(page, "2 · Respondes por voz (aquí, un audio sintético de ejemplo)")
    fr.locator("input[type=file]").first.set_input_files(str(voz))
    fr.wait_for_selector("textarea", timeout=120000)
    fr.locator("textarea").first.scroll_into_view_if_needed()
    time.sleep(1.5)
    subtitulo(page, "3 · Whisper la transcribe en segundos y puedes corregirla antes de evaluar")
    time.sleep(4)
    subtitulo(page, "4 · El evaluador puntúa contra una rúbrica 55 % técnico / 30 % blandas / 15 % aporte propio")
    fr.get_by_role("button", name="Evaluar respuesta").click()
    fr.wait_for_selector("text=Tu feedback", timeout=180000)
    fr.locator("text=Tu feedback").first.scroll_into_view_if_needed()
    time.sleep(4.5)
    subtitulo(page, "El total y los subtotales los calcula el código, no el modelo")
    desplazar(fr, 1500)
    time.sleep(4.5)
    subtitulo(page, "Compara con una respuesta de referencia y usa RAG sobre 75 preguntas reales")
    desplazar(fr, 2300)
    time.sleep(5)
    if "Las cifras del feedback salen" in fr.inner_text("body"):
        subtitulo(page, "Y revisa que las cifras del feedback salgan de los anexos del caso")
        time.sleep(3)
    ctx.close()
    b.close()
    return Path(page.video.path())


def grabar_modulo_2(p, url: str, carpeta: Path) -> tuple[Path, float]:
    """Devuelve (video, segundos a recortar al inicio): al principio se busca una pregunta de liderazgo (no se muestra)."""
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport=TAMANO, record_video_dir=str(carpeta), record_video_size=TAMANO)
    t0 = time.time()
    page = ctx.new_page()
    page.goto(url, timeout=90000)
    fr = marco_de_la_app(page, "Graba tu respuesta")
    fr.get_by_text("Entrevista 1-a-1", exact=True).first.click()
    marco_de_la_app(page, "Responde la pregunta")
    for _ in range(60):  # la pregunta es aleatoria: se pide otra hasta que sea la de liderazgo
        if "lideraste a un grupo" in fr.inner_text("body"):
            break
        fr.get_by_role("button", name="🎲 Otra pregunta").click()
        time.sleep(1.3)
    recorte = time.time() - t0 - 0.3
    subtitulo(page, "5 · Entrevista 1-a-1 con el jefe final: preguntas reales del proceso peruano")
    time.sleep(4)
    caja = fr.get_by_label("O escribe tu respuesta")
    caja.scroll_into_view_if_needed()
    caja.fill(RESPUESTA_ENTREVISTA)
    caja.press("Control+Enter")
    subtitulo(page, "Respondes por voz o escribes; el evaluador usa la pista de lo que busca el entrevistador")
    time.sleep(4)
    fr.get_by_role("button", name="Evaluar respuesta").click()
    fr.wait_for_selector("text=Tu feedback", timeout=120000)
    fr.locator("text=Tu feedback").first.scroll_into_view_if_needed()
    subtitulo(page, "Puntúa por eje (STAR, técnica, fit o perfil); la duración de la respuesta la mide el código")
    time.sleep(5)
    desplazar(fr, 1900)
    time.sleep(4)
    subtitulo(page, "Código y documentación: github.com/RenataZuta/pract-IA")
    time.sleep(3)
    ctx.close()
    b.close()
    return Path(page.video.path()), recorte


def unir(ffmpeg: str, v1: Path, v2: Path, recorte2: float, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(v1), "-ss", f"{recorte2:.2f}", "-i", str(v2), "-filter_complex",
         "[0:v]setpts=PTS-STARTPTS,fps=25[a];[1:v]setpts=PTS-STARTPTS,fps=25[b];[a][b]concat=n=2:v=1:a=0[v]",
         "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30", "-preset", "slow", "-movflags", "+faststart", str(destino)],
        check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=URL_PUBLICA)
    ap.add_argument("--salida", default=str(SALIDA))
    args = ap.parse_args()
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        tmp = Path(tmp)
        voz = sintetizar_voz(tmp / "respuesta_demo.wav")
        v1 = grabar_modulo_1(p, args.url, voz, tmp)
        print(f"módulo 1 grabado; espero {PAUSA_ENTRE_EVALUACIONES_S} s por el límite de tokens de Groq...", flush=True)
        time.sleep(PAUSA_ENTRE_EVALUACIONES_S)
        v2, recorte = grabar_modulo_2(p, args.url, tmp)
        unir(imageio_ffmpeg.get_ffmpeg_exe(), v1, v2, recorte, Path(args.salida))
    print("video:", args.salida)


if __name__ == "__main__":
    main()
