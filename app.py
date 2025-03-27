import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import tempfile
from bs4 import BeautifulSoup

st.title("EPUB3 Chapter Splitter to TXT Files")

namespaces = {
    'epub': 'http://www.idpf.org/2007/ops',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf',
    'html': 'http://www.w3.org/1999/xhtml'
}

uploaded_file = st.file_uploader("Upload an EPUB3 file", type=["epub"])

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

def process_epub_to_txt(epub_file):
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

        chapters = []
        chapter_sections = soup.find_all('section', {'epub:type': 'chapter'})
        
        for section in chapter_sections:
            # Remove title (h1)
            title = section.find('h1')
            if title:
                title.extract()
            
            # Process paragraphs
            text_blocks = []
            for p in section.find_all('p', recursive=False):
                block_text = p.get_text(separator="\n", strip=True)
                if block_text.strip():
                    text_blocks.append(block_text)
            
            # Join with double line breaks between paragraphs
            chapter_text = "\n\n".join(text_blocks)
            chapters.append(chapter_text)

        # Create ZIP archive
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for i, text in enumerate(chapters, 1):
                zipf.writestr(f"Chapter_{i}.txt", text.encode('utf-8'))
        zip_buffer.seek(0)
        return zip_buffer.getvalue(), len(chapters)

if uploaded_file:
    with st.spinner("Processing EPUB..."):
        try:
            zip_data, num_chapters = process_epub_to_txt(uploaded_file)
            st.success(f"Extracted {num_chapters} chapters with proper formatting!")
            st.download_button(
                label="Download Chapters as ZIP",
                data=zip_data,
                file_name="chapters.zip",
                mime="application/zip"
            )
        except Exception as e:
            st.error(f"Error processing EPUB: {str(e)}")
else:
    st.info("Please upload an EPUB3 file to begin")