#include <raylib.h>
#include "Particles.h"
#include <Eigen/Dense>

int main()
{
    // Initialize window
    const int screenWidth = 800;
    const int screenHeight = 600;
    
    InitWindow(screenWidth, screenHeight, "Raylib Particles Application");
    SetTargetFPS(60);

    // Create particle system
    Particles particleSystem;
    
    // Add some initial particles
    for (int i = 0; i < 10; ++i)
    {
        Eigen::Vector2f pos(screenWidth / 2.0f, screenHeight / 2.0f);
        Eigen::Vector2f vel(GetRandomValue(-100, 100), GetRandomValue(-100, 100));
        float lifespan = GetRandomValue(2, 5);
        particleSystem.addParticle(pos, vel, lifespan);
    }

    // Main game loop
    while (!WindowShouldClose())
    {
        float deltaTime = GetFrameTime();
        
        // Update
        particleSystem.update(deltaTime);
        particleSystem.removeDeadParticles();
        
        // Add new particles periodically
        if (IsMouseButtonDown(MOUSE_LEFT_BUTTON))
        {
            Vector2 mousePos = GetMousePosition();
            Eigen::Vector2f pos(mousePos.x, mousePos.y);
            Eigen::Vector2f vel(GetRandomValue(-100, 100), GetRandomValue(-100, 100));
            particleSystem.addParticle(pos, vel, 3.0f);
        }
        
        // Draw
        BeginDrawing();
        
        ClearBackground(RAYWHITE);
        
        // Draw particles
        for (size_t i = 0; i < particleSystem.getParticleCount(); ++i)
        {
            const auto& particle = particleSystem.getParticle(i);
            float alpha = particle.lifespan / 5.0f; // Fade based on lifespan
            Color color = ColorAlpha(RED, alpha);
            DrawCircle(static_cast<int>(particle.position.x()), 
                      static_cast<int>(particle.position.y()), 
                      5.0f, color);
        }
        
        DrawText("Click and hold to spawn particles", 10, 40, 20, DARKGRAY);
        DrawText(TextFormat("Particles: %d", particleSystem.getParticleCount()), 10, 70, 20, DARKGRAY);
        DrawFPS(10, 10);
        
        EndDrawing();
    }

    // Cleanup
    CloseWindow();

    return 0;
}
