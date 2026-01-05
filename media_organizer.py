import os
import shutil
import json
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
from pathlib import Path
from PIL import Image

class MediaOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Media File Organizer (Recursive)")
        self.root.geometry("700x550")
        
        # State variables
        self.folder_path = None
        self.is_processing = False
        self.undo_log_file = "organizer_undo_log.json"
        
        # Supported extensions (added common Google Takeout variations)
        self.extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', # Images
            '.mp4', '.mov', '.avi', '.mp', '.mkv', '.wmv', '.3gp',     # Videos
            '.heic', '.heif', '.raw', '.dng', '.cr2', '.nef', '.arw'   # Raw/Modern
        }
        
        self.create_widgets()

    def create_widgets(self):
        main = tk.Frame(self.root, padx=20, pady=20)
        main.pack(expand=True, fill='both')

        lbl_header = tk.Label(main, text="Media Organizer", font=("Helvetica", 16, "bold"))
        lbl_header.pack(pady=(0, 20))

        # Folder Selection
        frame_select = tk.Frame(main)
        frame_select.pack(fill='x', pady=5)
        
        self.btn_select = tk.Button(frame_select, text="Select Root Folder", command=self.select_folder, height=2)
        self.btn_select.pack(side='left', padx=(0, 10))
        
        self.lbl_path = tk.Label(frame_select, text="No folder selected", relief="sunken", anchor="w")
        self.lbl_path.pack(side='left', fill='x', expand=True, ipady=8)

        # Options
        self.chk_clean_var = tk.BooleanVar(value=True)
        self.chk_clean = tk.Checkbutton(main, text="Delete empty subfolders after moving files", variable=self.chk_clean_var)
        self.chk_clean.pack(anchor="w", pady=(10, 0))

        # Progress Section
        self.progress = ttk.Progressbar(main, orient="horizontal", length=100, mode='determinate')
        self.progress.pack(fill='x', pady=(20, 5))
        
        self.lbl_status = tk.Label(main, text="Ready", fg="grey")
        self.lbl_status.pack(pady=5)

        # Actions
        frame_actions = tk.Frame(main)
        frame_actions.pack(pady=20)

        self.btn_run = tk.Button(frame_actions, text="Organize All (Recursive)", command=self.start_organizing, 
                               bg="#e1f5fe", state="disabled", width=20, height=2)
        self.btn_run.pack(side='left', padx=10)

        self.btn_revert = tk.Button(frame_actions, text="Undo Changes", command=self.start_reverting, 
                                  bg="#ffebee", state="disabled", width=20, height=2)
        self.btn_revert.pack(side='left', padx=10)

        # Log Text Box
        self.txt_log = tk.Text(main, height=10, state='disabled', font=("Consolas", 9))
        self.txt_log.pack(fill='both', expand=True, pady=10)

    def log(self, message):
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, f"{message}\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path = Path(path)
            self.lbl_path.config(text=str(self.folder_path))
            self.btn_run.config(state="normal")
            self.check_undo_availability()
            self.log(f"Selected: {self.folder_path}")

    def check_undo_availability(self):
        if self.folder_path and (self.folder_path / self.undo_log_file).exists():
            self.btn_revert.config(state="normal")
        else:
            self.btn_revert.config(state="disabled")

    def toggle_controls(self, enable):
        state = "normal" if enable else "disabled"
        self.btn_select.config(state=state)
        self.btn_run.config(state=state)
        if enable: self.check_undo_availability()
        else: self.btn_revert.config(state="disabled")

    def get_date_taken(self, file_path):
        timestamp = None
        # 1. Try Image EXIF
        if file_path.suffix.lower() in {'.jpg', '.jpeg', '.tiff', '.png', '.webp'}:
            try:
                img = Image.open(file_path)
                exif = img.getexif()
                if exif:
                    # 36867=DateTimeOriginal, 306=DateTime
                    date_str = exif.get(36867) or exif.get(306)
                    if date_str:
                        timestamp = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            except Exception:
                pass

        # 2. Fallback to stats
        if not timestamp:
            stat = os.stat(file_path)
            creation_time = getattr(stat, 'st_birthtime', stat.st_mtime)
            timestamp = datetime.fromtimestamp(min(creation_time, stat.st_mtime))
        return timestamp

    def get_unique_path(self, destination):
        if not destination.exists():
            return destination
        counter = 1
        while True:
            new_name = f"{destination.stem}_{counter}{destination.suffix}"
            new_dest = destination.parent / new_name
            if not new_dest.exists():
                return new_dest
            counter += 1

    def clean_empty_folders(self):
        """Remove empty folders recursively bottom-up"""
        cleaned_count = 0
        for dirpath, dirnames, filenames in os.walk(self.folder_path, topdown=False):
            # Don't delete the root folder itself
            if Path(dirpath) == self.folder_path:
                continue
            try:
                # Remove if empty (rmdir only removes empty dirs)
                os.rmdir(dirpath)
                cleaned_count += 1
            except OSError:
                pass # Directory not empty
        return cleaned_count

    def start_organizing(self):
        if not self.folder_path: return
        threading.Thread(target=self.organize_process, daemon=True).start()

    def organize_process(self):
        self.is_processing = True
        self.root.after(0, lambda: self.toggle_controls(False))
        self.root.after(0, lambda: self.log("Scanning files recursively..."))
        
        # RECURSIVE SEARCH using rglob
        # We convert to list to freeze the list before we start moving things
        all_files = [f for f in self.folder_path.rglob('*') 
                     if f.is_file() and f.suffix.lower() in self.extensions and f.name != self.undo_log_file]
        
        total = len(all_files)
        moved_log = []
        
        self.root.after(0, lambda: self.progress.config(maximum=total, value=0))
        
        for i, file_path in enumerate(all_files):
            try:
                date_obj = self.get_date_taken(file_path)
                
                # New Structure: Root/2023/05_May
                month_name = date_obj.strftime("%m_%B")
                year_folder = self.folder_path / str(date_obj.year)
                month_folder = year_folder / month_name
                
                # Skip if file is already in the correct folder
                if file_path.parent == month_folder:
                    self.root.after(0, lambda v=i+1: self.progress.config(value=v))
                    continue

                month_folder.mkdir(parents=True, exist_ok=True)
                
                dest_path = month_folder / file_path.name
                final_dest = self.get_unique_path(dest_path)
                
                shutil.move(str(file_path), str(final_dest))
                
                moved_log.append({
                    "src": str(file_path.relative_to(self.folder_path)),
                    "dest": str(final_dest.relative_to(self.folder_path))
                })
                
                if i % 10 == 0: # Update UI every 10 files to reduce lag
                    self.root.after(0, lambda v=i+1: self.progress.config(value=v))
                
            except Exception as e:
                print(f"Error: {e}")

        # Save Undo Log
        if moved_log:
            log_path = self.folder_path / self.undo_log_file
            existing_data = []
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f: existing_data = json.load(f)
                except: pass
            
            existing_data.extend(moved_log)
            with open(log_path, 'w') as f: json.dump(existing_data, f, indent=2)

        # Cleanup Empty Folders
        cleaned_dirs = 0
        if self.chk_clean_var.get():
            self.root.after(0, lambda: self.log("Cleaning empty folders..."))
            cleaned_dirs = self.clean_empty_folders()

        self.root.after(0, lambda: [
            self.toggle_controls(True),
            self.progress.config(value=total),
            self.lbl_status.config(text=f"Done! Moved {len(moved_log)} files."),
            self.log(f"Organization Complete.\nMoved: {len(moved_log)} files.\nRemoved: {cleaned_dirs} empty folders."),
            messagebox.showinfo("Success", f"Organized {len(moved_log)} files.\nCleaned {cleaned_dirs} empty folders.")
        ])
        self.is_processing = False

    def start_reverting(self):
        if messagebox.askyesno("Confirm Undo", "Move files back to original structure?"):
            threading.Thread(target=self.revert_process, daemon=True).start()

    def revert_process(self):
        self.is_processing = True
        self.root.after(0, lambda: self.toggle_controls(False))
        
        log_path = self.folder_path / self.undo_log_file
        try:
            with open(log_path, 'r') as f: history = json.load(f)
        except: return

        self.root.after(0, lambda: self.progress.config(maximum=len(history), value=0))
        
        for i, entry in enumerate(reversed(history)):
            try:
                current_loc = self.folder_path / entry['dest']
                original_loc = self.folder_path / entry['src']
                
                if current_loc.exists():
                    # Important: Recreate the original parent folder structure
                    original_loc.parent.mkdir(parents=True, exist_ok=True)
                    
                    final_dest = self.get_unique_path(original_loc)
                    shutil.move(str(current_loc), str(final_dest))
                    
                    # Try to remove the Month/Year folder if it becomes empty
                    try:
                        if not any(current_loc.parent.iterdir()):
                            current_loc.parent.rmdir()
                        if not any(current_loc.parent.parent.iterdir()):
                            current_loc.parent.parent.rmdir()
                    except: pass
                
                if i % 10 == 0:
                    self.root.after(0, lambda v=i+1: self.progress.config(value=v))
            except: pass

        os.remove(log_path)
        self.root.after(0, lambda: [
            self.toggle_controls(True),
            self.lbl_status.config(text="Revert complete."),
            messagebox.showinfo("Revert", "Files restored.")
        ])
        self.is_processing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = MediaOrganizerApp(root)
    root.mainloop()
