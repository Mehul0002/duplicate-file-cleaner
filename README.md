# Duplicate File Finder & Cleaner

A small desktop tool that scans a folder for duplicate files and lets you delete the extra copies, without touching anything by accident.

I built this because I had a Downloads folder with the same PDFs and screenshots saved three or four times under different names, and none of the "duplicate finder" tools I found online were free, offline, or trustworthy enough to point at my whole hard drive. So this is just a single Python file. No installer, no account, no internet connection, nothing phoning home. You run it, you see exactly what it finds, and you decide what gets deleted.

## How it actually finds duplicates

It doesn't just compare file names. It:

1. Walks through the folder (and all subfolders) you pick.
2. Groups files that are the same size, since two files can't be identical if their sizes differ — this step is basically free and skips most of the work.
3. For files that do share a size, it hashes the actual content (MD5) and compares those. If two files hash the same, they're byte-for-byte identical, regardless of what they're named or when they were created.

So a file named `vacation.jpg` and one named `vacation (1).jpg` will get flagged as duplicates if their content matches — and files with the same name but different content won't.

## Running it

You need Python installed (most Macs and Linux machines already have it; on Windows grab it from python.org). No extra libraries to install — it only uses what ships with Python.

```bash
python3 duplicate_finder.py
```

On Linux, if you get an error about `tkinter` missing:
```bash
sudo apt install python3-tk
```

## Using it

1. Click **Browse** and pick the folder you want to check.
2. Click **Scan for Duplicates** — for a folder with a lot of files this can take a minute or two, there's a progress bar so you know it's still working.
3. Results show up grouped: each group is a set of identical files, with the first one marked **KEEP (original)** in green and the rest marked **duplicate** in red.
4. Click **Auto-select duplicates** to select every red entry across all groups (the green "original" in each group is never auto-selected, so you always keep at least one copy).
5. Review the list — you can also click individual files yourself if you'd rather keep a different one in a group.
6. Click **Delete Selected**. It shows you exactly what's about to be deleted and how much space you'll get back, and asks you to confirm before anything actually happens.

Deletion is permanent — it doesn't go through your OS's recycle bin/trash. If you're nervous the first time, scan a small test folder before pointing it at anything important.

## Why it's one file

No dependencies to manage, no `pip install`, nothing to go out of date. Download the file, run it, that's the whole setup.

## License

MIT — do whatever you want with it.
