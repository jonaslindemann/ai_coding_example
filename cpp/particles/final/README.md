# Raylib Particles Application

A C++ raylib application using CMake and vcpkg.

## Prerequisites

- CMake 3.21 or higher
- vcpkg (must be in PATH or VCPKG_ROOT environment variable set)
- Visual Studio 2022 (for Visual Studio generator)
- C++17 compatible compiler

## Setup

Make sure vcpkg is properly set up:
- Either add vcpkg to your PATH
- Or set the VCPKG_ROOT environment variable to point to your vcpkg installation

## Build Instructions

### Configure Debug Build
```bash
cmake -B build-debug -S . -G "Visual Studio 17 2022"
```

### Configure Release Build
```bash
cmake -B build-release -S . -G "Visual Studio 17 2022"
```

### Build Debug
```bash
cmake --build build-debug --config Debug
```

### Build Release
```bash
cmake --build build-release --config Release
```

## Run the Application

### Debug Version
```bash
.\build-debug\bin\Debug\RaylibParticlesd.exe
```

### Release Version
```bash
.\build-release\bin\Release\RaylibParticles.exe
```

## Project Structure

```
.
├── CMakeLists.txt      # CMake configuration
├── vcpkg.json          # vcpkg manifest for dependencies
├── src/
│   └── main.cpp        # Main application source
├── build-debug/        # Debug build directory (generated)
└── build-release/      # Release build directory (generated)
```

## Notes

- The debug build automatically adds a 'd' suffix to the executable on Windows (RaylibParticlesd.exe)
- vcpkg dependencies are managed through vcpkg.json manifest mode
- The project uses vcpkg autodetection via VCPKG_ROOT environment variable
