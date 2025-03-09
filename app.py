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
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator="\n")
                chapters.append(text)
    finally:
        os.unlink(tmp_file_name)
    
    return chapters

# Initialize session state
if 'chapter_index' not in st.session_state:
    st.session_state.chapter_index = 0
if 'uploaded_epub' not in st.session_state:
    st.session_state.uploaded_epub = None
if 'chapters' not in st.session_state:
    st.session_state.chapters = []

# Hardcoded configuration
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 40
LENGTH_FUNCTION = len
SPLITTER_CHOICE = "Character"
PREFIX = "translate following text from chinese to english\n"

# EPUB File Uploader
uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])
if uploaded_file:
    st.session_state.uploaded_epub = uploaded_file.read()
    st.session_state.chapters = extract_chapters(st.session_state.uploaded_epub)

# Process first chapter if available
doc = ""
if st.session_state.chapters:
    doc = st.session_state.chapters[st.session_state.chapter_index]

# Split Text Button
if st.button("Split Text"):
    if not doc:
        st.error("Please upload an EPUB file first!")
    else:
        try:
            if SPLITTER_CHOICE == "Character":
                splitter = CharacterTextSplitter(
                    separator="\n\n",
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    length_function=LENGTH_FUNCTION
                )
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    length_function=LENGTH_FUNCTION
                )

            splits = splitter.split_text(doc)
            split_chunks = [PREFIX + s for s in splits]
            
            for idx, chunk in enumerate(split_chunks, 1):
                # Display chunk with copy button
                components.html(f"""
                <div style="margin-bottom: 2rem;">
                    <div style="
                        border: 1px solid #e6e6e6;
                        border-radius: 0.5rem;
                        padding: 1rem;
                        margin-bottom: 0.5rem;
                        background-color: #f8f9fa;">
                        {chunk}
                    </div>
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
                            width: 100%;"
                        onmouseover="this.style.backgroundColor='#d52f5b'"
                        onmouseout="this.style.backgroundColor='#f63366'">
                        📋 Copy Chunk {idx}
                    </button>
                </div>
                """, height=250)

        except Exception as e:
            st.error(f"Processing error: {str(e)}")