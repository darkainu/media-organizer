import os
import shutil
from datetime import datetime
from PIL import Image
import exifread
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

class MediaOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Media File Organizer")
        self.root.geometry("600x400")
        self.moved_files = set()

        # Month names mapping
        self.month_name = {
            1: "01_January", 2: "02_February", 3: "03_March",
            4: "04_April", 5: "05_May", 6: "06_June",
            7: "07_July", 8: "08_August", 9: "09_September",
            10: "10_October", 11: "11_November", 12: "12_December"
        }

        self.create_widgets()

    def create_widgets(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # Select folder button
        self.select_btn = tk.Button(self.main_frame, text="Select Folder", command=self.select_folder)
        self.select_btn.pack(pady=20)

        # Display selected path
        self.path_label = tk.Label(self.main_frame, text="No folder selected", wraplength=500)
        self.path_label.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame, length=400, mode='determinate')
        self.progress.pack(pady=20)

        # Status label
        self.status_label = tk.Label(self.main_frame, text="")
        self.status_label.pack(pady=10)

        # Organize button
        self.organize_btn = tk.Button(self.main_frame, text="Organize Files", command=self.organize_files)
        self.organize_btn.pack(pady=20)

        # Revert button
        self.revert_btn = tk.Button(self.main_frame, text="Revert Changes", command=self.revert_changes)
        self.revert_btn.pack(pady=20)

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path = folder_path
            self.path_label.config(text=f"Selected: {folder_path}")

    def organize_files(self):
        if not hasattr(self, 'folder_path'):
            self.status_label.config(text="Please select a folder first!")
            return

        files = [f for f in os.listdir(self.folder_path)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.avi', '.mp', '.heic'))]

        self.progress['maximum'] = len(files)
        self.progress['value'] = 0

        for i, file in enumerate(files):
            file_path = os.path.join(self.folder_path, file)
            date_taken = self.get_date_taken(file_path)

            # Create year/month folder structure
            year_folder = os.path.join(self.folder_path, str(date_taken.year))
            month_folder = os.path.join(year_folder, self.month_name[date_taken.month])

            # Create folders if they don't exist
            os.makedirs(month_folder, exist_ok=True)

            # Move file to appropriate folder
            destination = os.path.join(month_folder, file)
            shutil.move(file_path, destination)
            self.moved_files.add((destination, file_path))

            # Update progress
            self.progress['value'] = i + 1
            self.root.update()

        self.status_label.config(text="Organization complete!")

    def get_date_taken(self, file_path):
        try:
            # 1. Try EXIF data first (most accurate for photos)
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                if 'EXIF DateTimeOriginal' in tags:
                    date_str = str(tags['EXIF DateTimeOriginal'])
                    return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')

            # 2. Try getting creation time (birthtime) if available
            stat = os.stat(file_path)
            creation_time = stat.st_birthtime if hasattr(stat, 'st_birthtime') else stat.st_ctime
            modified_time = stat.st_mtime

            # Use the earlier of creation or modification time
            earliest_time = min(creation_time, modified_time)
            return datetime.fromtimestamp(earliest_time)

        except Exception:
            # Fallback to modification time if all else fails
            return datetime.fromtimestamp(os.path.getmtime(file_path))

    def revert_changes(self):
        if not self.moved_files:
            self.status_label.config(text="No changes to revert!")
            return

        for new_path, original_path in self.moved_files:
            if os.path.exists(new_path):
                os.makedirs(os.path.dirname(original_path), exist_ok=True)
                shutil.move(new_path, original_path)

        self.moved_files.clear()
        self.status_label.config(text="All changes reverted!")

if __name__ == "__main__":
    root = tk.Tk()
    app = MediaOrganizerApp(root)
    root.mainloop()

HOME_DIR = Path.home()
APP_DIR = Path(__file__).parent
CONFIG_PATH = APP_DIR / "config.env"

def revert_changes(self):
    if not self.moved_files:
        self.status_label.config(text="No changes to revert!")
        return

    for new_path, original_path in self.moved_files:
        if os.path.exists(new_path):
            os.makedirs(os.path.dirname(original_path), exist_ok=True)
            shutil.move(new_path, original_path)

    self.moved_files.clear()
    self.status_label.config(text="All changes reverted!")

import configparser

def select_folder(self):
    home_dir = str(Path.home())
    folder_path = filedialog.askdirectory(initialdir=home_dir)
    if folder_path:
        self.folder_path = folder_path
        self.path_label.config(text=f"Selected: {folder_path}")
