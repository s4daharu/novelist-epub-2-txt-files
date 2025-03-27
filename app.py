import streamlit as st
from docx import Document
import os
import zipfile
from io import BytesIO
import tempfile

st.title("DOCX Chapter Splitter (Page Break Edition)")

uploaded_file = st.file_uploader("Upload a DOCX file", type=["docx"])

def is_page_break(paragraph):
    """Check if a paragraph contains a page break"""
    for run in paragraph.runs:
        for elem in run._element:
            if (elem.tag == 
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br" 
                and elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"):
                return True
    return False

if uploaded_file:
    with st.spinner("Processing..."):
        try:
            temp_dir = tempfile.TemporaryDirectory()
            doc = Document(uploaded_file)
            
            chapters = []
            current_chapter = []
            
            for para in doc.paragraphs:
                if is_page_break(para):
                    # Save current chapter and start new one
                    if current_chapter:
                        chapters.append(current_chapter)
                        current_chapter = []
                else:
                    current_chapter.append(para.text.strip())
            
            # Add the last chapter
            if current_chapter:
                chapters.append(current_chapter)
            
            # Handle case with no page breaks
            if not chapters:
                st.warning("No page breaks found! Treating as single chapter.")
                chapters = [current_chapter]
            
            # Create text files
            for i, chapter in enumerate(chapters, 1):
                filename = f"Chapter_{i}.txt"
                with open(os.path.join(temp_dir.name, filename), "w", encoding="utf-8") as f:
                    f.write("\n".join(chapter))
            
            # Create ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zipf:
                for root, _, files in os.walk(temp_dir.name):
                    for file in files:
                        zipf.write(os.path.join(root, file), arcname=file)
            
            st.success(f"Split into {len(chapters)} chapters successfully!")
            st.download_button(
                label="Download Chapters",
                data=zip_buffer.getvalue(),
                file_name="chapters.zip",
                mime="application/zip"
            )
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
        
        finally:
            temp_dir.cleanup()
else:
    st.info("Please upload a DOCX file to begin")