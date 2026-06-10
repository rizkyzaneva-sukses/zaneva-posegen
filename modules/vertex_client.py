import json
import os
import base64
import logging

logger = logging.getLogger(__name__)

_initialized = False
_project_id = None

SA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "service-account.json")


def init_from_file(json_path: str = SA_PATH):
    global _initialized, _project_id
    from google.oauth2 import service_account
    import vertexai

    with open(json_path) as f:
        sa_info = json.load(f)

    credentials = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )

    vertexai.init(
        project=sa_info["project_id"],
        location="us-central1",
        credentials=credentials
    )

    _initialized = True
    _project_id = sa_info["project_id"]
    return _project_id


def is_initialized() -> bool:
    return _initialized


def get_project_id():
    return _project_id


def test_connection() -> dict:
    """Test apakah credentials valid."""
    try:
        if not _initialized:
            return {"ok": False, "error": "Vertex AI belum diinisialisasi"}
        from vertexai.preview.vision_models import ImageGenerationModel
        ImageGenerationModel.from_pretrained("imagegeneration@006")
        return {"ok": True, "project_id": _project_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def generate_image(garment_image_path: str, pose_prompt: str, number_of_images: int = 1) -> bytes:
    """
    Generate fashion image dengan Vertex AI Imagen.
    garment_image_path : path ke foto produk (dipakai sebagai reference)
    pose_prompt        : prompt lengkap pose + deskripsi
    return             : bytes JPEG
    """
    if not _initialized:
        raise RuntimeError("Vertex AI belum diinisialisasi. Setup service account dulu.")

    from vertexai.preview.vision_models import ImageGenerationModel
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")

    response = model.generate_images(
        prompt=pose_prompt,
        number_of_images=number_of_images,
        aspect_ratio="2:3",
        safety_filter_level="block_some",
        person_generation="allow_adult",
    )

    if not response.images:
        raise ValueError("Vertex AI tidak menghasilkan gambar")

    return response.images[0]._image_bytes
