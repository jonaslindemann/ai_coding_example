#pragma once

/**
 * @file glfw_window.h
 * @brief GLFW window wrapper class for OpenGL rendering and user input handling
 * @author Generated documentation
 * @version 1.0
 */

#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>

#include <map>
#include <memory>
#include <mutex>
#include <string>

#include <ivfui/ui_manager.h>

namespace ivfui {

/**
 * @class GLFWWindow
 * @brief A wrapper class for GLFW window management with OpenGL rendering and user input handling
 * 
 * This class provides a high-level interface for creating and managing GLFW windows,
 * handling user input (keyboard and mouse), and managing the rendering loop.
 * It supports callback-based event handling through virtual methods that can be
 * overridden in derived classes.
 * 
 * @note This class is designed to be used with OpenGL contexts
 * @see GLFWWindowPtr for the recommended smart pointer type
 */
class GLFWWindow {
private:
    GLFWwindow *m_window;       ///< Pointer to the GLFW window object
    GLFWwindow *m_sharedWindow; ///< Pointer to a shared GLFW window for context sharing
    GLFWmonitor *m_monitor;     ///< Pointer to the monitor where the window is displayed
    int m_width;                ///< Current width of the window in pixels
    int m_height;               ///< Current height of the window in pixels
    std::string m_title;        ///< Title of the window
    int m_mouseButton;          ///< Last mouse button that was pressed or released
    int m_mouseAction;          ///< Last mouse action (press, release, etc.)
    int m_mouseMods;            ///< Modifier keys pressed during last mouse event
    int m_mouseX;               ///< Current X coordinate of the mouse cursor
    int m_mouseY;               ///< Current Y coordinate of the mouse cursor
    bool m_shiftDown;           ///< True if shift key is currently pressed
    bool m_ctrlDown;            ///< True if control key is currently pressed
    bool m_altDown;             ///< True if alt key is currently pressed
    bool m_escQuit;             ///< If true, pressing ESC will close the window
    bool m_enabled;             ///< If true, the window is enabled for input and rendering
    bool m_runSetup;            ///< If true, setup routines need to be run
    int m_currentKey;           ///< The current key being processed
    std::mutex m_mutex;         ///< Mutex for thread-safe operations
    double m_t0;                ///< Time at the start of the current frame
    double m_t1;                ///< Time at the start of the previous frame
    double m_frameTime;         ///< Time elapsed for the last frame in seconds
    int m_frameCount;           ///< Total number of frames rendered
    int m_lastError;            ///< Last error code encountered
    UiRendererPtr m_uiRenderer; ///< Pointer to the UI renderer

public:
    /**
     * @brief Constructs a new GLFWWindow object
     * @param width Width of the window in pixels
     * @param height Height of the window in pixels
     * @param title Title text displayed in the window's title bar
     * @param monitor Optional monitor to display the window on (nullptr for windowed mode)
     * @param shared Optional shared window for OpenGL context sharing
     */
    GLFWWindow(int width, int height, const std::string title, GLFWmonitor *monitor = nullptr,
               GLFWwindow *shared = nullptr);

    /**
     * @brief Destroys the GLFWWindow object and releases resources
     */
    virtual ~GLFWWindow();

    /**
     * @brief Factory method to create a shared pointer to a GLFWWindow
     * @param width Width of the window in pixels
     * @param height Height of the window in pixels
     * @param title Title text displayed in the window's title bar
     * @param monitor Optional monitor to display the window on (nullptr for windowed mode)
     * @param shared Optional shared window for OpenGL context sharing
     * @return Shared pointer to the newly created GLFWWindow
     */
    static std::shared_ptr<GLFWWindow> create(int width, int height, const std::string title,
                                              GLFWmonitor *monitor = nullptr, GLFWwindow *shared = nullptr);

    /**
     * @brief Makes this window's OpenGL context current
     */
    void makeCurrent();
    
    /**
     * @brief Checks if the window is marked for closing
     * @return true if the window should close, false otherwise
     */
    bool isClosing();
    
    /**
     * @brief Marks the window for closing
     */
    void close();
    
    /**
     * @brief Swaps the front and back buffers of the window
     */
    void swapBuffers();
    
