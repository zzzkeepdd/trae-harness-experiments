import os

def save_file(uploaded_file, destination_dir, filename):
    filepath = os.path.join(destination_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(uploaded_file)
    return filepath

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ('.jpg', '.png', '.pdf', '.txt')
