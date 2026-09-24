from __future__ import annotations

import asyncio

from google import genai
from google.genai import types

from app.core.config import settings

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"


def _build_prompt(prompt_text: str) -> str:
    return (
        "Edita la imagen del cliente usando la mascara como area exacta de intervencion. "
        "Coloca o reemplaza un producto de vidrio/aluminio de El Cercho dentro de la zona blanca de la mascara. "
        "Conserva perspectiva, escala, iluminacion, sombras, reflejos, materiales alrededor y contexto del espacio. "
        "No modifiques areas fuera de la mascara. "
        f"Producto solicitado: {prompt_text}"
    )


def _generate_product_simulation_sync(
    client_image_bytes: bytes,
    mask_bytes: bytes,
    prompt_text: str,
) -> bytes:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY no esta configurada.")

    with genai.Client(api_key=settings.gemini_api_key) as client:
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=[
                types.Part.from_bytes(data=client_image_bytes, mime_type="image/png"),
                types.Part.from_bytes(data=mask_bytes, mime_type="image/png"),
                _build_prompt(prompt_text),
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

    for part in response.parts or []:
        if part.inline_data and part.inline_data.data:
            return bytes(part.inline_data.data)

    raise RuntimeError("Gemini no devolvio imagen generada.")


async def generate_product_simulation(
    client_image_bytes: bytes,
    mask_bytes: bytes,
    prompt_text: str,
) -> bytes:
    return await asyncio.to_thread(
        _generate_product_simulation_sync,
        client_image_bytes,
        mask_bytes,
        prompt_text,
    )
