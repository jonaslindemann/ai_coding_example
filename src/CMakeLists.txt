# Set the source files for the application
#INCLUDE_DIRECTORIES(${raylib_project_SOURCE_DIR}/include)
file(GLOB SOURCE_FILES *.cpp)
file(GLOB INCLUDE_FILES ${raylib_project_SOURCE_DIR}/include/*.h)

set(SOURCES ../include/parcticle.h particle.cpp main.cpp)

# Create the executable
add_executable(raylib_example ${INCLUDE_FILES} ${SOURCE_FILES})

# Link the raylib library to the executable
target_link_libraries(raylib_example PRIVATE raylib)
