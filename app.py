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
        try:
            temp_dir = tempfile.TemporaryDirectory()
            doc = Document(uploaded_file)
            
            chapters = {}
            current_chapter = None
            
            for para in doc.paragraphs:
                # Allow multiple heading styles (adjust as needed)
                if para.style.name in ["Heading 1", "Heading 2"]:
                    current_chapter = para.text.strip()
                    chapters[current_chapter] = []
                elif current_chapter:
                    chapters[current_chapter].append(para.text.strip())
            
            # Debugging output
            st.write(f"Detected {len(chapters)} chapters:")
            st.write(list(chapters.keys()))
            
            # Handle documents with no headings
            if not chapters:
                st.warning("No chapters detected! Treating as a single document.")
                chapters["Full_Document"] = [para.text.strip() for para in doc.paragraphs]
            
            # Save to text files
            for chapter, content in chapters.items():
                safe_title = "".join([c if c.isalnum() else "_" for c in chapter]) + ".txt"
                with open(os.path.join(temp_dir.name, safe_title), "w", encoding="utf-8") as f:
                    f.write("\n".join(content))
            
            # Create ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zipf:
                for root, _, files in os.walk(temp_dir.name):
                    for file in files:
                        zipf.write(os.path.join(root, file), arcname=file)
            
            st.success(f"Successfully split into {len(chapters)} chapters!")
            st.download_button(
                label="Download ZIP",
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