    /**
     * @brief Destroys the window and releases GLFW resources
     */
    void destroy();
    
    /**
     * @brief Gets the width of the window
     * @return Current width in pixels
     */
    int width();
    
    /**
     * @brief Gets the height of the window
     * @return Current height in pixels
     */
    int height();
    
    /**
     * @brief Gets the window dimensions
     * @param[out] width Reference to store the width
     * @param[out] height Reference to store the height
     */
    void getSize(int &width, int &height);
    
    /**
     * @brief Sets the window icon from an image file
     * @param filename Path to the icon image file
     */
    void setWindowIcon(const std::string filename);
    
    /**
     * @brief Maximizes the window
     */
    void maximize();
    
    /**
     * @brief Enables the window for input and rendering
     */
    void enable();
    
    /**
     * @brief Disables the window for input and rendering
     */
    void disable();
    
    /**
     * @brief Checks if the window is enabled
     * @return true if enabled, false otherwise
     */
    bool isEnabled();
    
    /**
     * @brief Executes the main draw cycle including scene and UI rendering
     */
    void draw();
    
    /**
     * @brief Draws only the scene (without UI)
     */
    void drawScene();
    
    /**
     * @brief Gets the underlying GLFW window pointer
     * @return Pointer to the GLFWwindow object
     */
    GLFWwindow *ref();
    
    /**
     * @brief Gets the last mouse button that was pressed or released
     * @return GLFW mouse button code
     */
    int mouseButton();
    
    /**
     * @brief Gets the last mouse action
     * @return GLFW action code (press, release, etc.)
     */
    int mouseAction();
    
    /**
     * @brief Gets the modifier keys for the last mouse event
     * @return Bitfield of GLFW modifier key flags
     */
    int mouseMods();
    
    /**
     * @brief Gets the current X coordinate of the mouse
     * @return X coordinate in pixels
     */
    int mouseX();
    
    /**
     * @brief Gets the current Y coordinate of the mouse
     * @return Y coordinate in pixels
     */
    int mouseY();
    
    /**
     * @brief Checks if any mouse button is currently pressed
     * @return true if any button is down, false otherwise
     */
    bool isAnyMouseButtonDown();
    
    /**
     * @brief Checks if the shift key is currently pressed
     * @return true if shift is down, false otherwise
     */
    bool isShiftDown();
    
    /**
     * @brief Checks if the control key is currently pressed
     * @return true if control is down, false otherwise
     */
    bool isCtrlDown();
    
    /**
     * @brief Checks if the alt key is currently pressed
     * @return true if alt is down, false otherwise
     */
    bool isAltDown();
    
    /**
     * @brief Checks if ESC key will close the window
     * @return true if ESC quits, false otherwise
     */
    bool useEscQuit();
    
    /**
     * @brief Sets whether ESC key should close the window
     * @param flag true to enable ESC quit, false to disable
     */
    void setUseEscQuit(bool flag);
    
    /**
     * @brief Gets the last error code
     * @return Error code (0 if no error)
     */
    int lastError() const;
    
    /**
     * @brief Clears the last error code
     */
    void clearError();
    
    /**
     * @brief Sets an error code
     * @param error Error code to set
     */
    void setError(int error);
    
    /**
     * @brief Gets the time elapsed for the last frame
     * @return Frame time in seconds
     */
    double frameTime() const;
    
    /**
     * @brief Gets the total number of frames rendered
     * @return Frame count
     */
    int frameCount() const;
    
    /**
     * @brief Gets the total elapsed time since window creation
     * @return Elapsed time in seconds
     */
    double elapsedTime() const;
    
    /**
     * @brief Gets the UI renderer instance
     * @return Shared pointer to the UI renderer
     */
    UiRendererPtr uiRenderer() const { return m_uiRenderer; }

public:
    /**
     * @brief Internal handler for keyboard events (calls onKey)
     * @param key GLFW key code
     * @param scancode Platform-specific scan code
     * @param action GLFW action (press, release, repeat)
     * @param mods Bitfield of modifier keys
     */
    virtual void doKey(int key, int scancode, int action, int mods);
    
