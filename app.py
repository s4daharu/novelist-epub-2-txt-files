import streamlit as st
from docx import Document
from bs4 import BeautifulSoup
import os
import zipfile
from io import BytesIO
import tempfile

st.title("DOCX/EPUB Chapter Splitter (Page Break Edition)")
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

def extract_epub_chapters(epub_path):
    """Extract chapters from EPUB using CSS page-break detection"""
    chapters = []
    current_chapter = []
    
    with zipfile.ZipFile(epub_path) as epub_zip:
        # Extract EPUB contents to temporary directory
        with tempfile.TemporaryDirectory() as extract_dir:
            epub_zip.extractall(extract_dir)
            
            # Find all HTML/XHTML files
            html_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(('.html', '.xhtml')):
                        html_files.append(os.path.join(root, file))
            
            for html_file in html_files:
                with open(html_file, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'lxml')
                
                for element in soup.descendants:
                    if isinstance(element, str):
                        continue  # Skip text nodes
                    
                    style = element.get('style', '')
                    if 'page-break-before: always' in style or 'page-break-after: always' in style:
                        if current_chapter:
                            chapters.append(current_chapter)
                            current_chapter = []
                    else:
                        text_content = element.get_text(strip=True, separator=' ')
                        if text_content:
                            current_chapter.append(text_content)
                
                # Add remaining content as final chapter in file
                if current_chapter:
                    chapters.append(current_chapter)
                    current_chapter = []
    
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
                chapters = [chapters]
            
            # Create text files (excluding first paragraph)
            for i, chapter in enumerate(chapters, 1):
                filename = f"Chapter_{i}.txt"
                # Skip first paragraph if exists
                content = chapter[1:] if len(chapter) > 1 else chapter
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