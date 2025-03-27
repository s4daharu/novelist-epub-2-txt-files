import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import tempfile
from bs4 import BeautifulSoup

st.title("EPUB3 Chapter Splitter & TOC Fixer")

namespaces = {
    'epub': 'http://www.idpf.org/2007/ops',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf',
    'html': 'http://www.w3.org/1999/xhtml'
}

uploaded_file = st.file_uploader("Upload an EPUB3 file", type=["epub"])

def find_content_path(opf_root):
    spine = opf_root.find(".//opf:spine", namespaces)
    for itemref in spine.findall(".//opf:itemref", namespaces):
        item_id = itemref.get('idref')
        item = opf_root.find(f".//opf:item[@id='{item_id}']", namespaces)
        if item is not None and item.get('media-type') == 'application/xhtml+xml':
            return item.get('href')
    raise ValueError("Content file not found")

def update_toc(temp_dir, content_soup, content_href):
    # Find or create nav.xhtml
    nav_path = os.path.join(temp_dir, 'OPS', 'book', 'table-of-contents.xhtml')
    if not os.path.exists(nav_path):
        return
    
    with open(nav_path, 'r', encoding='utf-8') as f:
        nav_soup = BeautifulSoup(f, 'lxml-xml')
    
    toc_nav = nav_soup.find('nav', {'epub:type': 'toc'})
    if not toc_nav:
        return
    
    ol = toc_nav.find('ol')
    ol.clear()
    
    # Extract chapter info
    chapters = []
    for section in content_soup.find_all('section', {'epub:type': 'chapter'}):
        h1 = section.find('h1')
        chapter_id = h1.get('id', f'ch_{len(chapters)+1}')
        title_p = section.find('p')
        title = title_p.get_text(strip=True) if title_p else f"Chapter {len(chapters)+1}"
        href = f"{content_href}#{chapter_id}"
        chapters.append((title, href))
        
        # Ensure section has an ID
        if not h1.get('id'):
            h1['id'] = chapter_id
    
    # Update TOC entries
    for title, href in chapters:
        li = nav_soup.new_tag('li')
        a = nav_soup.new_tag('a', href=href)
        a.string = title
        li.append(a)
        ol.append(li)
    
    # Save updated nav.xhtml
    with open(nav_path, 'w', encoding='utf-8') as f:
        f.write(str(nav_soup))
    
    # Save updated content with IDs
    content_path = os.path.join(temp_dir, 'OPS', content_href)
    with open(content_path, 'w', encoding='utf-8') as f:
        f.write(str(content_soup))

def process_epub(epub_file):
    base_name, _ = os.path.splitext(epub_file.name)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract original EPUB
        with zipfile.ZipFile(epub_file, 'r') as z:
            z.extractall(temp_dir)
        
        # Process OPF file
        opf_path = os.path.join(temp_dir, 'OPS', 'package.opf')
        tree = ET.parse(opf_path)
        root = tree.getroot()
        content_href = find_content_path(root)
        content_path = os.path.join(temp_dir, 'OPS', content_href)
        
        # Parse content file
        with open(content_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml-xml')
        
        # Update TOC
        update_toc(temp_dir, soup, content_href)
        
        # Create new EPUB
        epub_buffer = BytesIO()
        with zipfile.ZipFile(epub_buffer, 'w') as new_epub:
            for root_dir, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    compress_type = zipfile.ZIP_STORED if arcname == 'mimetype' else zipfile.ZIP_DEFLATED
                    new_epub.write(file_path, arcname, compress_type=compress_type)
        
        epub_buffer.seek(0)
        epub_data = epub_buffer.getvalue()
        
        # Create TXT files
        chapters = []
        for section in soup.find_all('section', {'epub:type': 'chapter'}):
            title = section.find('h1')
            if title:
                title.extract()
            
            text_blocks = []
            for p in section.find_all('p', recursive=False):
                block_text = p.get_text(separator="\n", strip=True)
                if block_text.strip():
                    text_blocks.append(block_text)
            
            chapters.append("\n\n".join(text_blocks))
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for i, text in enumerate(chapters, 1):
                filename = f"{base_name}{i:02d}.txt"
                zipf.writestr(filename, text.encode('utf-8'))
        zip_buffer.seek(0)
        
        return zip_buffer.getvalue(), epub_data, base_name

if uploaded_file:
    with st.spinner("Processing EPUB..."):
        try:
            txt_zip, epub_data, base_name = process_epub(uploaded_file)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label=f"Download TXT Files ({base_name}.zip)",
                    data=txt_zip,
                    file_name=f"{base_name}_chapters.zip",
                    mime="application/zip"
                )
            
            with col2:
                st.download_button(
                    label=f"Download Updated EPUB ({base_name}_v2.epub)",
                    data=epub_data,
                    file_name=f"{base_name}_v2.epub",
                    mime="application/epub+zip"
                )
            
            st.success(f"Processed {base_name}.epub successfully!")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
else:
    st.info("Please upload an EPUB3 file to begin")
