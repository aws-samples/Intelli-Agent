import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Iterator
from langchain.document_loaders.pdf import BasePDFLoader
from langchain.docstore.document import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NougatPDFLoader(BasePDFLoader):
    """A PDF loader class for converting PDF files to MMD.

    This class leverages the `nougat` library to perform the conversion from PDF to HTML.
    It inherits from `BasePDFLoader` and extends its functionality to utilize the `nougat` library.

    Attributes:
        file_path (str): The path to the PDF file to be loaded.
        headers (Optional[Dict]): Optional headers to be used when loading the PDF.

    Raises:
        ImportError: If the `nougat` library is not installed.
        RuntimeError: If the `nougat` command fails to execute successfully.
    """
    def __init__(self, file_path: str, *, headers: Optional[Dict] = None):
        """Initialize with a file path."""
        try:
            import nougat
        except ImportError:
            raise ImportError(
                "Please install nougat to use NougatPDFLoader. "
                "You can install it with `pip install nougat`."
            )

        super().__init__(file_path, headers=headers)

    def nougat(self, file_path: Path) -> str:
        """Executes the `nougat` command to convert the specified PDF file to Markdown format.

        Args:
            file_path (Path): The path to the PDF file to be converted.

        Returns:
            str: The Markdown content resulting from the `nougat` conversion.
        """
        # nougat ./paperSnapshot.pdf --full-precision --markdown -m 0.1.0-base -o tmp --recompute
        cli_command = ["nougat", str(file_path), "full-precision", "--markdown", "-m", "0.1.0-base", "-o", "tmp", "--recompute"]

        try:
            result = subprocess.run(
                cli_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            result.check_returncode()
            return result.stdout

        except subprocess.CalledProcessError as e:
            logging.error(
                f"Nougat command failed with return code {e.returncode}: {e.stderr}"
            )
            raise RuntimeError("Nougat command failed.") from e

    def load(self) -> List[Document]:
        """Loads and processes the specified PDF file, converting it to a list of Document objects.

        Returns:
            List[Document]: A list containing a single Document object with the processed content.
        """
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load and process the specified PDF file, yielding Document objects.

        This method reads the PDF file, processes it using the `nougat` command,
        reads the resulting Markdown content, and yields a Document object with the content.
        """
        try:
            file_path = self.file_path
            # Call the method to run the Nougat OCR command
            self.nougat(file_path)

            # Rest of your code for reading and processing the output
            file_path = Path(file_path)
            output_path = Path("tmp") / f"{file_path.stem}.mmd"
            with output_path.open("r") as f:
                content = f.read()
            # consider math expressions are enclosed in \( and \) in Markdown
            content = (
                content.replace(r"\(", "$")
                .replace(r"\)", "$")
                .replace(r"\[", "$$")
                .replace(r"\]", "$$")
            )
            metadata = {"source": self.file_path}
            yield Document(page_content=content, metadata=metadata)

        except Exception as e:
            logging.error(f"An error occurred while processing the PDF: {str(e)}")

# local debugging purpose
# if __name__ == "__main__":
#     # local pdf file in current folder
#     loader = NougatPDFLoader('paperSnapshot.pdf')
#     data = loader.load()
#     logging.info("text: %s", data)