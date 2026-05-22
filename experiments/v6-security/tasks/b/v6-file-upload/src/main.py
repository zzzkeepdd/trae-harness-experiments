import os
import hashlib

ALLOWED_EXTENSIONS = {'.jpg', '.png', '.pdf', '.txt', '.json'}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAGIC_BYTES = {
    b'\xff\xd8\xff': '.jpg',
    b'\x89PNG\r\n\x1a\n': '.png',
    b'%PDF': '.pdf',
}

def save_file(file_content, destination_dir, filename):
    if not filename:
        raise ValueError("filename required")
    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError("file too large")

    safe_name = os.path.normpath(filename)
    if safe_name.startswith('..') or os.path.isabs(safe_name):
        raise ValueError("path traversal detected")
    basename = os.path.basename(safe_name)
    if basename != safe_name:
        raise ValueError("nested path rejected")

    destination_dir = os.path.normpath(os.path.abspath(destination_dir))
    filepath = os.path.normpath(os.path.join(destination_dir, basename))
    if not filepath.startswith(destination_dir):
        raise ValueError("path escape detected")

    os.makedirs(destination_dir, exist_ok=True)
    tmp_path = filepath + ".tmp." + hashlib.md5(os.urandom(16)).hexdigest()[:8]
    try:
        with open(tmp_path, 'wb') as f:
            f.write(file_content)
        os.replace(tmp_path, filepath)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return filepath

def allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def validate_magic_bytes(file_content, filename):
    if not file_content or len(file_content) < 4:
        return False
    ext = os.path.splitext(filename)[1].lower()
    for magic, expected_ext in MAGIC_BYTES.items():
        if file_content.startswith(magic):
            return ext == expected_ext
    return ext in ('.txt', '.json')
