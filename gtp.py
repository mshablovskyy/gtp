import os
import re
import json
from datetime import datetime
import filedate
import shutil
from difflib import SequenceMatcher
import time
from tqdm import tqdm
import argparse

path = "/Users/mshablovskyy/Python/gtp/Takeout"

def exists(path):
    if path:
        return os.path.exists(path)
    else: return False

def checkout_dir(path, onlynew = False):
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

def get_file_names(path):
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

def unpack_json(path):
    if exists(path):
        with open(path, "r", encoding='utf-8') as file:
            content = json.load(file)
        return {"filepath": path,
                "title": content["title"],
                "date": datetime.fromtimestamp(int(content["photoTakenTime"]["timestamp"]))}
    else: 
        return None
    
def find_file(jsondata, files):
    if len(jsondata["title"]) > 51:
        name, ext = os.path.splitext(jsondata["title"])
        jsondata["title"] = f'{name[0:51-len(ext)]}{ext}'
    if jsondata["filepath"].endswith(").json"):
        brackets = re.findall("\\([1-999]\\)\\.json", jsondata["filepath"])
        if brackets:
            brackets = brackets[-1][:-5]
            name, ext = os.path.splitext(jsondata["title"])
            jsondata["title"] = f'{name}{brackets}{ext}'
    
    filepath = [file for file in files if file["filename"] == jsondata["title"]]
    
    if filepath:
        return True, filepath[0]
    else:
        return False, {"jsonpath": jsondata["filepath"],
                       "title": jsondata["title"]}
    
def copy_modify(file, date, copyto):
    copyto = checkout_dir(os.path.join(copyto, f"Photos from {date.year}"))
    
    new_file =  os.path.join(copyto, file["filename"])
    shutil.copy(file["filepath"], new_file)
    filedate.File(new_file).set(created = date, modified = date)
    
    return new_file

def copy_unprocessed(unprocessed, saveto):
    to_return = []
    for file in tqdm(unprocessed, desc="Copying"):
        new_file = os.path.join(saveto, checkout_dir(os.path.join(saveto, "unprocessed")), file["filename"])
        shutil.copy(file["filepath"], new_file)
        file["procpath"] = new_file
        to_return.append(file)
    return to_return

def savelogs(saveto, processed, unprocessed, unprocessed_jsons, endtime):
    with open(os.path.join(saveto, "logs.txt"), "w") as logfile:
        logfile.write(f"Processed files:\n\n")
        for file in processed:
            logfile.write(f"    {file["filename"]}:\n")
            logfile.write(f"        base file:     {file["filepath"]}\n")
            logfile.write(f"        modified file: {file["procpath"]}\n\n")
        
        logfile.write(f"Unrocessed jsons:\n\n")
        for file in unprocessed_jsons:
            logfile.write(f"    {file["filename"]}:\n")
            logfile.write(f"        base file:     {file["filepath"]}\n")
            logfile.write(f"        this json file did not find his pair among files: {file["title"]}\n\n")
        
        logfile.write(f"Unrocessed files:\n\n")
        for file in unprocessed:
            logfile.write(f"    {file["filename"]}:\n")
            logfile.write(f"        base file:     {file["filepath"]}\n")
            logfile.write(f"        json-based search have not reached this file\n\n")
            
        logfile.write(f"Processed: {len(processed)} files\n")
        logfile.write(f"Unprocessed: {len(unprocessed)} files, {len(unprocessed_jsons)} jsons\n")
        logfile.write(f"Time used: {endtime} seconds")
        
def main(path):
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
        exist, file = find_file(jsondata, files)
        if exist:
            # copy and modify file, if found
            procpath = copy_modify(file, jsondata["date"], saveto)
            # save path to modified file
            file["procpath"] = procpath
            processed.append(file)
        else:
            # add info about jsons which have not found any pair, to present it in logs
            unprocessed_jsons.append({"filename": file["jsonpath"][len(os.path.dirname(file["jsonpath"]))+1::],
                                      "filepath": file["jsonpath"],
                                      "title": file["title"]})
    
    
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
    
def wizard():
    print("\nYou have not give arguments needed, so now you in the Wizard setup")
    try:
        path = input("Enter path to your folder with takeouts: ")
        return path
    except:
        pass
    
def parse():
    parser = argparse.ArgumentParser(description="Google Takeout Processor")
    
    parser.add_argument("path", help="Path to the folder with your takeouts")
    
    try:
        args = parser.parse_args()
        path = args.path
    except:
        path = wizard()
    
    main(path)

if __name__ == "__main__":
    parse()