
#include "raylib.h"

#include "particles.h"

using namespace particles;

int main(void)
{
    // Initialization
    //--------------------------------------------------------------------------------------
    const int screenWidth = 1280;
    const int screenHeight = 1024;
    InitWindow(screenWidth, screenHeight, "raylib example - moving ball");

    auto particleSystem = ParticleSystem::create(100);

    Vector2 ballPosition = {(float)screenWidth / 2, (float)screenHeight / 2};
    float ballSpeed = 5.0f;
    SetTargetFPS(60);
    //--------------------------------------------------------------------------------------

    // Main game loop
    while (!WindowShouldClose()) // Detect window close button or ESC key
    {
        // Update
        //----------------------------------------------------------------------------------

        particleSystem->update();

        // Draw
        //----------------------------------------------------------------------------------
        BeginDrawing();

        ClearBackground(RAYWHITE);

        DrawCircleV(ballPosition, 20, MAROON);

        DrawText("Move the ball with arrow keys", 10, 10, 20, DARKGRAY);

        particleSystem->draw();

        EndDrawing();
        //----------------------------------------------------------------------------------
    }

    // De-Initialization
    //--------------------------------------------------------------------------------------
    CloseWindow(); // Close window and OpenGL context
    //--------------------------------------------------------------------------------------

    return 0;
}
