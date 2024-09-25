import sys
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtGui import (
    QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLVertexArrayObject,
    QOpenGLShader, QMatrix4x4, QVector3D, QSurfaceFormat
)
from OpenGL import GL

class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.rotation_x = 0
        self.rotation_y = 0
        self.last_pos = None
        self.zoom_level = 1.0  # Initial zoom level

        # Enable multi-sampling for anti-aliasing
        fmt = QSurfaceFormat()
        fmt.setSamples(4)
        self.setFormat(fmt)

    def initializeGL(self):
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_MULTISAMPLE)

        # Compile shaders
        self.program = QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QOpenGLShader.Vertex, vertex_shader_source)
        self.program.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment_shader_source)
        self.program.link()

        # Set up vertex data and buffers
        self.setup_axes_and_grid()

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        mvp_matrix = self.get_mvp_matrix()
        model_matrix = self.get_model_matrix()
        camera_position = self.get_camera_position()

        self.program.bind()
        self.program.setUniformValue('mvp_matrix', mvp_matrix)
        self.program.setUniformValue('model_matrix', model_matrix)
        self.program.setUniformValue('camera_position', camera_position)

        self.vao.bind()
        self.vbo.bind()

        self.program.enableAttributeArray(0)
        self.program.setAttributeBuffer(0, GL.GL_FLOAT, 0, 3, 0)

        # Draw axes
        colors = [QVector3D(0.8, 0.4, 0.4), QVector3D(0.4, 0.8, 0), QVector3D(0.2, 0.4, 1)]
        axis_segments = [2, 2, 2]  # Each axis has 2 vertices (start and end)
        offset = 0
        for i in range(3):
            self.program.setUniformValue('color', colors[i])
            GL.glDrawArrays(GL.GL_LINES, offset, axis_segments[i])
            offset += axis_segments[i]

        # Draw grid
        grid_start = offset
        grid_count = len(self.grid_vertices) // 3
        self.program.setUniformValue('color', QVector3D(0.6, 0.6, 0.6))  # Base color (will be modified in shader)
        GL.glDrawArrays(GL.GL_LINES, grid_start, grid_count)

        self.vbo.release()
        self.vao.release()
        self.program.release()

    def setup_axes_and_grid(self):
        # Define axes as long lines
        axis_length = 1000.0  # Large value to simulate infinite axes
        axes_vertices = np.array([
            # X axis
            -axis_length, 0.0, 0.0,
             axis_length, 0.0, 0.0,
            # Y axis
            0.0, -axis_length, 0.0,
            0.0,  axis_length, 0.0,
            # Z axis
            0.0, 0.0, -axis_length,
            0.0, 0.0,  axis_length,
        ], dtype=np.float32)

        # Generate initial grid vertices
        self.generate_grid_vertices()

        # Combine axes and grid vertices
        self.vertices = np.concatenate((axes_vertices, self.grid_vertices))

        # Create Vertex Buffer Object (VBO)
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.vbo.create()

        # Create Vertex Array Object (VAO)
        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()

        self.update_vertex_buffer()

    def generate_grid_vertices(self):
        # Grid density adjusts based on zoom level
        base_grid_spacing = 1.0  # Base spacing
        zoom_factor = self.zoom_level

        # Adjust grid spacing based on zoom level
        if zoom_factor < 0.1:
            zoom_factor = 0.1  # Prevent too fine grid
        grid_spacing = base_grid_spacing / zoom_factor

        # Limit grid size to prevent performance issues
        grid_size = int(50 * zoom_factor)
        grid_size = min(max(grid_size, 10), 1000)  # Keep grid size between 10 and 1000

        grid_lines = []
        for i in range(-grid_size, grid_size + 1):
            # Skip lines that are on the axes (where X or Z is 0)
            if i == 0:
                continue

            # Lines parallel to Z-axis (X constant)
            grid_lines.extend([i * grid_spacing, 0.0, -grid_size * grid_spacing])
            grid_lines.extend([i * grid_spacing, 0.0, grid_size * grid_spacing])

            # Lines parallel to X-axis (Z constant)
            grid_lines.extend([-grid_size * grid_spacing, 0.0, i * grid_spacing])
            grid_lines.extend([grid_size * grid_spacing, 0.0, i * grid_spacing])

        self.grid_vertices = np.array(grid_lines, dtype=np.float32)

    def update_vertex_buffer(self):
        # Combine axes and grid vertices
        axes_count = 6  # Number of vertices in axes
        self.vertices = np.concatenate((self.vertices[:axes_count*3], self.grid_vertices))

        # Update VBO
        self.vbo.bind()
        self.vbo.allocate(self.vertices.tobytes(), self.vertices.nbytes)
        self.vbo.release()

    def get_mvp_matrix(self):
        mvp = QMatrix4x4()
        aspect_ratio = self.width() / self.height() if self.height() != 0 else 1.0
        mvp.perspective(45.0, aspect_ratio, 0.1, 10000.0)
        mvp.lookAt(self.get_camera_position(), QVector3D(0, 0, 0), QVector3D(0, 1, 0))
        mvp.rotate(self.rotation_x, 1, 0, 0)
        mvp.rotate(self.rotation_y, 0, 1, 0)
        return mvp

    def get_model_matrix(self):
        model = QMatrix4x4()
        model.setToIdentity()
        return model

    def get_camera_position(self):
        # Position the camera based on zoom level
        base_distance = 10.0  # Base distance from the origin
        distance = base_distance / self.zoom_level  # Adjust distance based on zoom level
        return QVector3D(distance, distance, distance)

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            self.last_pos = event.pos()
            return

        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()

        # Update rotation angles based on mouse movement
        self.rotation_x += dy * 0.5  # Sensitivity factor
        self.rotation_y += dx * 0.5

        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        # Implement zoom functionality
        delta = event.angleDelta().y() / 120  # 120 units per scroll
        zoom_factor = 0.1
        self.zoom_level += delta * zoom_factor
        self.zoom_level = max(0.1, self.zoom_level)  # Prevent zooming too close

        # Regenerate grid with new density
        self.update_vertex_buffer()
        self.update()

vertex_shader_source = """
#version 330 core
layout(location = 0) in vec3 position;

uniform mat4 mvp_matrix;
uniform mat4 model_matrix;
uniform vec3 camera_position;

out vec3 frag_world_position;

void main()
{
    vec4 world_position = model_matrix * vec4(position, 1.0);
    frag_world_position = world_position.xyz;
    gl_Position = mvp_matrix * vec4(position, 1.0);
}
"""

fragment_shader_source = """
#version 330 core
in vec3 frag_world_position;
out vec4 fragColor;

uniform vec3 color;
uniform vec3 camera_position;

void main()
{
    float distance_to_camera = length(frag_world_position - camera_position);

    // Apply color gradient based on distance
    float gradient_factor = distance_to_camera / 100.0;  // Adjust denominator to control gradient spread
    gradient_factor = clamp(gradient_factor, 0.0, 1.0);

    vec3 gradient_color = mix(color, vec3(0.0, 0.0, 0.0), gradient_factor);  // Transition from base color to blue

    // Adjust opacity based on distance (optional)
    float opacity = 1.0 - gradient_factor * 0.9;  // Fade out with distance
    opacity = clamp(opacity, 0.1, 1.0);

    fragColor = vec4(gradient_color, opacity);
}
"""

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Modern 3D Viewer')
        self.setGeometry(100, 100, 1200, 800)
        self.gl_widget = GLWidget(self)
        self.setCentralWidget(self.gl_widget)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
