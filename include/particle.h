#include "raylib.h"
#include <cmath>

namespace particles {

class Vec2d {
private:
    float m_x, m_y;

public:
    // Constructors
    Vec2d() : m_x(0), m_y(0)
    {}
    Vec2d(float x, float y) : m_x(x), m_y(y)
    {}
    Vec2d(const Vector2 &v) : m_x(v.x), m_y(v.y)
    {}

    // Basic vector operations
    Vec2d operator+(const Vec2d &other) const
    {
        return Vec2d(m_x + other.m_x, m_y + other.m_y);
    }

    Vec2d operator-(const Vec2d &other) const
    {
        return Vec2d(m_x - other.m_x, m_y - other.m_y);
    }

    Vec2d operator*(float scalar) const
    {
        return Vec2d(m_x * scalar, m_y * scalar);
    }

    float magnitude() const
    {
        return sqrt(m_x * m_x + m_y * m_y);
    }

    // Convert to raylib's Vector2
    Vector2 toVector2() const
    {
        return {m_x, m_y};
    }

    // Getters for x and y
    float x() const
    {
        return m_x;
    }
    float y() const
    {
        return m_y;
    }
};

class Particle {
private:
    Vec2d m_position;
    Vec2d m_velocity;
    float m_radius;
    Color m_color;

public:
    Particle(Vector2 position, Vector2 velocity, float radius, Color color);
    void update();
    void draw();
    bool isAlive();
    Vector2 position();
    float radius();
    Color color();
};

} // namespace particles
