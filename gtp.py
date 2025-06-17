import os
import re
import json
from datetime import datetime
import filedate
import shutil
import time
from tqdm import tqdm
import argparse

description = (
    "Google Takeout Processor\n\n"
    "This program processes Google Takeout data by analyzing files in a specified folder. "
    "It identifies `.json` files for metadata (e.g., creation date, file name) and processes the "
    "corresponding files accordingly.\n\n"
    "Files without a matching `.json` file or those that cannot be located are marked as unprocessed "
    "and copied to a separate folder for review.\n\n"
    "Processed files are copied and modified based on their metadata, while unprocessed ones are logged.\n\n"
    "More details can be found in the README file.\n"
    "Git repository for this project: https://github.com/mshablovskyy/gtp.git\n"
)

def exists(path): # check if path exists
    if path:
        return os.path.exists(path)
    else: return False

def checkout_dir(path, onlynew = False): # check if directory exists, if not, create new. onlynew forces to create new repository in any case. Return is needed to give path to the new repository.
    if not os.path.isdir(path) and not onlynew:
        os.mkdir(path)
    elif onlynew:
        if not os.path.isdir(path):
            os.mkdir(path)
        else:
            n = 1
            while os.path.isdir(f"{path} {n}"):
                n += 1
            path = f"{path} {n}"
            os.mkdir(path)
    return path

def get_file_names(path): # get all files from all folders inside directory given and return them in structured form.
    content = os.walk(path)
    
    files = []
    jsons = []
    
    for dir_cont in content:
        for file in dir_cont[2]:
            if file.endswith(".json"):
                jsons.append(os.path.join(dir_cont[0], file))
            else:
                files.append({
                    "filename": file,
                    "filepath": os.path.join(dir_cont[0], file)
                })
    return jsons, files

def unpack_json(path, savelogsto): # get what needed from single json file.
    # Log the processing of the JSON file
    log_detail(savelogsto, f"Processing JSON file: {path}")
    if exists(path):
        try:
            # Open the JSON file and load its content
            with open(path, "r", encoding='utf-8') as file:
                content = json.load(file)
            # Check for required keys
            if (not content or 
                "title" not in content or
                "photoTakenTime" not in content or
                "timestamp" not in content["photoTakenTime"]):
                # If the required keys are missing, log the error and return None
                log_detail(savelogsto, f"Invalid JSON structure in file, skipping: {path}")
                return None
            # Extract the required information
            log_detail(savelogsto, f"Extracting data from JSON file: {path}")
            return {"filepath": path,
                    "title": content["title"],
                    "date": datetime.fromtimestamp(int(content["photoTakenTime"]["timestamp"]))}
        except Exception as e:
            log_detail(savelogsto, f"Error processing JSON file, error: {e}, skipping: {path}")
            return None
    else: 
        log_detail(savelogsto, f"JSON file does not exist, skipping: {path}")
        return None
    
def gener_names(filename, suffixes): # generate possible file names using suffixes provided.
    if filename["brackets"]:
        return [(filename["name"] + suf + filename["brackets"] + filename["extension"]) for suf in suffixes]
    else:
        return [(filename["name"] + suf + filename["extension"]) for suf in suffixes]
    
def find_file(jsondata, files, suffixes): # get full path to the file, based on it's name, which was extracted from json.
    # logic is to make dictionary with sufficient data to create file name to search for, using gener_names function.
    name, ext = os.path.splitext(jsondata["title"])
    filename = {
        "name": name,
        "extension": ext,
        "brackets": None
    }
    if len(filename["name"] + filename["extension"]) > 51:
        filename["name"] = filename["name"][0:51-len(filename["extension"])]
    if jsondata["filepath"].endswith(").json"):
        brackets = re.findall("\\([1-999]\\)\\.json", jsondata["filepath"])
        if brackets:
            brackets = brackets[-1][:-5]
            filename["brackets"] = brackets
    
    # actual search, code just looks for same filenames, based on json's data and suffixes.
    filepath = [file for file in files if file["filename"] in gener_names(filename, suffixes)] 
    
    if filepath:
        return True, filepath
    else:
        return False, [{"jsonpath": jsondata["filepath"],
                       "title": jsondata["title"]}]
    
