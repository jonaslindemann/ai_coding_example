The computational core in this folder (sections.py, frame_model.py, verification.py, test_frame_model.py) is written and verified by the engineer. The prompts below build the application around it. Precomputed results are in final/.

Review frame_model.py as an experienced structural engineer and numerical analyst. Do not change the code. List anything that could give wrong results: units, sign conventions, local versus global directions, boundary conditions, and assumptions that are not stated. For each point, say how it could be tested.

Create a self-contained HTML calculation report for the PlaneFrame class in frame_model.py. Do not modify frame_model.py, sections.py or verification.py, and do not compute any engineering quantities in the report - only present results from the model. The report should:
- Echo every input value exactly as passed to the model, including the column base condition
- List the modelling assumptions and limitations
- Show the serviceability and strength checks against their limits with a clear OK / NOT OK status, and a banner at the top summarising the outcome
- Include figures of the model with supports and loads, the deformed shape (state the scale factor and the real maximum displacement), and bending moment, normal force and shear force diagrams. Draw bending moments on the tension side
- Tables of support reactions and member results
- A verification section with the global equilibrium residuals and the analytical benchmarks from verification.py
- A sign-off table for "Prepared" and "Checked"
Embed figures as SVG made with matplotlib so the file works offline and prints well. Put it in frame_report.py with a build_report(frame) function and a command line interface.

Create a web application for the PlaneFrame class in frame_model.py using NiceGUI and Plotly. Reuse PlaneFrame, the benchmarks in verification.py and the figure helpers in frame_report.py without modifying them. The application should:
- Have a parameter panel on the left: number of bays and bay width, number of storeys and storey height, column and beam sections, steel grade, fixed or pinned column bases, floor, roof and horizontal loads, and self-weight
- Show check cards for interstorey drift, beam deflection, maximum utilisation and verification status (benchmarks and equilibrium), coloured green or red
- Show result tabs: model and loads, deformed shape with an adjustable exaggeration, bending moment, shear force, normal force, utilisation and verification. Show values when hovering
- Show an "as modelled" line rendered from the solved model object, not from the input widgets
- Download the calculation report
- Be responsive: debounce input changes, solve without blocking the page, and only render the visible tab
- Work on smaller screens

Put the application in frame_app.py and make it runnable with "python frame_app.py". List the extra dependencies needed (nicegui, plotly).
