import os
import uuid
import io
from typing import Tuple, Optional
from PIL import Image, ImageOps
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

# Supported MIME types and extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
THUMBNAIL_MAX_SIZE = (300, 300)


def validate_and_process_image(
    file_bytes: bytes,
    original_filename: Optional[str] = None
) -> Tuple[Image.Image, str, int, int]:
    """
    Validates the uploaded file bytes using Pillow, normalizes orientation,
    and returns the processed PIL image, normalized format extension, width, and height.
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        http_status = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        raise HTTPException(
            status_code=http_status,
            detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )


    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    try:
        # Open image with Pillow to verify integrity
        image_stream = io.BytesIO(file_bytes)
        img = Image.open(image_stream)
        img.verify()

        # Reopen for actual processing (verify closes/invalidates the stream)
        image_stream.seek(0)
        img = Image.open(image_stream)

        # Check format
        fmt = img.format.lower() if img.format else ""
        if fmt not in ["jpeg", "jpg", "png", "webp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format '{fmt}'. Allowed formats: JPG, JPEG, PNG, WEBP."
            )

        # Normalize EXIF orientation if present
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        ext = f".{fmt}" if fmt != "jpeg" else ".jpg"
        width, height = img.size
        return img, ext, width, height

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted image file: {str(e)}"
        )


def save_report_image(
    report_id: str,
    file_bytes: bytes,
    original_filename: Optional[str] = None
) -> dict:
    """
    Validates, processes, and saves full image and its thumbnail to secure storage.
    Returns metadata dictionary for database insertion.
    """
    img, ext, width, height = validate_and_process_image(file_bytes, original_filename)

    # Secure directory structure: uploads/reports/{report_id}/
    report_upload_dir = os.path.join(settings.UPLOAD_DIRECTORY, "reports", str(report_id))
    os.makedirs(report_upload_dir, exist_ok=True)

    file_uuid = uuid.uuid4().hex
    main_filename = f"{file_uuid}{ext}"
    thumb_filename = f"{file_uuid}_thumb{ext}"

    main_filepath = os.path.join(report_upload_dir, main_filename)
    thumb_filepath = os.path.join(report_upload_dir, thumb_filename)

    # Save original/processed image
    # Convert RGBA to RGB for JPEG if necessary
    save_format = "JPEG" if ext == ".jpg" else ext.replace(".", "").upper()
    if save_format == "JPEG" and img.mode in ("RGBA", "P"):
        img_to_save = img.convert("RGB")
    else:
        img_to_save = img

    img_to_save.save(main_filepath, format=save_format, quality=85, optimize=True)

    # Generate and save thumbnail
    thumb = img.copy()
    thumb.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)
    if save_format == "JPEG" and thumb.mode in ("RGBA", "P"):
        thumb_to_save = thumb.convert("RGB")
    else:
        thumb_to_save = thumb
    thumb_to_save.save(thumb_filepath, format=save_format, quality=80, optimize=True)

    # Relative paths for portable storage / URL generation
    rel_main_path = os.path.join("uploads", "reports", str(report_id), main_filename).replace("\\", "/")
    rel_thumb_path = os.path.join("uploads", "reports", str(report_id), thumb_filename).replace("\\", "/")

    mime_type = f"image/{save_format.lower()}"

    return {
        "file_path": rel_main_path,
        "thumbnail_path": rel_thumb_path,
        "file_type": mime_type,
        "file_size": len(file_bytes),
        "width": width,
        "height": height,
    }
