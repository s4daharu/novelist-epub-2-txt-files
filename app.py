import streamlit as st
from io import BytesIO
import chardet
import tiktoken
from concurrent.futures import ThreadPoolExecutor
from ebooklib import epub
from bs4 import BeautifulSoup
import time

# Initialize expensive resources once
enc = tiktoken.get_encoding("cl100k_base")

# Cached EPUB processing
@st.cache_data(max_entries=3, show_spinner=False)
def process_epub(uploaded_content):
    def process_item(item):
        if item.get_type() == epub.EpubHtml:
            try:
                content = item.get_content()
                encoding = chardet.detect(content)['encoding'] or 'utf-8'
                html = content.decode(encoding, errors='replace')
                return BeautifulSoup(html, 'html.parser').get_text(separator='\n')
            except Exception:
                return ""
        return ""
    
    book = epub.read_epub(BytesIO(uploaded_content))
    with ThreadPoolExecutor() as executor:
        chapters = list(executor.map(process_item, book.get_items()))
    return [ch for ch in chapters if ch.strip()]

# Session state initialization
if 'chapters' not in st.session_state:
    st.session_state.update({
        'chapters': [],
        'chapter_index': 0,
        'cached_epub': None
    })

# UI Configuration
st.set_page_config(layout="wide")
input_method = st.radio("Input Method", ["Manual Input", "Upload EPUB"], index=1)

# Splitter Configuration
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1: chunk_size = st.number_input("Chunk Size", min_value=1, value=1950)
with col2: chunk_overlap = st.number_input("Chunk Overlap", min_value=1, value=40)
with col3: len_func = st.selectbox("Length Function", ["Characters", "Tokens"])
with col4: splitter_type = st.selectbox("Splitter Type", ["Character", "Recursive", "Language"])

# Document Input Handling
doc = ""
if input_method == "Manual Input":
    doc = st.text_area("Input Text", height=300)
else:
    uploaded = st.file_uploader("Upload EPUB", type="epub")
    if uploaded:
        if st.session_state.cached_epub != uploaded.getvalue():
            with st.spinner("Processing EPUB..."):
                st.session_state.chapters = process_epub(uploaded.getvalue())
                st.session_state.cached_epub = uploaded.getvalue()
        
        if st.session_state.chapters:
            st.success(f"Loaded {len(st.session_state.chapters)} chapters")
            idx = st.selectbox("Chapter", range(len(st.session_state.chapters)), 
                         format_func=lambda x: x+1, index=st.session_state.chapter_index)
            st.session_state.chapter_index = idx
            doc = st.session_state.chapters[idx]
            st.text_area("Chapter Content", value=doc, height=300)

# Text Processing
if st.button("Split Text") and doc:
    start_time = time.time()
    
    # Lazy imports for splitters
    if splitter_type == "Character":
        from langchain.text_splitter import CharacterTextSplitter
        splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len if len_func == "Characters" else lambda t: len(enc.encode(t))
        )
    else:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len if len_func == "Characters" else lambda t: len(enc.encode(t))
        )
    
    # Parallel splitting
    with ThreadPoolExecutor() as executor:
        chunks = list(executor.map(splitter.split_text, [doc]))
    
    # Display results
    st.write(f"Processing time: {time.time()-start_time:.2f}s")
    for i, chunk in enumerate(chunks[0]):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.text_area(f"Chunk {i+1}", value=chunk, height=150, key=f"chunk_{i}")
        with col2:
            if st.button("📋", key=f"copy_{i}"):
                st.session_state.clipboard = chunk
                st.toast("Copied to clipboard!")