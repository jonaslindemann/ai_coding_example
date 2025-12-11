# -*- coding: utf-8 -*-
"""
Qt User Interface for BeamSimplySupported model

@author: Jonas Lindemann
"""

import sys
from qtpy.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QTableWidget, QTableWidgetItem, QLabel, 
                            QLineEdit, QPushButton, QGroupBox, QGridLayout,
                            QHeaderView)
from qtpy.QtCore import Qt
from qtpy.QtGui import QDoubleValidator
from beam_model_decorators import BeamSimplySupported


class BeamUI(QMainWindow):
    """Main window for the beam analysis user interface"""
    
    def __init__(self):
        super().__init__()
        self.beam = BeamSimplySupported()
        self.setup_ui()
        self.update_table()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Beam Analysis - Simply Supported Beam")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create input parameters group
        input_group = self.create_input_group()
        main_layout.addWidget(input_group)
        
        # Create results table
        self.table = self.create_results_table()
        main_layout.addWidget(self.table)
        
        # Create control buttons
        button_layout = QHBoxLayout()
        
        self.update_button = QPushButton("Update Table")
        self.update_button.clicked.connect(self.update_table)
        button_layout.addWidget(self.update_button)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
    def create_input_group(self):
        """Create the input parameters group box"""
        group = QGroupBox("Beam Parameters")
        layout = QGridLayout(group)
        
        # Create input fields with labels and validators
        self.inputs = {}
        
        # Parameter definitions: (name, label, initial_value, unit)
        parameters = [
            ('a', 'Distance a:', self.beam.a, 'm'),
            ('b', 'Distance b:', self.beam.b, 'm'),
            ('P', 'Load P:', self.beam.P, 'N'),
            ('E', 'Elastic modulus E:', self.beam.E, 'Pa'),
            ('I', 'Moment of inertia I:', self.beam.I, 'm⁴')
        ]
        
        for i, (param, label, value, unit) in enumerate(parameters):
            # Label
            label_widget = QLabel(label)
            layout.addWidget(label_widget, i, 0)
            
            # Input field
            input_field = QLineEdit()
            input_field.setText(str(value))
            input_field.setValidator(QDoubleValidator())
            input_field.textChanged.connect(self.on_parameter_changed)
            layout.addWidget(input_field, i, 1)
            
            # Unit label
            unit_label = QLabel(unit)
            layout.addWidget(unit_label, i, 2)
            
            self.inputs[param] = input_field
            
        # Add calculated length (read-only)
        length_label = QLabel('Total length L:')
        layout.addWidget(length_label, len(parameters), 0)
        
        self.length_display = QLabel(f"{self.beam.L:.3f}")
        layout.addWidget(self.length_display, len(parameters), 1)
        
        length_unit = QLabel('m')
        layout.addWidget(length_unit, len(parameters), 2)
        
        return group
        
    def create_results_table(self):
        """Create the results table"""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['x (m)', 'v (m)', 'V (N)', 'M (Nm)'])
        
        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Make table read-only
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        return table
        
    def on_parameter_changed(self):
        """Handle parameter changes"""
        try:
            # Update beam parameters from input fields
            self.beam.a = float(self.inputs['a'].text())
            self.beam.b = float(self.inputs['b'].text())
            self.beam.P = float(self.inputs['P'].text())
            self.beam.E = float(self.inputs['E'].text())
            self.beam.I = float(self.inputs['I'].text())
            
            # Update length display
            self.length_display.setText(f"{self.beam.L:.3f}")
            
            # Update table
            self.update_table()
            
        except ValueError:
            # Handle invalid input gracefully
            pass
    
    def update_table(self):
        """Update the results table with current beam parameters"""
        # Define x range and step size
        dx = 0.1
        x_values = []
        x = 0.0
        
        # Generate x values from 0 to L
        while x <= self.beam.L + dx/2:  # Small tolerance for floating point
            x_values.append(x)
            x += dx
            
        # Set table size
        self.table.setRowCount(len(x_values))
        
        # Fill table with calculated values
        for i, x in enumerate(x_values):
            try:
                v_val = self.beam.v(x)
                V_val = self.beam.V(x)
                M_val = self.beam.M(x)
                
                # Create table items with formatted values
                x_item = QTableWidgetItem(f"{x:.3f}")
                v_item = QTableWidgetItem(f"{v_val:.6f}")
                V_item = QTableWidgetItem(f"{V_val:.3f}")
                M_item = QTableWidgetItem(f"{M_val:.3f}")
                
                # Center align the values
                for item in [x_item, v_item, V_item, M_item]:
                    item.setTextAlignment(Qt.AlignCenter)
                
                # Set items in table
                self.table.setItem(i, 0, x_item)
                self.table.setItem(i, 1, v_item)
                self.table.setItem(i, 2, V_item)
                self.table.setItem(i, 3, M_item)
                
            except Exception as e:
                # Handle any calculation errors
                print(f"Error calculating values at x={x}: {e}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = BeamUI()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()