from __future__ import annotations

import asyncio
import gc
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from app.core.config import settings

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1024
MAX_IMAGE_PIXELS = MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def _build_prompt(prompt_text: str) -> str:
    return (
        "Edita la imagen del cliente usando la mascara como area exacta de intervencion. "
        "Coloca o reemplaza un producto de vidrio/aluminio de El Cercho dentro de la zona blanca de la mascara. "
        "Conserva perspectiva, escala, iluminacion, sombras, reflejos, materiales alrededor y contexto del espacio. "
        "No modifiques areas fuera de la mascara. "
        f"Producto solicitado: {prompt_text}"
    )


def _optimize_image(image_bytes: bytes, *, mask: bool) -> tuple[bytes, str]:
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("La imagen supera el limite de 8 MB.")

    with BytesIO(image_bytes) as input_buffer, Image.open(input_buffer) as image:
        width, height = image.size
        if max(width, height) > MAX_IMAGE_DIMENSION or width * height > MAX_IMAGE_PIXELS:
            raise ValueError("La imagen supera las dimensiones permitidas.")
        image.load()
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)

        with BytesIO() as output:
            if mask:
                image.convert("L").save(output, format="PNG", optimize=True)
                mime_type = "image/png"
            else:
                image.convert("RGB").save(output, format="JPEG", quality=82, optimize=True, progressive=True)
                mime_type = "image/jpeg"
            return output.getvalue(), mime_type


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
                    response_modalities=["IMAGE"],
                ),
            )

        optimized_client_bytes = None
        optimized_mask_bytes = None

        for part in genai_response.parts or []:
            if part.inline_data and part.inline_data.data:
                return bytes(part.inline_data.data)

        raise RuntimeError("Gemini no devolvio imagen generada.")
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
