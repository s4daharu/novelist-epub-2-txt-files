import streamlit as st
from docx import Document
import os
import zipfile
from io import BytesIO
import tempfile

st.title("DOCX Chapter Splitter")

uploaded_file = st.file_uploader("Upload a DOCX file", type=["docx"])

if uploaded_file:
    with st.spinner("Processing..."):
        # Create a temporary directory
        temp_dir = tempfile.TemporaryDirectory()
        
        # Read the DOCX file
        doc = Document(uploaded_file)
        
        current_chapter = None
        chapters = {}
        
        for para in doc.paragraphs:
            if para.style.name == 'Heading 1':
                chapter_title = para.text.strip()
                current_chapter = chapter_title
                chapters[current_chapter] = []
            elif current_chapter:
                chapters[current_chapter].append(para.text.strip())
        
        # Create text files for each chapter
        for chapter, content in chapters.items():
            safe_title = "".join([c if c.isalnum() else "_" for c in chapter]) + ".txt"
            file_path = os.path.join(temp_dir.name, safe_title)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content))
        
        # Create ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for root, dirs, files in os.walk(temp_dir.name):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=file)
        
        st.success(f"Successfully split into {len(chapters)} chapters!")
        st.download_button(
            label="Download ZIP",
            data=zip_buffer.getvalue(),
            file_name="chapters.zip",
            mime="application/zip"
        )
        
        # Cleanup
        temp_dir.cleanup()
else:
    st.info("Please upload a DOCX file to begin")