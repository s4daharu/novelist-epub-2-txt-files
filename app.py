import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import tempfile
from bs4 import BeautifulSoup

st.title("EPUB3 Chapter Splitter to TXT Files")

# Namespaces for XML parsing
namespaces = {
    'epub': 'http://www.idpf.org/2007/ops',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf',
    'html': 'http://www.w3.org/1999/xhtml'
}

uploaded_file = st.file_uploader("Upload an EPUB3 file", type=["epub"])

def find_content_path(opf_root):
    """Find main content file from OPF spine"""
    spine = opf_root.find(".//opf:spine", namespaces)
    if spine is None:
        raise ValueError("Spine not found in package.opf")
    
    # Find first XHTML content item in spine
    for itemref in spine.findall(".//opf:itemref", namespaces):
        item_id = itemref.get('idref')
        item = opf_root.find(f".//opf:item[@id='{item_id}']", namespaces)
        if item is not None and item.get('media-type') == 'application/xhtml+xml':
            return item.get('href')
    raise ValueError("Main content file not found in spine")

def process_epub_to_txt(epub_file):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract EPUB contents
        with zipfile.ZipFile(epub_file, 'r') as z:
            z.extractall(temp_dir)
        
        # Locate and parse package.opf
        opf_path = os.path.join(temp_dir, 'OPS', 'package.opf')
        if not os.path.exists(opf_path):
            opf_path = os.path.join(temp_dir, 'package.opf')
        
        tree = ET.parse(opf_path)
        root = tree.getroot()
        
        # Find main content file path
        content_href = find_content_path(root)
        content_path = os.path.join(temp_dir, content_href)
        
        # Parse content.xhtml with BeautifulSoup
        with open(content_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')  # Use HTML parser

        # Find all chapters
        chapters = []
        chapter_sections = soup.find_all('section', {'epub:type': 'chapter'})
        
        # Process each chapter
        for section in chapter_sections:
            # Remove title element (h1)
            title = section.find('h1')
            if title:
                title.extract()
            
            # Get cleaned text content
            text = section.get_text(separator="\n", strip=True)
            chapters.append(text)
        
        # Create TXT files in temporary directory
        txt_dir = os.path.join(temp_dir, 'txt_chapters')
        os.makedirs(txt_dir, exist_ok=True)
        txt_files = []
        for i, chapter_text in enumerate(chapters, 1):
            filename = f"Chapter_{i}.txt"
            filepath = os.path.join(txt_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(chapter_text)
            txt_files.append(filepath)
        
        # Create ZIP archive
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filepath in txt_files:
                arcname = os.path.basename(filepath)
                zipf.write(filepath, arcname)
        zip_buffer.seek(0)
        
        return zip_buffer.getvalue(), len(chapters)

if uploaded_file:
    with st.spinner("Processing EPUB..."):
        try:
            zip_data, num_chapters = process_epub_to_txt(uploaded_file)
            st.success(f"Extracted {num_chapters} chapters!")
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