import streamlit as st
import io
import zipfile
import tempfile
import os
from ebooklib import epub
from bs4 import BeautifulSoup
import tiktoken
import streamlit.components.v1 as components
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter

# -------------------------
# Configuration
# -------------------------
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 10
LENGTH_FUNCTION_CHOICE = "Characters"  # Options: "Characters" or "Tokens"
SPLITTER_CHOICE = "Character"           # Options: "Character", "RecursiveCharacter", or e.g. "Language.English"
PREFIX = "translate following text from chinese to english\n"

if LENGTH_FUNCTION_CHOICE == "Characters":
    length_function = len
elif LENGTH_FUNCTION_CHOICE == "Tokens":
    enc = tiktoken.get_encoding("cl100k_base")
    def length_function(text: str) -> int:
        return len(enc.encode(text))

# -------------------------
# Helper Functions
# -------------------------
def extract_chapters_from_epub(epub_content):
    """Extract chapters from an EPUB file."""
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

def extract_chapters_from_zip(zip_bytes):
    """Extract chapters from a ZIP file containing TXT files.
       Each TXT file is considered one chapter.
    """
    chapters = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        txt_files = sorted([f for f in z.namelist() if f.lower().endswith(".txt")])
        for filename in txt_files:
            with z.open(filename) as f:
                try:
                    content = f.read().decode('utf-8')
                except Exception:
                    content = f.read().decode('latin-1', errors='ignore')
                chapters.append(content)
    return chapters

def split_text(text):
    """Split a given text using the selected splitter and add a prefix to each chunk."""
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
    splits = splitter.split_text(text)
    return [PREFIX + s for s in splits]

def build_epub(split_chapters):
    """Package the split chapters into an EPUB file.
       split_chapters is a list where each element corresponds to a chapter,
       and is itself a list of chunk strings.
    """
    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title('Processed Book')
    book.set_language('en')
    book.add_author('Processed via Streamlit App')
    
    epub_chapters = []
    for chapter_index, chapter_chunks in enumerate(split_chapters, start=1):
        for part_index, chunk in enumerate(chapter_chunks, start=1):
            title = f"Chapter {chapter_index} Part {part_index}"
            c = epub.EpubHtml(title=title,
                                file_name=f'chap_{chapter_index}_part_{part_index}.xhtml',
                                lang='en')
            # Wrap the chunk in basic HTML
            c.content = f"<h1>{title}</h1><p>{chunk.replace(chr(10), '<br/>')}</p>"
            book.add_item(c)
            epub_chapters.append(c)
    
    # Define Table Of Contents and Spine
    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + epub_chapters
    
    # Write the epub to a temporary file and return its bytes
    temp_epub = tempfile.NamedTemporaryFile(delete=False, suffix=".epub")
    epub.write_epub(temp_epub.name, book, {})
    with open(temp_epub.name, "rb") as f:
        epub_bytes = f.read()
    os.unlink(temp_epub.name)
    return epub_bytes

# -------------------------
# Session State Initialization
# -------------------------
if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'split_chapters' not in st.session_state:
    st.session_state.split_chapters = []

# -------------------------
# File Upload Section
# -------------------------
uploaded_file = st.file_uploader("Upload an EPUB or ZIP (of TXT chapters) file", type=["epub", "zip"])

if uploaded_file:
    file_bytes = uploaded_file.read()
    if uploaded_file.name.lower().endswith(".epub"):
        st.session_state.chapters = extract_chapters_from_epub(file_bytes)
    elif uploaded_file.name.lower().endswith(".zip"):
        st.session_state.chapters = extract_chapters_from_zip(file_bytes)
    st.success(f"Loaded {len(st.session_state.chapters)} chapters.")

# -------------------------
# Chapter Display and Splitting
# -------------------------
if st.session_state.chapters:
    chapter_index = st.number_input("Select Chapter Number to View", 
                                    min_value=1, max_value=len(st.session_state.chapters), step=1, value=1)
    current_chapter = st.session_state.chapters[chapter_index - 1]
    st.markdown(f"### Chapter {chapter_index}")
    st.text_area("Chapter Text", value=current_chapter, height=300, key=f"chapter_text_{chapter_index}")
    
    if st.button("Split Current Chapter"):
        split_chunks = split_text(current_chapter)
        # Display each chunk with a label indicating chapter and part number.
        st.markdown(f"#### Splits for Chapter {chapter_index}")
        for idx, chunk in enumerate(split_chunks, start=1):
            st.text_area(f"Chapter {chapter_index} Part {idx}", value=chunk, height=200, key=f"chunk_{chapter_index}_{idx}")
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
                    📋 Copy Chapter {chapter_index} Part {idx}
                </button>
            </div>
            """, height=60)
        # Save the split version for later packaging. Use a dictionary keyed by chapter number.
        if len(st.session_state.split_chapters) < chapter_index:
            # Extend the list if needed
            st.session_state.split_chapters.extend([None]*(chapter_index - len(st.session_state.split_chapters)))
        st.session_state.split_chapters[chapter_index - 1] = split_chunks

# -------------------------
# Process All Chapters and Package into EPUB
# -------------------------
if st.button("Process All Chapters and Generate EPUB"):
    if not st.session_state.chapters:
        st.error("No chapters loaded!")
    else:
        all_split = []
        # For each chapter, split it if not already split
        for chapter in st.session_state.chapters:
            split_chunks = split_text(chapter)
            all_split.append(split_chunks)
        epub_bytes = build_epub(all_split)
        st.success("EPUB generated successfully!")
        st.download_button(
            label="Download Processed EPUB",
            data=epub_bytes,
            file_name="processed_book.epub",
            mime="application/epub+zip"
        )