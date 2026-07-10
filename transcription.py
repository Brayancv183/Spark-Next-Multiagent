import os
import tempfile
import logging
from groq import Groq

logger = logging.getLogger(__name__)


def transcribir_audio(archivo_ogg: bytes, groq_api_key: str) -> str:
    cliente = Groq(api_key=groq_api_key)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(archivo_ogg)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            transcripcion = cliente.audio.transcriptions.create(
                file=(os.path.basename(tmp_path), f),
                model="whisper-large-v3-turbo",
                response_format="json",
                timeout=60,
            )
        return transcripcion.text
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {e}")
        raise RuntimeError(f"No se pudo transcribir el audio: {e}") from e
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
