# -*- coding: utf-8 -*-
"""
User interface for BeamSimplySupported model

@author: Jonas Lindemann
"""

from qtpy.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QTableWidget,
                             QTableWidgetItem, QGroupBox, QFormLayout)
from qtpy.QtCore import Qt
import sys
from beam_model_decorators import BeamSimplySupported


class BeamUI(QMainWindow):
    """User interface for beam calculation"""
    
    def __init__(self):
        super().__init__()
        self.beam = BeamSimplySupported()
        self.init_ui()
        self.update_table()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Simply Supported Beam Calculator")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Input parameters group
        input_group = QGroupBox("Input Parameters")
        input_layout = QFormLayout()
        
        # Create input fields
        self.a_input = QLineEdit(str(self.beam.a))
        self.a_input.textChanged.connect(self.on_input_changed)
        input_layout.addRow("a (m):", self.a_input)
        
        self.b_input = QLineEdit(str(self.beam.b))
        self.b_input.textChanged.connect(self.on_input_changed)
        input_layout.addRow("b (m):", self.b_input)
        
        self.P_input = QLineEdit(str(self.beam.P))
        self.P_input.textChanged.connect(self.on_input_changed)
        input_layout.addRow("P (N):", self.P_input)
        
        self.E_input = QLineEdit(str(self.beam.E))
        self.E_input.textChanged.connect(self.on_input_changed)
        input_layout.addRow("E (Pa):", self.E_input)
        
        self.I_input = QLineEdit(str(self.beam.I))
        self.I_input.textChanged.connect(self.on_input_changed)
        input_layout.addRow("I (m⁴):", self.I_input)
        
        # Display L (calculated)
        self.L_label = QLabel(f"{self.beam.L:.3f}")
        input_layout.addRow("L (m):", self.L_label)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # Results table
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["x (m)", "v (m)", "V (N)", "M (Nm)"])
        
        # Make table read-only
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        results_layout.addWidget(self.table)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
    def on_input_changed(self):
        """Handle input parameter changes"""
        # Update beam model
        self.beam.a = self.a_input.text()
        self.beam.b = self.b_input.text()
        self.beam.P = self.P_input.text()
        self.beam.E = self.E_input.text()
        self.beam.I = self.I_input.text()
        
        # Update L label
        self.L_label.setText(f"{self.beam.L:.3f}")
        
        # Update table
        self.update_table()
        
    def update_table(self):
        """Update the results table with calculated values"""
        # Calculate number of points
        dx = 0.1
        x = 0.0
        points = []
        
        # Collect data points
        while x <= self.beam.L + dx/2:
            v_val = self.beam.v(x)
            V_val = self.beam.V(x)
            M_val = self.beam.M(x)
            points.append((x, v_val, V_val, M_val))
            x += dx
            
        # Update table
        self.table.setRowCount(len(points))
        
        for row, (x_val, v_val, V_val, M_val) in enumerate(points):
            # x column
            item = QTableWidgetItem(f"{x_val:.3f}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 0, item)
            
            # v column
            item = QTableWidgetItem(f"{v_val:.6e}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 1, item)
            
            # V column
            item = QTableWidgetItem(f"{V_val:.3f}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, item)
            
            # M column
            item = QTableWidgetItem(f"{M_val:.3f}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, item)
        
        # Resize columns to content
        self.table.resizeColumnsToContents()


def main():
    """Main function to run the application"""
    app = QApplication(sys.argv)
    window = BeamUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
