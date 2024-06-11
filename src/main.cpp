#include <raylib.h>

#include "particle.h"

using namespace particles;

int main()
{
    // Initialization
    const int screenWidth = 800;
    const int screenHeight = 450;

    InitWindow(screenWidth, screenHeight, "Raylib Example");

    SetTargetFPS(60);

    // Main game loop
    while (!WindowShouldClose())
    {
        // Update

        // Draw
        BeginDrawing();

        ClearBackground(RAYWHITE);

        DrawText("Hello, Raylib!", 10, 10, 20, DARKGRAY);

        EndDrawing();
    }

    // Cleanup
    CloseWindow();

    return 0;
}