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
 * @brief A wrapper class for GLFW window management with OpenGL rendering capabilities
 * 
 * This class provides a high-level interface for creating and managing GLFW windows,
 * handling user input (keyboard and mouse), and providing OpenGL rendering context.
 * It supports virtual methods for customizable event handling and drawing operations.
 * 
 * The class manages window properties such as size, title, and various input states.
 * It also provides timing information for frame rate calculations and performance monitoring.
 * 
 * @note This class is designed to be inherited for custom window implementations
 * @see GLFW documentation for underlying window management details
 */
class GLFWWindow {
private:
    /// @brief Pointer to the GLFW window instance
    GLFWwindow *m_window;       
    /// @brief Pointer to shared GLFW window for OpenGL context sharing
    GLFWwindow *m_sharedWindow;
    /// @brief Pointer to the monitor for fullscreen mode (nullptr for windowed mode)
    GLFWmonitor *m_monitor;
    /// @brief Current window dimensions
    int m_width, m_height;
    /// @brief Window title string
    std::string m_title;
    /// @brief Current mouse button being pressed/released
    int m_mouseButton;
    /// @brief Current mouse button action (press/release)
    int m_mouseAction;
    /// @brief Mouse button modifier keys state
    int m_mouseMods;
    /// @brief Current mouse X coordinate
    int m_mouseX;
    /// @brief Current mouse Y coordinate
    int m_mouseY;
    /// @brief State of shift key (pressed/released)
    bool m_shiftDown;
    /// @brief State of control key (pressed/released)
    bool m_ctrlDown;
    /// @brief State of alt key (pressed/released)
    bool m_altDown;
    /// @brief Whether ESC key should quit the application
    bool m_escQuit;
    /// @brief Whether the window is enabled for input processing
    bool m_enabled;
    /// @brief Whether setup has been run
    bool m_runSetup;
    /// @brief Currently pressed key code
    int m_currentKey;
    /// @brief Mutex for thread-safe operations
    std::mutex m_mutex;
    /// @brief Previous frame timestamp
    double m_t0;
    /// @brief Current frame timestamp
    double m_t1;
    /// @brief Time taken for the last frame
    double m_frameTime;
    /// @brief Total number of frames rendered
    int m_frameCount;
    /// @brief Last error code that occurred
    int m_lastError;
    /// @brief Shared pointer to UI renderer instance
    UiRendererPtr m_uiRenderer;

public:
    /**
     * @brief Constructs a new GLFWWindow instance
     * @param width Initial window width in pixels
     * @param height Initial window height in pixels
     * @param title Window title string
     * @param monitor Monitor for fullscreen mode (nullptr for windowed mode)
     * @param shared Window whose context to share (nullptr for no sharing)
     * @throws std::runtime_error if window creation fails
     */
    GLFWWindow(int width, int height, const std::string title, GLFWmonitor *monitor = nullptr,
               GLFWwindow *shared = nullptr);

    /**
     * @brief Virtual destructor that properly cleans up GLFW resources
     * @note Automatically calls destroy() if the window hasn't been destroyed yet
     */
    virtual ~GLFWWindow();

    /**
     * @brief Creates a shared pointer to a new GLFWWindow instance
     * @param width Initial window width in pixels
     * @param height Initial window height in pixels
     * @param title Window title string
     * @param monitor Monitor for fullscreen mode (nullptr for windowed mode)
     * @param shared Window whose context to share (nullptr for no sharing)
     * @return std::shared_ptr<GLFWWindow> Shared pointer to the created window
     * @note Preferred method for creating GLFWWindow instances
     */
    static std::shared_ptr<GLFWWindow> create(int width, int height, const std::string title,
                                              GLFWmonitor *monitor = nullptr, GLFWwindow *shared = nullptr);

    /**
     * @brief Makes this window's OpenGL context current for the calling thread
     * @note Required before any OpenGL calls
     */
    void makeCurrent();

    /**
     * @brief Checks if the user has requested to close the window
     * @return bool True if window should close, false otherwise
     */
    bool isClosing();

    /**
     * @brief Sets the window close flag to request closure
     */
    void close();

    /**
     * @brief Swaps the front and back framebuffers
     * @note Call this at the end of each frame to display rendered content
     */
    void swapBuffers();

