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
    """Extracts chapters from EPUB content bytes using temporary file."""
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
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator="\n")
                chapters.append(text)
    finally:
        os.unlink(tmp_file_name)  # Clean up temporary file
    
    return chapters

# Initialize session state variables
if 'chapter_index' not in st.session_state:
    st.session_state.chapter_index = 0
if 'uploaded_epub' not in st.session_state:
    st.session_state.uploaded_epub = None
if 'chapters' not in st.session_state:
    st.session_state.chapters = []

# --------------------------------------------
# Instead of a radio to choose input method, we directly use EPUB upload.
# The "Manual Input" UI remains in the code (for potential future use)
# but is not displayed.
# --------------------------------------------
input_method = "Upload EPUB"

# Configuration Columns
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1:
    chunk_size = st.number_input("Chunk Size", min_value=1, value=1950)
with col2:
    chunk_overlap = st.number_input("Chunk Overlap", min_value=1, max_value=chunk_size-1, value=40)
    if chunk_overlap >= chunk_size:
        st.warning("Chunk Overlap should be less than Chunk Size!")
with col3:
    length_function_choice = st.selectbox("Length Function", ["Characters", "Tokens"], index=0)
with col4:
    splitter_choices = ["Character", "RecursiveCharacter"] + [str(v) for v in Language]
    splitter_choice = st.selectbox("Text Splitter", splitter_choices, index=0)

# Length Function Setup
if length_function_choice == "Characters":
    length_function = len
elif length_function_choice == "Tokens":
    enc = tiktoken.get_encoding("cl100k_base")
    def length_function(text: str) -> int:
        return len(enc.encode(text))

# Document Input Section
doc = ""
# The manual input area is still in the code below, but is not reached because
# input_method is fixed to "Upload EPUB".
if input_method == "Manual Input":
    doc = st.text_area("Paste your text here:")

elif input_method == "Upload EPUB":
    uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])
    
    # Store uploaded file in session state
    if uploaded_file:
        st.session_state.uploaded_epub = uploaded_file.read()
        st.session_state.chapters = extract_chapters(st.session_state.uploaded_epub)
    
    if st.session_state.chapters:
        # Clear session button
        clear_col1, clear_col2 = st.columns([3, 1])
        with clear_col1:
            st.success(f"Loaded {len(st.session_state.chapters)} chapters")
        with clear_col2:
            if st.button("🚮 Clear EPUB"):
                st.session_state.uploaded_epub = None
                st.session_state.chapters = []
                st.session_state.chapter_index = 0
                st.rerun()
        
        # Chapter Selection and Display
        chapter_numbers = list(range(1, len(st.session_state.chapters) + 1))
        selected_chapter = st.selectbox("Chapter Number", chapter_numbers, 
                                     index=st.session_state.chapter_index)
        st.session_state.chapter_index = selected_chapter - 1

        st.markdown(f"### Chapter {st.session_state.chapter_index + 1}")
        doc = st.session_state.chapters[st.session_state.chapter_index]
        
        # Chapter text with unique key based on chapter index
        st.text_area("Chapter Text", 
                   value=doc,
                   height=300,
                   key=f"chapter_text_{st.session_state.chapter_index}")

        # Responsive Navigation Buttons with forced rerun
        nav_col1, nav_col2 = st.columns([1, 1])
        with nav_col1:
            if st.button("◀ Previous", use_container_width=True):
                if st.session_state.chapter_index > 0:
                    st.session_state.chapter_index -= 1
                    st.rerun()
        with nav_col2:
            if st.button("Next ▶", use_container_width=True):
                if st.session_state.chapter_index < len(st.session_state.chapters)-1:
                    st.session_state.chapter_index += 1
                    st.rerun()

# Text Processing Section
prefix = "translate following text from chinese to english\n"
if st.button("Split Text"):
    if not doc:
        st.error("No text to process!")
    else:
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
            elif "Language." in splitter_choice:
                language = splitter_choice.split(".")[1].lower()
                splitter = RecursiveCharacterTextSplitter.from_language(
                    language=language,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=length_function
                )
            
            splits = splitter.split_text(doc)
            split_chunks = [prefix + s for s in splits]
            
            for idx, chunk in enumerate(split_chunks, 1):
                # Text area with unique key based on chapter and chunk index
                st.text_area(f"Chunk {idx}", 
                           value=chunk,
                           height=200,
                           key=f"chunk_{st.session_state.chapter_index}_{idx}")
                
                # Copy button with consistent styling
                components.html(f"""
                <div>
                    <button onclick="navigator.clipboard.writeText(`{chunk}`)"
                        style="
                            padding: 0.25rem 0.75rem;
                            background-color: #f63366;
                            color: white;
                            border: none;
                            border-radius: 0.5rem;
                            font-family: sans-serif;
                            font-size: 0.9rem;
                            cursor: pointer;
                            transition: all 0.3s ease;
                            margin: 5px 0;
                            width: 100%;
                        "
                        onmouseover="this.style.backgroundColor='#d52f5b'"
                        onmouseout="this.style.backgroundColor='#f63366'">
                        📋 Copy Chunk {idx}
                    </button>
                </div>
                """, height=60)

        except Exception as e:
            st.error(f"Processing error: {str(e)}")