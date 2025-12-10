"""
PyQt6 User Interface for the Countries API.

This module provides a tabbed interface for querying country information
using the countries module.
"""

from __future__ import annotations

import sys
from typing import Any

from qtpy.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QPushButton,
    QLabel,
    QTextEdit,
    QHeaderView,
    QMessageBox,
    QComboBox,
)
from qtpy.QtCore import Qt, QThread, Signal
from qtpy.QtGui import QFont

from countries import RestCountriesClient, Country


class WorkerThread(QThread):
    """Worker thread for API calls to prevent UI blocking."""
    
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CountryTableTab(QWidget):
    """Tab for displaying all countries in a searchable table."""
    
    def __init__(self, client: RestCountriesClient):
        super().__init__()
        self.client = client
        self.all_countries: list[Country] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by name, code, capital, or region...")
        self.search_input.textChanged.connect(self.filter_table)
        
        self.load_button = QPushButton("Load Countries")
        self.load_button.clicked.connect(self.load_countries)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.load_button)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Code", "Capital", "Region", "Population"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        
        # Status label
        self.status_label = QLabel("Click 'Load Countries' to fetch data")
        
        layout.addLayout(search_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def load_countries(self):
        """Load all countries from the API."""
        self.load_button.setEnabled(False)
        self.search_input.setEnabled(False)
        self.status_label.setText("⏳ Loading countries...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        self.worker = WorkerThread(
            self.client.get_all_countries,
            fields=["capital", "region", "population"]
        )
        self.worker.finished.connect(self.on_countries_loaded)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_countries_loaded(self, countries: list[Country]):
        """Handle loaded countries."""
        self.all_countries = countries
        self.populate_table(countries)
        self.status_label.setText(f"✓ Loaded {len(countries)} countries")
        self.load_button.setEnabled(True)
        self.search_input.setEnabled(True)
        QApplication.restoreOverrideCursor()
    
    def populate_table(self, countries: list[Country]):
        """Populate the table with country data."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(countries))
        
        for row, country in enumerate(countries):
            self.table.setItem(row, 0, QTableWidgetItem(country.common_name))
            self.table.setItem(row, 1, QTableWidgetItem(country.code))
            
            capital = country.data.get("capital", ["N/A"])
            capital_str = capital[0] if capital else "N/A"
            self.table.setItem(row, 2, QTableWidgetItem(capital_str))
            
            region = country.data.get("region", "N/A")
            self.table.setItem(row, 3, QTableWidgetItem(region))
            
            population = country.data.get("population", 0)
            pop_item = QTableWidgetItem()
            pop_item.setData(Qt.ItemDataRole.DisplayRole, population)
            self.table.setItem(row, 4, pop_item)
        
        self.table.setSortingEnabled(True)
    
    def filter_table(self, text: str):
        """Filter table based on search text."""
        search_text = text.lower()
        
        for row in range(self.table.rowCount()):
            show_row = False
            
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    show_row = True
                    break
            
            self.table.setRowHidden(row, not show_row)
    
    def on_error(self, error_msg: str):
        """Handle errors."""
        self.status_label.setText(f"✗ Error: {error_msg}")
        self.load_button.setEnabled(True)
        self.search_input.setEnabled(True)
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "Error", f"Failed to load countries:\n{error_msg}")


class CountryByCodeTab(QWidget):
    """Tab for searching countries by code."""
    
    def __init__(self, client: RestCountriesClient):
        super().__init__()
        self.client = client
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Country Code:")
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter country code (e.g., SE, USA, 840)")
        self.code_input.returnPressed.connect(self.search_country)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_country)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.code_input)
        search_layout.addWidget(self.search_button)
        
        # Results display
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.result_text.setFont(font)
        
        layout.addLayout(search_layout)
        layout.addWidget(QLabel("Country Information:"))
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def search_country(self):
        """Search for a country by code."""
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "Input Required", "Please enter a country code")
            return
        
        self.search_button.setEnabled(False)
        self.code_input.setEnabled(False)
        self.result_text.setText("⏳ Searching...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        self.worker = WorkerThread(
            self.client.get_country_by_code,
            code,
            fields=["capital", "region", "subregion", "population", "area", 
                   "languages", "currencies", "timezones", "flags"]
        )
        self.worker.finished.connect(self.on_country_found)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_country_found(self, country: Country):
        """Display country information."""
        data = country.data
        
        result = f"{'=' * 60}\n"
        result += f"  {country.common_name}\n"
        result += f"{'=' * 60}\n\n"
        
        result += f"Official Name:  {country.official_name}\n"
        result += f"Country Code:   {country.code}\n"
        result += f"CCA2:           {country.cca2}\n"
        result += f"CCA3:           {country.cca3}\n\n"
        
        capital = data.get("capital", ["N/A"])
        result += f"Capital:        {capital[0] if capital else 'N/A'}\n"
        result += f"Region:         {data.get('region', 'N/A')}\n"
        result += f"Subregion:      {data.get('subregion', 'N/A')}\n\n"
        
        population = data.get("population", 0)
        result += f"Population:     {population:,}\n"
        
        area = data.get("area", 0)
        result += f"Area:           {area:,} km²\n\n"
        
        languages = data.get("languages", {})
        if languages:
            result += f"Languages:      {', '.join(languages.values())}\n"
        
        currencies = data.get("currencies", {})
        if currencies:
            curr_list = [f"{v.get('name')} ({k})" for k, v in currencies.items()]
            result += f"Currencies:     {', '.join(curr_list)}\n"
        
        timezones = data.get("timezones", [])
        if timezones:
            result += f"Timezones:      {', '.join(timezones)}\n"
        
        self.result_text.setText(result)
        self.search_button.setEnabled(True)
        self.code_input.setEnabled(True)
        QApplication.restoreOverrideCursor()
    
    def on_error(self, error_msg: str):
        """Handle errors."""
        self.result_text.setText(f"✗ Error: {error_msg}")
        self.search_button.setEnabled(True)
        self.code_input.setEnabled(True)
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "Error", f"Failed to find country:\n{error_msg}")


class CountryByNameTab(QWidget):
    """Tab for searching countries by name."""
    
    def __init__(self, client: RestCountriesClient):
        super().__init__()
        self.client = client
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Country Name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter country name (e.g., Sweden, Germany)")
        self.name_input.returnPressed.connect(self.search_country)
        
        self.exact_match = QComboBox()
        self.exact_match.addItems(["Partial Match", "Exact Match"])
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_country)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.name_input)
        search_layout.addWidget(self.exact_match)
        search_layout.addWidget(self.search_button)
        
        # Results display
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.result_text.setFont(font)
        
        layout.addLayout(search_layout)
        layout.addWidget(QLabel("Country Information:"))
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def search_country(self):
        """Search for countries by name."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Required", "Please enter a country name")
            return
        
        self.search_button.setEnabled(False)
        self.name_input.setEnabled(False)
        self.exact_match.setEnabled(False)
        self.result_text.setText("⏳ Searching...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        full_text = self.exact_match.currentIndex() == 1
        
        self.worker = WorkerThread(
            self.client.get_country_by_name,
            name,
            fields=["capital", "region", "subregion", "population", "area", 
                   "languages", "currencies", "timezones", "borders", "flags"],
            full_text=full_text
        )
        self.worker.finished.connect(self.on_countries_found)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_countries_found(self, countries: list[Country]):
        """Display country information."""
        if not countries:
            self.result_text.setText("No countries found")
            self.search_button.setEnabled(True)
            return
        
        result = ""
        
        for i, country in enumerate(countries):
            if i > 0:
                result += "\n" + "=" * 60 + "\n\n"
            
            data = country.data
            
            result += f"{'=' * 60}\n"
            result += f"  {country.common_name}\n"
            result += f"{'=' * 60}\n\n"
            
            result += f"Official Name:  {country.official_name}\n"
            result += f"Country Code:   {country.code}\n"
            result += f"CCA2:           {country.cca2}\n"
            result += f"CCA3:           {country.cca3}\n\n"
            
            capital = data.get("capital", ["N/A"])
            result += f"Capital:        {capital[0] if capital else 'N/A'}\n"
            result += f"Region:         {data.get('region', 'N/A')}\n"
            result += f"Subregion:      {data.get('subregion', 'N/A')}\n\n"
            
            population = data.get("population", 0)
            result += f"Population:     {population:,}\n"
            
            area = data.get("area", 0)
            result += f"Area:           {area:,} km²\n\n"
            
            languages = data.get("languages", {})
            if languages:
                result += f"Languages:      {', '.join(languages.values())}\n"
            
            currencies = data.get("currencies", {})
            if currencies:
                curr_list = [f"{v.get('name')} ({k})" for k, v in currencies.items()]
                result += f"Currencies:     {', '.join(curr_list)}\n"
            
            timezones = data.get("timezones", [])
            if timezones:
                result += f"Timezones:      {', '.join(timezones)}\n"
            
            borders = data.get("borders", [])
            if borders:
                result += f"Borders:        {', '.join(borders)}\n"
        
        if len(countries) > 1:
            result = f"Found {len(countries)} countries:\n\n" + result
        
        self.result_text.setText(result)
        self.search_button.setEnabled(True)
        self.name_input.setEnabled(True)
        self.exact_match.setEnabled(True)
        QApplication.restoreOverrideCursor()
    
    def on_error(self, error_msg: str):
        """Handle errors."""
        self.result_text.setText(f"✗ Error: {error_msg}")
        self.search_button.setEnabled(True)
        self.name_input.setEnabled(True)
        self.exact_match.setEnabled(True)
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "Error", f"Failed to search countries:\n{error_msg}")


class CountriesMainWindow(QMainWindow):
    """Main window for the Countries application."""
    
    def __init__(self):
        super().__init__()
        self.client = RestCountriesClient()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Countries Information Browser")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Create tabs
        self.country_table_tab = CountryTableTab(self.client)
        self.country_code_tab = CountryByCodeTab(self.client)
        self.country_name_tab = CountryByNameTab(self.client)
        
        # Add tabs
        tabs.addTab(self.country_table_tab, "Country Table")
        tabs.addTab(self.country_code_tab, "Country by Code")
        tabs.addTab(self.country_name_tab, "Country by Name")
        
        self.setCentralWidget(tabs)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.client.close()
        event.accept()


def main():
    """Run the application."""
    app = QApplication(sys.argv)
    window = CountriesMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
