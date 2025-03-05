import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter, Language
import code_snippets as code_snippets
import tiktoken
import streamlit.components.v1 as components
from ebooklib import epub
from bs4 import BeautifulSoup

# ---------- Helper Function ----------
def extract_chapters(epub_file_path):
    """
    Extracts chapters from an EPUB file by decoding and parsing XHTML content.
    Returns a list of plain text chapters.
    """
    book = epub.read_epub(epub_file_path)
    chapters = []
    for item in book.get_items():
        # Check for items of type EpubHtml or items with a .xhtml filename.
        if item.get_type() == epub.EpubHtml or item.get_name().endswith('.xhtml'):
            try:
                content = item.get_body_content().decode('utf-8')
            except Exception:
                try:
                    content = item.get_body_content().decode('gb18030')
                except Exception:
                    content = item.get_body_content().decode('latin-1', errors='ignore')
            # Use BeautifulSoup to strip HTML tags and extract text.
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator="\n")
            chapters.append(text)
    return chapters

# ---------- UI Header ----------
st.title("Text Splitter & EPUB Chapter Translator Playground")
st.info(
    """Split a text into chunks using a **Text Splitter** and add a translation prefix for each chunk.

**Configuration Parameters:**

- **Chunk Size**: Maximum size of the resulting chunks.
- **Chunk Overlap**: Overlap between the chunks.
- **Length Function**: Measurement method for chunk lengths (Characters or Tokens).
- **Text Splitter**: Determines the splitting strategy.

You can either manually paste text or upload an EPUB file. When uploading an EPUB, its chapters will be extracted, and you can navigate or directly choose a chapter.
"""
)

# ---------- Input Method Selection (default set to EPUB) ----------
input_method = st.radio("Input Method", ["Upload EPUB", "Manual Input"], index=0)

# ---------- Common Text Splitter Configuration ----------
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])

with col1:
    chunk_size = st.number_input("Chunk Size", min_value=1, value=1950)

with col2:
    chunk_overlap = st.number_input("Chunk Overlap", min_value=1, max_value=chunk_size - 1, value=40)
    if chunk_overlap >= chunk_size:
        st.warning("Chunk Overlap should be less than Chunk Size!")

with col3:
    length_function_choice = st.selectbox("Length Function", ["Characters", "Tokens"], index=0)

splitter_choices = ["Character", "RecursiveCharacter"] + [str(v) for v in Language]
with col4:
    splitter_choice = st.selectbox("Select a Text Splitter", splitter_choices, index=0)

if length_function_choice == "Characters":
    length_function = len
    length_function_str = code_snippets.CHARACTER_LENGTH
elif length_function_choice == "Tokens":
    enc = tiktoken.get_encoding("cl100k_base")
    def length_function(text: str) -> int:
        return len(enc.encode(text))
    length_function_str = code_snippets.TOKEN_LENGTH
else:
    st.error("Invalid Length Function selection.")

if splitter_choice == "Character":
    import_text = code_snippets.CHARACTER.format(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=length_function_str
    )
elif splitter_choice == "RecursiveCharacter":
    import_text = code_snippets.RECURSIVE_CHARACTER.format(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=length_function_str
    )
elif "Language." in splitter_choice:
    import_text = code_snippets.LANGUAGE.format(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, language=splitter_choice, length_function=length_function_str
    )
else:
    st.error("Invalid Text Splitter selection.")

# Display code snippet with syntax highlighting
st.code(import_text, language="python")

# ---------- Input Section ----------
doc = ""
if input_method == "Manual Input":
    doc = st.text_area("Paste your text here:")
elif input_method == "Upload EPUB":
    uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])
    if uploaded_file is not None:
        # Save the uploaded EPUB file temporarily.
        with open("temp.epub", "wb") as f:
            f.write(uploaded_file.getbuffer())
        chapters = extract_chapters("temp.epub")
        
        if not chapters:
            st.error("No chapters were found in the uploaded EPUB file. Please ensure the EPUB is properly formatted.")
        else:
            st.success(f"Found {len(chapters)} chapters in the EPUB file.")
            
            # Use session state to store the chapter index.
            if "chapter_index" not in st.session_state:
                st.session_state.chapter_index = 0

            # Navigation buttons.
            col_prev, col_next = st.columns(2)
            with col_prev:
                if st.button("Previous Chapter") and st.session_state.chapter_index > 0:
                    st.session_state.chapter_index -= 1
            with col_next:
                if st.button("Next Chapter") and st.session_state.chapter_index < len(chapters) - 1:
                    st.session_state.chapter_index += 1

            # Select box for choosing a chapter number.
            chapter_numbers = list(range(1, len(chapters) + 1))
            selected_chapter = st.selectbox("Select Chapter Number", chapter_numbers, index=st.session_state.chapter_index)
            st.session_state.chapter_index = selected_chapter - 1

            st.markdown(f"### Chapter {st.session_state.chapter_index + 1}")
            doc = chapters[st.session_state.chapter_index]
            st.text_area("Chapter Text", doc, height=300)

# ---------- Translation Prefix ----------
prefix = "translate following text from chinese to english\n"

# ---------- Text Splitting & Processing ----------
if st.button("Split Text"):
    if not doc:
        st.error("No text provided. Please paste text or upload an EPUB file.")
    else:
        # Choose the text splitter based on configuration.
        if splitter_choice == "Character":
            splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function
            )
        elif splitter_choice == "RecursiveCharacter":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function
            )
        elif "Language." in splitter_choice:
            language = splitter_choice.split(".")[1].lower()
            splitter = RecursiveCharacterTextSplitter.from_language(
                language,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function
            )
        else:
            st.error("Invalid Text Splitter selection.")
            splitter = None

        if splitter:
            # Split the text and add the translation prefix to each chunk.
            splits = splitter.split_text(doc)
            split_chunks = [prefix + s for s in splits]
            for idx, chunk_with_prefix in enumerate(split_chunks, start=1):
                # HTML snippet for a scrollable code block with header containing the Copy button.
                copy_button_html = f"""
                <div style="border: 1px solid #ddd; border-radius: 6px; overflow: hidden; margin-top: 10px;">
                    <div style="background: #f5f5f5; padding: 4px 8px; text-align: right;">
                        <button onclick="copyToClipboard_{idx}()" style="border: none; background: transparent; cursor: pointer; font-size: 12px;">Copy</button>
                    </div>
                    <pre id="code_block_{idx}" style="margin: 0; padding: 8px; font-family: monospace; background: #f6f8fa; overflow: auto; max-height: 300px; white-space: pre;">{chunk_with_prefix}</pre>
                </div>
                <script>
                    function copyToClipboard_{idx}() {{
                        const code = document.getElementById("code_block_{idx}").innerText;
                        navigator.clipboard.writeText(code).then(() => {{
                            console.log("Code copied to clipboard.");
                        }}, (err) => {{
                            console.error("Failed to copy text: ", err);
                        }});
                    }}
                </script>
                """
                st.markdown(copy_button_html, unsafe_allow_html=True)
