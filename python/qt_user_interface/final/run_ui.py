# -*- coding: utf-8 -*-
"""
Test script for the beam UI

@author: Jonas Lindemann
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from beam_ui import main
    print("Starting Beam Analysis UI...")
    main()
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure qtpy and PySide6 are installed:")
    print("pip install qtpy PySide6")
except Exception as e:
    print(f"Error running UI: {e}")