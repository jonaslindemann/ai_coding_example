import os
import argparse

def traverse_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            print(os.path.join(root, file))
        for dir in dirs:
            print(os.path.join(root, dir))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traverse a directory tree")
    parser.add_argument("-d", "--directory", default=os.getcwd(), help="Start directory for traversal")
    args = parser.parse_args()

    traverse_directory(args.directory)