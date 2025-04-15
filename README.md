# Google Takeout Processor (GTP)

Google Takeout Processor (GTP) is a utility designed to help you organize Google Photos data from Google Takeout archives quickly and effectively. Whether you're frustrated with scattered files or incorrect dates, this tool provides a solution that automates sorting, updates file attributes, and simplifies your workflow.

---

## 😫 The Problem

When downloading your Google Photos data via Google Takeout, you may encounter several issues:

- **Randomly Packed Archives:** Photos and videos are distributed across various zip files and folders without consistent organization.
- **Incorrect Dates:** File creation and modification dates are often set to today's date or a very old date, making it impossible to detect when the photos were originally taken.
- **Manually Sorting Files:** Organizing hundreds or thousands of files into proper folders can be overwhelming and time-consuming.

---

## 💡 The Solution

This utility solves these problems:

- **Organizes Your Photos by Year:** Photos are organized into folders like "Photos from 2008," based on their original creation date.
- **Corrects File Attributes:** Updates the creation and modification dates of files to match the timestamps from their metadata.
- **Manages Unprocessed Files:** Automatically relocates unmatched or unprocessable files to an "Unprocessed" folder for manual review.
- **Generates Logs:** Creates a `logs.txt` file summarizing the operations for processed and unprocessed files.

---

## 🛠️ Setup and Usage

**🚨 Note:**  
The program **copies** all processed and unprocessed files. Ensure you have sufficient free space to accommodate slightly more than the total size of the input folder!

### 1. **Prepare Your Takeout Data**

- Download your Google Photos archives from Google Takeout.
- Unpack the downloaded zip files into a single folder. This folder will be the input for the program.
- Ensure the folder contains only Google Photos data, as unrelated files may slow down the process and will be moved into the "Unprocessed" folder.

### 2. **Install Python and Dependencies**

- Install Python (version 3.9.6 or later is preffered, it was not tested on older versions).
- Clone this repository:

  ```bash
  git clone https://github.com/mshablovskyy/GTP.git
  cd GTP
  ```

- Install the required dependencies:

  ```bash
  pip install -r requirements.txt
  ```

### 3. **Run the Script**

Run the program via the terminal, ensure `<path-to-unpacked-folder>` is enclosed in quotation marks `"`:

#### Windows:

```bash
python gtp.py <path-to-unpacked-folder>
```

#### macOS:

```bash
python3 gtp.py <path-to-unpacked-folder>
```

#### Linux:

```bash
python3 gtp.py <path-to-unpacked-folder>
```

---

Alternatively, you can run the script without arguments, and program will prompt you to paste the path interactively:

#### Windows:

```bash
python gtp.py
```

#### macOS:

```bash
python3 gtp.py
```

#### Linux:

```bash
python3 gtp.py
```

---

## 📂 What You’ll Get

Once the program finishes processing:

1. A new folder, **ProcessedPhotos**, will appear next to the folder you provided. This folder will include:
   - Subfolders organized by year, e.g., `Photos from 2008`, `Photos from 2023`, etc.
   - An `Unprocessed` folder containing files and metadata that couldn't be matched for processing.
   - A `logs.txt` file summarizing:
     - Processed files with updated attributes.
     - Unprocessed files and metadata for review.
2. A terminal output summarizing:
   - The number of processed/unprocessed files.
   - The total time taken for processing.

---

## ⚙️ How It Works: Step-by-Step

1. **Gather Input Data:**  
   The program scans the input folder and generates a list of all files with their full paths. It then separates the data into two lists:  
   - **JSON Files** (metadata files).  
   - **Other Files** (media files like `.jpg`, `.png`, etc.).

2. **Create Output Folder:**  
   A new folder named `ProcessedPhotos` is created next to the input folder to store organized data.

3. **Process JSON Files:**  
   For every JSON file:
   - **Extract Metadata:** The program reads the JSON file to retrieve the name of the associated file and its original creation date.  
   - **Handle Naming Exceptions:** Google often shortens filenames or does not add parentheses like `(1)` to the name of the file, to which JSON file refers. The program resolves these issues to accurately match files.  
   - **Copy & Modify Files:**  
     - Matched files are copied into a subfolder named by their year of creation (e.g., `Photos from 2008`).  
     - Creation and modification dates are corrected.  
     - Matched files are added to the list of processed files.  
   - **Unmatched JSONs:** If no corresponding file is found, the JSON is added to the list of unprocessed JSONs.

4. **Handle Unprocessed Files:**  
   After processing JSONs, the program compares the list of all files with the list of processed files. Any difference is saved as unprocessed files.  

5. **Copy Unprocessed Files:**  
   Any unmatched files and JSONs are copied to the `unprocessed` folder inside `ProcessedPhotos` for review.

6. **Save Logs:**  
   Information about all operations is saved in a `logs.txt` file that includes:  
   - **Processed Files:** Original path, new path, and name.  
   - **Unprocessed Files:** Original path, new path, and name.  
   - **Unprocessed JSONs:** Original path, new path, and name.

---

## 🛑 Why Files Might Not Be Found  

Files and metadata may fail to match for several reasons:  

1. **Unrelated Files:**  
   Unwanted or system-related files like `.DS_Store` (Mac).  

2. **Filename Changes:**  
   - **Special Characters (Case 1):** A file named `can't.png` is stored as `can_t.png`, but the JSON still refers to `can't.png`.  
   - **Local Symbols (Case 2):** Names with Cyrillic, Arabic, or other special characters may appear mismatched due to unpredictable encoding changes by Google.  

3. **Missing JSON:**  
   A file might lack a corresponding JSON file entirely, preventing processing.

In all such cases, files and JSONs are moved to the `unprocessed` folder for manual review.

---

## 📂 Program Output  

After running the program, the following will appear next to your input folder:

- **ProcessedPhotos Folder:**  
  - Subfolders organized by year (e.g., `Photos from 2008`, `Photos from 2023`).  
  - An `unprocessed` folder containing unmatched files and JSONs.  
- **logs.txt File:**  
  - Details of processed files, unprocessed files, and unprocessed JSONs.

---

## 🔄 Final Result  

At the end of execution, you’ll see:  

- Correctly organized and dated files.  
- A separate folder for anything unprocessed.  
- Comprehensive logs to review any anomalies.  

---

## 📞 Addition

If you encounter issues or have questions, feel free to:

- Open an [issue](https://github.com/mshablovskyy/GTP/issues) on GitHub.
- Contact me

---

## Contribute, if you want, that is welcomed!