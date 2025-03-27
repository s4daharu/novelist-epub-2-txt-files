import streamlit as st
from docx import Document
from ezodf import opendoc
import os
import zipfile
from io import BytesIO
import tempfile
from lxml import etree

st.title("Document Splitter (DOCX/ODT)")

uploaded_file = st.file_uploader("Upload a file", type=["docx", "odt"])

def is_page_break_docx(paragraph):
    """Check for page breaks in DOCX paragraphs"""
    for run in paragraph.runs:
        for elem in run._element:
            if (elem.tag == 
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br" 
                and elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"):
                return True
    return False

def is_page_break_odt(paragraph):
    """Check for page breaks in ODT paragraphs"""
    for child in paragraph.xmlnode.iter():
        if 'text:soft-page-break' in child.tag:
            return True
    return False

if uploaded_file:
    file_ext = uploaded_file.name.split('.')[-1].lower()
    temp_dir = tempfile.TemporaryDirectory()
    
    try:
        chapters = []
        current_chapter = []
        
        if file_ext == 'docx':
            doc = Document(uploaded_file)
            for para in doc.paragraphs:
                if is_page_break_docx(para):
                    if current_chapter:
                        chapters.append(current_chapter)
                        current_chapter = []
                else:
                    current_chapter.append(para.text.strip())
        
        elif file_ext == 'odt':
            doc = opendoc(uploaded_file)
            for element in doc.body:
                if isinstance(element, ezodf.text.P):
                    if is_page_break_odt(element):
                        if current_chapter:
                            chapters.append(current_chapter)
                            current_chapter = []
                    else:
                        current_chapter.append(element.plaintext().strip())
        
        # Add final chapter
        if current_chapter:
            chapters.append(current_chapter)
        
        # Handle no-split case
        if not chapters:
            chapters = [current_chapter] if current_chapter else []
            if not chapters:
                st.warning("Empty document detected")
                st.stop()
        
        # Create text files
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, chapter in enumerate(chapters, 1):
                filename = f"section_{i}.txt"
                with open(os.path.join(temp_dir, filename), "w", encoding="utf-8") as f:
                    f.write("\n".join(chapter))
            
            # Create ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), arcname=file)
        
        st.success(f"Split into {len(chapters)} sections successfully!")
        st.download_button(
            label="Download Sections",
            data=zip_buffer.getvalue(),
            file_name="document_sections.zip",
            mime="application/zip"
        )
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    finally:
        temp_dir.cleanup()
else:
    st.info("Please upload a DOCX or ODT file")