import streamlit as st
import time
import requests
import replicate
import io
from PIL import Image

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Neural Threads Fabric Lab")

st.title("🧵 Neural Threads Fabric Lab")
st.caption("Industrial Material Swapping · Latent Diffusion Matrix Compiler")
st.write("---")

# ─────────────────────────────────────────────
# ▼▼▼  PASTE YOUR REPLICATE API TOKEN HERE  ▼▼▼
# ─────────────────────────────────────────────
# Option A — hardcode for local testing (NOT for sharing):
REPLICATE_API_TOKEN = "r8_PVvQTYQ2WFiwxHrXpUvz2mc07LvrfPl041rCT"

# Option B (recommended for deployment) — use Streamlit secrets:
# 1. Create a file at .streamlit/secrets.toml
# 2. Add this line:  REPLICATE_API_TOKEN = "r8_your_token_here"
# 3. Then replace the line above with:
#    REPLICATE_API_TOKEN = st.secrets["REPLICATE_API_TOKEN"]
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# DEMO MODE — Pre-load your backup images here
# ─────────────────────────────────────────────
DEMO_IMAGES = {
    "Model_Charlie (Opaque Dress)":   "demo_charlie.jpg",   # ← put your pre-generated JPG filenames here
    "Model_Foxtrot (Tailored Suit)":  "demo_foxtrot.jpg",
    "Model_November (Fluid Silk)":    "demo_november.jpg",
}
# Place the demo image files in the SAME folder as app.py.
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# LAYOUT: Three columns
# ─────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1.5, 2], gap="large")

# ══════════════════════════════════════════════
# COLUMN 1 — SOURCE ASSETS
# ══════════════════════════════════════════════
with col1:
    st.subheader("1. Source Assets")

    model_choice = st.selectbox(
        "Target Model / Garment Archetype:",
        list(DEMO_IMAGES.keys())
    )
    uploaded_model = st.file_uploader(
        "Upload Custom Model Image (.jpg/.png)",
        type=["jpg", "jpeg", "png"],
        key="model_upload"
    )

    st.write("---")

    fabric_choice = st.selectbox(
        "Select Reference Fabric Swatch:",
        ["FA003 (Airy Open-Weave Linen)",
         "FA004 (Parallel Black-Stitch Knit)",
         "FA005 (Structured Cotton)"]
    )
    uploaded_fabric = st.file_uploader(
        "Upload Custom Fabric Swatch (.jpg/.png)",
        type=["jpg", "jpeg", "png"],
        key="fabric_upload"
    )

    st.write("---")

    # ── DEMO MODE TOGGLE ──────────────────────
    demo_mode = st.toggle(
        "🎭 Demo Mode (Offline)",
        value=False,
        help=(
            "ON  → Bypasses the API. Uses your pre-generated images. "
            "Safe for live presentations.\n"
            "OFF → Calls Replicate API with your uploaded images."
        )
    )
    if demo_mode:
        st.success("Demo Mode ON — API bypassed. Using pre-generated images.")
    else:
        st.info("Live Mode — Replicate API will be called on Execute.")

# ══════════════════════════════════════════════
# COLUMN 2 — MATERIAL CHARACTERISTICS
# ══════════════════════════════════════════════
with col2:
    st.subheader("2. Material Characteristics")
    st.write("Define the precise physical parameters of the target fabric:")

    weight = st.radio(
        "Textile Weight:",
        ["Ultra-Lightweight", "Medium-Weight", "Heavy-Duty", "Rigid/Structured"],
        index=0
    )
    opacity = st.radio(
        "Optical Opacity / Translucency:",
        ["Pure Opaque", "Semi-Sheer / Open-Weave", "Translucent / Airborne Physics"],
        index=0
    )
    elasticity = st.radio(
        "Elasticity & Stretch:",
        ["Stiff / Zero Mechanical Stretch", "Slight Mechanical Give", "High Elasticity / Fluid Knit"],
        index=1
    )

    st.write("---")

    # Build the compiled prompt
    compiled_prompt = (
        f"Fashion editorial photograph. "
        f"1:1 fabric pattern swap on {model_choice.split('(')[0].strip()}. "
        f"Reference fabric: {fabric_choice}. "
        f"Textile weight: {weight.lower()}. "
        f"Opacity: {opacity.lower()}. "
        f"Stretch: {elasticity.lower()}. "
        f"Lock original silhouette, body pose, identity, and background exactly. "
        f"Re-materialize only the garment fabric with geometric pattern continuity "
        f"across all 3D curves, folds, and compressed fabric zones. "
        f"High resolution, professional studio lighting."
    )

    negative_prompt = (
        "deformed body, changed silhouette, different pose, different person, "
        "wrong proportions, blurry, low quality, watermark, artifacts"
    )

    st.text_area(
        "Compiled Prompt Payload:",
        value=compiled_prompt,
        height=140,
        disabled=True
    )

    generate_btn = st.button("🚀 Execute Latent Swap Engine", use_container_width=True)

