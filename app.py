import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import streamlit.components.v1 as components
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os
import json

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
        os.unlink(tmp_file_name)
    return chapters

# Initialize session state variables
if 'chapter_index' not in st.session_state:
    st.session_state.chapter_index = 0
if 'uploaded_epub' not in st.session_state:
    st.session_state.uploaded_epub = None
if 'chapters' not in st.session_state:
    st.session_state.chapters = []

# -------------------------
# Configuration with improvements
# -------------------------
CHUNK_SIZE = 500  # Token-based size
CHUNK_OVERLAP = 50
PREFIX = "translate following text from chinese to english\n"

# Tokenizer setup
enc = tiktoken.get_encoding("cl100k_base")
def length_function(text: str) -> int:
    return len(enc.encode(text))

prefix_tokens = length_function(PREFIX)
adjusted_chunk_size = CHUNK_SIZE - prefix_tokens

# UI elements for configuration
st.sidebar.subheader("Splitting Configuration")
splitter_language = st.sidebar.selectbox("Splitter Language", 
                                        ["Chinese", "English", "Other"],
                                        index=0)
show_token_counts = st.sidebar.checkbox("Show token counts", value=True)

# Separator selection based on language
if splitter_language == "Chinese":
    separators = ["。", "！", "？", "\n\n", "\n", ""]
elif splitter_language == "English":
    separators = ["\n\n", "\n", " ", ""]
else:
    separators = ["\n\n", "\n", " ", ""]

# -------------------------
# EPUB Upload Handling
# -------------------------
uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])

if uploaded_file:
    st.session_state.uploaded_epub = uploaded_file.read()
    st.session_state.chapters = extract_chapters(st.session_state.uploaded_epub)

if st.session_state.chapters:
    # Chapter management UI
    clear_col1, clear_col2 = st.columns([3, 1])
    with clear_col1:
        st.success(f"Loaded {len(st.session_state.chapters)} chapters")
    with clear_col2:
        if st.button("🗑️ Clear EPUB"):
            st.session_state.uploaded_epub = None
            st.session_state.chapters = []
            st.session_state.chapter_index = 0

    # Chapter selection and navigation
    chapter_numbers = list(range(1, len(st.session_state.chapters)+1))
    selected_chapter = st.selectbox("Chapter Number", chapter_numbers, 
                                    index=st.session_state.chapter_index)
    st.session_state.chapter_index = selected_chapter - 1

    st.markdown(f"### Chapter {selected_chapter}")
    current_chapter = st.session_state.chapters[st.session_state.chapter_index]
    st.text_area("Chapter Text", value=current_chapter, height=300,
                 key=f"chapter_{st.session_state.chapter_index}")

    nav_col1, nav_col2 = st.columns([1, 1])
    with nav_col1:
        if st.button("← Previous", use_container_width=True) and st.session_state.chapter_index > 0:
            st.session_state.chapter_index -= 1
    with nav_col2:
        if st.button("Next →", use_container_width=True) and st.session_state.chapter_index < len(st.session_state.chapters)-1:
            st.session_state.chapter_index += 1

# -------------------------
# Text Processing Section
# -------------------------
if st.button("SplitOptions"):
    current_text = st.session_state.chapters[st.session_state.chapter_index] if st.session_state.chapters else ""
    if not current_text:
        st.error("No text to process!")
    else:
        try:
            # Create splitter with language-specific configuration
            splitter = RecursiveCharacterTextSplitter(
                separators=separators,
                chunk_size=adjusted_chunk_size,
                chunk_overlap=CHUNK_OVERLAP,
                length_function=length_function
            )
            
            splits = splitter.split_text(current_text)
            valid_chunks = []
            
            for s in splits:
                chunk = PREFIX + s
                chunk_length = length_function(chunk)
                
                if chunk_length <= CHUNK_SIZE:
                    valid_chunks.append(chunk)
                else:
                    st.warning(f"Oversized chunk skipped ({chunk_length} tokens)")

            # Display results
            st.subheader(f"Created {len(valid_chunks)} chunks:")
            for idx, chunk in enumerate(valid_chunks, 1):
                # Token count display
                if show_token_counts:
                    st.caption(f"Tokens: {length_function(chunk)} / {CHUNK_SIZE}")
                
                # Scrollable text area
                st.text_area(
                    label=f"Chunk {idx}",
                    value=chunk,
                    height=150,
                    key=f"chunk_{st.session_state.chapter_index}_{idx}",
                    label_visibility="visible"
                )
                
                # Enhanced copy button
                components.html(f"""
                <div style="margin: 5px 0;">
                    <button onclick="navigator.clipboard.writeText({json.dumps(chunk)})"
                        style="
                            padding: 0.5rem 1rem;
                            background: #f63366;
                            color: white;
                            border: none;
                            border-radius: 0.375rem;
                            cursor: pointer;
                            transition: all 0.2s ease;
                            width: 100%;
                            font-size: 0.9rem;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        "
                        onmouseover="this.style.backgroundColor='#d52f5b'"
                        onmouseout="this.style.backgroundColor='#f63366'">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clipboard" viewBox="0 0 16 16" style="margin-right: 8px;">
                            <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2H4zM3 3.5h10a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z"/>
                        </svg>
                        Copy Chunk {idx}
                    </button>
                </div>
                """, height=60)

        except Exception as e:
            st.error(f"Processing error: {str(e)}")