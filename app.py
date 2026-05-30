import streamlit as st
import replicate
import requests
import os
import io
import time
from PIL import Image
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
#   REPLICATE_API_TOKEN = "r8_your_token_here"
# Locally → .streamlit/secrets.toml (add to .gitignore)
# ─────────────────────────────────────────────
os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]

# ─────────────────────────────────────────────
# DEMO MODE — place pre-generated JPGs in the
# same folder as app.py and update paths below.
# ─────────────────────────────────────────────
DEMO_IMAGE_PATH = "demo_output.jpg"

# ─────────────────────────────────────────────
# LOOKBOOK CSS OVERHAUL
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

  /* ── Sidebar (if ever used) ── */
  [data-testid="stSidebar"] {
    background-color: #F5F0E8 !important;
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
  [data-testid="stFileUploadDropzone"] label {
    color: #777 !important;
    font-size: 0.8rem !important;
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
  .stButton > button:active {
    transform: translateY(0) !important;
  }

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
  .stDownloadButton > button:hover {
    background-color: #333333 !important;
  }

  /* ── Toggle ── */
  [data-testid="stToggle"] label {
    color: #000000 !important;
    font-weight: 600 !important;
  }

  /* ── Info / success / warning boxes ── */
  [data-testid="stAlert"] {
    border-radius: 10px !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06) !important;
  }

  /* ── Filename display pill ── */
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

  /* ── Output image container ── */
  .output-wrap {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  }

  /* ── Divider ── */
  hr {
    border: none !important;
    border-top: 1px solid #EDE8E0 !important;
    margin: 1.5rem 0 !important;
  }

  /* ── Spinner text ── */
  [data-testid="stSpinner"] p {
    color: #555 !important;
    font-style: italic !important;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPER: extract readable name from filename
# ─────────────────────────────────────────────
def fabric_name_from_file(uploaded_file) -> str:
    """
    Turns 'Structured_Cotton.jpg' → 'Structured Cotton'
    Turns 'airy-open-weave-linen.PNG' → 'Airy Open Weave Linen'
    """
    stem = Path(uploaded_file.name).stem          # strip extension
    name = stem.replace("_", " ").replace("-", " ")
    return name.title()


def build_prompt(fabric_name: str) -> tuple[str, str]:
    prompt = (
        f"Fashion editorial photograph. "
        f"Fabric swap: re-materialize the garment using {fabric_name} textile. "
        f"Preserve the exact body pose, silhouette, identity, and background. "
        f"Apply the fabric texture with geometric continuity across all 3D garment "
        f"curves, folds, and compressed zones. "
        f"High resolution, professional studio lighting, minimalist lookbook aesthetic."
    )
    negative = (
        "deformed body, changed silhouette, different pose, different person, "
        "wrong proportions, blurry, low quality, watermark, artifacts, nudity"
    )
    return prompt, negative


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
# DEMO MODE TOGGLE (top of page, always visible)
# ─────────────────────────────────────────────
demo_mode = st.toggle(
    "🎭  Demo Mode (Offline — safe for live presentations)",
    value=False,
    help=(
        "ON  → Bypasses the API entirely. Simulates loading, then shows your "
        "pre-generated image. Guaranteed not to fail during your presentation.\n"
        "OFF → Calls the Replicate API live with your uploaded images."
    )
)
if demo_mode:
    st.success("**Demo Mode ON** — API is bypassed. Pre-generated image will display after simulated loading.")
else:
    st.info("**Live Mode** — Replicate img2img API will be called on Execute.")

st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN LAYOUT: 2 columns
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

    st.markdown("<br>", unsafe_allow_html=True)
    execute_btn = st.button("🚀  Execute Fabric Swap", use_container_width=True)

# ══════════════════════════════════════════════
# RIGHT COLUMN — OUTPUT VIEWPORT
# ══════════════════════════════════════════════
with col_right:
    st.subheader("Output Viewport")
    st.markdown(" ")

    output_slot  = st.empty()
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
            with st.spinner("Simulating neural engine… (Demo Mode)"):
                time.sleep(3)
            try:
                demo_img = Image.open(DEMO_IMAGE_PATH)
                output_slot.markdown(
                    '<div class="output-wrap">', unsafe_allow_html=True
                )
                output_slot.image(
                    demo_img,
                    caption="Demo Output — pre-generated result",
                    use_container_width=True
                )
                buf = io.BytesIO()
                demo_img.save(buf, format="JPEG", quality=95)
                download_slot.download_button(
                    label="⬇️  Download as JPG",
                    data=buf.getvalue(),
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
                prompt, negative_prompt = build_prompt(fabric_name)

                with st.spinner(f"Neural engine running… applying '{fabric_name}' fabric…"):
                    try:
                        model_bytes  = uploaded_model.read()
                        model_stream = io.BytesIO(model_bytes)

                        output = replicate.run(
                            # SDXL img2img — current latest version (verified May 2026)
                            # Full hash required — short hashes cause 422 errors.
                            # To use IP-Adapter (texture injection from swatch image), replace with:
                            # "lucataco/ip-adapter-sdxl:a4a8bafd6089e1716b06057c42b19378250d008b4fe1c752748f07b03de89e6"
                            "stability-ai/sdxl:7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc",
                            input={
                                "image":           model_stream,
                                "prompt":          prompt,
                                "negative_prompt": negative_prompt,
                                # 0.55–0.70: sweet spot for silhouette lock + fabric change
                                # Lower = closer to source image
                                "prompt_strength": 0.62,
                                "num_inference_steps": 30,
                                "guidance_scale":  7.5,
                                "scheduler":       "DPMSolverMultistep",
                                "num_outputs":     1,
                            }
                        )

                        result_url      = output[0]
                        result_bytes    = requests.get(result_url).content
                        result_img      = Image.open(io.BytesIO(result_bytes))

                        output_slot.image(
                            result_img,
                            caption=f"Fabric swap — {fabric_name}",
                            use_container_width=True
                        )

                        buf = io.BytesIO()
                        result_img.save(buf, format="JPEG", quality=95)
                        download_slot.download_button(
                            label="⬇️  Download as JPG",
                            data=buf.getvalue(),
                            file_name=f"neural_threads_{int(time.time())}.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )

                    except replicate.exceptions.ReplicateError as e:
                        output_slot.error(f"Replicate API error: {e}")
                    except Exception as e:
                        output_slot.error(f"Unexpected error: {e}")
