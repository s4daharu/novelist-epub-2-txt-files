import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import tempfile
from bs4 import BeautifulSoup

st.title("EPUB3 Chapter Splitter")

# Register EPUB namespaces
namespaces = {
    'epub': 'http://www.idpf.org/2007/ops',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf',
    'html': 'http://www.w3.org/1999/xhtml'
}

uploaded_file = st.file_uploader("Upload an EPUB3 file", type=["epub"])

def process_epub(epub_file):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract EPUB contents
        with zipfile.ZipFile(epub_file, 'r') as z:
            z.extractall(temp_dir)
        
        # Find content file from package.opf
        rootfile_path = os.path.join(temp_dir, 'OPS', 'package.opf')
        tree = ET.parse(rootfile_path)
        root = tree.getroot()
        
        # Get content file path
        content_item = root.find(".//opf:item[@id='book-content']", namespaces)
        content_path = os.path.join(temp_dir, 'OPS', content_item.get('href'))
        
        # Parse content.xhtml
        with open(content_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')
        
        # Split chapters
        chapters = soup.find_all('section', {'epub:type': 'chapter'})
        
        # Create new directory for split chapters
        split_dir = os.path.join(temp_dir, 'OPS', 'split')
        os.makedirs(split_dir, exist_ok=True)
        
        # Process each chapter
        chapter_files = []
        for i, chapter in enumerate(chapters, 1):
            # Create new XHTML file for chapter
            chapter_soup = BeautifulSoup(str(chapter), 'xml')
            
            # Clean up chapter content
            for elem in chapter_soup.find_all(['html:section']):
                elem.unwrap()
            
            # Create new XHTML structure
            new_content = f"""<?xml version='1.0' encoding='utf-8'?>
            <html xmlns='http://www.w3.org/1999/xhtml' xmlns:epub='http://www.idpf.org/2007/ops'>
                <head>
                    <meta charset="utf-8"/>
                    <title>Chapter {i}</title>
                    <link href="../css/main.css" rel="stylesheet"/>
                </head>
                <body>
                    {chapter_soup.body}
                </body>
            </html>"""
            
            # Save chapter file
            chap_filename = f'chapter_{i}.xhtml'
            chap_path = os.path.join(split_dir, chap_filename)
            with open(chap_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            chapter_files.append(chap_filename)
        
        # Update package.opf
        manifest = root.find('opf:manifest', namespaces)
        spine = root.find('opf:spine', namespaces)
        
        # Add new chapter items to manifest and spine
        for i, chap in enumerate(chapter_files, 1):
            item_id = f'chap{i}'
            manifest.append(ET.fromstring(
                f'<item id="{item_id}" href="split/{chap}" media-type="application/xhtml+xml"/>'
            ))
            spine.append(ET.fromstring(f'<itemref idref="{item_id}"/>'))
        
        # Save updated package.opf
        tree.write(rootfile_path, encoding='utf-8', xml_declaration=True)
        
        # Create new EPUB
        new_epub = BytesIO()
        with zipfile.ZipFile(new_epub, 'w') as zf:
            for root_dir, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arcname)
        
        new_epub.seek(0)
        return new_epub.getvalue(), len(chapters)

if uploaded_file:
    with st.spinner("Processing EPUB..."):
        try:
            processed_epub, num_chapters = process_epub(uploaded_file)
            st.success(f"Split into {num_chapters} chapters successfully!")
            
            st.download_button(
                label="Download Split EPUB",
                data=processed_epub,
                file_name="split_book.epub",
                mime="application/epub+zip"
            )
        except Exception as e:
            st.error(f"Error processing EPUB: {str(e)}")
else:
    st.info("Please upload an EPUB3 file to begin")