import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import tempfile
from bs4 import BeautifulSoup
import time

# Set page configuration
st.set_page_config(page_title="EPUB3 Chapter Splitter", page_icon="📚")

# Custom CSS for better appearance
st.markdown("""
<style>
.stButton>button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 24px;
    border: none;
    cursor: pointer;
    border-radius: 5px;
}
.stButton>button:hover {
    background-color: #45a049;
}
</style>
""", unsafe_allow_html=True)

# Add keep-alive script
st.markdown(
    """
    <script>
    setInterval(function() {
        fetch(window.location.href, {cache: 'no-store'})
            .then(response => {
                if (!response.ok) {
                    console.log('Connection lost, retrying...');
                    setTimeout(() => window.location.reload(), 1000);
                }
            });
    }, 30000);  // 30-second keep-alive
    </script>
    """,
    unsafe_allow_html=True
)

# Initialize session state
if 'processed' not in st.session_state:
    st.session_state.processed = False
    st.session_state.zip_data = None
    st.session_state.base_name = None
    st.session_state.chapter_count = 0

# Title and instructions
st.title("EPUB3 Chapter Splitter")
st.info("Upload an EPUB3 file to split chapters into TXT files. The app will maintain your session even if you switch tabs.")

namespaces = {
    'epub': 'http://www.idpf.org/2007/ops',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf',
    'html': 'http://www.w3.org/1999/xhtml'
}

uploaded_file = st.file_uploader("Upload EPUB file", type=["epub"])

def find_content_path(opf_root):
    spine = opf_root.find(".//opf:spine", namespaces)
    if spine is None:
        raise ValueError("Spine not found in package.opf")
    
    for itemref in spine.findall(".//opf:itemref", namespaces):
        item_id = itemref.get('idref')
        item = opf_root.find(f".//opf:item[@id='{item_id}']", namespaces)
        if item is not None:
            media_type = item.get('media-type')
            properties = item.get('properties', '')
            if 'nav' in properties:
                continue
            if media_type == 'application/xhtml+xml':
                return item.get('href')
    raise ValueError("Main content file not found in spine")

def process_epub(epub_file):
    base_name, _ = os.path.splitext(epub_file.name)
    chapters = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(epub_file, 'r') as z:
            z.extractall(temp_dir)
        
        opf_path = os.path.join(temp_dir, 'OPS', 'package.opf')
        if not os.path.exists(opf_path):
            opf_path = os.path.join(temp_dir, 'package.opf')
        
        opf_dir = os.path.dirname(opf_path)
        tree = ET.parse(opf_path)
        root = tree.getroot()
        
        content_href = find_content_path(root)
        content_path = os.path.join(opf_dir, content_href)
        
        with open(content_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml-xml')

        chapter_sections = soup.find_all('section', {'epub:type': 'chapter'})
        
        for section in chapter_sections:
            title = section.find('h1')
            if title:
                title.extract()
            
            text_blocks = []
            for p in section.find_all('p', recursive=False):
                block_text = p.get_text(separator="\n", strip=True)
                if block_text.strip():
                    text_blocks.append(block_text)
            
            chapters.append("\n\n".join(text_blocks))
    
    return chapters, base_name

def create_zip(chapters, base_name):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for i, text in enumerate(chapters, 1):
            filename = f"{base_name}{i:02d}.txt"
            zipf.writestr(filename, text.encode('utf-8'))
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

if uploaded_file:
    if not st.session_state.processed:
        with st.spinner("Processing EPUB..."):
            try:
                chapters, base_name = process_epub(uploaded_file)
                zip_data = create_zip(chapters, base_name)
                st.session_state.processed = True
                st.session_state.zip_data = zip_data
                st.session_state.base_name = base_name
                st.session_state.chapter_count = len(chapters)
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.stop()
    
    if st.session_state.processed:
        st.success(f"Ready to download: {st.session_state.chapter_count} chapters from {st.session_state.base_name}.epub")
        st.download_button(
            label=f"Download {st.session_state.base_name}.zip",
            data=st.session_state.zip_data,
            file_name=f"{st.session_state.base_name}.zip",
            mime="application/zip"
        )
else:
    st.session_state.processed = False
