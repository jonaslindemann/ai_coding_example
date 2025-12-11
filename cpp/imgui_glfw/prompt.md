Create a short example of using ImGUI with the GLFW library. The example should create a window with a button that, when clicked, increments a counter displayed in the window. Use CMake for building the project and provide the necessary CMakeLists.txt file. Also, use vcpkg for dependency management. 

Make sure to include the following features: 

* Assume that vcpkg is in the search path and add autodetection of the vcpkg environment in the CMakeLists.txt file. 
* The project should have separate debug and release builds. Using build-debug and build-release folders. 
* Provide instructions on how to build and run the project. 
* It should also automatically add d suffix for debug builds on Windows.
* Ensure CMAKE_TOOLCHAIN_FILE is set before the project() command in CMakeLists.txt for proper vcpkg integration.

I want it to be built using:

cmake -B build-debug -S . -G "Visual Studio 18 2026"
cmake -B build-release -S . -G "Visual Studio 18 2026"
cmake --build build-debug --config Debug
cmake --build build-release --config Release