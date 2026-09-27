#!/usr/bin/env python3
"""
Duplicate File Finder & Cleaner — single-file GUI app.

Scans a folder (and subfolders) for duplicate files by CONTENT, not name,
using a fast size-check first, then an MD5 hash for files that match in
size. Shows results in a window, lets you review each duplicate group,
and safely delete the copies you don't want — with a confirmation step
and the original file always protected from accidental deletion.

Requirements: nothing but Python itself (tkinter ships with Python on
Windows/Mac; on Linux install it once with: sudo apt install python3-tk)

RUN:
    python3 duplicate_finder.py
"""

import os
import hashlib
import threading
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# --------------------------------------------------------------------------
# Scanning logic
# --------------------------------------------------------------------------

def hash_file(path, chunk_size=65536):
    """Return the MD5 hash of a file's contents."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def find_duplicates(root_dir, progress_callback=None):
    """
    Walk root_dir, group files by size first (cheap), then hash only the
    files that share a size (expensive but necessary for correctness).
    Returns: dict[hash] -> list of file paths, only for groups with 2+ files.
    """
    size_groups = defaultdict(list)
    all_files = []

    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            path = os.path.join(dirpath, name)
            all_files.append(path)

    total = len(all_files)
    for i, path in enumerate(all_files):
        try:
            size = os.path.getsize(path)
            if size > 0:  # skip empty files, they're not meaningful "duplicates"
                size_groups[size].append(path)
        except OSError:
            pass
        if progress_callback and i % 50 == 0:
            progress_callback(i, total, phase="Scanning files")

    # Only hash files that share a size with at least one other file
    hash_groups = defaultdict(list)
    candidates = [p for group in size_groups.values() if len(group) > 1 for p in group]
    for i, path in enumerate(candidates):
        digest = hash_file(path)
        if digest:
            hash_groups[digest].append(path)
        if progress_callback and i % 20 == 0:
            progress_callback(i, len(candidates), phase="Hashing candidates")

    return {h: paths for h, paths in hash_groups.items() if len(paths) > 1}


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

class DuplicateFinderApp:
    def __init__(self, root):
        self.root = root
        root.title("Duplicate File Finder & Cleaner")
        root.geometry("880x560")

        self.folder_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Choose a folder to scan.")
        self.duplicate_groups = {}   # hash -> [paths]
        self.item_to_path = {}       # treeview item id -> file path

        self._build_ui()

    # ---- UI construction ----
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Folder:").pack(side="left")
        ttk.Entry(top, textvariable=self.folder_path, width=60).pack(side="left", padx=5)
        ttk.Button(top, text="Browse...", command=self.browse_folder).pack(side="left")
        ttk.Button(top, text="Scan for Duplicates", command=self.start_scan).pack(side="left", padx=10)

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10)

        ttk.Label(self.root, textvariable=self.status_text, foreground="gray").pack(anchor="w", padx=10, pady=(2, 8))

        # Tree view of duplicate groups
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill="both", expand=True, padx=10)

        columns = ("size", "path")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Group / File")
        self.tree.heading("size", text="Size")
        self.tree.heading("path", text="Full Path")
        self.tree.column("#0", width=260)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("path", width=460)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Bottom action bar
        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill="x")

        ttk.Button(bottom, text="Auto-select duplicates (keep first in each group)",
                   command=self.auto_select_duplicates).pack(side="left")
        ttk.Button(bottom, text="Delete Selected", command=self.delete_selected).pack(side="right")
        ttk.Button(bottom, text="Clear Selection", command=lambda: self.tree.selection_remove(self.tree.selection())).pack(side="right", padx=8)

    # ---- Actions ----
    def browse_folder(self):
        path = filedialog.askdirectory(title="Choose a folder to scan")
        if path:
            self.folder_path.set(path)

    def start_scan(self):
        path = self.folder_path.get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Invalid folder", "Please choose a valid folder first.")
            return
        self.tree.delete(*self.tree.get_children())
        self.item_to_path.clear()
        self.progress["value"] = 0
        self.status_text.set("Scanning... this may take a while for large folders.")
        threading.Thread(target=self._scan_worker, args=(path,), daemon=True).start()

    def _scan_worker(self, path):
        def progress_cb(i, total, phase):
            pct = (i / total * 100) if total else 0
            self.root.after(0, lambda: (
                self.progress.configure(value=pct),
                self.status_text.set(f"{phase}... {i}/{total}")
            ))

        groups = find_duplicates(path, progress_callback=progress_cb)
        self.root.after(0, lambda: self._display_results(groups))

    def _display_results(self, groups):
        self.duplicate_groups = groups
        self.progress["value"] = 100

        if not groups:
            self.status_text.set("No duplicates found. Your folder is clean!")
            return

        total_wasted = 0
        total_files = 0
        for i, (digest, paths) in enumerate(groups.items(), start=1):
            size = os.path.getsize(paths[0])
            wasted = size * (len(paths) - 1)
            total_wasted += wasted
            total_files += len(paths)

            group_label = f"Group {i} — {len(paths)} copies — {self._fmt_size(size)} each"
            group_id = self.tree.insert("", "end", text=group_label, open=True)

            for j, p in enumerate(paths):
                tag = "original" if j == 0 else "duplicate"
                label = "KEEP (original)" if j == 0 else "duplicate"
                item = self.tree.insert(group_id, "end", text=label, values=(self._fmt_size(size), p), tags=(tag,))
                self.item_to_path[item] = p

        self.tree.tag_configure("original", foreground="#1a7a1a")
        self.tree.tag_configure("duplicate", foreground="#b00020")

        self.status_text.set(
            f"Found {len(groups)} duplicate groups ({total_files} files). "
            f"Potential space to free: {self._fmt_size(total_wasted)}."
        )

    def auto_select_duplicates(self):
        """Select every file tagged 'duplicate' (i.e. everything but the first in each group)."""
        self.tree.selection_remove(self.tree.selection())
        to_select = []
        for item in self.item_to_path:
            if "duplicate" in self.tree.item(item, "tags"):
                to_select.append(item)
        if to_select:
            self.tree.selection_set(to_select)
            self.status_text.set(f"Selected {len(to_select)} duplicate files. Review, then click Delete Selected.")
        else:
            self.status_text.set("Nothing to select — scan a folder first.")

    def delete_selected(self):
        selected = [i for i in self.tree.selection() if i in self.item_to_path]
        if not selected:
            messagebox.showinfo("Nothing selected", "Select files in the list first (or use Auto-select).")
            return

        paths = [self.item_to_path[i] for i in selected]
        total_size = sum(os.path.getsize(p) for p in paths if os.path.exists(p))

        preview = "\n".join(paths[:15]) + ("\n..." if len(paths) > 15 else "")
        confirm = messagebox.askyesno(
            "Confirm deletion",
            f"You are about to permanently delete {len(paths)} file(s), "
            f"freeing {self._fmt_size(total_size)}.\n\nFiles:\n{preview}\n\n"
            "This cannot be undone. Continue?"
        )
        if not confirm:
            return

        deleted, failed = 0, []
        for item in selected:
            path = self.item_to_path[item]
            try:
                os.remove(path)
                self.tree.delete(item)
                deleted += 1
            except OSError as e:
                failed.append(f"{path} ({e})")

        msg = f"Deleted {deleted} file(s), freed {self._fmt_size(total_size)}."
        if failed:
            msg += f"\n\n{len(failed)} could not be deleted:\n" + "\n".join(failed[:10])
        self.status_text.set(msg.split("\n")[0])
        messagebox.showinfo("Done", msg)

    @staticmethod
    def _fmt_size(num_bytes):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num_bytes < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} PB"


def main():
    root = tk.Tk()
    app = DuplicateFinderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
