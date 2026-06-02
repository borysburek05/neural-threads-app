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
    page_title="Neural Threads Fabric Lab",
    page_icon="🧵"
)

# ─────────────────────────────────────────────
# SECURITY: Load API key from Streamlit Secrets
# On Streamlit Cloud → App Settings → Secrets:
#   GOOGLE_API_KEY = "AIza_your_key_here"
# Locally → .streamlit/secrets.toml (add to .gitignore)
# ─────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

# Timeout is in milliseconds. 180_000 = 3 minutes.
# retry_options auto-retries on 503 (the exact error you were hitting).
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
# LOOKBOOK CSS — unchanged from previous version
# ─────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Hide Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }
  .stDeployButton { display: none; }

  /* ── Global background & font ── */
  html, body, [data-testid="stAppViewContainer"],
  [data-testid="stApp"], .main {
    background-color: #FAF7F2 !important;
    color: #000000 !important;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
  }

  /* ── Page title ── */
  h1 {
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    color: #000000 !important;
    margin-bottom: 0 !important;
  }

  /* ── Subheaders ── */
  h2, h3 {
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #000000 !important;
  }

  /* ── Caption / body text ── */
  p, .stMarkdown p, label,
  [data-testid="stText"] {
    color: #333333 !important;
    font-size: 0.875rem !important;
  }

  /* ── File uploader box ── */
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

  /* ── Primary Execute button ── */
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

  /* ── Download button ── */
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

  /* ── Toggle ── */
  [data-testid="stToggle"] label {
    color: #000000 !important;
    font-weight: 600 !important;
  }

  /* ── Alerts ── */
  [data-testid="stAlert"] {
    border-radius: 10px !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06) !important;
  }

  /* ── Filename pill ── */
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

  /* ── Divider ── */
  hr {
    border: none !important;
    border-top: 1px solid #EDE8E0 !important;
    margin: 1.5rem 0 !important;
  }

  /* ── Spinner ── */
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


def build_gemini_prompt(model_name: str, fabric_name: str,
                        weight: str, opacity: str) -> str:
    """
    Constructs the structured fabric-swap instruction sent to Gemini.
    Fills in the blanks in the required prompt template.
    """
    return (
        f"Task: 1:1 Fabric Pattern Swap.\n"
        f"Target Garment: The garment worn by the model in the first image.\n"
        f"Strict Constraints: Lock model identity, face, pose, background, "
        f"and all non-targeted garments to remain 100% identical.\n"
        f"Physics Rule: The original garment is {weight.lower()}; "
        f"the reference fabric is {fabric_name} ({opacity.lower()}).\n"
        f"Action: Preserve the original garment's exact silhouette. "
        f"Do not alter the fit or calculate new physics. "
        f"Simply replace the surface look, color and volume with the new "
        f"reference fabric shown in the second image, mapping it realistically "
        f"to the current folds and lighting of the original garment."
    )


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.title("NEURAL THREADS")
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
    "🎭  Demo Mode (Offline — safe for live presentations)",
    value=False,
    help=(
        "ON  → Bypasses the API entirely. Simulates loading then shows your "
        "pre-generated image. Guaranteed not to fail during your presentation.\n"
        "OFF → Calls the Gemini API live with your uploaded images."
    )
)
if demo_mode:
    st.success("**Demo Mode ON** — API is bypassed. Pre-generated image will display after simulated loading.")
else:
    st.info("**Live Mode** — Google Gemini image-editing API will be called on Execute.")

st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN LAYOUT — 2 columns
# ─────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.4], gap="large")

# ══════════════════════════════════════════════
# LEFT COLUMN — SOURCE ASSETS
# ══════════════════════════════════════════════
with col_left:
    st.subheader("Source Assets")
    st.markdown(" ")

    # ── Model Image ──────────────────────────
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

    st.markdown(" ")

    # ── Fabric Swatch ────────────────────────
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

    st.markdown(" ")

    # ── Physics hints (lightweight UI, feeds into prompt) ────
    with st.expander("⚙️  Optional physics hints", expanded=False):
        garment_weight = st.radio(
            "Original garment weight:",
            ["ultra-lightweight", "medium-weight", "heavy/structured"],
            index=0,
            horizontal=True
        )
        fabric_opacity = st.radio(
            "Reference fabric opacity:",
            ["fully opaque", "semi-sheer", "translucent"],
            index=0,
            horizontal=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    execute_btn = st.button("🚀  Execute Fabric Swap", use_container_width=True)

# ══════════════════════════════════════════════
# RIGHT COLUMN — OUTPUT VIEWPORT
# ══════════════════════════════════════════════
with col_right:
    st.subheader("Output Viewport")
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
                demo_img = Image.open(DEMO_IMAGE_PATH)
                output_slot.image(
                    demo_img,
                    caption="Demo Output — pre-generated result",
                    use_container_width=True
                )
                download_slot.download_button(
                    label="⬇️  Download as JPG",
                    data=pil_to_bytes(demo_img),
                    file_name=f"neural_threads_demo_{int(time.time())}.jpg",
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
                prompt_text = build_gemini_prompt(
                    model_name=uploaded_model.name,
                    fabric_name=fabric_name,
                    weight=garment_weight,
                    opacity=fabric_opacity
                )

                with st.spinner(f"Gemini is swapping fabric: '{fabric_name}'… (may take up to 2 min)"):
                    try:
                        # Read uploaded bytes once, then open as PIL
                        model_bytes  = uploaded_model.read()
                        fabric_bytes = uploaded_fabric.read()
                        model_img    = Image.open(io.BytesIO(model_bytes)).convert("RGB")
                        fabric_img   = Image.open(io.BytesIO(fabric_bytes)).convert("RGB")

                        # ── Gemini API call ───────────────────────────────────────────
                        # Model  : gemini-2.5-flash-image
                        #          The correct image-editing model for AI Studio keys.
                        #          (imagen-3.0-capability-001 edit_image() requires
                        #           Vertex AI — not available with an AI Studio key.)
                        #
                        # Contents order matters:
                        #   1. text prompt  — task instructions
                        #   2. model_img    — the garment photo to edit
                        #   3. fabric_img   — the reference texture to apply
                        #
                        # response_modalities=["IMAGE"] forces an image-only response,
                        # preventing the model from returning text instead of pixels.
                        # ─────────────────────────────────────────────────────────────
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

                        # ── Extract image from response parts ─────────────────────────
                        # The response is a list of parts; find the first inline_data
                        # part whose mime_type starts with "image/".
                        result_img   = None
                        text_parts   = []

                        for part in response.candidates[0].content.parts:
                            if part.inline_data is not None and \
                               part.inline_data.mime_type.startswith("image/"):
                                result_img = Image.open(
                                    io.BytesIO(part.inline_data.data)
                                ).convert("RGB")
                                break
                            if part.text:
                                text_parts.append(part.text)

                        # ── Render result ─────────────────────────────────────────────
                        if result_img is not None:
                            output_slot.image(
                                result_img,
                                caption=f"Fabric swap — {fabric_name}",
                                use_container_width=True,
                            )
                            download_slot.download_button(
                                label="⬇️  Download as JPG",
                                data=pil_to_bytes(result_img),
                                file_name=f"neural_threads_{int(time.time())}.jpg",
                                mime="image/jpeg",
                                use_container_width=True,
                            )
                        else:
                            # Model returned text instead of an image — show it so
                            # you can see exactly why it refused or what went wrong.
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
