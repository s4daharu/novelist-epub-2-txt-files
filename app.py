import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter, Language
import code_snippets as code_snippets
import tiktoken
import streamlit.components.v1 as components
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os

def extract_chapters(epub_content):
    """Extracts chapters from EPUB content bytes using a temporary file."""
    chapters = []
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(epub_content)
        tmp_file_name = tmp_file.name
    try:
        book = epub.read_epub(tmp_file_name)
        for item in book.get_items():
            if item.get_type() == epub.EpubHtml or item.get_name().endswith('.xhtml'):
                try:
                    content = item.get_content().decode('utf-8')
                except Exception:
                    try:
                        content = item.get_content().decode('gb18030')
                    except Exception:
                        content = item.get_content().decode('latin-1', errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator="\n")
                chapters.append(text)
    finally:
        os.unlink(tmp_file_name)  # Clean up temporary file
    return chapters

# Initialize session state variables
if 'chapter_index' not in st.session_state:
    st.session_state.chapter_index = 0
if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'input_method' not in st.session_state:
    st.session_state.input_method = None

# -------------------------
# Configuration
# -------------------------
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 10
LENGTH_FUNCTION_CHOICE = "Characters"
SPLITTER_CHOICE = "Character"
PREFIX = "translate following text from chinese to english\n"

# Length function setup
if LENGTH_FUNCTION_CHOICE == "Characters":
    length_function = len
elif LENGTH_FUNCTION_CHOICE == "Tokens":
    enc = tiktoken.get_encoding("cl100k_base")
    def length_function(text: str) -> int:
        return len(enc.encode(text))

# -------------------------
# Input Method Selection
# -------------------------
input_method = st.radio("Input Method", ["Upload EPUB", "Input Text"], 
                        horizontal=True, key="input_method_selector")

if input_method == "Upload EPUB":
    uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])
    
    if uploaded_file:
        # Clear previous input data
        st.session_state.input_method = "EPUB"
        st.session_state.chapters = extract_chapters(uploaded_file.read())
        st.session_state.chapter_index = 0
        st.success(f"Loaded {len(st.session_state.chapters)} chapters")
        
        # Clear EPUB button
        if st.button("🗑️ Clear EPUB"):
            st.session_state.input_method = None
            st.session_state.chapters = []
            st.session_state.chapter_index = 0
            st.experimental_rerun()
        
elif input_method == "Input Text":
    raw_text = st.text_area("Paste your text here", height=300, key="raw_input")
    
    # Input text action buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✅ Use This Text"):
            st.session_state.input_method = "Text"
            st.session_state.chapters = [raw_text]
            st.session_state.chapter_index = 0
            st.success("Text loaded successfully!")
    with col2:
        if st.button("🗑️ Clear Text"):
            st.session_state.input_method = None
            st.session_state.chapters = []
            st.session_state.chapter_index = 0
            st.experimental_rerun()

# -------------------------
# Display Section
# -------------------------
if st.session_state.input_method == "EPUB" and st.session_state.chapters:
    # Chapter navigation for EPUB
    chapter_numbers = list(range(1, len(st.session_state.chapters) + 1))
    selected_chapter = st.selectbox("Chapter Number", chapter_numbers, 
                                    index=st.session_state.chapter_index)
    st.session_state.chapter_index = selected_chapter - 1
    
    st.markdown(f"### Chapter {st.session_state.chapter_index + 1}")
    current_text = st.session_state.chapters[st.session_state.chapter_index]
    st.text_area("Chapter Text", value=current_text, height=300, 
                 key=f"chapter_{st.session_state.chapter_index}")

elif st.session_state.input_method == "Text" and st.session_state.chapters:
    st.markdown("### Input Text")
    current_text = st.session_state.chapters[0]
    st.text_area("Text Content", value=current_text, height=300, key="raw_display")

# -------------------------
# Common Processing
# -------------------------
if st.session_state.chapters:
    # Navigation buttons for EPUB
    if st.session_state.input_method == "EPUB":
        nav_col1, nav_col2 = st.columns([1, 1])
        with nav_col1:
            if st.button("← Previous", use_container_width=True) and st.session_state.chapter_index > 0:
                st.session_state.chapter_index -= 1
                st.experimental_rerun()
        with nav_col2:
            if st.button("Next →", use_container_width=True) and st.session_state.chapter_index < len(st.session_state.chapters)-1:
                st.session_state.chapter_index += 1
                st.experimental_rerun()
    
    # Split text button
    if st.button("SplitOptions"):
        doc = st.session_state.chapters[st.session_state.chapter_index] if st.session_state.input_method == "EPUB" else st.session_state.chapters[0]
        
        if not doc:
            st.error("No text to process!")
        else:
            try:
                # Splitter selection logic remains the same
                # ... (existing splitter code from original app)
                splits = splitter.split_text(doc)
                split_chunks = [PREFIX + s for s in splits]
                
                for idx, chunk in enumerate(split_chunks, 1):
                    st.text_area(f"Chunk {idx}", value=chunk, height=200, key=f"chunk_{idx}")
                    components.html(f"""
                    <button onclick="navigator.clipboard.writeText(`{chunk}`)"
                        style="background:#f63366;color:white;border:none;padding:8px 12px;border-radius:5px;cursor:pointer;width:100%;">
                        📋 Copy Chunk {idx}
                    </button>
                    """, height=50)
            except Exception as e:
                st.error(f"Error: {str(e)}")