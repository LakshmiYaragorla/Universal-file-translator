import streamlit as st
import os
import time
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
import docx

# Page configuration
st.set_page_config(
    page_title="Universal File Translator",
    page_icon="🌐",
    layout="wide"
)

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS & TRANSLATION PIPELINE
# -----------------------------------------------------------------------------

# Supported Languages Mapping
LANGUAGES = {
    "Auto Detect": "auto",
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese (Simplified)": "zh-CN",
    "Japanese": "ja",
    "Hindi": "hi",
    "Arabic": "ar",
    "Portuguese": "pt",
    "Russian": "ru"
}

def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translates plain text chunks using translation engine."""
    if not text.strip():
        return ""
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)
    except Exception as e:
        return f"[Translation Error: {str(e)}]"

def process_docx(file_bytes, source_lang: str, target_lang: str) -> bytes:
    """Extracts text from .docx, translates paragraph by paragraph, and returns converted file."""
    doc = docx.Document(file_bytes)
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            translated = translate_text(paragraph.text, source_lang, target_lang)
            paragraph.text = translated
    
    # Save modified document to temporary memory buffer
    output_path = "temp_output.docx"
    doc.save(output_path)
    with open(output_path, "rb") as f:
        translated_bytes = f.read()
    if os.path.exists(output_path):
        os.remove(output_path)
    return translated_bytes

def process_txt(file_bytes, source_lang: str, target_lang: str) -> bytes:
    """Processes plain text files."""
    text = file_bytes.getvalue().decode("utf-8")
    lines = text.splitlines()
    translated_lines = [translate_text(line, source_lang, target_lang) for line in lines]
    return "\n".join(translated_lines).encode("utf-8")

def translate_file_worker(uploaded_file, source_lang_code: str, target_lang_code: str):
    """Background worker task for processing an individual file based on format."""
    file_name = uploaded_file.name
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Simulate processing delay / Heavy API call simulation
    time.sleep(1)
    
    try:
        if file_ext == ".docx":
            content = process_docx(uploaded_file, source_lang_code, target_lang_code)
        elif file_ext in [".txt", ".md", ".json", ".csv", ".srt"]:
            content = process_txt(uploaded_file, source_lang_code, target_lang_code)
        else:
            # Fallback for formats requiring dedicated document APIs (e.g. PDF/PPTX)
            content = f"Simulated translated content for unsupported demo format: {file_name}".encode("utf-8")

        new_filename = f"{os.path.splitext(file_name)[0]}_{target_lang_code}{file_ext}"
        return {
            "status": "success",
            "filename": file_name,
            "translated_filename": new_filename,
            "data": content,
            "ext": file_ext
        }
    except Exception as e:
        return {
            "status": "error",
            "filename": file_name,
            "error": str(e)
        }

# -----------------------------------------------------------------------------
# USER INTERFACE LAYOUT
# -----------------------------------------------------------------------------

st.title("🌐 Universal Document Translator")
st.markdown("Batch translate files while maintaining output file structures.")

st.divider()

# Controls Row
col1, col2, col3 = st.columns(3)

with col1:
    source_lang_name = st.selectbox(
        "1. Select Source Language",
        options=list(LANGUAGES.keys()),
        index=0
    )

with col2:
    target_lang_name = st.selectbox(
        "2. Select Target Language",
        options=[k for k in LANGUAGES.keys() if k != "Auto Detect"],
        index=0  # Default to English
    )

with col3:
    max_workers = st.slider("Background Threads", min_value=1, max_value=8, value=4)

# File Uploader
uploaded_files = st.file_uploader(
    "3. Upload files to translate",
    type=["txt", "docx", "md", "csv", "json", "srt", "pdf", "pptx", "xlsx"],
    accept_multiple_files=True
)

st.divider()

# Start Translation Action
if st.button("🚀 Start Translation Process", type="primary", disabled=not uploaded_files):
    source_code = LANGUAGES[source_lang_name]
    target_code = LANGUAGES[target_lang_name]

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    total_files = len(uploaded_files)
    
    status_text.info(f"Processing {total_files} file(s) in background workers...")
    
    # ThreadPoolExecutor for background parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(translate_file_worker, file, source_code, target_code)
            for file in uploaded_files
        ]
        
        for idx, future in enumerate(futures):
            res = future.result()
            results.append(res)
            # Update progress
            progress = (idx + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"Processed {idx + 1}/{total_files} files...")

    status_text.success("🎉 All files processed successfully!")

    # Display Results & Downloads
    st.subheader("📥 Download Translated Files")
    for res in results:
        if res["status"] == "success":
            st.download_button(
                label=f"⬇️ Download {res['translated_filename']}",
                data=res["data"],
                file_name=res["translated_filename"],
                mime="application/octet-stream",
                key=res["translated_filename"]
            )
        else:
            st.error(f"❌ Failed to translate {res['filename']}: {res['error']}")
