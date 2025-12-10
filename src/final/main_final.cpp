#include <raylib.h>

#include "particles.h"

using namespace particles;

int main()
{
    // Initialization
    const int screenWidth = 1024;
    const int screenHeight = 768;

    InitWindow(screenWidth, screenHeight, "Raylib Example");
    SetTargetFPS(60);

    // Initialize particle system

    auto particleSystem = ParticleSystem::create(10000);

    // Main game loop
    while (!WindowShouldClose())
    {
        // Update

        particleSystem->update();
        particleSystem->checkBounds();

        // Draw

        BeginDrawing();

        ClearBackground(RAYWHITE);

        DrawText("Hello, Raylib!", 10, 10, 20, DARKGRAY);

        particleSystem->draw();

        EndDrawing();
    }

    // Cleanup
    CloseWindow();

    return 0;
}
