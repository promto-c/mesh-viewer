import sys
import enum
import numpy as np
import pymeshlab
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtGui import (
    QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLVertexArrayObject,
    QOpenGLShader, QMatrix4x4, QVector3D, QSurfaceFormat
)
from OpenGL import GL

class RenderMode(enum.Enum):
    FACE = enum.auto()
    WIREFRAME = enum.auto()
    HIDDEN_LINE = enum.auto()
    POINT = enum.auto()

class GLWidget(QOpenGLWidget):
    RENDER_MODE_TO_GL_POLYGON = {
        RenderMode.WIREFRAME: GL.GL_LINE,
        RenderMode.FACE: GL.GL_FILL,
        RenderMode.POINT: GL.GL_POINT,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.last_pos = None
        self.zoom_level = 1.0  # Initial zoom level
        self.translation = QVector3D(0.0, 0.0, 0.0)
        self.render_mode = RenderMode.FACE  # Default render mode
        self.middle_button_pressed = False

        # Variables for the 3D model
        self.model_vbo_vertices = None
        self.model_vbo_normals = None
        self.model_ebo = None
        self.model_vao = None
        self.model_vertex_count = 0
        self.model_loaded = False

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

        # Compile shaders for axes and grid
        self.program = QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QOpenGLShader.Vertex, vertex_shader_source)
        self.program.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment_shader_source)
        self.program.link()

        # Compile shaders for model rendering
        self.program_model = QOpenGLShaderProgram()
        self.program_model.addShaderFromSourceCode(QOpenGLShader.Vertex, model_vertex_shader_source)
        self.program_model.addShaderFromSourceCode(QOpenGLShader.Fragment, model_fragment_shader_source)
        self.program_model.link()

        # Set up vertex data and buffers for axes and grid
        self.setup_axes_and_grid()

        # Load a model (replace with the path to your model file)
        self.load_model('example_models/cat.glb')

    def load_model(self, file_path):
        # Load the mesh using PyMeshLab
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(file_path)
        
        # Compute normals unconditionally
        # ms.apply_filter('compute_normals_for_point_sets')
        mesh = ms.current_mesh()

        # Get vertex positions and faces
        vertices = np.array(mesh.vertex_matrix(), dtype=np.float32)
        faces = np.array(mesh.face_matrix(), dtype=np.uint32)
        indices = faces.flatten()
        normals = np.array(mesh.vertex_normal_matrix(), dtype=np.float32)

        # Create VBOs for vertices and normals
        self.model_vbo_vertices = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.model_vbo_vertices.create()
        self.model_vbo_vertices.bind()
        self.model_vbo_vertices.allocate(vertices.tobytes(), vertices.nbytes)
        self.model_vbo_vertices.release()

        self.model_vbo_normals = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.model_vbo_normals.create()
        self.model_vbo_normals.bind()
        self.model_vbo_normals.allocate(normals.tobytes(), normals.nbytes)
        self.model_vbo_normals.release()

        # Create EBO for indices
        self.model_ebo = QOpenGLBuffer(QOpenGLBuffer.IndexBuffer)
        self.model_ebo.create()
        self.model_ebo.bind()
        self.model_ebo.allocate(indices.tobytes(), indices.nbytes)
        self.model_ebo.release()

        # Create VAO for the model
        self.model_vao = QOpenGLVertexArrayObject()
        self.model_vao.create()
        self.model_vao.bind()

        # Bind VBOs and set attribute pointers
        self.program_model.bind()
        self.model_vbo_vertices.bind()
        self.program_model.enableAttributeArray(0)
        self.program_model.setAttributeBuffer(0, GL.GL_FLOAT, 0, 3)
        self.model_vbo_vertices.release()

        self.model_vbo_normals.bind()
        self.program_model.enableAttributeArray(1)
        self.program_model.setAttributeBuffer(1, GL.GL_FLOAT, 0, 3)
        self.model_vbo_normals.release()

        self.model_ebo.bind()
        self.model_vao.release()

        self.model_vertex_count = indices.size
        self.model_loaded = True

    def set_render_mode(self, mode):
        self.render_mode = mode
        self.update()

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        mvp_matrix = self.get_mvp_matrix()
        model_matrix = self.get_model_matrix()
        camera_position = self.get_camera_position()

        # Render axes and grid
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
        self.program.setUniformValue('color', QVector3D(0.4, 0.4, 0.4))
        GL.glDrawArrays(GL.GL_LINES, grid_start, grid_count)

        self.vbo.release()
        self.vao.release()
        self.program.release()

        # Render the model if loaded
        if self.model_loaded:
            mvp_matrix = self.get_mvp_matrix()
            model_matrix = self.get_model_matrix()
            normal_matrix = model_matrix.normalMatrix()
            camera_position = self.get_camera_position()

            self.program_model.bind()
            self.program_model.setUniformValue('mvp_matrix', mvp_matrix)
            self.program_model.setUniformValue('model_matrix', model_matrix)
            self.program_model.setUniformValue('normal_matrix', normal_matrix)
            self.program_model.setUniformValue('light_position', QVector3D(10.0, 10.0, 10.0))
            self.program_model.setUniformValue('view_position', camera_position)
            self.program_model.setUniformValue('light_color', QVector3D(1.0, 1.0, 1.0))
            self.program_model.setUniformValue('object_color', QVector3D(0.8, 0.5, 0.3))  # Adjust as needed

            self.model_vao.bind()

            if self.render_mode == RenderMode.HIDDEN_LINE:
                # Enable face culling
                GL.glEnable(GL.GL_CULL_FACE)
                GL.glCullFace(GL.GL_BACK)  # Cull back faces

                # Set polygon mode to line for front faces
                GL.glPolygonMode(GL.GL_FRONT, GL.GL_LINE)

                # Optionally, set line width
                GL.glLineWidth(1.0)

                # Draw the model
                GL.glDrawElements(GL.GL_TRIANGLES, self.model_vertex_count, GL.GL_UNSIGNED_INT, None)

                # Reset polygon mode and disable face culling
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                GL.glDisable(GL.GL_CULL_FACE)
            else:
                # Render in the selected mode
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, self.RENDER_MODE_TO_GL_POLYGON[self.render_mode])
                GL.glDrawElements(GL.GL_TRIANGLES, self.model_vertex_count, GL.GL_UNSIGNED_INT, None)
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

            self.model_vao.release()
            self.program_model.release()

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
        model.translate(self.translation)
        return model

    def get_camera_position(self):
        # Position the camera based on zoom level
        base_distance = 10.0  # Base distance from the origin
        distance = base_distance / self.zoom_level  # Adjust distance based on zoom level
        return QVector3D(distance, distance, distance)

    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        if event.button() == QtCore.Qt.MiddleButton:
            self.middle_button_pressed = True

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.middle_button_pressed = False

    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            self.last_pos = event.pos()
            return

        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()

        if event.buttons() == QtCore.Qt.LeftButton:
            # Rotate
            self.rotation_x += dy * 0.5  # Sensitivity factor
            self.rotation_y += dx * 0.5
        elif self.middle_button_pressed:
            # Translate
            self.translation.setX(self.translation.x() + dx * 0.01)  # Adjust factors as needed
            self.translation.setY(self.translation.y() - dy * 0.01)
        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        # Implement zoom functionality
        delta = event.angleDelta().y() / 120  # 120 units per scroll
        zoom_factor = 1.0
        self.zoom_level += delta * zoom_factor
        self.zoom_level = max(0.1, self.zoom_level)  # Prevent zooming too close

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

    vec3 gradient_color = mix(color, vec3(0.0, 0.0, 0.0), gradient_factor);  // Transition from base color to black

    // Adjust opacity based on distance
    float opacity = 1.0 - gradient_factor * 0.9;  // Fade out with distance
    opacity = clamp(opacity, 0.1, 1.0);

    fragColor = vec4(gradient_color, opacity);
}
"""

model_vertex_shader_source = """
#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;