def copy_modify(file, date, copyto): # copy and change creation and modification date of the file
    copyto = checkout_dir(os.path.join(copyto, f"Photos from {date.year}"))
    
    new_file =  os.path.join(copyto, file["filename"])
    shutil.copy(file["filepath"], new_file)
    filedate.File(new_file).set(created = date, modified = date)
    
    return new_file

def copy_unprocessed(unprocessed, saveto): # copy all files that were not returned during json-based search
    to_return = []
    for file in tqdm(unprocessed, desc="Copying"):
        # log the copying of unprocessed files
        log_detail(saveto, f"Copying unprocessed file: {file['filepath']}")
        new_file = os.path.join(saveto, checkout_dir(os.path.join(saveto, "Unprocessed")), file["filename"])
        shutil.copy(file["filepath"], new_file)
        # log the successful copying of the unprocessed file
        log_detail(saveto, f"Successfully copied unprocessed file to: {new_file}\n")
        file["procpath"] = new_file
        to_return.append(file)
    return to_return # return list with all unprocessed files, with path to the copied unmodified files

def log_detail(saveto, message):
    # Append a message to the detailed log file.
    with open(os.path.join(saveto, "detailed_logs.txt"), "a", encoding="utf-8") as logfile:
        logfile.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def savelogs(saveto, processed, unprocessed, unprocessed_jsons, endtime, startdate, enddate): # save everything that was done in separate file
    with open(os.path.join(saveto, "logs.txt"), "w", encoding="utf-8") as logfile:
        if processed: # if any files were processed
            logfile.write(f"Processed files:\n\n")
            
        for file in processed:
            filename = file["filename"]
            filepath = file["filepath"]
            procpath = file["procpath"]
            jsonname = file["jsonpath"]
            time_ = file["time"]
            logfile.write(f"    {filename}:\n")
            logfile.write(f"        original file:     {filepath}\n")
            logfile.write(f"        destination file:  {procpath}\n")
            logfile.write(f"        source json:       {jsonname}\n")
            logfile.write(f"    time processed:        {time_}\n\n")
        
        if unprocessed_jsons: # if any jsons were unprocessed
            logfile.write(f"Unprocessed jsons:\n\n")
        for file in unprocessed_jsons:
            filename = file["filename"]
            filepath = file["filepath"]
            title = file["title"]
            time_ = file["time"]
            logfile.write(f"    {filename}:\n")
            logfile.write(f"        original file:     {filepath}\n")
            logfile.write(f"        this json file did not find his pair among files: {title}\n")
            logfile.write(f"    time processed:        {time_}\n\n")
        
        if unprocessed: # if any files were unprocessed
            logfile.write(f"Unprocessed files:\n\n")
        for file in unprocessed:
            filename = file["filename"]
            filepath = file["filepath"]
            procpath = file["procpath"]
            logfile.write(f"    {filename}:\n")
            logfile.write(f"        original file:     {filepath}\n")
            logfile.write(f"        copied file:       {procpath}\n")
            logfile.write(f"        json-based search have not reached this file\n\n")
            
        logfile.write(f"Processed: {len(processed)} files\n")
        logfile.write(f"Unprocessed: {len(unprocessed)} files, {len(unprocessed_jsons)} jsons\n")
        logfile.write(f"Time used: {endtime} seconds\n")
        logfile.write(f"Started: {startdate}\n")
        logfile.write(f"Ended:   {enddate}\n")
        
