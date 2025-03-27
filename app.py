import streamlit as st
from docx import Document
from bs4 import BeautifulSoup
import os
import zipfile
from io import BytesIO
import tempfile
import re

st.title("DOCX/EPUB Chapter Splitter")
uploaded_file = st.file_uploader("Upload a DOCX or EPUB file", type=["docx", "epub"])

def is_page_break(paragraph):
    """Check if a DOCX paragraph contains a page break"""
    for run in paragraph.runs:
        for elem in run._element:
            if (elem.tag == 
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br" 
                and elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"):
                return True
    return False

def parse_epub_toc(epub_zip):
    """Parse EPUB3/2 TOC specifically for your structure"""
    toc_entries = []
    
    # Check for EPUB3 XHTML TOC
    if 'OPS/table-of-contents.xhtml' in epub_zip.namelist():
        with epub_zip.open('OPS/table-of-contents.xhtml') as toc_file:
            soup = BeautifulSoup(toc_file, 'lxml')
            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)
                src = a['href']
                toc_entries.append((title, src))
    
    # Fallback to EPUB2 NCX TOC
    elif 'OPS/table-of-contents.ncx' in epub_zip.namelist():
        with epub_zip.open('OPS/table-of-contents.ncx') as ncx_file:
            soup = BeautifulSoup(ncx_file, 'xml')
            for nav_point in soup.find_all('navPoint'):
                title = nav_point.navLabel.text.strip()
                src = nav_point.content['src']
                toc_entries.append((title, src))
    
    return toc_entries

def extract_epub_chapters(epub_path):
    """Extract chapters specifically for your content.xhtml structure"""
    chapters = []
    with zipfile.ZipFile(epub_path) as epub_zip:
        toc_entries = parse_epub_toc(epub_zip)
        
        with tempfile.TemporaryDirectory() as extract_dir:
            epub_zip.extractall(extract_dir)
            
            for title, src in toc_entries:
                # Handle both full paths and fragment identifiers
                src_parts = src.split('#', 1)
                html_file = src_parts[0] if src_parts[0] else 'OPS/content.xhtml'
                fragment_id = src_parts[1] if len(src_parts) > 1 else None
                
                html_path = os.path.join(extract_dir, html_file)
                
                if not os.path.exists(html_path):
                    continue
                
                with open(html_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'lxml')
                
                # Find the chapter section
                if fragment_id:
                    chapter_section = soup.find(id=fragment_id)
                    if chapter_section and chapter_section.parent.name == 'section':
                        # Get full chapter content
                        chapter_content = chapter_section.parent.get_text(separator='\n', strip=True)
                        chapters.append((title, [chapter_content]))
                else:
                    # Handle full HTML content
                    sections = soup.find_all('section', {'epub:type': 'chapter'})
                    for section in sections:
                        chapter_text = section.get_text(separator='\n', strip=True)
                        chapters.append((title, [chapter_text]))
    
    return chapters

if uploaded_file:
    with st.spinner("Processing..."):
        try:
            temp_dir = tempfile.TemporaryDirectory()
            file_ext = uploaded_file.name.split('.')[-1].lower()
            chapters = []
            
            # DOCX Processing
            if file_ext == 'docx':
                doc = Document(uploaded_file)
                current_chapter = []
                for para in doc.paragraphs:
                    if is_page_break(para):
                        if current_chapter:
                            chapters.append(current_chapter)
                            current_chapter = []
                    else:
                        current_chapter.append(para.text.strip())
                if current_chapter:
                    chapters.append(current_chapter)
            
            # EPUB Processing
            elif file_ext == 'epub':
                with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    chapters = extract_epub_chapters(tmp_file.name)
                os.unlink(tmp_file.name)
            
            else:
                st.error("Unsupported file format")
                raise ValueError("Unsupported file format")
            
            # Handle files with no chapters
            if not chapters:
                st.warning("No chapters found! Creating single chapter.")
                chapters = [(f"Chapter 1", ["No content detected"])]
            
            # Create text files with titles
            for i, (title, content) in enumerate(chapters, 1):
                filename = f"{title}.txt" if title else f"Chapter_{i}.txt"
                # Sanitize filename
                filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                with open(os.path.join(temp_dir.name, filename), "w", encoding="utf-8") as f:
                    f.write("\n".join(content))
            
            # Create ZIP archive
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir.name):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, arcname=file)
            
            st.success(f"Split into {len(chapters)} chapters successfully!")
            st.download_button(
                label="Download Chapters",
                data=zip_buffer.getvalue(),
                file_name="chapters.zip",
                mime="application/zip"
            )
        
        except Exception as e:
            st.error(f"Processing error: {str(e)}")
        
        finally:
            temp_dir.cleanup()
else:
    st.info("Please upload a DOCX or EPUB file to begin")