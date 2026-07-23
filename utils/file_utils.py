"""
utils/file_utils.py - File Handling Utilities
==============================================
Secure file upload helpers used by the admin dataset upload route.
"""

import os
import uuid
from werkzeug.utils import secure_filename


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Check if a filename has an allowed extension.

    Args:
        filename:          The original uploaded filename.
        allowed_extensions: Set of lowercase allowed extensions (e.g. {'csv', 'xlsx'}).

    Returns:
        True if the extension is in the allowed set.
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )


def save_uploaded_file(file_storage, destination_folder: str) -> str:
    """
    Save a werkzeug FileStorage object securely to disk.

    - Sanitises the filename with werkzeug's secure_filename.
    - Prepends a UUID to prevent filename collisions.
    - Creates destination_folder if it does not exist.

    Args:
        file_storage:       werkzeug.datastructures.FileStorage object.
        destination_folder: Absolute path to save the file.

    Returns:
        The saved filename (not the full path).
    """
    os.makedirs(destination_folder, exist_ok=True)

    original_name  = secure_filename(file_storage.filename)
    unique_prefix  = uuid.uuid4().hex[:8]
    safe_filename  = f"{unique_prefix}_{original_name}"
    full_path      = os.path.join(destination_folder, safe_filename)

    file_storage.save(full_path)
    return safe_filename


def get_file_size(filepath: str) -> int:
    """
    Return the file size in bytes.

    Args:
        filepath: Absolute path to the file.

    Returns:
        File size in bytes, or 0 if the file does not exist.
    """
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0