def main(path, suffixes):
    start_time = time.time() # saving current time to return time program ran in the end
    start_date = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # log lists:
    processed = []
    unprocessed = []
    unprocessed_jsons = []
    
    # check if path provided exists:
    if not exists(path):
        print("Sorry, path you provided does not exist")
        return
    
    # let people know, what you work with
    print("\nProcess started...")
    print(f"\nWorking in directory {path}")
    
    # get lists with json files and non-json files
    jsons, files = get_file_names(path)
    
    # creating new folder for all modified files
    saveto = checkout_dir(os.path.join(os.path.dirname(path), "gtpOutput"), onlynew = True)
    
    # adding first line to the detailed_logs.txt file
    log_detail(saveto, f"Started processing directory: {path}\n")
    
    # main loop: (tqdm is for dynamic progress bar in terminal)
    for jsonpath in tqdm(jsons, desc="Files processed"):
        # get everithing from json:
        jsondata = unpack_json(jsonpath, saveto)
        
        if not jsondata:
            unprocessed_jsons.append({"filename": jsonpath[len(os.path.dirname(jsonpath))+1::],
                                      "filepath": jsonpath,
                                      "title": "Title is missing",
                                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            # log the scipping of the JSON file
            log_detail(saveto, f"Skipping JSON file in the main loop: {jsonpath}\n")
            continue # if json is empty, skip it
        
        # look for file pair based on json data
        # log the search for the file pairs based on json data
        log_detail(saveto, f"Searching for file pairs based on \"title\" from JSON: {jsondata['title']}")
        exist, files_ = find_file(jsondata, files, suffixes)
        for file in files_:
            if exist:
                # copy and modify file, if found
                # log the copying and modification of the file
                log_detail(saveto, f"Copying and modifying file: {file['filepath']}")
                procpath = copy_modify(file, jsondata["date"], checkout_dir(os.path.join(saveto, "Processed")))
                # save path to modified file
                file["procpath"] = procpath
                file["jsonpath"] = jsonpath
                file["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                # log the successful processing of the file
                log_detail(saveto, f"Successfully processed file: {file['filename']}\n")
                processed.append(file)
            else:
                # log the unprocessed JSON file
                log_detail(saveto, f"Unprocessed JSON file, no pair found for: {file['jsonpath']}\n")
                # add info about jsons which have not found any pair, to present it in logs
                unprocessed_jsons.append({"filename": file["jsonpath"][len(os.path.dirname(file["jsonpath"]))+1::],
                                          "filepath": file["jsonpath"],
                                          "title": file["title"],
                                          "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    
    
    print("\nWorking with unprocessed files...")
    
    # log the processing of unprocessed files
    log_detail(saveto, f"Processing unprocessed files...\n")
    # make list of files, which have not been processed, based by list of all files and processed ones, and that save name and path separately not to extract it every time needed
    unprocessed = [{"filename": file[len(os.path.dirname(file))+1::], "filepath": file} for file in tqdm(list(set([file["filepath"] for file in files]) - set([file["filepath"] for file in processed])), desc="Analizing")]
    
    print("\nFinal steps with unprocessed files...")
    # copy unprocessed jsons and files to separate folder, to not lose any file
    if unprocessed_jsons:
        unprocessed_jsons = copy_unprocessed(unprocessed_jsons, saveto)
    if unprocessed:
        unprocessed = copy_unprocessed(unprocessed, saveto)
    
    # calculate time, needed for program
    end_time = round(time.time() - start_time, 3)
    end_date = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # log the end of the processing
    log_detail(saveto, f"Finished processing directory: {path}, readable logs are in {saveto}/logs.txt")
    # create and save logs into separate file inside "saveto" folder
    savelogs(saveto, processed, unprocessed, unprocessed_jsons, end_time, start_date, end_date)
    
    print("\nFinished!")
    print(f"Processed {len(processed)} files")
    print(f"Unprocessed: {len(unprocessed)} files, {len(unprocessed_jsons)} jsons")
    print(f"Time used: {end_time} seconds")
    procpath = os.path.join(saveto, "Processed")
    print(f"\nFolder with processed files:\n{procpath}")
    unprocpath = os.path.join(saveto, "Unprocessed")
    print(f"Folder with unprocessed files:\n{unprocpath}\n")
    
def wizard(): # wizard mode, if user have not given the argument before running
    print("\nYou have not given arguments needed, so you have been redirected to the Wizard setup")
    try:
        path = input("Enter path to your folder with takeouts: ")
        return path
    except:
        pass
    
def parse(description): # start point of the program, where variable "path" is being created
    suffixes = ["", "-edited"] # text google can add to the name of the file and without making separate json
    # this means that file cat.png and cat-edited.png have only one json - cat.png.supplemental-metadata.json
    
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument("-p", "--path", help="The full path to the repository containing Takeout folders", type=str, default=None)
    parser.add_argument("-s", "--suffix", action="append", help="Additional suffixes you want to add", type=str, default=suffixes)
    
    args = parser.parse_args()
        
    if not args.path:
        path = wizard()
    else: path = args.path
    
    suffixes = args.suffix
    
    main(path, suffixes)


if __name__ == "__main__": # run the program
    parse(description)
