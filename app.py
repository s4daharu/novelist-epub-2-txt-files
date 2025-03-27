import streamlit as st
from docx import Document
from bs4 import BeautifulSoup
import os
import zipfile
from io import BytesIO
import tempfile
import re

st.title("DOCX/EPUB Chapter Splitter (TOC/Page Break Edition)")
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

def parse_epub_toc(epub_path):
    """Parse EPUB TOC to get chapter titles and their source files"""
    toc_entries = []
    with zipfile.ZipFile(epub_path) as epub_zip:
        # Check for both EPUB 2 (toc.ncx) and EPUB 3 (nav.xhtml) TOC files
        if 'OEBPS/toc.ncx' in epub_zip.namelist():
            with epub_zip.open('OEBPS/toc.ncx') as toc_file:
                soup = BeautifulSoup(toc_file, 'xml')
                for nav_point in soup.find_all('navPoint'):
                    title = nav_point.navLabel.text.strip()
                    src = nav_point.content['src']
                    toc_entries.append((title, src))
        elif 'EPUB/nav.xhtml' in epub_zip.namelist():
            with epub_zip.open('EPUB/nav.xhtml') as nav_file:
                soup = BeautifulSoup(nav_file, 'lxml')
                for a in soup.nav.find_all('a', href=True):
                    title = a.text.strip()
                    src = a['href']
                    toc_entries.append((title, src))
    return toc_entries

def extract_epub_chapters(epub_path):
    """Extract chapters using TOC entries"""
    chapters = []
    toc_entries = parse_epub_toc(epub_path)
    
    with zipfile.ZipFile(epub_path) as epub_zip:
        with tempfile.TemporaryDirectory() as extract_dir:
            epub_zip.extractall(extract_dir)
            
            for title, src in toc_entries:
                # Handle both direct HTML references and fragment identifiers
                if '#' in src:
                    html_file, fragment = src.split('#', 1)
                else:
                    html_file = src
                    fragment = None
                
                html_path = os.path.join(extract_dir, html_file)
                
                if not os.path.exists(html_path):
                    continue
                
                with open(html_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'lxml')
                
                # Find content based on fragment ID
                if fragment:
                    content = soup.find(id=fragment)
                    if content:
                        chapter_text = [content.get_text(separator='\n', strip=True)]
                        chapters.append((title, chapter_text))
                else:
                    # If no fragment, take the entire HTML content
                    body = soup.find('body')
                    if body:
                        chapter_text = [p.get_text(separator='\n', strip=True) 
                                       for p in body.find_all(['p', 'h1', 'h2', 'h3'])]
                        chapters.append((title, chapter_text))
    
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
                # Remove invalid characters from filename
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