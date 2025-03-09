import streamlit as st
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    Language
)
import code_snippets as code_snippets  # if needed for template strings
import tiktoken
import streamlit.components.v1 as components
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os

# --- Caching and Helper Functions ---

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

@st.cache_data(show_spinner=False)
def get_chapters(epub_content):
    """Cache the chapter extraction so repeated runs don't reprocess the EPUB."""
    return extract_chapters(epub_content)

@st.cache_data(show_spinner=False)
def split_document(text, splitter_choice, chunk_size, chunk_overlap, length_function):
    """Cache text splitting for the given document."""
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
    else:
        splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function
        )
    splits = splitter.split_text(text)
    # Prepend a prefix to each chunk if needed
    prefix = "translate following text from chinese to english\n"
    return [prefix + s for s in splits]

# --- Session State Initialization ---

if 'chapter_index' not in st.session_state:
    st.session_state.chapter_index = 0
if 'uploaded_epub' not in st.session_state:
    st.session_state.uploaded_epub = None
if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'chunks' not in st.session_state:
    st.session_state.chunks = []
if 'chunk_page' not in st.session_state:
    st.session_state.chunk_page = 0

# --- Sidebar: Input Method and Configuration ---
st.sidebar.header("Input Method & Configurations")
input_method = st.sidebar.radio("Input Method", ["Manual Input", "Upload EPUB"], index=1)

chunk_size = st.sidebar.number_input("Chunk Size", min_value=1, value=1950)
chunk_overlap = st.sidebar.number_input("Chunk Overlap", min_value=1, max_value=chunk_size - 1, value=40)
if chunk_overlap >= chunk_size:
    st.sidebar.warning("Chunk Overlap should be less than Chunk Size!")

length_function_choice = st.sidebar.selectbox("Length Function", ["Characters", "Tokens"], index=0)
if length_function_choice == "Characters":
    length_function = len
elif length_function_choice == "Tokens":
    enc = tiktoken.get_encoding("cl100k_base")
    def length_function(text: str) -> int:
        return len(enc.encode(text))

splitter_choices = ["Character", "RecursiveCharacter"] + [str(v) for v in Language]
splitter_choice = st.sidebar.selectbox("Text Splitter", splitter_choices, index=0)

# --- Document Input Section ---
doc = ""
if input_method == "Manual Input":
    doc = st.text_area("Paste your text here:")
else:
    uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])
    if uploaded_file:
        epub_bytes = uploaded_file.read()
        st.session_state.uploaded_epub = epub_bytes
        st.session_state.chapters = get_chapters(epub_bytes)
    
    if st.session_state.chapters:
        st.success(f"Loaded {len(st.session_state.chapters)} chapters")
        if st.button("🚮 Clear EPUB"):
            st.session_state.uploaded_epub = None
            st.session_state.chapters = []
            st.session_state.chapter_index = 0
            st.session_state.chunks = []
            st.experimental_rerun()

        # Chapter selection
        chapter_numbers = list(range(1, len(st.session_state.chapters) + 1))
        selected_chapter = st.selectbox("Chapter Number", chapter_numbers, index=st.session_state.chapter_index)
        st.session_state.chapter_index = selected_chapter - 1

        st.markdown(f"### Chapter {st.session_state.chapter_index + 1}")
        doc = st.session_state.chapters[st.session_state.chapter_index]
        st.text_area("Chapter Text", value=doc, height=300, key=f"chapter_text_{st.session_state.chapter_index}")

# --- Text Splitting and Pagination for Chunks ---
if st.button("Split Text"):
    if not doc:
        st.error("No text to process!")
    else:
        st.session_state.chunks = split_document(doc, splitter_choice, chunk_size, chunk_overlap, length_function)
        st.session_state.chunk_page = 0

if st.session_state.chunks:
    chunks = st.session_state.chunks
    # Pagination: display 3 chunks per page
    chunks_per_page = 3
    total_pages = (len(chunks) - 1) // chunks_per_page + 1

    st.markdown(f"### Displaying Chunks (Page {st.session_state.chunk_page + 1} of {total_pages})")
    start_idx = st.session_state.chunk_page * chunks_per_page
    end_idx = start_idx + chunks_per_page
    for idx, chunk in enumerate(chunks[start_idx:end_idx], start=start_idx + 1):
        st.text_area(f"Chunk {idx}", value=chunk, height=200, key=f"chunk_{st.session_state.chapter_index}_{idx}")
        # Copy button for the chunk
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

    # Pagination Navigation
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    with nav_col1:
        if st.button("◀ Previous Page") and st.session_state.chunk_page > 0:
            st.session_state.chunk_page -= 1
            st.experimental_rerun()
    with nav_col3:
        if st.button("Next Page ▶") and st.session_state.chunk_page < total_pages - 1:
            st.session_state.chunk_page += 1
            st.experimental_rerun()