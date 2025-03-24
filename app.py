import os
import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
import chardet
import tiktoken

# Constants
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 10
TRANSLATION_PREFIX = "translate following text from chinese to english\n"
SUPPORTED_ENCODINGS = ['utf-8', 'gb18030', 'latin-1']

def extract_chapters(uploaded_file):
    try:
        with open("temp.epub", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        book = epub.read_epub("temp.epub")
        chapters = []
        
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text = soup.get_text().strip()
                if text:
                    detected = detect_encoding(text)
                    text = text.encode(detected['encoding'], 'ignore').decode(detected['encoding'])
                    chapters.append(text)
        
        os.unlink("temp.epub")
        return chapters
    
    except Exception as e:
        st.error(f"Error processing EPUB: {str(e)}")
        return []
    finally:
        if os.path.exists("temp.epub"):
            os.unlink("temp.epub")

def detect_encoding(text):
    result = chardet.detect(text)
    encoding = result['encoding'] if result['confidence'] > 0.7 else 'utf-8'
    return {'encoding': encoding, 'confidence': result['confidence']}

def split_text(text, splitter_type='recursive'):
    try:
        if not text.strip():
            return []

        if splitter_type == 'character':
            splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                length_function=len
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                length_function=len
            )
        
        chunks = splitter.split_text(text)
        return [f"{TRANSLATION_PREFIX}{chunk}" for chunk in chunks]
    
    except Exception as e:
        st.error(f"Error splitting text: {str(e)}")
        return []

def main():
    st.set_page_config(page_title="Document Processor", layout="wide")
    
    # Custom CSS for copy buttons
    st.markdown("""
    <style>
    .copy-btn {
        background-color: #4CAF50;
        color: white;
        padding: 2px 10px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        float: right;
    }
    .copy-btn:hover {background-color: #45a049;}
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'chapters' not in st.session_state:
        st.session_state.chapters = []
    if 'current_chapter' not in st.session_state:
        st.session_state.current_chapter = 0
    if 'manual_text' not in st.session_state:
        st.session_state.manual_text = ""
    if 'chunks' not in st.session_state:
        st.session_state.chunks = []

    st.title("Document Processing Tool")
    
    # Input type selector
    input_type = st.radio(
        "Input Type:",
        ("EPUB File", "Manual Text"),
        horizontal=True,
        index=0,
        key="input_type"
    )

    # Input section
    if input_type == "EPUB File":
        uploaded_file = st.file_uploader("Upload EPUB file", type=["epub"])
        if uploaded_file:
            st.session_state.chapters = extract_chapters(uploaded_file)
            st.session_state.manual_text = ""
            st.session_state.current_chapter = 0
    else:
        manual_text = st.text_area(
            "Enter text:",
            value=st.session_state.manual_text,
            height=200,
            key="manual_text_input"
        )
        if manual_text:
            st.session_state.manual_text = manual_text.strip()
            st.session_state.chapters = [st.session_state.manual_text]
            st.session_state.current_chapter = 0

    # Content display and navigation
    if st.session_state.chapters:
        if input_type == "EPUB File":
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if st.button("⏮ Previous"):
                    if st.session_state.current_chapter > 0:
                        st.session_state.current_chapter -= 1
            with col3:
                if st.button("Next ⏭"):
                    if st.session_state.current_chapter < len(st.session_state.chapters) - 1:
                        st.session_state.current_chapter += 1
            with col2:
                st.markdown(f"**Chapter {st.session_state.current_chapter + 1} of {len(st.session_state.chapters)}**")

        current_content = st.session_state.chapters[st.session_state.current_chapter]
        st.text_area("Current Content", value=current_content, height=300, key="content_display", disabled=True)

        # Processing options
        col1, col2 = st.columns(2)
        with col1:
            splitter_type = st.selectbox(
                "Splitter Type:",
                ("Recursive", "Character"),
                index=0
            )
        with col2:
            if st.button("🚀 Process Content"):
                if current_content.strip():
                    st.session_state.chunks = split_text(
                        current_content,
                        splitter_type.lower()
                    )
                else:
                    st.warning("Please enter valid content to process")

        # Display chunks
        if st.session_state.chunks:
            st.subheader("Processed Chunks")
            for i, chunk in enumerate(st.session_state.chunks):
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;">
                    <button class="copy-btn" onclick="navigator.clipboard.writeText(`{chunk}`)">Copy</button>
                    <strong>Chunk {i+1}</strong>
                    <div style="margin-top: 10px; white-space: pre-wrap;">{chunk}</div>
                </div>
                """, unsafe_allow_html=True)

    # Clear button
    if st.button("🚮 Clear All"):
        st.session_state.clear()
        st.session_state.update({
            'chapters': [],
            'current_chapter': 0,
            'manual_text': "",
            'chunks': []
        })

if __name__ == "__main__":
    main()
