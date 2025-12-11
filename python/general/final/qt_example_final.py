#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        # Create a menu bar
        menubar = self.menuBar()

        # Create a File menu
        file_menu = menubar.addMenu('File')

        # Create a New action
        new_action = QAction('New', self)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        # Create an Open action
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        # Create a Save action
        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        # Create an Exit action
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Set the window title and size
        self.setWindowTitle('Qt Example')
        self.setGeometry(100, 100, 400, 300)

    def new_file(self):
        print('New file action triggered')

    def open_file(self):
        print('Open file action triggered')

    def save_file(self):
        print('Save file action triggered')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())