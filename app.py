import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import tempfile
from bs4 import BeautifulSoup

st.title("EPUB3 Chapter Splitter to TXT Files")

# Register necessary namespaces for parsing package.opf.
namespaces = {
    'epub': 'http://www.idpf.org/2007/ops',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf',
    'html': 'http://www.w3.org/1999/xhtml'
}

uploaded_file = st.file_uploader("Upload an EPUB3 file", type=["epub"])

def process_epub_to_txt(epub_file):
    # Create a temporary directory to extract the EPUB contents.
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract all files from the EPUB archive.
        with zipfile.ZipFile(epub_file, 'r') as z:
            z.extractall(temp_dir)
        
        # Locate the package.opf file (assumed to be in OPS folder).
        package_path = os.path.join(temp_dir, 'OPS', 'package.opf')
        tree = ET.parse(package_path)
        root = tree.getroot()
        
        # Find the manifest item with id 'book-content' which points to the content.xhtml file.
        content_item = root.find(".//opf:item[@id='book-content']", namespaces)
        if content_item is None:
            raise ValueError("Content item with id 'book-content' not found in package.opf")
        content_href = content_item.get('href')
        # Construct the full path to the content file (e.g., OPS/book/content.xhtml).
        content_path = os.path.join(temp_dir, 'OPS', content_href)
        
        # Parse the content.xhtml file using BeautifulSoup.
        with open(content_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')
        
        # Find all chapter sections by looking for <section> elements with epub:type="chapter".
        chapter_sections = soup.find_all('section', {'epub:type': 'chapter'})
        
        # If no chapters are found, treat the entire file as one chapter.
        chapters = []
        if not chapter_sections:
            full_text = soup.get_text(separator="\n").strip()
            chapters = [full_text]
        else:
            for section in chapter_sections:
                # Get the complete text and split it into lines.
                text = section.get_text(separator="\n").strip()
                lines = text.splitlines()
                # Remove the first line (assumed to be the title) if available.
                if lines:
                    lines = lines[1:]
                chapter_text = "\n".join(lines).strip()
                chapters.append(chapter_text)
        
        # Create TXT files for each chapter in a temporary directory.
        txt_dir = os.path.join(temp_dir, 'txt_chapters')
        os.makedirs(txt_dir, exist_ok=True)
        txt_files = []
        for i, chapter_text in enumerate(chapters, start=1):
            filename = f"Chapter_{i}.txt"
            filepath = os.path.join(txt_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(chapter_text)
            txt_files.append(filepath)
        
        # Create a ZIP archive containing all TXT chapter files.
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filepath in txt_files:
                arcname = os.path.basename(filepath)
                zipf.write(filepath, arcname=arcname)
        zip_buffer.seek(0)
        return zip_buffer.getvalue(), len(txt_files)

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
            st.error(f"Error processing EPUB: {e}")
else:
    st.info("Please upload an EPUB3 file to begin")