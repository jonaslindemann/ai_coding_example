#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Qt Example")
        self.setGeometry(100, 100, 400, 300)

        # Create a menu bar
        menubar = self.menuBar()

        # Create a File menu
        file_menu = menubar.addMenu("File")

        # Create a New action
        new_action = QAction("New", self)
        new_action.triggered.connect(self.newFile)
        file_menu.addAction(new_action)

        # Create an Open action
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.openFile)
        file_menu.addAction(open_action)

        # Create a Save action
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.saveFile)
        file_menu.addAction(save_action)

    def newFile(self):
        print("New file event")

    def openFile(self):
        print("Open file event")

    def saveFile(self):
        print("Save file event")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())