uniform mat4 mvp_matrix;
uniform mat4 model_matrix;
uniform mat3 normal_matrix;

out vec3 frag_normal;
out vec3 frag_position;

void main()
{
    frag_position = vec3(model_matrix * vec4(position, 1.0));
    frag_normal = normalize(normal_matrix * normal);
    gl_Position = mvp_matrix * vec4(position, 1.0);
}
"""

model_fragment_shader_source = """
#version 330 core
in vec3 frag_normal;
in vec3 frag_position;

uniform vec3 light_position;
uniform vec3 view_position;
uniform vec3 light_color;
uniform vec3 object_color;

out vec4 fragColor;

void main()
{
    // Ambient lighting
    float ambient_strength = 0.2;
    vec3 ambient = ambient_strength * light_color;

    // Diffuse lighting
    vec3 norm = normalize(frag_normal);
    vec3 light_dir = normalize(light_position - frag_position);
    float diff = max(dot(norm, light_dir), 0.0);
    vec3 diffuse = diff * light_color;

    // Specular lighting
    float specular_strength = 0.5;
    vec3 view_dir = normalize(view_position - frag_position);
    vec3 reflect_dir = reflect(-light_dir, norm);
    float spec = pow(max(dot(view_dir, reflect_dir), 0.0), 32);
    vec3 specular = specular_strength * spec * light_color;

    vec3 result = (ambient + diffuse + specular) * object_color;
    fragColor = vec4(result, 1.0);
}
"""

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('3D Viewer')
        self.setGeometry(100, 100, 1200, 800)
        self.gl_widget = GLWidget(self)
        self.setCentralWidget(self.gl_widget)

        # Add UI elements for changing render modes
        self.create_ui()

    def create_ui(self):
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)

        # Render mode actions
        face_action = QtWidgets.QAction('Face Mode', self)
        face_action.triggered.connect(lambda: self.gl_widget.set_render_mode(RenderMode.FACE))
        toolbar.addAction(face_action)

        wireframe_action = QtWidgets.QAction('Wireframe Mode', self)
        wireframe_action.triggered.connect(lambda: self.gl_widget.set_render_mode(RenderMode.WIREFRAME))
        toolbar.addAction(wireframe_action)

        point_action = QtWidgets.QAction('Point Mode', self)
        point_action.triggered.connect(lambda: self.gl_widget.set_render_mode(RenderMode.POINT))
        toolbar.addAction(point_action)

        hidden_line_action = QtWidgets.QAction('Hidden-Line Mode', self)
        hidden_line_action.triggered.connect(lambda: self.gl_widget.set_render_mode(RenderMode.HIDDEN_LINE))
        toolbar.addAction(hidden_line_action)


if __name__ == '__main__':
    # Set up QSurfaceFormat for antialiasing
    format = QtGui.QSurfaceFormat()
    format.setSamples(4)
    format.setDepthBufferSize(24)
    QtGui.QSurfaceFormat.setDefaultFormat(format)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
