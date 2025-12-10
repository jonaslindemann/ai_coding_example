#include "raylib.h"
#include <cmath>
#include <memory>
#include <vector>

#include "vector_math.h"

namespace particles {

class Particle {
private:
    vector_math::Vec2d m_position;
    vector_math::Vec2d m_velocity;
    float m_radius;
    Color m_color;

public:
    Particle(Vector2 position, Vector2 velocity, float radius = 5.0f, Color color = BLACK);

    static std::shared_ptr<Particle> create(Vector2 position, Vector2 velocity, float radius = 5.0f,
                                            Color color = BLACK);

    void update();
    void draw();
    bool isAlive();
    Vector2 position();
    Vector2 velocity();
    void setPosition(Vector2 position);
    void setVelocity(Vector2 velocity);
    void reverseVelocity();
    void bounceX();
    void bounceY();
    float radius();
    Color color();
};

typedef std::shared_ptr<Particle> ParticlePtr;

class ParticleSystem {
private:
    std::vector<ParticlePtr> m_particles;

public:
    ParticleSystem(int nParticles);

    static std::shared_ptr<ParticleSystem> create(int nParticles);

    void update();
    void draw();

    void checkBounds();
};

typedef std::shared_ptr<ParticleSystem> ParticleSystemPtr;

} // namespace particles
