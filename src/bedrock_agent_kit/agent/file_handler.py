import os
from typing import Dict, Any, Optional


class FileHandler:
    """Handles file-related events and storage"""

    def __init__(self, output_directory: str = "output"):
        """Initialize FileHandler

        Args:
            output_directory: Directory to store output files. Defaults to "output"
        """
        self._output_directory = output_directory

        # Create output directory if it doesn't exist
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

    def process_file_event(self, file_event: Dict[str, Any]) -> Optional[str]:
        """Process file event from agent response

        Args:
            file_event: Dictionary containing file event data

        Returns:
            str: Path to saved file if successful, None otherwise
        """
        if "files" not in file_event:
            return None

        files_list = file_event["files"]["files"]
        for this_file in files_list:
            file_name = this_file['name']
            # file_type = this_file['type']
            file_bytes = this_file["bytes"]

            self.save_file(file_bytes, file_name)

    def save_file(self, file_data: bytes, file_name: str) -> str:
        """Save file to the output directory

        Args:
            file_data: Binary file data
            file_name: Name of the file

        Returns:
            str: Path to saved file
        """
        file_path = os.path.join(self._output_directory, file_name)

        with open(file_path, "wb") as f:
            f.write(file_data)

        return file_path
