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
- **Generates Detailed Logs:** Creates a `detailed_logs.txt` file, showing how everything was done step by step and helps to found errors.

---

## 🛠️ Setup and Usage

**🚨 Note:**  
The program **does not change** any source folders or files, does not delete or modify, it strictly **copies** all processed and unprocessed files. Ensure you have sufficient free space to accommodate slightly more than the total size of the input folder!

### 1. **Prepare Your Takeout Data**

- Download your Google Photos archives from Google Takeout.
- Unpack the downloaded zip files into a single folder. This folder will be the input for the program.
- Ensure the folder contains only Google Photos data, as unrelated files may slow down the process and will be moved into the "Unprocessed" folder.

### 2. **Install Python and Dependencies**

- Install Python (version 3.9.6 or later is preffered, it was not tested on older versions).
- Clone this repository:

  ```bash
  git clone https://github.com/mshablovskyy/gtp.git
  cd gtp
  ```

- Install the required dependencies:

  - #### Windows:

  ```bash
  pip install -r requirements.txt
  ```

  - #### macOS/Linux:

  ```bash
  pip3 install -r requirements.txt
  ```

### 3. **Run the Script**

Run the program via the terminal:

- #### Windows:

```bash
python gtp.py --path <your-path-to-unpacked-folder>
```

- #### macOS/Linux:

```bash
python3 gtp.py --path <your-path-to-unpacked-folder>
```

Ensure `<your-path-to-unpacked-folder>` is enclosed in quotation marks `"`, if names of your folders contain special characters or spaces.

---

Alternatively, you can run the script without arguments, and program will prompt you to paste the path interactively:

- #### Windows:

```bash
python gtp.py
```

- #### macOS/Linux:

```bash
python3 gtp.py
```

#### Expected output:

```bash
You have not given arguments needed, so you have been redirected to the Wizard setup
Enter path to your folder with takeouts: 
```

---

## 📂 What You’ll Get

Once the program finishes processing:

1. A new folder, **ProcessedPhotos**, will appear next to the folder you provided. This folder will include:
   - An `Processed` folder containing subfolders organized by year, e.g., `Photos from 2008`, `Photos from 2023`, etc.
   - An `Unprocessed` folder containing files and metadata that couldn't be matched for processing.
   - A `logs.txt` file summarizing:
     - Processed files with updated attributes.
     - Unprocessed files and metadata for review.
   - A `detailed_logs.txt` file, showing step by step every:
     - Skip
     - Copy
     - Exraction
     - Change
2. A terminal output summarizing:
   - The number of processed/unprocessed files.
   - The total time taken for processing.

---

## Terminal running

Running from terminal supports arguments. Example with help:

- #### Windows:

```bash
python gtp.py -h
```

- #### macOS/Linux:

```bash
python3 gtp.py -h
```

#### Expected output:

```bash
Google Takeout Processor

This program processes Google Takeout data by analyzing files in a specified folder. It identifies `.json` files for metadata (e.g., creation date, file name) and processes the corresponding files accordingly.

Files without a matching `.json` file or those that cannot be located are marked as unprocessed and copied to a separate folder for review.

Processed files are copied and modified based on their metadata, while unprocessed ones are logged.

More details can be found in the README file.
Git repository for this project: https://github.com/mshablovskyy/gtp.git

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  The full path to the repository containing Takeout folders
  -s SUFFIX, --suffix SUFFIX  Additional suffixes you want to add
```

### Detailed explaining of every argument:

- **`-h` or `--help`** - Returns help, where program is briefly presented and arguments are displayed.

- **`-p <path>` or `--path <path>`** - argument, which have to be followed by path to the directory with all takeouts. Takes only one argument, is mandatory, but if not given, wizard setup mode asks `<path>` again.

- **`-s <suffix>` or `--suffix <suffix>`** - argument, which uses "append" principle and takes only one argument. As default, is set to `["", "-edited"]`, to add few suffixes, argument has to be specified separately for each value. Example:
  
  - ```bash
    gtp.py --path /Users/photolover/my-takeouts -s "-stickers" -s "-connect"
    ```

---

## Suffixes

You might wonder—what exactly are these suffixes? While they may not seem entirely logical, we must work around Google's peculiar conventions, so let's get used to them.

### The Issue

In an ideal situation:

- Each file would have its corresponding JSON data file, meaning the number of JSONs and other associated files would be equal.

However, during development, I discovered that this isn't always the case:

- Often, there are fewer JSON files compared to other files.
- Initially, I ignored the extra, "unprocessed" files, assuming Google forgot to provide JSON data for them.

But after testing the program on larger datasets, I uncovered a pattern:

- Many unprocessed files contained the suffix `-edited` before their file extension (e.g., `cat-edited.png`), but don't have json associated with `cat-edited.png` file. At the same time files without suffixes were processed correctly, as `json` with metadata for them exist.
- These unprocessed files had counterparts without the `-edited` suffix (e.g., `cat.png`) that were being processed correctly.
- Google implicitly expects us to treat `cat.png` and `cat-edited.png` as sharing a single JSON file (`cat.json`). 

This quirk is exactly why **suffixes were implemented**.

### Suffix Solution

Since I cannot predict all the variations Google might append to filenames, such as `-edited`, `-sticker`, or others, suffixes allow you to manually address this issue when running the program.

If you notice files in the `unprocessed` folder with suffixes (e.g., `-sticker`) that should be treated as their base counterparts (e.g., `file-sticker.png` → `file.png`), you can specify the suffix, which will be used as additional filter, to handle more files during execution.

Keep in mind that creation date for files with suffixes is obtained from `json` file, related to file with the same name, but without suffix, as files with suffixes in name do not have their own `json` file.

### Preset suffixes:

- ` ` - actually, nothing. Usually, nothing is added, so this suffix is obligatory.
- `-edited` - important suffix, which, as I understood, Google adds to files you edited in Google Photos. I do not know why exact modification date is not saved, but not to leave such files unprocessed, this suffix exists.

### Usage

To utilize suffixes, simply pass them as arguments when running the program from the terminal, as demonstrated earlier.

For example:

```bash
gtp.py -p <path> -s -sticker
```

### Note:

You should not add suffixes, if you do not have problems with a lot of **unprocessed** files, or if you are not fully aware what you are doing. It can lead to incorrect file handling or potential data loss.

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
   - **Processed Files:** Original path, new path, name, path to source json and time processed.
   - **Unprocessed Files:** Original path, new path, and name.  
   - **Unprocessed JSONs:** Original path, new path, name of the file they are refered to, time processed.

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

## 🔄 Final Result  

At the end of execution, you’ll see:  

- Correctly organized and dated files.  
- A separate folder for anything unprocessed.  
- Comprehensive logs to review any anomalies.  

---

## 📞 Addition

If you encounter issues or have questions, feel free to:

- Open an [issue](https://github.com/mshablovskyy/gtp/issues) on GitHub.
- Contact me

---

## 🔧 Already Solved Issues

- If processed folder contained any unrelated `.json`s, program crashed. Now it is solved.

---

## Contribute, if you want, that is welcomed!