# ══════════════════════════════════════════════
# COLUMN 3 — OUTPUT VIEWPORT
# ══════════════════════════════════════════════
with col3:
    st.subheader("3. Outcome Viewport")
    output_placeholder = st.empty()
    download_placeholder = st.empty()
    output_placeholder.info("Awaiting execution… Select assets and press Execute.")

    if generate_btn:

        # ── DEMO MODE PATH ────────────────────────────────────────────────
        if demo_mode:
            with st.spinner("Demo Mode: Loading pre-generated result…"):
                time.sleep(3)  # simulates realistic loading for the presentation

            demo_path = DEMO_IMAGES.get(model_choice)
            try:
                demo_img = Image.open(demo_path)
                output_placeholder.image(demo_img, caption=f"Demo Output — {model_choice}", use_container_width=True)

                # Download button
                buf = io.BytesIO()
                demo_img.save(buf, format="JPEG", quality=95)
                download_placeholder.download_button(
                    label="⬇️ Download as JPG",
                    data=buf.getvalue(),
                    file_name=f"neural_threads_demo_{int(time.time())}.jpg",
                    mime="image/jpeg"
                )
            except FileNotFoundError:
                output_placeholder.error(
                    f"Demo image '{demo_path}' not found. "
                    f"Place your pre-generated JPGs in the same folder as app.py."
                )

        # ── LIVE API PATH ─────────────────────────────────────────────────
        else:
            if uploaded_model is None:
                output_placeholder.warning("⚠️ Please upload a model image to use Live Mode.")
            else:
                with st.spinner("Neural Engine: Running img2img latent diffusion…"):
                    try:
                        # Set the API token for this session
                        import os
                        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

                        # Prepare inputs
                        model_bytes = uploaded_model.read()
                        model_img   = io.BytesIO(model_bytes)

                        # Build input dict — fabric swatch used to enrich the prompt
                        # (for IP-Adapter texture injection, swap the model ID below)
                        input_payload = {
                            "image":           model_img,
                            "prompt":          compiled_prompt,
                            "negative_prompt": negative_prompt,

                            # ── img2img strength ──────────────────────────
                            # 0.0 = identical to source, 1.0 = fully regenerated
                            # 0.55–0.70 is the sweet spot for silhouette-locked fabric swap
                            "prompt_strength": 0.62,

                            "num_inference_steps": 30,
                            "guidance_scale":      7.5,
                            "scheduler":           "DPMSolverMultistep",
                            "num_outputs":         1,
                        }

                        # ── REPLICATE MODEL ID ────────────────────────────
                        # Current endpoint: SDXL img2img (silhouette-preserving)
                        # To switch to IP-Adapter (for texture injection from swatch),
                        # replace the model string with:
                        # "lucataco/ip-adapter-sdxl:a4a8bafd6089e1716b06057c42b19378250d008b4fe1c752748f07b03de89e6"
                        output = replicate.run(
                            "stability-ai/sdxl:7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd72c19b408e8",
                            input=input_payload
                        )

                        # output is a list of image URLs
                        result_url = output[0]
                        result_img_data = requests.get(result_url).content
                        result_img = Image.open(io.BytesIO(result_img_data))

                        output_placeholder.image(
                            result_img,
                            caption="AI Fabric Swap Output",
                            use_container_width=True
                        )

                        # Download button
                        buf = io.BytesIO()
                        result_img.save(buf, format="JPEG", quality=95)
                        download_placeholder.download_button(
                            label="⬇️ Download as JPG",
                            data=buf.getvalue(),
                            file_name=f"neural_threads_{int(time.time())}.jpg",
                            mime="image/jpeg"
                        )

                    except replicate.exceptions.ReplicateError as e:
                        output_placeholder.error(f"Replicate API error: {e}")
                    except Exception as e:
                        output_placeholder.error(f"Unexpected error: {e}")
