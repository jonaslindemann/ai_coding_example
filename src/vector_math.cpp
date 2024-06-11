#include "vector_math.h"

using namespace vector_math;

Vec2d::Vec2d() : m_x(0), m_y(0)
{}
Vec2d::Vec2d(float x, float y) : m_x(x), m_y(y)
{}
Vec2d::Vec2d(const Vector2 &v) : m_x(v.x), m_y(v.y)
{}

// Basic vector operations
Vec2d Vec2d::operator+(const Vec2d &other) const
{
    return Vec2d(m_x + other.m_x, m_y + other.m_y);
}

Vec2d Vec2d::operator-(const Vec2d &other) const
{
    return Vec2d(m_x - other.m_x, m_y - other.m_y);
}

Vec2d Vec2d::operator*(float scalar) const
{
    return Vec2d(m_x * scalar, m_y * scalar);
}

float Vec2d::magnitude() const
{
    return sqrt(m_x * m_x + m_y * m_y);
}

// Convert to raylib's Vector2
Vector2 Vec2d::toVector2() const
{
    return {m_x, m_y};
}

// Getters for x and y
float Vec2d::x() const
{
    return m_x;
}
float Vec2d::y() const
{
    return m_y;
}
