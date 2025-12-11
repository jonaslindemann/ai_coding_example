# ImGui + GLFW Example

A simple example demonstrating how to use ImGui with GLFW to create a window with a button that increments a counter.

## Prerequisites

- CMake 3.20 or higher
- vcpkg (in PATH or VCPKG_ROOT environment variable set)
- Visual Studio 2026 (or compatible C++ compiler)
- Git (for vcpkg dependency installation)

## Setup vcpkg

Make sure vcpkg is installed and the `VCPKG_ROOT` environment variable is set:

```bash
# Set VCPKG_ROOT environment variable (if not already set)
# Example: set VCPKG_ROOT=C:\vcpkg
```

## Dependencies

The project uses the following dependencies managed by vcpkg:
- `imgui[glfw-binding,opengl3-binding]` - Dear ImGui with GLFW and OpenGL3 backends
- `glfw3` - GLFW windowing library

Dependencies are automatically installed by vcpkg when you configure the project.

## Building the Project

### Configure Debug Build

```bash
cmake -B build-debug -S . -G "Visual Studio 18 2026"
```

### Configure Release Build

```bash
cmake -B build-release -S . -G "Visual Studio 18 2026"
```

### Build Debug Version

```bash
cmake --build build-debug --config Debug
```

### Build Release Version

```bash
cmake --build build-release --config Release
```

## Running the Application

### Debug Build

```bash
.\build-debug\bin\Debug\ImGuiGlfwExampled.exe
```

### Release Build

```bash
.\build-release\bin\Release\ImGuiGlfwExample.exe
```

## Features

- **vcpkg Auto-detection**: The CMakeLists.txt automatically detects vcpkg from the VCPKG_ROOT environment variable or a local vcpkg folder
- **Debug Suffix**: Debug builds automatically add 'd' suffix to the executable name on Windows (ImGuiGlfwExampled.exe)
- **Separate Build Folders**: Debug and Release builds use separate build-debug and build-release folders
- **ImGui Integration**: Complete ImGui setup with GLFW and OpenGL3 backends
- **Counter Button**: Click the button to increment the displayed counter
- **FPS Display**: Shows current framerate and frame time

## Project Structure

```
imgui_glfw/
├── main.cpp           - Main application code
├── CMakeLists.txt     - CMake build configuration
├── vcpkg.json         - vcpkg dependencies manifest
└── README.md          - This file
```

## Troubleshooting

### vcpkg not found
Make sure the `VCPKG_ROOT` environment variable is set or vcpkg is in your PATH.

### Missing dependencies
If dependencies are not automatically installed, you can manually install them:
```bash
vcpkg install imgui[glfw-binding,opengl3-binding]:x64-windows glfw3:x64-windows
```

### Build errors
Make sure you have Visual Studio 2026 installed with C++ development tools.

## Notes

- The CMAKE_TOOLCHAIN_FILE is set before the project() command for proper vcpkg integration
- The example uses OpenGL 3.3 Core Profile with GLSL 130
- VSync is enabled by default for smoother rendering
