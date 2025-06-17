import argparse
import os
import shutil
import gtp

def parse():
    # Parse command-line arguments for source and destination paths
    parser = argparse.ArgumentParser(description="Get json files and everything else from source separated into destination.")
    parser.add_argument('-s', '--source', required=True, help='Source path')
    parser.add_argument('-d', '--destination', required=True, help='Destination path')
    parser.parse_args()
    source = parser.parse_args().source
    destination = parser.parse_args().destination
    return source, destination

def main():
    # Get source and destination paths from arguments
    source, destination = parse()
    
    # Check if source and destination directories exist
    if not gtp.exists(source) or not gtp.exists(destination):
        print("Source or destination path does not exist.")
        return
    
    # Get lists of JSON files and other files from the source directory
    jsons, files = gtp.get_file_names(source)
    
    # If there are files to process, create a new output directory
    if jsons or files:
        destination = gtp.checkout_dir(os.path.join(destination, 'SeparateOutput'), onlynew = True)
    else:
        print("No files to separate.")
        return
    
    # Create a subdirectory for JSON files and copy them there
    if jsons:
        gtp.checkout_dir(os.path.join(destination, 'jsons'))
    for jsonpath in jsons:
        # Copy each JSON file to the 'jsons' subdirectory
        shutil.copy(jsonpath, os.path.join(destination, 'jsons', jsonpath[len(os.path.dirname(jsonpath))+1::]))
        
    # Create a subdirectory for other files and copy them there
    if files:
        gtp.checkout_dir(os.path.join(destination, 'files'))
    for file in files:
        # Copy each non-JSON file to the 'files' subdirectory
        shutil.copy(file["filepath"], os.path.join(destination, 'files', file["filename"]))
    
if __name__ == "__main__":
    main()
