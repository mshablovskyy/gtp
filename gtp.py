import os
import re
import json
from datetime import datetime
import filedate
import shutil

path = "/Users/mshablovskyy/Python/gtp/Takeout 2"

def exists(path):
    return os.path.exists(path)

def get_file_names(path):
    content = os.walk(path)
    
    files = []
    jsons = []
    
    for dir_cont in content:
        for file in dir_cont[2]:
            if re.search(".+\\.json", file):
                jsons.append({
                    "filename": file,
                    "filepath": os.path.join(dir_cont[0], file)
                })
            else: 
                files.append({
                    "filename": file,
                    "filepath": os.path.join(dir_cont[0], file)
                })
    return {"files": files, "jsons": jsons}

def checkout_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)
        
def search_json(name, jsons): 
    # match checks if pattern exist in string; 
    # escape transfroms normal text into text, re module understands(replaces special symbols)
    # slicing of the name variable is important, because if length of the original name is more than 46, google just cuts it after 46th symbol and adds .json
    # examples:
    # cat (4)_&_b825c4ce-dd75-4d6f-82e6-f0165da48e39.jpg
    # cat (4)_&_b825c4ce-dd75-4d6f-82e6-f0165da48e39.json
    # cat (14)_&_6928cf76-d478-4de1-8c42-53a61f3c8e44.jpg
    # cat (14)_&_6928cf76-d478-4de1-8c42-53a61f3c8e4.json
    matches = list(filter(lambda file: re.match(f"{re.escape(name[0:46])}.*\\.json", file["filename"]), jsons))
    if len(matches)>1:
        return False
    elif matches:
        return matches[0]["filepath"]
    
def copy_unproc(file, directory):
    directory = os.path.join(directory, "Unprocessed")
    checkout_dir(directory)
    
    new_file = os.path.join(directory, file["filename"])
    shutil.copy(file["filepath"], new_file) 
    
    return new_file
       
def copy_modify(file, date, directory):
    directory = os.path.join(directory, f"Photos from {date.year}")
    checkout_dir(directory)
    
    new_file = os.path.join(directory, file["filename"])
    shutil.copy(file["filepath"], new_file)
    
    filedate.File(new_file).set(created = date, modified = date)
    
    return new_file
    
def get_time_from_json(path):
    if exists(path):
        with open(path) as file:
            data = json.load(file)
        return datetime.fromtimestamp(int(data["photoTakenTime"]["timestamp"]))
    else:
        return None

def testmain(path):
    # logs:
    processed = []
    unprocessed = []
    retry = []
    # ---
    if not exists(path):
        return
    content = get_file_names(path)
    files = content["files"]
    jsons = content["jsons"]
    
    saveto = os.path.join(os.path.dirname(path), "ProccesedPhotos")
    
    checkout_dir(saveto)
    
    for file in files:
        jsonpath = search_json(file["filename"], jsons)
        if jsonpath == None:
            procpath = copy_unproc(file, saveto)
            file["procpath"] = procpath
            unprocessed.append(file)
        elif jsonpath == False:
            # retry.append(file)
            # unprocessed.append(file)
            
            procpath = copy_unproc(file, saveto)
            file["procpath"] = procpath
            unprocessed.append(file)
        elif jsonpath:
            creation_time = get_time_from_json(jsonpath)
            procpath = copy_modify(file, creation_time, saveto)
            file["procpath"] = procpath
            processed.append(file)
    
    with open(os.path.join(saveto, "logs.txt"), "w") as logsfile:
        logsfile.write("Proccesed files:\n")
        for file in processed:
            logsfile.write(f"name: {file["filename"]}\n")
            logsfile.write(f"   base path: {file["filepath"]}\n")
            logsfile.write(f"   proccesed file: {file["procpath"]}\n\n")
            
        logsfile.write("Unproccesed files:\n")
        for file in unprocessed:
            logsfile.write(f"   name: {file["filename"]}\n")
            logsfile.write(f"   path: {file["filepath"]}\n")
            logsfile.write(f"   copied file: {file["procpath"]}\n\n")
            
        logsfile.write(f"Proccesed {len(processed)} files\n")
        logsfile.write(f"Unproccesed {len(unprocessed)} files\n")



# print(get_file_names(path))
# print(checkout_dir(path))
testmain(path)
# names = get_file_names(path)
# print(f"files: {len(names["files"])}")
# print(f"json: {len(names["jsons"])}")
