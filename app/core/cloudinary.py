import os
from io import BytesIO

import cloudinary
import cloudinary.uploader


def init_cloudinary() -> None:
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    if not (cloud_name and api_key and api_secret):
        # No config provided; skip initialization
        return
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


# Initialize on import
init_cloudinary()


def upload_image_bytes(image_bytes: bytes, *, folder: str = "cercho/simulations") -> str:
    result = cloudinary.uploader.upload(
        BytesIO(image_bytes),
        folder=folder,
        resource_type="image",
    )
    secure_url = result.get("secure_url")
    if not secure_url:
        raise RuntimeError("Cloudinary no devolvio una URL segura.")
    return str(secure_url)
