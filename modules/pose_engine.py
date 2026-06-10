# modules/pose_engine.py
# 25 pose definitions untuk Zaneva PoseGen
# Semua prompt include base modifier muslimah

BASE_MODIFIER = (
    "hijab-wearing woman, modest activewear muslimah, full hijab covering hair and neck, "
    "professional fashion photography, clean studio background, "
    "the clothing must remain exactly as shown in the reference photo — "
    "same color, same design, same pattern, no alterations to the garment"
)

POSE_GROUPS = {
    "A": "Berdiri (Standing)",
    "B": "Aktivitas Olahraga",
    "C": "Casual / Lifestyle",
    "D": "Detail Produk",
    "E": "Candid / Dynamic",
}

POSE_PROMPTS = {
    # === GRUP A — Berdiri ===
    "A1": (
        "Full body front view, standing straight, arms relaxed at sides, "
        "neutral confident expression, fashion photography, high quality, "
        "{modifier}"
    ),
    "A2": (
        "Full body front view, one hand on hip, other arm relaxed, "
        "confident pose, slight smile, fashion photography, "
        "{modifier}"
    ),
    "A3": (
        "Full body three-quarter angle side view, standing pose, "
        "looking slightly toward camera, fashion photography, "
        "{modifier}"
    ),
    "A4": (
        "Full body back view, standing straight, looking straight ahead, "
        "showing back of garment, fashion photography, "
        "{modifier}"
    ),
    "A5": (
        "Full body front view, head slightly turned to the side, "
        "natural relaxed pose, soft expression, fashion photography, "
        "{modifier}"
    ),

    # === GRUP B — Aktivitas Olahraga ===
    "B1": (
        "Full body, dynamic running pose, one foot forward, arms in motion, "
        "athletic activewear, sports photography, dynamic movement, "
        "{modifier}"
    ),
    "B2": (
        "Full body, warm-up stretching pose, arms extended overhead, "
        "side stretch, athletic pose, sports photography, "
        "{modifier}"
    ),
    "B3": (
        "Full body, squat pose, knees bent, arms forward for balance, "
        "athletic squatting position, sports photography, "
        "{modifier}"
    ),
    "B4": (
        "Full body, jumping pose mid-air, slight crouch landing position, "
        "energetic athletic movement, sports photography, dynamic, "
        "{modifier}"
    ),
    "B5": (
        "Full body, yoga pose, standing balance pose or light plank position, "
        "calm focused expression, sports photography, "
        "{modifier}"
    ),

    # === GRUP C — Casual / Lifestyle ===
    "C1": (
        "Full body, sitting casually on floor, legs crossed or extended, "
        "relaxed natural pose, lifestyle photography, "
        "{modifier}"
    ),
    "C2": (
        "Full body, standing pose facing slightly toward mirror angle, "
        "natural selfie-style pose, casual lifestyle photography, "
        "{modifier}"
    ),
    "C3": (
        "Full body, mid-walk casual pose, one foot forward, "
        "natural walking movement, lifestyle street photography, "
        "{modifier}"
    ),
    "C4": (
        "Full body, standing pose holding a bag or accessory, "
        "casual lifestyle look, natural expression, "
        "{modifier}"
    ),
    "C5": (
        "Full body, outdoor casual pose, one hand gently touching hijab or near hair area, "
        "relaxed natural outdoor lifestyle, "
        "{modifier}"
    ),

    # === GRUP D — Detail Produk ===
    "D1": (
        "Close-up upper body chest area, showing garment front detail and any logo clearly, "
        "sharp focus on fabric and design, product photography, macro detail, "
        "{modifier}"
    ),
    "D2": (
        "Close-up fabric texture detail shot, showing material quality and weave, "
        "sharp macro photography, product detail, "
        "{modifier}"
    ),
    "D3": (
        "Close-up accent and design detail of garment, stitching, seams, or special features, "
        "sharp product photography, "
        "{modifier}"
    ),
    "D4": (
        "Full body from distance, showing complete silhouette of outfit, "
        "wide fashion shot, full garment visible, clean background, "
        "{modifier}"
    ),
    "D5": (
        "Medium shot waist-up, showing upper body garment detail clearly, "
        "half body fashion photography, "
        "{modifier}"
    ),

    # === GRUP E — Candid / Dynamic ===
    "E1": (
        "Full body, natural laughing expression, candid moment, "
        "genuine smile, lifestyle candid photography, "
        "{modifier}"
    ),
    "E2": (
        "Full body, pose adjusting outer layer or jacket, "
        "dynamic candid movement, natural gesture, lifestyle photography, "
        "{modifier}"
    ),
    "E3": (
        "Full body back view with head slightly turned looking over shoulder, "
        "candid dynamic pose, editorial fashion photography, "
        "{modifier}"
    ),
    "E4": (
        "Full body dynamic movement pose, energetic action, "
        "motion blur suggestion, dynamic fashion photography, "
        "{modifier}"
    ),
    "E5": (
        "Full body candid walking pose, looking down at phone naturally, "
        "urban lifestyle candid photography, "
        "{modifier}"
    ),
}

# Urutan generate (A1 → E5)
POSE_ORDER = [
    "A1", "A2", "A3", "A4", "A5",
    "B1", "B2", "B3", "B4", "B5",
    "C1", "C2", "C3", "C4", "C5",
    "D1", "D2", "D3", "D4", "D5",
    "E1", "E2", "E3", "E4", "E5",
]

POSE_LABELS = {
    "A1": "Berdiri Tegak",
    "A2": "Tangan di Pinggang",
    "A3": "3/4 Angle",
    "A4": "Tampak Belakang",
    "A5": "Menoleh Samping",
    "B1": "Pose Lari",
    "B2": "Pemanasan",
    "B3": "Squat",
    "B4": "Melompat",
    "B5": "Yoga / Plank",
    "C1": "Duduk Santai",
    "C2": "Selfie Pose",
    "C3": "Berjalan Kasual",
    "C4": "Pegang Tas",
    "C5": "Outdoor Casual",
    "D1": "Detail Dada / Logo",
    "D2": "Tekstur Bahan",
    "D3": "Detail Aksen",
    "D4": "Full Siluet",
    "D5": "Medium Shot",
    "E1": "Tertawa Natural",
    "E2": "Buka Outer",
    "E3": "Balik Badan",
    "E4": "Pose Dinamis",
    "E5": "Candid HP",
}


def build_prompt(pose_id: str, body_type: str = "average", background: str = "putih") -> str:
    """Build full prompt untuk satu pose."""
    template = POSE_PROMPTS.get(pose_id)
    if not template:
        raise ValueError(f"Pose {pose_id} tidak ditemukan")

    body_desc = {
        "slim": "slim body type",
        "average": "average body type",
        "plus": "plus size body type",
    }.get(body_type, "average body type")

    bg_desc = {
        "putih": "pure white clean background",
        "abu": "neutral gray studio background",
        "outdoor": "blurred outdoor background, bokeh",
        "transparan": "transparent background, isolated subject",
    }.get(background, "pure white clean background")

    modifier = f"{BASE_MODIFIER}, {body_desc}, {bg_desc}"
    return template.format(modifier=modifier)


def get_all_prompts(body_type: str = "average", background: str = "putih") -> dict:
    """Return dict pose_id -> prompt untuk semua 25 pose."""
    return {pid: build_prompt(pid, body_type, background) for pid in POSE_ORDER}
