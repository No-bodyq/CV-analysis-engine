import pdfplumber
from docx import Document
import os


def clean_text(text: str) -> str:
    """
    Cleans extracted text by removing extra spaces and line breaks.
    """
    text = text.replace("\n", " ")
    text = " ".join(text.split())
    return text.strip()


def extract_text_from_pdf(file) -> str:
    """
    Extracts text from a PDF file using pdfplumber.
    """
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        text = clean_text(text)

        if not text:
            raise ValueError("No readable text found in the PDF.")

        return text

    except Exception as e:
        raise ValueError(f"Could not read PDF file: {str(e)}")


def extract_text_from_docx(file) -> str:
    """
    Extracts text from a Word document (.docx).
    """
    text = ""
    try:
        doc = Document(file)
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"

        text = clean_text(text)

        if not text:
            raise ValueError("No readable text found in the DOCX file.")

        return text

    except Exception as e:
        raise ValueError(f"Could not read Word document: {str(e)}")


def extract_cv_text(file, filename: str) -> str:
    """
    Master function:
    Detects file type and extracts text accordingly.

    Supported formats:
    - PDF (.pdf)
    - Word (.docx)

    Raises:
        ValueError for unsupported formats or unreadable files.
    """
    filename = filename.lower()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file)

    elif filename.endswith(".docx"):
        return extract_text_from_docx(file)

    elif filename.endswith(".doc"):
        raise ValueError(
            "Old .doc format is not supported. "
            "Please save your CV as .docx or PDF and try again."
        )

    else:
        raise ValueError(
            "Unsupported file format. Please upload a PDF or DOCX file."
        )


# ================================
# TEST BLOCK (for manual testing)
# ================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cv_reader.py yourfile.pdf")
        print("  python cv_reader.py yourfile.docx")
    else:
        file_path = sys.argv[1]

        if not os.path.exists(file_path):
            print("Error: File does not exist.")
            exit()

        filename = os.path.basename(file_path)

        try:
            with open(file_path, "rb") as f:
                extracted_text = extract_cv_text(f, filename)

            print("=" * 50)
            print("EXTRACTED TEXT:")
            print("=" * 50)
            print(extracted_text)
            print("=" * 50)
            print(f"Total words extracted: {len(extracted_text.split())}")

        except Exception as e:
            print(f"Error: {str(e)}")