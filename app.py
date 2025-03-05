import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter, Language
import code_snippets as code_snippets
import tiktoken
import streamlit.components.v1 as components
from ebooklib import epub
from bs4 import BeautifulSoup

def extract_chapters(epub_file_path):
    """Extracts chapters from an EPUB file."""
    book = epub.read_epub(epub_file_path)
    chapters = []
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
    return chapters

# Input Method Selection
input_method = st.radio("Input Method", ["Manual Input", "Upload EPUB"], index=1)

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
if input_method == "Manual Input":
    doc = st.text_area("Paste your text here:")
elif input_method == "Upload EPUB":
    uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])
    if uploaded_file:
        with open("temp.epub", "wb") as f:
            f.write(uploaded_file.getbuffer())
        chapters = extract_chapters("temp.epub")
        
        if chapters:
            st.success(f"Found {len(chapters)} chapters")
            if "chapter_index" not in st.session_state:
                st.session_state.chapter_index = 0

            # Chapter Selection and Display
            chapter_numbers = list(range(1, len(chapters)+1))
            selected_chapter = st.selectbox("Chapter Number", chapter_numbers, 
                                         index=st.session_state.chapter_index)
            st.session_state.chapter_index = selected_chapter - 1

            st.markdown(f"### Chapter {st.session_state.chapter_index + 1}")
            doc = chapters[st.session_state.chapter_index]
            st.text_area("Chapter Text", doc, height=300)

            # Responsive Navigation Buttons
            nav_col1, nav_col2 = st.columns([1, 1])
            with nav_col1:
                if st.button("◀ Prev", use_container_width=True) and st.session_state.chapter_index > 0:
                    st.session_state.chapter_index -= 1
            with nav_col2:
                if st.button("Next ▶", use_container_width=True) and st.session_state.chapter_index < len(chapters)-1:
                    st.session_state.chapter_index += 1

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
                st.text_area(f"Chunk {idx}", chunk, height=200)
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