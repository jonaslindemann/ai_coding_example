# Prompt 1

Create a skeleton C++ project for a raylib application using CMake can vcpkg. Make sure to include the following features: 

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

# Prompt 2

Add a class Particles that manages a collection of particles. Each particle should have position, velocity, and lifespan attributes. The Particles class should provide methods to update the particles' positions based on their velocities and decrease their lifespans over time. When a particle's lifespan reaches zero, it should be removed from the collection. Use Eigen library for vector and array operations. Implement the class in header and a source file.

