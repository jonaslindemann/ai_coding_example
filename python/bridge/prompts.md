Create an example of a parametric truss bridge design implemented as a class in calfem using the bar2 elements. You should be able to set total width and height and other relevant parameters.

Create a user interface in Qt for visualizing and interacting with the truss bridge simulation implemented in truss_bridge.py. The user interface should be able to:
- Select the type of truss (Pratt, Howe, Warren)
- Adjust the bridge parameters such as width, height, and number of panels
- Solve the truss bridge and display the deformed shape
- Show the normal forces in the elements with a color-coded representation
- Display a summary of the bridge including maximum deflection and stresses
- The interaction should be as responsive as possible, providing immediate visual feedback when parameters are adjusted.

Add a plot showing the utilisation of the truss elements, indicating how much of their capacity is being used.

Create a web application for the truss bridge simulation implemented in truss_bridge.py using NiceGUI and Plotly. Reuse the TrussBridge class without modifying it. The web application should provide the same functionality as the Qt user interface in truss_bridge_ui.py:
- Select the type of truss (Pratt, Howe, Warren)
- Adjust the bridge parameters such as width, height, number of panels, E-modulus, yield strength, cross-section areas and deck load
- Solve the truss bridge and display the undeformed and deformed shape with an adjustable deformation scale
- Show the normal forces in the elements with a color-coded representation and a color bar. Hovering over an element should show its normal force, stress and utilisation
- Show a plot of the utilisation of the truss elements, highlighting elements above 100 %
- Display a summary of the bridge including maximum deflection, maximum stresses and maximum utilisation
- The interaction should be as responsive as possible: update the model while sliders are being dragged, using debouncing so the browser stays smooth
- Use a layout with a parameter panel on the left and the plots on the right, which should also work on smaller screens

Put the application in truss_bridge_web.py and make it runnable with "python truss_bridge_web.py". List the extra dependencies needed (nicegui, plotly).
