import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import tempfile
from bs4 import BeautifulSoup

# Configure XML namespaces
namespaces = {
    'opf': 'http://www.idpf.org/2007/opf',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'html': 'http://www.w3.org/1999/xhtml',
    'epub': 'http://www.idpf.org/2007/ops'
}

st.title("EPUB3 Chapter Splitter")

def process_epub(epub_file):
    """Process EPUB file and extract chapters as TXT files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract EPUB contents
        with zipfile.ZipFile(epub_file, 'r') as z:
            z.extractall(temp_dir)
        
        try:
            # Parse package.opf to find content file
            opf_path = os.path.join(temp_dir, 'OPS', 'package.opf')
            tree = ET.parse(opf_path)
            root = tree.getroot()
            
            # Find main content file
            content_item = root.find(".//opf:item[@id='book-content']", namespaces)
            if not content_item:
                raise ValueError("Main content file not found in OPF manifest")
            
            content_path = os.path.join(temp_dir, 'OPS', content_item.get('href'))
            
            # Parse content file
            with open(content_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'xml')
            
            # Extract chapters
            chapters = soup.find_all('section', {'epub:type': 'chapter'})
            if not chapters:
                raise ValueError("No chapters found in content file")
            
            # Create TXT files
            txt_files = []
            for idx, chapter in enumerate(chapters, 1):
                # Extract text paragraphs (skip first paragraph as title)
                paragraphs = chapter.find_all('p')
                content = [p.get_text(strip=True) for p in paragraphs[1:]] if len(paragraphs) > 1 else []
                
                # Create TXT content
                txt_content = '\n'.join(content)
                
                # Save to temporary file
                filename = f"Chapter_{idx}.txt"
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(txt_content)
                txt_files.append(file_path)
            
            # Create ZIP in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zipf:
                for file_path in txt_files:
                    zipf.write(file_path, arcname=os.path.basename(file_path))
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue(), len(chapters)
        
        finally:
            # Cleanup temporary files
            for f in txt_files:
                if os.path.exists(f):
                    os.remove(f)

# Streamlit UI
uploaded_file = st.file_uploader("Upload an EPUB3 file", type=["epub"])

if uploaded_file:
    with st.spinner("Processing EPUB..."):
        try:
            zip_data, chapter_count = process_epub(uploaded_file)
            st.success(f"Successfully split into {chapter_count} chapters!")
            
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