    /**
     * @brief Internal handler for mouse position events (calls onMousePosition)
     * @param x X coordinate of the cursor
     * @param y Y coordinate of the cursor
     */
    virtual void doMousePosition(double x, double y);
    
    /**
     * @brief Internal handler for mouse button events (calls onMouseButton)
     * @param button GLFW mouse button code
     * @param action GLFW action (press or release)
     * @param mods Bitfield of modifier keys
     */
    virtual void doMouseButton(int button, int action, int mods);
    
    /**
     * @brief Internal handler for window resize events (calls onResize)
     * @param width New width in pixels
     * @param height New height in pixels
     */
    virtual void doResize(int width, int height);
    
    /**
     * @brief Internal update handler called each frame (calls onUpdate)
     */
    virtual void doUpdate();
    
    /**
     * @brief Internal draw handler for scene rendering (calls onDraw)
     */
    virtual void doDraw();
    
    /**
     * @brief Internal draw handler for UI rendering (calls onDrawUi)
     */
    virtual void doDrawUi();
    
    /**
     * @brief Internal handler called after all drawing is complete (calls onDrawComplete)
     */
    virtual void doDrawComplete();
    
    /**
     * @brief Internal handler for updating other UI elements (calls onUpdateOtherUi)
     */
    virtual void doUpdateOtherUi();
    
    /**
     * @brief Internal handler called before setup (calls user setup methods)
     */
    virtual void doPreSetup();
    
    /**
     * @brief Internal setup handler (calls onSetup)
     * @return Setup result code (0 for success)
     */
    virtual int doSetup();
    
    /**
     * @brief Internal handler called after setup completes
     */
    virtual void doPostSetup();
    
    /**
     * @brief User-overridable callback for keyboard events
     * @param key GLFW key code
     * @param scancode Platform-specific scan code
     * @param action GLFW action (press, release, repeat)
     * @param mods Bitfield of modifier keys
     * @note Override this method in derived classes to handle keyboard input
     */
    virtual void onKey(int key, int scancode, int action, int mods);
    
    /**
     * @brief User-overridable callback for mouse movement
     * @param x X coordinate of the cursor
     * @param y Y coordinate of the cursor
     * @note Override this method in derived classes to handle mouse movement
     */
    virtual void onMousePosition(double x, double y);
    
    /**
     * @brief User-overridable callback for mouse button events
     * @param button GLFW mouse button code
     * @param action GLFW action (press or release)
     * @param mods Bitfield of modifier keys
     * @note Override this method in derived classes to handle mouse clicks
     */
    virtual void onMouseButton(int button, int action, int mods);
    
    /**
     * @brief User-overridable callback for window resize events
     * @param width New width in pixels
     * @param height New height in pixels
     * @note Override this method in derived classes to handle window resizing
     */
    virtual void onResize(int width, int height);
    
    /**
     * @brief User-overridable callback for frame updates
     * @note Override this method in derived classes to update application state each frame
     */
    virtual void onUpdate();
    
    /**
     * @brief User-overridable callback for scene rendering
     * @note Override this method in derived classes to render the 3D scene
     */
    virtual void onDraw();
    
    /**
     * @brief User-overridable callback for UI rendering
     * @note Override this method in derived classes to render UI elements
     */
    virtual void onDrawUi();
    
    /**
     * @brief User-overridable callback called after rendering completes
     * @note Override this method in derived classes for post-rendering tasks
     */
    virtual void onDrawComplete();
    
    /**
     * @brief User-overridable callback for updating other UI elements
     * @note Override this method in derived classes to update non-rendering UI state
     */
    virtual void onUpdateOtherUi();
    
    /**
     * @brief User-overridable callback for initialization
     * @return Setup result code (0 for success, non-zero for errors)
     * @note Override this method in derived classes to perform initialization tasks
     */
    virtual int onSetup();
};

/**
 * @typedef GLFWWindowPtr
 * @brief Shared pointer type alias for GLFWWindow
 * @note Preferred way to manage GLFWWindow instances for automatic memory management
 */
typedef std::shared_ptr<GLFWWindow> GLFWWindowPtr;

}; // namespace ivfui
