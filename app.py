import streamlit as st
from docx import Document
from odf.opendocument import load
from odf import text
from odf.teletype import extractText
import os
import zipfile
from io import BytesIO
import tempfile

st.title("DOCX/ODT Chapter Splitter (Page Break Edition)")

uploaded_file = st.file_uploader("Upload a DOCX or ODT file", type=["docx", "odt"])

def is_page_break(paragraph):
    """Check if a DOCX paragraph contains a page break"""
    for run in paragraph.runs:
        for elem in run._element:
            if (elem.tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br" 
                and elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"):
                return True
    return False

def is_page_break_odt(paragraph):
    """Check if an ODT paragraph contains a page break"""
    for node in paragraph.childNodes:
        # Instead of using text.LineBreak.qname, check the node's name directly.
        if node.nodeName == "text:line-break" and node.getAttribute('type') == 'page':
            return True
    return False

if uploaded_file:
    with st.spinner("Processing..."):
        try:
            temp_dir = tempfile.TemporaryDirectory()
            file_ext = uploaded_file.name.split('.')[-1].lower()
            chapters = []
            current_chapter = []

            # DOCX Processing
            if file_ext == 'docx':
                doc = Document(uploaded_file)
                for para in doc.paragraphs:
                    if is_page_break(para):
                        if current_chapter:
                            chapters.append(current_chapter)
                            current_chapter = []
                    else:
                        current_chapter.append(para.text.strip())

            # ODT Processing
            elif file_ext == 'odt':
                with tempfile.NamedTemporaryFile(delete=False, suffix=".odt") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                odt_doc = load(tmp_path)
                paragraphs = odt_doc.text.getElementsByType(text.P)

                for para in paragraphs:
                    if is_page_break_odt(para):
                        if current_chapter:
                            chapters.append(current_chapter)
                            current_chapter = []
                    else:
                        text_content = extractText(para).strip()
                        if text_content:  # Skip empty paragraphs
                            current_chapter.append(text_content)

                os.unlink(tmp_path)

            else:
                st.error("Unsupported file format")
                raise ValueError("Unsupported file format")

            # Add final chapter
            if current_chapter:
                chapters.append(current_chapter)

            # Handle files with no page breaks
            if not chapters:
                st.warning("No page breaks found! Treating as single chapter.")
                chapters = [current_chapter]

            # Create text files (excluding title/first paragraph)
            for i, chapter in enumerate(chapters, 1):
                filename = f"Chapter_{i}.txt"
                # Skip first paragraph if it exists
                content = chapter[1:] if len(chapter) > 1 else []
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
    st.info("Please upload a DOCX or ODT file to begin")