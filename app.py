import streamlit as st
from langchain.text_splitter import (RecursiveCharacterTextSplitter,
                                   CharacterTextSplitter, Language)
import tiktoken
import tempfile
import os
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List
import streamlit.components.v1 as components

# ---------- Cached Resources ----------
@st.cache_resource
def get_encoder():
    return tiktoken.get_encoding("cl100k_base")

# ---------- Helper Functions ----------
def extract_chapters(epub_file_path: str) -> List[str]:
    """Extracts chapters from an EPUB file with proper error handling."""
    chapters = []
    try:
        book = epub.read_epub(epub_file_path)
        for item in book.get_items():
            if item.get_type() == epub.EpubHtml or item.get_name().endswith('.xhtml'):
                try:
                    content = item.get_body_content().decode('utf-8')
                except UnicodeDecodeError:
                    content = item.get_body_content().decode('latin-1', errors='ignore')
                
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator="\n").strip()
                if text:
                    chapters.append(text)
    except epub.EpubException as e:
        st.error(f"Invalid EPUB file: {str(e)}")
    return chapters

# ---------- Session State Management ----------
def reset_state():
    keys_to_keep = ["file_uploader_key"]
    new_state = {k: v for k, v in st.session_state.items() if k in keys_to_keep}
    st.session_state.clear()
    st.session_state.update(new_state)
    st.session_state.file_uploader_key = st.session_state.get("file_uploader_key", 0) + 1

# ---------- UI Configuration ----------
st.set_page_config(page_title="Text Splitter Pro", layout="wide")
st.title("Text Splitter with EPUB Support")

# Initialize session state
if "split_chunks" not in st.session_state:
    st.session_state.split_chunks = []
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

# ---------- Input Method Selection ----------
input_method = st.radio("Input Method", ["Manual Input", "Upload EPUB"], index=1)

# ---------- Text Splitter Configuration ----------
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1:
    chunk_size = st.number_input("Chunk Size", min_value=1, max_value=8191, value=1950,
                               help="Should match your LLM's context window size")

with col2:
    chunk_overlap = st.number_input("Chunk Overlap", min_value=1, 
                                  max_value=chunk_size-1 if chunk_size else 100, 
                                  value=40)

with col3:
    length_function = len if st.selectbox("Length Function", ["Characters", "Tokens"], index=0) == "Characters" \
        else lambda text: len(get_encoder().encode(text))

with col4:
    splitter_choice = st.selectbox("Text Splitter", 
                                 ["Character", "RecursiveCharacter"] + [lang.value for lang in Language],
                                 index=0)

# ---------- Help Documentation ----------
with st.expander("ℹ️ Help & Documentation"):
    st.markdown("""
    **Text Splitting Guide:**
    - **Character Splitter:** Simple split by paragraph breaks
    - **RecursiveCharacter:** Smart splitting that preserves structure
    - **Language-specific:** Optimized for programming languages
    """)

# ---------- Input Handling ----------
doc = ""
if input_method == "Manual Input":
    doc = st.text_area("Input Text:", height=300)
else:
    uploaded_file = st.file_uploader("Upload EPUB", type=["epub"], 
                                   key=st.session_state.file_uploader_key)
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_path = tmp_file.name
        
        with st.spinner("Extracting chapters..."):
            chapters = extract_chapters(tmp_path)
        
        os.unlink(tmp_path)  # Cleanup temp file

        if chapters:
            st.session_state.split_chunks = []  # Clear previous chunks
            st.success(f"Found {len(chapters)} chapters")
            selected_idx = st.selectbox("Chapter Selection", 
                                      range(len(chapters)),
                                      format_func=lambda x: f"Chapter {x+1}")
            doc = chapters[selected_idx]
            st.text_area("Chapter Content", doc, height=300)
        else:
            st.error("No readable chapters found in EPUB")

# ---------- Text Processing ----------
if st.button("Split Text"):
    if not doc.strip():
        st.error("Please provide valid input text")
        st.stop()
    
    try:
        if splitter_choice == "Character":
            splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function
            )
        elif splitter_choice == "RecursiveCharacter":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function
            )
        elif splitter_choice in [lang.value for lang in Language]:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=Language(splitter_choice),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function
            )
        else:
            raise ValueError("Invalid splitter choice")
        
        with st.spinner("Splitting text..."):
            splits = splitter.split_text(doc)
            st.session_state.split_chunks = [f"translate following text from chinese to english\n{s}" for s in splits]

        if not splits:
            st.warning("No chunks generated - try reducing chunk size")
            st.stop()

    except Exception as e:
        st.error(f"Processing error: {str(e)}")

# ---------- Display Chunks ----------
if st.session_state.split_chunks:
    st.subheader(f"Generated Chunks ({len(st.session_state.split_chunks)} total)")
    
    for idx, chunk in enumerate(st.session_state.split_chunks, 1):
        with st.container(border=True):
            # Display chunk text
            st.text_area(f"Chunk {idx}", chunk, height=200, key=f"chunk_{idx}_display")
            
            # Copy button with JavaScript
            components.html(
                f"""
                <textarea id="chunk_{idx}" style="display:none;">{chunk}</textarea>
                <button onclick="
                    navigator.clipboard.writeText(document.getElementById('chunk_{idx}').value);
                    window.parent.document.dispatchEvent(new CustomEvent('COPY_DONE', {{detail: {{idx: {idx}}}}));
                " style="margin: 5px 0;">
                    📋 Copy Chunk {idx}
                </button>
                """,
                height=40
            )

# Handle copy confirmation toast
if "copy_notification" in st.session_state:
    st.toast(f"Copied chunk {st.session_state.copy_notification} to clipboard!", icon="✅")
    del st.session_state.copy_notification

# JavaScript event listener for copy confirmation
components.html("""
<script>
    window.addEventListener('COPY_DONE', function(e) {
        Streamlit.setComponentValue(e.detail.idx);
    });
</script>
""")

# Handle the copy notification
if components.key in st.session_state:
    copied_idx = st.session_state[components.key]
    st.session_state.copy_notification = copied_idx

# ---------- Reset Controls ----------
st.button("🔄 Reset All", on_click=reset_state, help="Clear all inputs and results")