    /**
     * @brief Destroys the GLFW window and releases resources
     * @warning Window becomes unusable after calling this method
     */
    void destroy();

    /**
     * @brief Gets the current window width
     * @return int Current window width in pixels
     */
    int width();

    /**
     * @brief Gets the current window height
     * @return int Current window height in pixels
     */
    int height();

    /**
     * @brief Gets the current window dimensions by reference
     * @param[out] width Reference to store window width
     * @param[out] height Reference to store window height
     */
    void getSize(int &width, int &height);

    /**
     * @brief Sets the window icon from an image file
     * @param filename Path to the icon image file
     * @note Supports common image formats (PNG, JPEG, etc.)
     */
    void setWindowIcon(const std::string filename);

    /**
     * @brief Maximizes the window to fill the screen
     */
    void maximize();

    /**
     * @brief Enables input processing for this window
     */
    void enable();

    /**
     * @brief Disables input processing for this window
     */
    void disable();

    /**
     * @brief Checks if input processing is enabled
     * @return bool True if enabled, false if disabled
     */
    bool isEnabled();

    /**
     * @brief Performs the main drawing operations
     * @note Calls virtual draw methods in sequence
     */
    void draw();

    /**
     * @brief Draws the main scene content
     * @note Override doDrawScene() to customize scene rendering
     */
    void drawScene();

    /**
     * @brief Gets a pointer to the underlying GLFW window
     * @return GLFWwindow* Pointer to the GLFW window instance
     * @warning Use with caution - direct GLFW manipulation may break class state
     */
    GLFWwindow *ref();

    /**
     * @brief Gets the current mouse button that was pressed or released
     * @return int GLFW mouse button code (GLFW_MOUSE_BUTTON_*)
     */
    int mouseButton();

    /**
     * @brief Gets the current mouse button action
     * @return int GLFW action code (GLFW_PRESS, GLFW_RELEASE)
     */
    int mouseAction();

    /**
     * @brief Gets the modifier keys state during mouse action
     * @return int Bitfield of GLFW modifier flags (GLFW_MOD_*)
     */
    int mouseMods();

    /**
     * @brief Gets the current mouse X coordinate
     * @return int Mouse X position in window coordinates
     */
    int mouseX();

    /**
     * @brief Gets the current mouse Y coordinate
     * @return int Mouse Y position in window coordinates
     */
    int mouseY();

    /**
     * @brief Checks if any mouse button is currently pressed
     * @return bool True if any mouse button is down, false otherwise
     */
    bool isAnyMouseButtonDown();

    /**
     * @brief Checks if the Shift key is currently pressed
     * @return bool True if Shift is pressed, false otherwise
     */
    bool isShiftDown();

    /**
     * @brief Checks if the Control key is currently pressed
     * @return bool True if Ctrl is pressed, false otherwise
     */
    bool isCtrlDown();

    /**
     * @brief Checks if the Alt key is currently pressed
     * @return bool True if Alt is pressed, false otherwise
     */
    bool isAltDown();

    /**
     * @brief Checks if ESC key should quit the application
     * @return bool True if ESC quits, false otherwise
     */
    bool useEscQuit();

    /**
     * @brief Sets whether ESC key should quit the application
     * @param flag True to enable ESC quit, false to disable
     */
    void setUseEscQuit(bool flag);

    /**
     * @brief Gets the last error code that occurred
     * @return int Error code (0 means no error)
     */
    int lastError() const;

    /**
     * @brief Clears the current error state
     */
    void clearError();

    /**
     * @brief Sets an error code
     * @param error Error code to set
     */
    void setError(int error);

    /**
     * @brief Gets the time taken to render the last frame
     * @return double Frame time in seconds
     */
    double frameTime() const;

    /**
     * @brief Gets the total number of frames rendered
     * @return int Total frame count since window creation
     */
    int frameCount() const;

    /**
     * @brief Gets the total elapsed time since window creation
     * @return double Elapsed time in seconds
     */
    double elapsedTime() const;

    /**
     * @brief Gets the UI renderer instance
     * @return UiRendererPtr Shared pointer to the UI renderer
     */
    UiRendererPtr uiRenderer() const { return m_uiRenderer; }

public:
    /**
     * @brief Internal keyboard event handler
     * @param key GLFW key code
     * @param scancode Platform-specific scancode
     * @param action GLFW action (GLFW_PRESS, GLFW_RELEASE, GLFW_REPEAT)
     * @param mods Modifier key flags
     * @note Called by GLFW callback, calls onKey() for user override
     */
    virtual void doKey(int key, int scancode, int action, int mods);

