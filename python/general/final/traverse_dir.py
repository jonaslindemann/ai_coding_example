#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse

def traverse_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            print(file_path)  # Replace this with your desired logic

def main():
    parser = argparse.ArgumentParser(description='Directory traversal script')
    parser.add_argument('-d', '--directory', default=os.getcwd(), help='Start directory for traversal')
    args = parser.parse_args()

    traverse_directory(args.directory)

if __name__ == '__main__':
    main()