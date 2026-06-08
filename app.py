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
st.set_page_config(layout="wide", page_title="Eikon Fabric Lab", page_icon="🧵")

# ─────────────────────────────────────────────
# SECURITY
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

DEMO_IMAGE_PATH = "demo_output.jpg"

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }
  .stDeployButton { display: none; }

  html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main {
    background-color: #FAF7F2 !important;
    color: #000 !important;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
  }
  /* kill default padding so the 3-pane fits one screen */
  .block-container { padding-top: 1rem !important; padding-bottom: 0 !important; }

  h1 { font-size: 1.6rem !important; font-weight: 800 !important;
       letter-spacing: -0.03em !important; color: #000 !important; margin-bottom: 0 !important; }
  h2, h3 { font-weight: 700 !important; letter-spacing: -0.02em !important; color: #000 !important; }
  p, .stMarkdown p, label, [data-testid="stText"] { color: #333 !important; font-size: 0.82rem !important; }

  /* file uploader */
  [data-testid="stFileUploader"] {
    background: #fff !important; border: none !important;
    border-radius: 10px !important; box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
    padding: 4px !important;
  }
  [data-testid="stFileUploader"] section {
    border: 1.5px dashed #DDCCBB !important; border-radius: 8px !important;
    background: #FDFAF6 !important;
  }
  [data-testid="stFileUploader"] section:hover {
    border-color: #FF7F50 !important; background: #FFF4EE !important;
  }

  /* execute button */
  .stButton > button {
    background-color: #FF7F50 !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 700 !important; font-size: 0.9rem !important;
    padding: 0.6rem 1.2rem !important;
    box-shadow: 0 4px 14px rgba(255,127,80,0.35) !important;
    transition: background 0.2s, transform 0.1s !important;
  }
  .stButton > button:hover { background-color: #e86d3f !important; transform: translateY(-1px) !important; }
  .stButton > button:active { transform: translateY(0) !important; }

  /* download button */
  .stDownloadButton > button {
    background-color: #000 !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 0.82rem !important;
    padding: 0.5rem 1rem !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.18) !important;
  }
  .stDownloadButton > button:hover { background-color: #333 !important; }

  /* toggle */
  [data-testid="stToggle"] label { color: #000 !important; font-weight: 600 !important; }

  /* alerts */
  [data-testid="stAlert"] { border-radius: 8px !important; border: none !important; }

  /* filename pill */
  .filename-pill {
    display: inline-block; background: #fff; border: 1px solid #EADDD0;
    border-radius: 20px; padding: 2px 10px; font-size: 0.72rem;
    color: #FF7F50; font-weight: 600; margin-bottom: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  }
  .thumb-label { font-size: 0.68rem; color: #aaa; text-transform: uppercase;
                 letter-spacing: 0.07em; margin-bottom: 2px; }
  .pane-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em;
                text-transform: uppercase; color: #bbb; margin-bottom: 6px; }
  .output-placeholder {
    height: 340px; background: #fff; border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    display: flex; align-items: center; justify-content: center;
    color: #ccc; font-size: 0.8rem; letter-spacing: 0.05em;
  }
  hr { border: none !important; border-top: 1px solid #EDE8E0 !important; margin: 0.8rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fabric_name_from_file(f) -> str:
    return Path(f.name).stem.replace("_", " ").replace("-", " ").title()

def pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

def fit_thumbnail(img: Image.Image, max_h: int = 200) -> Image.Image:
    """Scale image down so height ≤ max_h, preserving aspect ratio."""
    if img.height <= max_h:
        return img
    ratio = max_h / img.height
    return img.resize((round(img.width * ratio), max_h), Image.LANCZOS)

def match_dimensions(result_img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale-to-fill then centre-crop to exact target dimensions."""
    if result_img.size == (target_w, target_h):
        return result_img
    sw, sh = result_img.size
    scale  = max(target_w / sw, target_h / sh)
    scaled = result_img.resize((round(sw * scale), round(sh * scale)),
                                Image.LANCZOS if scale < 1 else Image.BICUBIC)
    l = (scaled.width  - target_w) // 2
    t = (scaled.height - target_h) // 2
    return scaled.crop((l, t, l + target_w, t + target_h))

def open_rgb(uploaded) -> Image.Image:
    uploaded.seek(0)
    img = Image.open(io.BytesIO(uploaded.read())).convert("RGB")
    uploaded.seek(0)
    return img


# ─────────────────────────────────────────────
# PIPELINE STEP 1 — consensus fabric analysis
# ─────────────────────────────────────────────
def extract_consensus(model_img: Image.Image,
                      fabric_imgs: list[Image.Image]) -> str:
    """
    Sends the base model image + all fabric swatches to gemini-2.5-flash
    for a single consolidated architectural description.
    """
    contents = [
        "Analyze all provided fabric swatches and compare them to the target "
        "garment on the model. Act as a precise material analyst. Perform an "
        "automated average of the colors, patterns, and textures across all swatches. "
        "Output a consolidated, single-sentence architectural description specifying "
        "the exact consolidated fabric shade, pattern structure, textile weave, and "
        "expected scale relative to the base model. Do not use generic words. "
        "Focus on rigid technical details.",
        model_img,
        *fabric_imgs,
    ]
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
    )
    return response.text.strip()


# ─────────────────────────────────────────────
# PIPELINE STEP 2 — hyper-strict swap prompt
# ─────────────────────────────────────────────
def build_swap_prompt(consolidated_fabric_consensus: str,
                      garment_zone: str) -> str:
    if garment_zone == "upper":
        target_desc = (
            "the upper-body garment worn by the model "
            "(t-shirt, jacket, long-sleeve shirt, hoodie, or similar)"
        )
        lock_extra = "Keep the lower-body clothing 100% identical."
    else:
        target_desc = (
            "the lower-body garment worn by the model "
            "(trousers, jeans, skirt, shorts, or similar)"
        )
        lock_extra = "Keep the upper-body clothing 100% identical."

    return (
        f"Task: 1:1 Fabric Mapping.\n\n"
        f"Target Garment: {target_desc} — the item worn in the first image.\n\n"
        f"Fabric to Apply: {consolidated_fabric_consensus}\n\n"
        f"Forbidden Modification: You are strictly forbidden from altering the "
        f"model's face, hair, skin, body, or original pose. "
        f"Pay specific attention to the model's hands; they are *not* inside pockets. "
        f"You must preserve the exact position, shape, and visibility of the original "
        f"hands as they appear in the base model image. "
        f"Do not hide or reinvent the hands. "
        f"{lock_extra} "
        f"All non-targeted pixels must remain 100% identical.\n\n"
        f"CRITICAL FRAMING RULE: Do not crop, zoom, or pan the image. "
        f"You must return the full, uncropped original frame. "
        f"The borders, floor, ceiling, and subject's head must remain exactly "
        f"where they are in the base image.\n\n"
        f"Action: Seamlessly wrap the reference fabric colors and patterns onto the "
        f"target garment, matching folds, lighting, and contours."
    )


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.title("EIKON")
st.markdown(
    "<p style='color:#888;font-size:0.8rem;letter-spacing:0.12em;"
    "text-transform:uppercase;margin-top:-6px;margin-bottom:12px;'>"
    "Fabric swapping engine visualizer</p>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 3-PANE LAYOUT
# ─────────────────────────────────────────────
pane_input, pane_output, pane_controls = st.columns([1.1, 1.4, 0.75], gap="medium")

# ══════════════════════════════════════════════
# PANE 1 — INPUT
# ══════════════════════════════════════════════
with pane_input:
    st.subheader("Input")

    # ── Base model ────────────────────────────
    st.markdown("**Base Model Image**")
    uploaded_model = st.file_uploader(
        "Base model", type=["jpg","jpeg","png"],
        key="model_upload", label_visibility="collapsed",
    )
    if uploaded_model:
        st.markdown(f'<div class="filename-pill">📎 {uploaded_model.name}</div>',
                    unsafe_allow_html=True)
        thumb = fit_thumbnail(open_rgb(uploaded_model), 200)
        st.image(thumb, use_container_width=False)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Up to 3 fabric swatches (batch upload) ───────────────
    st.markdown("**Fabric Swatches** (up to 3)")
    raw_fabrics = st.file_uploader(
        "Drop 1–3 fabric swatches here", type=["jpg","jpeg","png"],
        accept_multiple_files=True,
        key="fabric_upload", label_visibility="collapsed",
    )
    # Validate count
    if len(raw_fabrics) > 3:
        st.warning("⚠️  Maximum 3 swatches allowed — only the first 3 will be used.")
    uploaded_fabrics = raw_fabrics[:3]

    if uploaded_fabrics:
        swatch_cols = st.columns(len(uploaded_fabrics))
        for uf, col in zip(uploaded_fabrics, swatch_cols):
            with col:
                st.markdown(f'<div class="filename-pill">🧵 {uf.name}</div>',
                            unsafe_allow_html=True)
                thumb = fit_thumbnail(open_rgb(uf), 200)
                st.image(thumb, use_container_width=True)

# ══════════════════════════════════════════════
# PANE 2 — OUTPUT
# ══════════════════════════════════════════════
with pane_output:
    st.subheader("Output")
    output_slot = st.empty()

    # Show persistent result if it exists in session state
    if "persistent_result_img" in st.session_state:
        output_slot.image(
            st.session_state["persistent_result_img"],
            caption=st.session_state.get("persistent_caption", "Fabric swap result"),
            use_container_width=True,
        )
    else:
        output_slot.markdown(
            '<div class="output-placeholder">Awaiting execution…</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════
# PANE 3 — CONTROLS
# ══════════════════════════════════════════════
with pane_controls:
    st.subheader("Controls")

    demo_mode = st.toggle(
        "🎭  Demo Mode",
        value=False,
        help=(
            "ON  → Bypasses API, shows pre-generated image.\n"
            "OFF → Runs live Gemini pipeline."
        ),
        key="demo_toggle",
    )

    st.markdown(" ")

    garment_zone = st.radio(
        "Target garment",
        options=["upper", "lower"],
        format_func=lambda x:
            "👕 Upper Body" if x == "upper" else "👖 Lower Body",
        index=0,
        key="garment_zone",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    execute_btn = st.button("🚀  Execute Fabric Swap", use_container_width=True)

    st.markdown(" ")

    # Download — reads from session_state so clicking never wipes the image
    if "persistent_result_img" in st.session_state:
        st.download_button(
            label="⬇️  Download as JPG",
            data=pil_to_bytes(st.session_state["persistent_result_img"]),
            file_name=f"eikon_{int(time.time())}.jpg",
            mime="image/jpeg",
            use_container_width=True,
        )


# ─────────────────────────────────────────────
# EXECUTE HANDLER
# ─────────────────────────────────────────────
if execute_btn:

    # ── DEMO MODE ────────────────────────────
    if demo_mode:
        with st.spinner("Demo Mode — loading pre-generated result…"):
            time.sleep(3)
        try:
            demo_img = Image.open(DEMO_IMAGE_PATH).convert("RGB")
            if uploaded_model:
                ref = open_rgb(uploaded_model)
                demo_img = match_dimensions(demo_img, *ref.size)
            st.session_state["persistent_result_img"] = demo_img
            st.session_state["persistent_caption"]    = "Demo output"
            st.rerun()
        except FileNotFoundError:
            with pane_output:
                st.error(f"Demo image `{DEMO_IMAGE_PATH}` not found.")

    # ── LIVE MODE ────────────────────────────
    else:
        if uploaded_model is None:
            with pane_controls:
                st.warning("⚠️  Upload a Base Model Image first.")
        elif len(uploaded_fabrics) == 0:
            with pane_controls:
                st.warning("⚠️  Upload at least one Fabric Swatch.")
        else:
            model_img   = open_rgb(uploaded_model)
            fabric_imgs = [open_rgb(f) for f in uploaded_fabrics]
            target_w, target_h = model_img.size

            # STEP 1 — consensus analysis
            progress_slot = st.empty()
            progress_slot.info("⚙️ Step 1/2: Analyzing fabric composition...")
            try:
                consolidated_fabric_consensus = extract_consensus(
                    model_img, fabric_imgs
                )
            except Exception as e:
                progress_slot.empty()
                with pane_output:
                    st.error(f"Step 1 error (fabric analysis): {e}")
                st.stop()

            # STEP 2 — image swap
            progress_slot.info("🚀 Step 2/2: Generating final picture...")
            try:
                prompt_text = build_swap_prompt(
                    consolidated_fabric_consensus, garment_zone
                )

                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=[prompt_text, model_img, *fabric_imgs],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        http_options=types.HttpOptions(timeout=180_000),
                    ),
                )

                result_img = None
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if (part.inline_data is not None and
                            part.inline_data.mime_type.startswith("image/")):
                        result_img = Image.open(
                            io.BytesIO(part.inline_data.data)
                        ).convert("RGB")
                        break
                    if part.text:
                        text_parts.append(part.text)

                progress_slot.empty()

                if result_img is not None:
                    # Force exact pixel match — guards against zoom/crop hallucination
                    result_img = result_img.resize(model_img.size, Image.LANCZOS)
                    st.session_state["persistent_result_img"] = result_img
                    st.session_state["persistent_caption"] = (
                        f"Fabric swap — {garment_zone} body"
                    )
                    st.rerun()
                else:
                    fallback = " ".join(text_parts) or "No image returned."
                    with pane_output:
                        st.warning(
                            f"⚠️  Gemini returned text instead of an image.\n\n"
                            f"**Model said:** {fallback}\n\n"
                            f"Try a simpler swatch or enable Demo Mode."
                        )

            except Exception as e:
                progress_slot.empty()
                with pane_output:
                    st.error(
                        f"Gemini API error: {e}\n\n"
                        f"If this is a 503, try again in a few seconds."
                    )
