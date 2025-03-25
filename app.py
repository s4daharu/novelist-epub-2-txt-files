import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter, Language
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

# -------------------------
# Initialize session state
# -------------------------
if 'chapter_index' not in st.session_state:
    st.session_state.chapter_index = 0
if 'uploaded_epub' not in st.session_state:
    st.session_state.uploaded_epub = None
if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'manual_input' not in st.session_state:
    st.session_state.manual_input = ""

# -------------------------
# Configuration
# -------------------------
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 10
LENGTH_FUNCTION_CHOICE = "Characters"  # Options: "Characters" or "Tokens"
SPLITTER_CHOICE = "Character"          # Options: "Character", "RecursiveCharacter", or "Language.English"
PREFIX = "translate following text from Chinese to English:\n"

# Set up length function
if LENGTH_FUNCTION_CHOICE == "Characters":
    length_function = len
elif LENGTH_FUNCTION_CHOICE == "Tokens":
    enc = tiktoken.get_encoding("cl100k_base")
    def length_function(text: str) -> int:
        return len(enc.encode(text))

# -------------------------
# Text Source Selection
# -------------------------
text_source = st.radio("Select text source:", ["Uploaded EPUB", "Manual Input"])

doc = ""

if text_source == "Uploaded EPUB":
    uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])
    if uploaded_file:
        st.session_state.uploaded_epub = uploaded_file.read()
        st.session_state.chapters = extract_chapters(st.session_state.uploaded_epub)

    if st.session_state.chapters:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"Loaded {len(st.session_state.chapters)} chapters")
        with col2:
            if st.button("🚮 Clear EPUB"):
                st.session_state.clear()
                st.experimental_rerun()

        # Select and display chapter
        chapter_numbers = list(range(1, len(st.session_state.chapters) + 1))
        selected_chapter = st.selectbox("Chapter Number", chapter_numbers, index=st.session_state.chapter_index)
        st.session_state.chapter_index = selected_chapter - 1

        st.markdown(f"### Chapter {st.session_state.chapter_index + 1}")
        doc = st.session_state.chapters[st.session_state.chapter_index]

        st.text_area("Chapter Text", value=doc, height=300, key=f"chapter_text_{st.session_state.chapter_index}")

        # Navigation buttons
        nav_col1, nav_col2 = st.columns([1, 1])
        with nav_col1:
            if st.button("◀ Previous", use_container_width=True) and st.session_state.chapter_index > 0:
                st.session_state.chapter_index -= 1
                st.experimental_rerun()
        with nav_col2:
            if st.button("Next ▶", use_container_width=True) and st.session_state.chapter_index < len(st.session_state.chapters) - 1:
                st.session_state.chapter_index += 1
                st.experimental_rerun()

elif text_source == "Manual Input":
    doc = st.text_area("Enter text to split:", value=st.session_state.manual_input, height=300, key="manual_input")

# -------------------------
# Reset and Split Buttons
# -------------------------
col_reset, col_split = st.columns([1, 2])
with col_reset:
    if st.button("Reset"):
        st.session_state.clear()
        st.experimental_rerun()

# -------------------------
# Text Splitting
# -------------------------
if st.button("Split Text"):
    if not doc:
        st.error("No text to process!")
    else:
        try:
            if SPLITTER_CHOICE == "Character":
                splitter = CharacterTextSplitter(
                    separator="\n\n",
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    length_function=length_function
                )
            elif SPLITTER_CHOICE == "RecursiveCharacter":
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    length_function=length_function
                )
            elif "Language." in SPLITTER_CHOICE:
                language = SPLITTER_CHOICE.split(".")[1].lower()
                splitter = RecursiveCharacterTextSplitter.from_language(
                    language=language,
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    length_function=length_function
                )

            splits = splitter.split_text(doc)
            split_chunks = [PREFIX + s for s in splits]

            for idx, chunk in enumerate(split_chunks, 1):
                st.text_area(f"Chunk {idx}", value=chunk, height=200, key=f"chunk_{idx}")

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