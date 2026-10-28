Create an example of a parametric concrete wall implemented as a class in calfem using suitable elements. The wall class should be able to add holes and doors. You should be able to set total width and height and other relevant parameters. The class should be able to plot the stresses both von mises as well as main principle stresses.

Add the ability to add boundary controls. Freely supported with supports at the ends and at specified positions. Also a fully supported option should be available.

Create a user interface in Qt (qtpy) for visualizing and interacting with the wall model simulation implemented in concrete_wall.py. The user interface should be able to:
- Select the wall dimensions
- Add holes and doors.
- Modify the material properties
- Modify the loads and boundary conditions.
Use tabs if suitable, especially for the results. 

Create a web application for the concrete wall simulation implemented in concrete_wall.py using NiceGUI and Plotly. Reuse the ConcreteWall class without modifying it. The web application should provide the same functionality as the Qt user interface in concrete_wall_ui.py:
- Set the wall dimensions, thickness and element size
- Add, edit and remove windows and doors in an openings table. Highlight the opening that causes a validation error
- Modify the material properties
- Modify the loads and boundary conditions (fully supported or freely supported on bearings at the ends and at specified positions)
- Show the results in tabs: mesh, deformed shape, von Mises stress, major and minor principal stresses and principal stress directions. Draw the openings and supports in all plots, and show values when hovering
- Show a summary of the model and results, and a status line with solve time and any input errors
- The interaction should be as responsive as possible: debounce rapid input changes, solve the model without blocking the page, and only render the visible result tab
- Use input tabs on the left and result tabs on the right, which should also work on smaller screens

Put the application in concrete_wall_web.py and make it runnable with "python concrete_wall_web.py". List the extra dependencies needed (nicegui, plotly).