    /**
     * @brief Internal mouse position event handler
     * @param x Mouse X coordinate
     * @param y Mouse Y coordinate
     * @note Called by GLFW callback, calls onMousePosition() for user override
     */
    virtual void doMousePosition(double x, double y);

    /**
     * @brief Internal mouse button event handler
     * @param button GLFW mouse button code
     * @param action GLFW action (GLFW_PRESS, GLFW_RELEASE)
     * @param mods Modifier key flags
     * @note Called by GLFW callback, calls onMouseButton() for user override
     */
    virtual void doMouseButton(int button, int action, int mods);

    /**
     * @brief Internal window resize event handler
     * @param width New window width
     * @param height New window height
     * @note Called by GLFW callback, calls onResize() for user override
     */
    virtual void doResize(int width, int height);

    /**
     * @brief Internal update handler called each frame
     * @note Calls onUpdate() for user override
     */
    virtual void doUpdate();

    /**
     * @brief Internal drawing handler for main scene
     * @note Calls onDraw() for user override
     */
    virtual void doDraw();

    /**
     * @brief Internal drawing handler for UI elements
     * @note Calls onDrawUi() for user override
     */
    virtual void doDrawUi();

    /**
     * @brief Internal handler called after drawing is complete
     * @note Calls onDrawComplete() for user override
     */
    virtual void doDrawComplete();

    /**
     * @brief Internal handler for updating other UI elements
     * @note Calls onUpdateOtherUi() for user override
     */
    virtual void doUpdateOtherUi();

    /**
     * @brief Internal pre-setup handler
     * @note Override to perform operations before main setup
     */
    virtual void doPreSetup();

    /**
     * @brief Internal setup handler
     * @return int Setup result code (0 for success)
     * @note Override to perform custom initialization
     */
    virtual int doSetup();

    /**
     * @brief Internal post-setup handler
     * @note Override to perform operations after main setup
     */
    virtual void doPostSetup();

    /**
     * @brief User-overridable keyboard event handler
     * @param key GLFW key code
     * @param scancode Platform-specific scancode
     * @param action GLFW action (GLFW_PRESS, GLFW_RELEASE, GLFW_REPEAT)
     * @param mods Modifier key flags
     * @note Override this method to handle keyboard input in derived classes
     */
    virtual void onKey(int key, int scancode, int action, int mods);

    /**
     * @brief User-overridable mouse position event handler
     * @param x Mouse X coordinate
     * @param y Mouse Y coordinate
     * @note Override this method to handle mouse movement in derived classes
     */
    virtual void onMousePosition(double x, double y);

    /**
     * @brief User-overridable mouse button event handler
     * @param button GLFW mouse button code
     * @param action GLFW action (GLFW_PRESS, GLFW_RELEASE)
     * @param mods Modifier key flags
     * @note Override this method to handle mouse clicks in derived classes
     */
    virtual void onMouseButton(int button, int action, int mods);

    /**
     * @brief User-overridable window resize event handler
     * @param width New window width
     * @param height New window height
     * @note Override this method to handle window resizing in derived classes
     */
    virtual void onResize(int width, int height);

    /**
     * @brief User-overridable update handler called each frame
     * @note Override this method to implement custom update logic
     */
    virtual void onUpdate();

    /**
     * @brief User-overridable drawing handler for main scene
     * @note Override this method to implement custom rendering
     */
    virtual void onDraw();

    /**
     * @brief User-overridable drawing handler for UI elements
     * @note Override this method to implement custom UI rendering
     */
    virtual void onDrawUi();

    /**
     * @brief User-overridable handler called after drawing is complete
     * @note Override this method for post-rendering operations
     */
    virtual void onDrawComplete();

    /**
     * @brief User-overridable handler for updating other UI elements
     * @note Override this method for additional UI update logic
     */
    virtual void onUpdateOtherUi();

    /**
     * @brief User-overridable setup handler
     * @return int Setup result code (0 for success, non-zero for error)
     * @note Override this method to implement custom initialization logic
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
