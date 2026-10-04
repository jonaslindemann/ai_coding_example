Create an example of a parametric concrete wall implemented as a class in calfem using suitable elements. The wall class should be able to add holes and doors. You should be able to set total width and height and other relevant parameters. The class should be able to plot the stresses both von mises as well as main principle stresses.

Add the ability to add boundary controls. Freely supported with supports at the ends and at specified positions. Also a fully supported option should be available.

Create a user interface in Qt (qtpy) for visualizing and interacting with the wall model simulation implemented in concrete_wall.py. The user interface should be able to:
- Select the wall dimensions
- Add holes and doors.
- Modify the material properties
- Modify the loads and boundary conditions.
Use tabs if suitable, especially for the results. 