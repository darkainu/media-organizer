import os
import shutil
import json
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
from pathlib import Path
from PIL import Image, ExifTags

class MediaOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Media File Organizer")
        self.root.geometry("700x500")
        
        # State variables
        self.folder_path = None
        self.is_processing = False
        self.undo_log_file = "organizer_undo_log.json"
        
        # Supported extensions
        self.extensions = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.avi', '.mp', '.heic', '.raw', '.dng'}
        
        self.create_widgets()

    def create_widgets(self):
        # Main container with padding
        main = tk.Frame(self.root, padx=20, pady=20)
        main.pack(expand=True, fill='both')

        # Header
        lbl_header = tk.Label(main, text="Media Organizer", font=("Helvetica", 16, "bold"))
        lbl_header.pack(pady=(0, 20))

        # Folder Selection
        frame_select = tk.Frame(main)
        frame_select.pack(fill='x', pady=5)
        
        self.btn_select = tk.Button(frame_select, text="Select Folder", command=self.select_folder, height=2)
        self.btn_select.pack(side='left', padx=(0, 10))
        
        self.lbl_path = tk.Label(frame_select, text="No folder selected", relief="sunken", anchor="w")
        self.lbl_path.pack(side='left', fill='x', expand=True, ipady=8)

        # Progress Section
        self.progress = ttk.Progressbar(main, orient="horizontal", length=100, mode='determinate')
        self.progress.pack(fill='x', pady=(30, 5))
        
        self.lbl_status = tk.Label(main, text="Ready", fg="grey")
        self.lbl_status.pack(pady=5)

        # Actions
        frame_actions = tk.Frame(main)
        frame_actions.pack(pady=20)

        self.btn_run = tk.Button(frame_actions, text="Organize Files", command=self.start_organizing, 
                               bg="#e1f5fe", state="disabled", width=15, height=2)
        self.btn_run.pack(side='left', padx=10)

        self.btn_revert = tk.Button(frame_actions, text="Undo Changes", command=self.start_reverting, 
                                  bg="#ffebee", state="disabled", width=15, height=2)
        self.btn_revert.pack(side='left', padx=10)

        # Log Text Box
        self.txt_log = tk.Text(main, height=8, state='disabled', font=("Consolas", 9))
        self.txt_log.pack(fill='both', expand=True, pady=10)

    def log(self, message):
        """Thread-safe logging to the text box"""
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
        """Check if an undo log exists in the selected folder"""
        if self.folder_path and (self.folder_path / self.undo_log_file).exists():
            self.btn_revert.config(state="normal")
        else:
            self.btn_revert.config(state="disabled")

    def toggle_controls(self, enable):
        state = "normal" if enable else "disabled"
        self.btn_select.config(state=state)
        self.btn_run.config(state=state)
        # Revert button logic is handled separately based on log file existence
        if enable: 
            self.check_undo_availability()
        else:
            self.btn_revert.config(state="disabled")

    def get_date_taken(self, file_path):
        """Robust date extraction"""
        timestamp = None
        
        # 1. Try Image EXIF
        if file_path.suffix.lower() in {'.jpg', '.jpeg', '.tiff', '.png'}:
            try:
                img = Image.open(file_path)
                exif = img.getexif()
                if exif:
                    # 36867 is DateTimeOriginal, 306 is DateTime
                    date_str = exif.get(36867) or exif.get(306)
                    if date_str:
                        timestamp = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            except Exception:
                pass

        # 2. Fallback to file system stats (Creation or Modification)
        if not timestamp:
            stat = os.stat(file_path)
            # On Unix, st_birthtime might not exist, fallback to mtime
            creation_time = getattr(stat, 'st_birthtime', stat.st_mtime)
            timestamp = datetime.fromtimestamp(min(creation_time, stat.st_mtime))

        return timestamp

    def get_unique_path(self, destination):
        """Handle file name collisions by appending a counter"""
        if not destination.exists():
            return destination
        
        counter = 1
        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent
        
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_dest = parent / new_name
            if not new_dest.exists():
                return new_dest
            counter += 1

    def start_organizing(self):
        if not self.folder_path: return
        threading.Thread(target=self.organize_process, daemon=True).start()

    def organize_process(self):
        self.is_processing = True
        self.root.after(0, lambda: self.toggle_controls(False))
        
        files = [f for f in self.folder_path.iterdir() 
                 if f.is_file() and f.suffix.lower() in self.extensions and f.name != self.undo_log_file]
        
        total = len(files)
        moved_log = []
        
        self.root.after(0, lambda: self.progress.config(maximum=total, value=0))
        
        for i, file_path in enumerate(files):
            try:
                date_obj = self.get_date_taken(file_path)
                
                # Folder structure: 2023/05_May
                month_name = date_obj.strftime("%m_%B")
                year_folder = self.folder_path / str(date_obj.year)
                month_folder = year_folder / month_name
                
                month_folder.mkdir(parents=True, exist_ok=True)
                
                # Determine destination
                dest_path = month_folder / file_path.name
                final_dest = self.get_unique_path(dest_path)
                
                # Move
                shutil.move(str(file_path), str(final_dest))
                
                # Record relative paths for portability
                moved_log.append({
                    "src": str(file_path.relative_to(self.folder_path)),
                    "dest": str(final_dest.relative_to(self.folder_path))
                })
                
                # Update UI
                msg = f"Moved: {file_path.name} -> {final_dest.parent.name}"
                self.root.after(0, lambda m=msg, v=i+1: [self.log(m), self.progress.config(value=v)])
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.log(f"Error moving {file_path.name}: {e}"))

        # Save Undo Log
        if moved_log:
            log_path = self.folder_path / self.undo_log_file
            
            # If log exists, append to it (load, extend, save)
            existing_data = []
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f:
                        existing_data = json.load(f)
                except: pass
            
            existing_data.extend(moved_log)
            
            with open(log_path, 'w') as f:
                json.dump(existing_data, f, indent=2)

        self.root.after(0, lambda: [
            self.toggle_controls(True),
            self.lbl_status.config(text=f"Completed! Organized {len(moved_log)} files."),
            messagebox.showinfo("Success", "Organization Complete")
        ])
        self.is_processing = False

    def start_reverting(self):
        if messagebox.askyesno("Confirm Undo", "This will move files back to the main folder and delete empty subfolders. Continue?"):
            threading.Thread(target=self.revert_process, daemon=True).start()

    def revert_process(self):
        self.is_processing = True
        self.root.after(0, lambda: self.toggle_controls(False))
        
        log_path = self.folder_path / self.undo_log_file
        
        try:
            with open(log_path, 'r') as f:
                history = json.load(f)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Could not read log file: {e}"))
            self.is_processing = False
            self.root.after(0, lambda: self.toggle_controls(True))
            return

        # Process in reverse order (LIFO)
        self.root.after(0, lambda: self.progress.config(maximum=len(history), value=0))
        
        success_count = 0
        
        for i, entry in enumerate(reversed(history)):
            try:
                # Reconstruct full paths
                current_loc = self.folder_path / entry['dest']
                original_loc = self.folder_path / entry['src']
                
                if current_loc.exists():
                    # Check for collision at original location
                    final_dest = self.get_unique_path(original_loc)
                    
                    shutil.move(str(current_loc), str(final_dest))
                    success_count += 1
                    
                    # Clean up empty folder
                    try:
                        if not any(current_loc.parent.iterdir()):
                            current_loc.parent.rmdir() # remove month
                            if not any(current_loc.parent.parent.iterdir()):
                                current_loc.parent.parent.rmdir() # remove year
                    except: pass
                
                self.root.after(0, lambda v=i+1: self.progress.config(value=v))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.log(f"Error reverting: {e}"))

        # Remove log file
        os.remove(log_path)
        
        self.root.after(0, lambda: [
            self.toggle_controls(True),
            self.lbl_status.config(text=f"Reverted {success_count} files."),
            self.log("Undo operation completed."),
            messagebox.showinfo("Revert", "Files have been moved back.")
        ])
        self.is_processing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = MediaOrganizerApp(root)
    root.mainloop()
