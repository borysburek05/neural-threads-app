import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import os
import time
from pathlib import Path

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Eikon Fabric Lab",
    page_icon="🧵"
)

# ─────────────────────────────────────────────
# SECURITY: Load API key from Streamlit Secrets
# On Streamlit Cloud → App Settings → Secrets:
#   GOOGLE_API_KEY = "AIza_your_key_here"
# Locally → .streamlit/secrets.toml (add to .gitignore)
# ─────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

_http_opts = types.HttpOptions(
    timeout=180_000,
    retry_options=types.HttpRetryOptions(
        attempts=3,
        initial_delay=2.0,
        http_status_codes=[408, 429, 500, 502, 503, 504],
    ),
)
client = genai.Client(http_options=_http_opts)

# ─────────────────────────────────────────────
# DEMO MODE — place a pre-generated JPG in the
# same folder as app.py and update the path.
# ─────────────────────────────────────────────
DEMO_IMAGE_PATH = "demo_output.jpg"

# ─────────────────────────────────────────────
# LOOKBOOK CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }
  .stDeployButton { display: none; }

  html, body, [data-testid="stAppViewContainer"],
  [data-testid="stApp"], .main {
    background-color: #FAF7F2 !important;
    color: #000000 !important;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
  }
  h1 {
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    color: #000000 !important;
    margin-bottom: 0 !important;
  }
  h2, h3 {
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #000000 !important;
  }
  p, .stMarkdown p, label, [data-testid="stText"] {
    color: #333333 !important;
    font-size: 0.875rem !important;
  }
  [data-testid="stFileUploader"] {
    background: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.07) !important;
    padding: 8px !important;
  }
  [data-testid="stFileUploader"] section {
    border: 1.5px dashed #DDCCBB !important;
    border-radius: 10px !important;
    background: #FDFAF6 !important;
  }
  [data-testid="stFileUploader"] section:hover {
    border-color: #FF7F50 !important;
    background: #FFF4EE !important;
  }
  .stButton > button {
    background-color: #FF7F50 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.03em !important;
    padding: 0.65rem 1.5rem !important;
    transition: background 0.2s, transform 0.1s !important;
    box-shadow: 0 4px 14px rgba(255,127,80,0.35) !important;
  }
  .stButton > button:hover {
    background-color: #e86d3f !important;
    transform: translateY(-1px) !important;
  }
  .stButton > button:active { transform: translateY(0) !important; }
  .stDownloadButton > button {
    background-color: #000000 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.55rem 1.25rem !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    transition: background 0.2s !important;
  }
  .stDownloadButton > button:hover { background-color: #333333 !important; }
  [data-testid="stToggle"] label {
    color: #000000 !important;
    font-weight: 600 !important;
  }
  [data-testid="stAlert"] {
    border-radius: 10px !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06) !important;
  }
  .filename-pill {
    display: inline-block;
    background: #FFFFFF;
    border: 1px solid #EADDD0;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.78rem;
    color: #FF7F50;
    font-weight: 600;
    letter-spacing: 0.01em;
    margin-bottom: 8px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
  }
  .thumb-label {
    font-size: 0.72rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 4px;
  }
  hr {
    border: none !important;
    border-top: 1px solid #EDE8E0 !important;
    margin: 1.5rem 0 !important;
  }
  [data-testid="stSpinner"] p {
    color: #555 !important;
    font-style: italic !important;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fabric_name_from_file(uploaded_file) -> str:
    """'Structured_Cotton.jpg' → 'Structured Cotton'"""
    stem = Path(uploaded_file.name).stem
    return stem.replace("_", " ").replace("-", " ").title()


def pil_to_bytes(img: Image.Image, fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=95)
    return buf.getvalue()


def match_dimensions(result_img: Image.Image, target_img: Image.Image) -> Image.Image:
    """
    Resize result_img to exactly match target_img's pixel dimensions.
    Uses LANCZOS for high-quality downscaling, BICUBIC for upscaling.
    Aspect ratio of result is NOT preserved — we force an exact pixel match
    so the output viewport sits flush against the input in the UI.
    """
    target_w, target_h = target_img.size
    if result_img.size == (target_w, target_h):
        return result_img
    resample = Image.LANCZOS if (
        result_img.width > target_w or result_img.height > target_h
    ) else Image.BICUBIC
    return result_img.resize((target_w, target_h), resample)


def build_gemini_prompt(fabric_name: str, garment_zone: str, fabric_color: str) -> str:
    """
    Builds the structured fabric-swap instruction sent to Gemini.
    garment_zone : "upper body" or "lower body"
    fabric_color : plain English color name e.g. "red", "navy blue"
    """
    if garment_zone == "upper":
        target_desc = (
            "the upper-body garment worn by the model "
            "(e.g. t-shirt, jacket, long-sleeve shirt, hoodie — "
            "whichever upper garment is present)"
        )
        lock_desc = "Keep the lower-body clothing, face, identity, pose, and background 100% identical."
    else:
        target_desc = (
            "the lower-body garment worn by the model "
            "(e.g. trousers, jeans, skirt, shorts — "
            "whichever lower garment is present)"
        )
        lock_desc = "Keep the upper-body clothing, face, identity, pose, and background 100% identical."

    return (
        f"Task: 1:1 Fabric & Color Swap on a specific garment.\n\n"
        f"Target Garment: Apply the swap ONLY to {target_desc}.\n\n"
        f"Color Instruction: The new fabric MUST be {fabric_color}. "
        f"This color overrides whatever color appears in the reference swatch. "
        f"Use the swatch only for texture, weave pattern, and material feel — not its color.\n\n"
        f"Strict Constraints: {lock_desc}\n\n"
        f"Action: Preserve the target garment's exact silhouette and fit. "
        f"Do not alter body shape or pose. "
        f"Replace only the surface appearance with the texture from the reference fabric image "
        f"'{fabric_name}', rendered in {fabric_color}, "
        f"mapped realistically across all existing folds, creases, and lighting."
    )


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.title("EIKON")
st.markdown(
    "<p style='color:#888;font-size:0.85rem;letter-spacing:0.12em;"
    "text-transform:uppercase;margin-top:-8px;margin-bottom:24px;'>"
    "Fabric Lab · AI Material Swapping Engine</p>",
    unsafe_allow_html=True
)
st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DEMO MODE TOGGLE
# ─────────────────────────────────────────────
demo_mode = st.toggle(
    "🎭  Demo Mode",
    value=False,
    help=(
        "ON  → Bypasses the API entirely. Simulates loading then shows your "
        "pre-generated image. Guaranteed not to fail during your presentation.\n"
        "OFF → Calls the Gemini API live with your uploaded images."
    )
)

st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN LAYOUT — 2 columns
# ─────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.4], gap="large")

# ══════════════════════════════════════════════
# LEFT COLUMN — SOURCE ASSETS
# ══════════════════════════════════════════════
with col_left:
    st.subheader("Input")
    st.markdown(" ")

    # ── Garment Zone ─────────────────────────
    st.markdown("**Target Garment**")
    garment_zone = st.radio(
        "Which part of the outfit to swap:",
        options=["upper", "lower"],
        format_func=lambda x: "👕  Upper Body (t-shirt, jacket, long-sleeve, hoodie…)"
                               if x == "upper"
                               else "👖  Lower Body (trousers, jeans, skirt, shorts…)",
        index=0,
        label_visibility="collapsed",
        horizontal=False,
        key="garment_zone"
    )

    st.markdown(" ")

    # ── Fabric Color ──────────────────────────
    st.markdown("**Fabric Color**")
    st.markdown(
        "<p style='font-size:0.78rem;color:#999;margin-top:-6px;margin-bottom:8px;'>"
        "Pick a color — the model will apply this to the texture from your swatch.</p>",
        unsafe_allow_html=True
    )
    COLOR_PRESETS = {
        "⬜ White":       "white",
        "🖤 Black":       "black",
        "🩶 Light Grey":  "light grey",
        "🩷 Dusty Pink":  "dusty pink",
        "🔴 Red":         "red",
        "🟠 Terracotta":  "terracotta",
        "🟡 Mustard":     "mustard yellow",
        "🟢 Olive":       "olive green",
        "🔵 Navy":        "navy blue",
        "🫐 Cobalt":      "cobalt blue",
        "🟣 Lavender":    "lavender",
        "🤎 Camel":       "camel brown",
    }
    color_label = st.selectbox(
        "Fabric color",
        options=list(COLOR_PRESETS.keys()),
        index=0,
        label_visibility="collapsed",
        key="color_select"
    )
    fabric_color = COLOR_PRESETS[color_label]

    st.markdown(" ")

    # ── Base Model Image ─────────────────────
    st.markdown("**Base Model Image**")
    uploaded_model = st.file_uploader(
        "Upload the garment photo you want to swap fabric on",
        type=["jpg", "jpeg", "png"],
        key="model_upload",
        label_visibility="collapsed"
    )
    if uploaded_model:
        st.markdown(
            f'<div class="filename-pill">📎 {uploaded_model.name}</div>',
            unsafe_allow_html=True
        )
        # Show thumbnail immediately on upload
        st.markdown('<div class="thumb-label">Preview</div>', unsafe_allow_html=True)
        model_preview = Image.open(io.BytesIO(uploaded_model.read())).convert("RGB")
        st.image(model_preview, width=300)
        uploaded_model.seek(0)   # rewind so the bytes are available again on Execute

    st.markdown(" ")

    # ── Reference Fabric Swatch ──────────────
    st.markdown("**Reference Fabric Swatch**")
    uploaded_fabric = st.file_uploader(
        "Upload the fabric texture you want applied",
        type=["jpg", "jpeg", "png"],
        key="fabric_upload",
        label_visibility="collapsed"
    )
    if uploaded_fabric:
        detected_name = fabric_name_from_file(uploaded_fabric)
        st.markdown(
            f'<div class="filename-pill">🧵 {uploaded_fabric.name}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f"<p style='font-size:0.8rem;color:#888;margin-top:2px;'>"
            f"Detected fabric: <strong style='color:#FF7F50'>{detected_name}</strong></p>",
            unsafe_allow_html=True
        )
        # Show thumbnail immediately on upload
        st.markdown('<div class="thumb-label">Preview</div>', unsafe_allow_html=True)
        fabric_preview = Image.open(io.BytesIO(uploaded_fabric.read())).convert("RGB")
        st.image(fabric_preview, width=300)
        uploaded_fabric.seek(0)  # rewind so the bytes are available again on Execute

    st.markdown("<br>", unsafe_allow_html=True)
    execute_btn = st.button("🚀  Execute Fabric Swap", use_container_width=True)

# ══════════════════════════════════════════════
# RIGHT COLUMN — OUTPUT VIEWPORT
# ══════════════════════════════════════════════
with col_right:
    st.subheader("Output")
    st.markdown(" ")

    output_slot   = st.empty()
    download_slot = st.empty()

    output_slot.markdown(
        "<div style='height:320px;background:#FFFFFF;border-radius:14px;"
        "box-shadow:0 4px 24px rgba(0,0,0,0.07);display:flex;align-items:center;"
        "justify-content:center;color:#BBAA99;font-size:0.85rem;letter-spacing:0.05em;'>"
        "Awaiting execution…</div>",
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────
    # EXECUTE HANDLER
    # ─────────────────────────────────────────
    if execute_btn:

        # ── DEMO MODE ────────────────────────
        if demo_mode:
            with st.spinner("Simulating Gemini engine… (Demo Mode)"):
                time.sleep(3)
            try:
                demo_img = Image.open(DEMO_IMAGE_PATH).convert("RGB")

                # Resize demo image to match uploaded model dimensions (if available)
                if uploaded_model:
                    ref = Image.open(io.BytesIO(uploaded_model.read())).convert("RGB")
                    uploaded_model.seek(0)
                    demo_img = match_dimensions(demo_img, ref)

                output_slot.image(
                    demo_img,
                    caption="Demo Output — pre-generated result",
                    use_container_width=True
                )
                download_slot.download_button(
                    label="⬇️  Download as JPG",
                    data=pil_to_bytes(demo_img),
                    file_name=f"eikon_demo_{int(time.time())}.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
            except FileNotFoundError:
                output_slot.error(
                    f"Demo image `{DEMO_IMAGE_PATH}` not found. "
                    "Place your pre-generated JPG in the same folder as app.py "
                    "and update the DEMO_IMAGE_PATH variable at the top of the script."
                )

        # ── LIVE MODE ────────────────────────
        else:
            if uploaded_model is None:
                output_slot.warning("⚠️  Please upload a Base Model Image to use Live Mode.")
            elif uploaded_fabric is None:
                output_slot.warning("⚠️  Please upload a Reference Fabric Swatch.")
            else:
                fabric_name = fabric_name_from_file(uploaded_fabric)
                prompt_text = build_gemini_prompt(fabric_name, garment_zone, fabric_color)

                with st.spinner(f"Gemini swapping '{fabric_name}' ({fabric_color}) on {garment_zone} body… (may take up to 2 min)"):
                    try:
                        # Read fresh bytes on every execution — prevents stale
                        # buffer reuse across multiple consecutive Execute presses.
                        model_bytes  = uploaded_model.read()
                        fabric_bytes = uploaded_fabric.read()
                        uploaded_model.seek(0)
                        uploaded_fabric.seek(0)

                        model_img  = Image.open(io.BytesIO(model_bytes)).convert("RGB")
                        fabric_img = Image.open(io.BytesIO(fabric_bytes)).convert("RGB")

                        # Capture target dimensions before API call
                        target_w, target_h = model_img.size

                        response = client.models.generate_content(
                            model="gemini-2.5-flash-image",
                            contents=[
                                prompt_text,
                                model_img,
                                fabric_img,
                            ],
                            config=types.GenerateContentConfig(
                                response_modalities=["IMAGE"],
                                http_options=types.HttpOptions(timeout=180_000),
                            ),
                        )

                        # Extract image from response parts
                        result_img = None
                        text_parts = []

                        for part in response.candidates[0].content.parts:
                            if part.inline_data is not None and \
                               part.inline_data.mime_type.startswith("image/"):
                                result_img = Image.open(
                                    io.BytesIO(part.inline_data.data)
                                ).convert("RGB")
                                break
                            if part.text:
                                text_parts.append(part.text)

                        if result_img is not None:
                            # Force exact pixel match to original model image
                            result_img = match_dimensions(
                                result_img,
                                Image.new("RGB", (target_w, target_h))
                            )
                            output_slot.image(
                                result_img,
                                caption=f"Fabric swap — {fabric_name}",
                                use_container_width=True,
                            )
                            download_slot.download_button(
                                label="⬇️  Download as JPG",
                                data=pil_to_bytes(result_img),
                                file_name=f"eikon_{int(time.time())}.jpg",
                                mime="image/jpeg",
                                use_container_width=True,
                            )
                        else:
                            fallback_msg = (
                                " ".join(text_parts)
                                if text_parts
                                else "No image or explanation returned."
                            )
                            output_slot.warning(
                                f"⚠️  Gemini returned a text response instead of an "
                                f"image. This usually means the safety filter blocked "
                                f"the request, or the model needs more context.\n\n"
                                f"**Model said:** {fallback_msg}\n\n"
                                f"**Fix:** Try simplifying the prompt, using a plain "
                                f"white-background fabric swatch, or toggling Demo Mode "
                                f"for your presentation."
                            )

                    except Exception as e:
                        output_slot.error(
                            f"Gemini API error: {e}\n\n"
                            f"If this is a 503, the timeout fix is already applied — "
                            f"try again in a few seconds."
                        )
