from __future__ import annotations

import asyncio
import gc
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"

# Techo de pixeles que se pueden llegar a decodificar. 50 Mpx en RGB son ~150 MB,
# que es lo que aguanta la instancia de 512 MB de Render con el resto del
# proceso vivo. Es un techo de FUENTE, no un filtro: cualquier imagen mayor se
# reescala.
#
# Debe coincidir con Image.MAX_IMAGE_PIXELS, que es el valor que Pillow usa para
# su propia comprobacion (avisa por encima de este, y lanza
# DecompressionBombError por encima del doble). Si se deja en el cuadrado de
# MAX_IMAGE_DIMENSION, Pillow avisa por CUALQUIER payload que pase un pixel del
# lado mayor, que es justo el caso normal del cliente cuando el calculo de
# dimensiones arrastra redondeos.
MAX_SOURCE_PIXELS = 50_000_000

# Objetivo de salida hacia Gemini. No es un filtro: una imagen mayor se
# reescala, nunca se rechaza.
MAX_IMAGE_DIMENSION = 1024

# Tope del campo base64 ya decodificado. El limite duro de la peticion vive en
# el servidor web; este evita decodificar en memoria un payload enorme.
MAX_IMAGE_BYTES = 5 * 1024 * 1024

Image.MAX_IMAGE_PIXELS = MAX_SOURCE_PIXELS

MAX_IMAGE_BYTES_LABEL = f"{MAX_IMAGE_BYTES // (1024 * 1024)} MB"


class ImageTooLargeError(ValueError):
    """La imagen supera los limites de bytes o de pixeles admitidos."""


class InvalidImageError(ValueError):
    """Los bytes recibidos no se pueden decodificar como imagen."""


def _build_prompt(prompt_text: str) -> str:
    return (
        "Edita la imagen del cliente usando la mascara como area exacta de intervencion. "
        "Coloca o reemplaza un producto de vidrio/aluminio de El Cercho dentro de la zona blanca de la mascara. "
        "Conserva perspectiva, escala, iluminacion, sombras, reflejos, materiales alrededor y contexto del espacio. "
        "No modifiques areas fuera de la mascara. "
        f"Producto solicitado: {prompt_text}"
    )


def _optimize_image(image_bytes: bytes, *, mask: bool) -> tuple[bytes, str]:
    """Reescala cualquier imagen valida al presupuesto de MAX_IMAGE_DIMENSION.

    No rechaza por dimensiones: reescalar es barato y el unico limite que de
    verdad importa es el consumo de memoria. Rechazar aqui solo producia 413 en
    clientes que ya habian hecho su propio resize.
    """
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImageTooLargeError(f"La imagen supera el limite de {MAX_IMAGE_BYTES_LABEL}.")

    target_mode = "L" if mask else "RGB"
    try:
        with BytesIO(image_bytes) as input_buffer, Image.open(input_buffer) as image:
            # draft() VA PRIMERO: en JPEG hace que libjpeg decodifique ya
            # escalado (1/2, 1/4, 1/8...), asi que el pico de memoria depende del
            # tamano objetivo y no del original, y una foto de 50 MP de telefono
            # se procesa como una de 3 MP. Sin draft, esas fotos se rechazan por
            # grande en vez de aceptarse. Es no-op en formatos sin soporte, que
            # es justo donde el techo de MAX_SOURCE_PIXELS sigue protegiendo.
            image.draft(target_mode, (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

            if image.width * image.height > MAX_SOURCE_PIXELS:
                raise ImageTooLargeError("La imagen tiene demasiados pixeles. Usa una foto de menor resolucion.")

            image.load()
            image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)

            with BytesIO() as output:
                image.convert(target_mode).save(
                    output,
                    format="JPEG",
                    quality=80,
                    optimize=True,
                    progressive=not mask,
                )
                return output.getvalue(), "image/jpeg"
    except ImageTooLargeError:
        raise
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError("La imagen tiene demasiados pixeles. Usa una foto de menor resolucion.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("No se pudo decodificar la imagen enviada.") from exc


def _generate_product_simulation_sync(
    client_image_bytes: bytes,
    mask_bytes: bytes,
    prompt_text: str,
) -> bytes:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY no esta configurada.")

    optimized_client_bytes = None
    optimized_mask_bytes = None
    genai_response = None
    try:
        optimized_client_bytes, client_mime_type = _optimize_image(client_image_bytes, mask=False)
        optimized_mask_bytes, mask_mime_type = _optimize_image(mask_bytes, mask=True)

        with genai.Client(api_key=settings.gemini_api_key) as client:
            genai_response = client.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=[
                    types.Part.from_bytes(data=optimized_client_bytes, mime_type=client_mime_type),
                    types.Part.from_bytes(data=optimized_mask_bytes, mime_type=mask_mime_type),
                    _build_prompt(prompt_text),
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )

        optimized_client_bytes = None
        optimized_mask_bytes = None

        for part in genai_response.parts or []:
            if part.inline_data and part.inline_data.data:
                return bytes(part.inline_data.data)

        prompt_feedback = getattr(genai_response, "prompt_feedback", None)
        block_reason = getattr(prompt_feedback, "block_reason", None)
        finish_reasons = [
            getattr(candidate, "finish_reason", None)
            for candidate in (getattr(genai_response, "candidates", None) or [])
        ]
        raise RuntimeError(
            "Gemini no devolvio imagen; "
            f"block_reason={block_reason}, finish_reasons={finish_reasons}."
        )
    finally:
        del optimized_client_bytes
        del optimized_mask_bytes
        del genai_response
        gc.collect()


async def generate_product_simulation(
    client_image_bytes: bytes,
    mask_bytes: bytes,
    prompt_text: str,
) -> bytes:
    try:
        return await asyncio.to_thread(
            _generate_product_simulation_sync,
            client_image_bytes,
            mask_bytes,
            prompt_text,
        )
    finally:
        del client_image_bytes
        del mask_bytes
        gc.collect()
