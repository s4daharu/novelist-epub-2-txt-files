import streamlit as st
from docx import Document
from ebooklib import epub
from bs4 import BeautifulSoup
import os
import zipfile
from io import BytesIO
import tempfile

st.title("DOCX/EPUB Chapter Splitter (Page Break Edition)")

uploaded_file = st.file_uploader("Upload a DOCX or EPUB file", type=["docx", "epub"])

def is_page_break(paragraph):
    """Check if a DOCX paragraph contains a page break."""
    for run in paragraph.runs:
        for elem in run._element:
            if (elem.tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br" 
                and elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"):
                return True
    return False

if uploaded_file:
    with st.spinner("Processing..."):
        try:
            temp_dir = tempfile.TemporaryDirectory()
            file_ext = uploaded_file.name.split('.')[-1].lower()
            chapters = []

            # DOCX Processing remains unchanged.
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

            # EPUB Processing for EPUB3 (OPS/Book structure)
            elif file_ext == 'epub':
                # Write the uploaded file to a temporary file.
                with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file.flush()
                    epub_path = tmp_file.name

                book = epub.read_epub(epub_path)
                os.unlink(epub_path)  # Clean up the temporary file

                # Look for the content file; typically its href contains "content.xhtml"
                content_item = None
                for item in book.get_items_of_type(epub.EpubHtml):
                    if "content.xhtml" in item.href.lower():
                        content_item = item
                        break

                if content_item is None:
                    st.error("Could not locate the content.xhtml file in the EPUB.")
                    raise ValueError("Missing content.xhtml in EPUB.")

                # Parse the content file with BeautifulSoup.
                soup = BeautifulSoup(content_item.get_content(), 'html.parser')
                # Find all sections that are marked as chapters.
                section_list = soup.find_all('section', attrs={"epub:type": "chapter"})
                if not section_list:
                    st.warning("No chapter sections found in content.xhtml; treating entire file as one chapter.")
                    full_text = soup.get_text(separator="\n").strip()
                    chapters.append(full_text.splitlines())
                else:
                    for sec in section_list:
                        paras = []
                        for p in sec.find_all('p'):
                            text_line = p.get_text().strip()
                            if text_line:
                                paras.append(text_line)
                        if paras:
                            chapters.append(paras)
            else:
                st.error("Unsupported file format")
                raise ValueError("Unsupported file format")

            # If no chapters were found, use a fallback.
            if not chapters:
                st.warning("No chapters found! Treating the file as a single chapter.")
                chapters = [["No content extracted"]]

            # Create a text file for each chapter.
            for i, chapter in enumerate(chapters, 1):
                filename = f"Chapter_{i}.txt"
                # Optionally skip the first paragraph if desired.
                content = chapter[1:] if len(chapter) > 1 else chapter
                with open(os.path.join(temp_dir.name, filename), "w", encoding="utf-8") as f:
                    f.write("\n".join(content))

            # Create a ZIP archive containing all chapter text files.
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir.name):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, arcname=file)
            zip_buffer.seek(0)

            st.success(f"Split into {len(chapters)} chapters successfully!")
            st.download_button(
                label="Download Chapters",
                data=zip_buffer,
                file_name="chapters.zip",
                mime="application/zip"
            )

        except Exception as e:
            st.error(f"Processing error: {str(e)}")
        finally:
            temp_dir.cleanup()
else:
    st.info("Please upload a DOCX or EPUB file to begin")