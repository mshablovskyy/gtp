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
    "Git repository for this project: https://github.com/mshablovskyy/GTP.git\n"
)

def exists(path): # check if path exists
    if path:
        return os.path.exists(path)
    else: return False

def checkout_dir(path, onlynew = False): # check if directory exist, if not, create hew. onlynew forces to create new in any case. return is needed to give path to new repository
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

def get_file_names(path): # get all files from all folders inside directory given and return them in structured form
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

def unpack_json(path): # get what needed from single json file
    if exists(path):
        with open(path, "r", encoding='utf-8') as file:
            content = json.load(file)
        return {"filepath": path,
                "title": content["title"],
                "date": datetime.fromtimestamp(int(content["photoTakenTime"]["timestamp"]))}
    else: 
        return None
    
def gener_names(title, suffixes):
    name, ext = os.path.splitext(title)
    return [(name + add + ext) for add in suffixes]
    
def find_file(jsondata, files, suffixes): # get full path to the file, based on it's name, which was extracted from json
    # logic to make "title" from json be the same as name of the file
    if len(jsondata["title"]) > 51:
        name, ext = os.path.splitext(jsondata["title"])
        jsondata["title"] = f'{name[0:51-len(ext)]}{ext}'
    if jsondata["filepath"].endswith(").json"):
        brackets = re.findall("\\([1-999]\\)\\.json", jsondata["filepath"])
        if brackets:
            brackets = brackets[-1][:-5]
            name, ext = os.path.splitext(jsondata["title"])
            jsondata["title"] = f'{name}{brackets}{ext}'
    
    filepath = [file for file in files if file["filename"] in gener_names(jsondata["title"], suffixes)] # actual search, I just look for same filenames, based on json's data
    
    if filepath:
        return True, filepath
    else:
        return False, {"jsonpath": jsondata["filepath"],
                       "title": jsondata["title"]}
    
def copy_modify(file, date, copyto): # copy and change creation and modification date of the file
    copyto = checkout_dir(os.path.join(copyto, f"Photos from {date.year}"))
    
    new_file =  os.path.join(copyto, file["filename"])
    shutil.copy(file["filepath"], new_file)
    filedate.File(new_file).set(created = date, modified = date)
    
    return new_file

def copy_unprocessed(unprocessed, saveto): # copy all files that were not returned during json-based search
    to_return = []
    for file in tqdm(unprocessed, desc="Copying"):
        new_file = os.path.join(saveto, checkout_dir(os.path.join(saveto, "unprocessed")), file["filename"])
        shutil.copy(file["filepath"], new_file)
        file["procpath"] = new_file
        to_return.append(file)
    return to_return # return list with all unprocessed files, with path to the copied unmodified files

def savelogs(saveto, processed, unprocessed, unprocessed_jsons, endtime): # save everything that was done in separate file
    with open(os.path.join(saveto, "logs.txt"), "w") as logfile:
        if processed: # if any files were processed
            logfile.write(f"Processed files:\n\n")
        for file in processed:
            filename = file["filename"]
            filepath = file["filepath"]
            procpath = file["procpath"]
            logfile.write(f"    {filename}:\n")
            logfile.write(f"        base file:     {filepath}\n")
            logfile.write(f"        modified file: {procpath}\n\n")
        
        if unprocessed_jsons: # if any jsons were unprocessed
            logfile.write(f"Unprocessed jsons:\n\n")
        for file in unprocessed_jsons:
            filename = file["filename"]
            filepath = file["filepath"]
            title = file["title"]
            logfile.write(f"    {filename}:\n")
            logfile.write(f"        base file:     {filepath}\n")
            logfile.write(f"        this json file did not find his pair among files: {title}\n\n")
        
        if unprocessed: # if any files were unprocessed
            logfile.write(f"Unprocessed files:\n\n")
        for file in unprocessed:
            filename = file["filename"]
            filepath = file["filepath"]
            procpath = file["procpath"]
            logfile.write(f"    {filename}:\n")
            logfile.write(f"        base file:     {filepath}\n")
            logfile.write(f"        copied file: {procpath}\n")
            logfile.write(f"        json-based search have not reached this file\n\n")
            
        logfile.write(f"Processed: {len(processed)} files\n")
        logfile.write(f"Unprocessed: {len(unprocessed)} files, {len(unprocessed_jsons)} jsons\n")
        logfile.write(f"Time used: {endtime} seconds")
        
def main(path, suffixes):
    start_time = time.time() # saving current time to return time program ran in the end
    
    # log lists:
    processed = []
    unprocessed = []
    unprocessed_jsons = []
    
    # check if path provided exists:
    if not exists(path):
        print("Sorry, path you provided does not exist")
        return
    
    # let people know, what you work with
    print("\nProgram started")
    print(f"\nWorking in directory {path}")
    
    # get lists with json files and non-json files
    jsons, files = get_file_names(path)
    
    # creating new folder for all modified files
    saveto = checkout_dir(os.path.join(os.path.dirname(path), "ProccesedPhotos"), onlynew = True)
    
    # main loop: (tqdm is for dynamic progress bar in terminal)
    for jsonpath in tqdm(jsons, desc="Files processed"):
        # get everithing from json:
        jsondata = unpack_json(jsonpath)
        
        # look for file pair based on json data
        exist, files_ = find_file(jsondata, files, suffixes)
        if exist:
            for file in files_:
                # copy and modify file, if found
                procpath = copy_modify(file, jsondata["date"], saveto)
                # save path to modified file
                file["procpath"] = procpath
                processed.append(file)
        else:
            # add info about jsons which have not found any pair, to present it in logs
            unprocessed_jsons.append({"filename": files_["jsonpath"][len(os.path.dirname(files_["jsonpath"]))+1::],
                                      "filepath": files_["jsonpath"],
                                      "title": files_["title"]})
    
    
    print("\nWorking with unprocessed files...")
    # make list of files, which have not been processed, based by list of all files and processed ones, and that save name and path separately not to extract it every time needed
    unprocessed = [{"filename": file[len(os.path.dirname(file))+1::], "filepath": file} for file in tqdm(list(set([file["filepath"] for file in files]) - set([file["filepath"] for file in processed])), desc="Analizing")]
    
    print("\nFinal steps with unprocessed files...")
    # copy unprocessed jsons and files to separate folder, to not lose any file
    if unprocessed_jsons:
        unprocessed_jsons = copy_unprocessed(unprocessed_jsons, saveto)
    if unprocessed:
        unprocessed = copy_unprocessed(unprocessed, saveto)
    
    # calculate time, needed for program
    endtime = round(time.time() - start_time, 3)
    
    # create and save logs into separate file inside "saveto" folder
    savelogs(saveto, processed, unprocessed, unprocessed_jsons, endtime)
    
    print("\nFinished!")
    print(f"Processed {len(processed)} files")
    print(f"Unprocessed: {len(unprocessed)} files, {len(unprocessed_jsons)} jsons")
    print(f"Time used: {endtime} seconds")
    print(f"\nRepository with processed files:\n{saveto}\n")
    
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
    
    parser.add_argument("path", help="The full path to the repository containing Takeout folders", type=str)
    parser.add_argument("suffixes", nargs="*", help="Additional suffixes you want to add", type=str)
    
    try:
        args = parser.parse_args()
        path = args.path
        for suffix in args.suffixes:
            for suf in suffix.split(","):
                suf = suf.strip()
                if suf:
                    suffixes.append(suf)
    except:
        path = wizard()
    
    main(path, suffixes)


if __name__ == "__main__": # run the program
    parse(description)