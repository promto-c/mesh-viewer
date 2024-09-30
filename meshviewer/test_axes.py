import sys
import enum
import numpy as np
import pymeshlab
from PyQt5 import QtWidgets, QtGui, QtCore
from OpenGL import GL

class RenderMode(enum.Enum):
    FACE = enum.auto()
    WIREFRAME = enum.auto()
    HIDDEN_LINE = enum.auto()
    POINT = enum.auto()

class Drawable:
    def initialize(self):
        """Initialize OpenGL buffers and other resources."""
        raise NotImplementedError

    def render(self):
        """Render the object using the given shader program and transformation matrices."""
        raise NotImplementedError

class Axes(Drawable):
    def __init__(self, length=1000.0):
        """Initialize the Axes object.

        Args:
            length (float): The length of each axis line.
        """
        self.length = length
        self.vertices = np.array([
            # X axis (Red)
            -self.length, 0.0, 0.0,
             self.length, 0.0, 0.0,
            # Y axis (Green)
            0.0, -self.length, 0.0,
            0.0,  self.length, 0.0,
            # Z axis (Blue)
            0.0, 0.0, -self.length,
            0.0, 0.0,  self.length,
        ], dtype=np.float32)

        self.colors = np.array([
            # X axis color (Red)
            0.8, 0.4, 0.4,
            0.8, 0.4, 0.4,
            # Y axis color (Green)
            0.4, 0.7, 0.0,
            0.4, 0.7, 0.0,
            # Z axis color (Blue)
            0.2, 0.4, 0.7,
            0.2, 0.4, 0.7,
        ], dtype=np.float32)

        self.vao = None
        self.vbo_vertices = None
        self.vbo_colors = None

        self.initialize()

    def initialize(self):
        """Initialize OpenGL buffers and configure the Vertex Array Object (VAO).
        """
        # Generate and bind VAO
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        # Generate and bind VBO for vertex positions
        self.vbo_vertices = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo_vertices)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glEnableVertexAttribArray(0)  # Location 1: color

        # Generate and bind VBO for vertex colors
        self.vbo_colors = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo_colors)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.colors.nbytes, self.colors, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glEnableVertexAttribArray(1)  # Location 1: color

        # Unbind VAO and VBOs
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

    def render(self):
        """Render the axes using the provided shader program and transformation matrices.
        """
        # Bind the VAO containing the axes' VBOs
        GL.glBindVertexArray(self.vao)
        # Draw axes lines
        GL.glDrawArrays(GL.GL_LINES, 0, 6)
        # Unbind the VAO
        GL.glBindVertexArray(0)

class Grid(Drawable):
    def __init__(self, grid_spacing=1.0, grid_size=50):
        """Initialize the Grid object.

        Args:
            grid_spacing (float): The spacing between grid lines.
            grid_size (int): The number of grid lines in each direction from the origin.
        """
        self.grid_spacing = grid_spacing
        self.grid_size = grid_size
        self.vertices = self.generate_grid_vertices()
        self.color = np.array([0.4, 0.4, 0.4], dtype=np.float32)  # Gray color

        self.vao = None
        self.vbo_vertices = None
        self.vbo_colors = None

        self.initialize()

    def generate_grid_vertices(self):
        """Generate the vertex data for the grid lines.

        Returns:
            np.ndarray: An array of vertex positions for the grid lines.
        """
        grid_spacing = self.grid_spacing
        grid_size = self.grid_size

        grid_lines = []
        for i in range(-grid_size, grid_size + 1):
            if i == 0:
                continue  # Skip the axes to avoid overlapping lines

            # Lines parallel to the Z-axis (X constant)
            grid_lines.extend([i * grid_spacing, 0.0, -grid_size * grid_spacing])
            grid_lines.extend([i * grid_spacing, 0.0, grid_size * grid_spacing])

            # Lines parallel to the X-axis (Z constant)
            grid_lines.extend([-grid_size * grid_spacing, 0.0, i * grid_spacing])
            grid_lines.extend([grid_size * grid_spacing, 0.0, i * grid_spacing])

        return np.array(grid_lines, dtype=np.float32)

    def initialize(self):
        """Initialize OpenGL buffers and configure the Vertex Array Object (VAO).
        """
        # Create and bind VAO
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        # Create and bind VBO for vertex positions
        self.vbo_vertices = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo_vertices)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices.tobytes(), GL.GL_STATIC_DRAW)

        # Enable the position attribute and set the pointer
        GL.glEnableVertexAttribArray(0)  # Assuming the position attribute is at index 0
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        # Create and bind VBO for vertex colors
        colors = np.tile(self.color, (len(self.vertices) // 3, 1)).flatten().astype(np.float32)
        self.vbo_colors = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo_colors)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, colors.nbytes, colors.tobytes(), GL.GL_STATIC_DRAW)

        # Enable the color attribute and set the pointer
        GL.glEnableVertexAttribArray(1)  # Assuming the color attribute is at index 1
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        # Unbind the VAO to prevent unintended modifications
        GL.glBindVertexArray(0)

    def render(self):
        """Render the grid using the provided shader program and transformation matrices.

        Args:
            shader_program (int): The OpenGL shader program ID to use for rendering.
            mvp_matrix (np.ndarray): The 4x4 Model-View-Projection matrix.
            model_matrix (np.ndarray): The 4x4 Model matrix.
            camera_position (np.ndarray): The position of the camera in world space.
        """
        # Bind the VAO containing the grid's VBOs
        GL.glBindVertexArray(self.vao)
        # Draw the grid lines
        GL.glDrawArrays(GL.GL_LINES, 0, len(self.vertices) // 3)
        # Unbind the VAO
        GL.glBindVertexArray(0)

class GLWidget(QtWidgets.QOpenGLWidget):
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
        self.translation = QtGui.QVector3D(0.0, 0.0, 0.0)
        self.render_mode = RenderMode.FACE  # Default render mode

        # Initialize visibility flags
        self.show_axes = True
        self.show_grid = True

        # Variables for the 3D model
        self.model_vbo_vertices = None
        self.model_vbo_normals = None
        self.model_ebo = None
        self.model_vao = None
        self.model_vertex_count = 0
        self.model_loaded = False

        # Enable multi-sampling for anti-aliasing
        fmt = QtGui.QSurfaceFormat()
        fmt.setSamples(4)
        self.setFormat(fmt)

    def initializeGL(self):
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_MULTISAMPLE)

        # Compile shaders for axes and grid
        self.program = QtGui.QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QtGui.QOpenGLShader.Vertex, vertex_shader_source)
        self.program.addShaderFromSourceCode(QtGui.QOpenGLShader.Fragment, fragment_shader_source)
        self.program.link()

        # Compile shaders for model rendering
        self.program_model = QtGui.QOpenGLShaderProgram()
        self.program_model.addShaderFromSourceCode(QtGui.QOpenGLShader.Vertex, model_vertex_shader_source)
        self.program_model.addShaderFromSourceCode(QtGui.QOpenGLShader.Fragment, model_fragment_shader_source)
        self.program_model.link()

        # Initialize drawable objects
        self.axes = Axes()
        self.grid = Grid()

        # Load a model (replace with the path to your model file)
        self.load_model('example_models/cat_cartoon.glb')

    def load_model(self, file_path):
        # Ensure pymeshlab is imported
        try:
            import pymeshlab
        except ImportError:
            print("PyMeshLab is required for model loading. Please install it via pip.")
            return

        # Load the mesh using PyMeshLab
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(file_path)
        
        # Compute normals unconditionally
        mesh = ms.current_mesh()

        # Get vertex positions and faces
        vertices = np.array(mesh.vertex_matrix(), dtype=np.float32)
        faces = np.array(mesh.face_matrix(), dtype=np.uint32)
        indices = faces.flatten()
        normals = np.array(mesh.vertex_normal_matrix(), dtype=np.float32)

        # Create VBOs for vertices and normals
        self.model_vbo_vertices = QtGui.QOpenGLBuffer(QtGui.QOpenGLBuffer.VertexBuffer)
        self.model_vbo_vertices.create()
        self.model_vbo_vertices.bind()
        self.model_vbo_vertices.allocate(vertices.tobytes(), vertices.nbytes)
        self.model_vbo_vertices.release()

        self.model_vbo_normals = QtGui.QOpenGLBuffer(QtGui.QOpenGLBuffer.VertexBuffer)
        self.model_vbo_normals.create()
        self.model_vbo_normals.bind()
        self.model_vbo_normals.allocate(normals.tobytes(), normals.nbytes)
        self.model_vbo_normals.release()

        # Create EBO for indices
        self.model_ebo = QtGui.QOpenGLBuffer(QtGui.QOpenGLBuffer.IndexBuffer)
        self.model_ebo.create()
        self.model_ebo.bind()
        self.model_ebo.allocate(indices.tobytes(), indices.nbytes)
        self.model_ebo.release()

        # Create VAO for the model
        self.model_vao = QtGui.QOpenGLVertexArrayObject()
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

    def set_show_axes(self, show: bool):
        """
        Set the visibility of the Axes.

        Args:
            show (bool): True to show Axes, False to hide.
        """
        self.show_axes = show
        self.update()

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
        self.program.release()

        # Render axes if enabled
        if self.show_axes:
            self.program.bind()
            self.axes.render()
            self.grid.render()
            self.program.release()

        # Render the model if loaded
        if self.model_loaded:
            mvp_matrix_model = self.get_mvp_matrix()
            model_matrix_model = self.get_model_matrix()
            normal_matrix = model_matrix_model.normalMatrix()
            camera_position_model = self.get_camera_position()

            self.program_model.bind()
            self.program_model.setUniformValue('mvp_matrix', mvp_matrix_model)
            self.program_model.setUniformValue('model_matrix', model_matrix_model)
            self.program_model.setUniformValue('normal_matrix', normal_matrix)
            self.program_model.setUniformValue('light_position', QtGui.QVector3D(10.0, 10.0, 10.0))
            self.program_model.setUniformValue('view_position', camera_position_model)
            self.program_model.setUniformValue('light_color', QtGui.QVector3D(1.0, 1.0, 1.0))
            self.program_model.setUniformValue('object_color', QtGui.QVector3D(0.8, 0.5, 0.3))

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

    def get_mvp_matrix(self):
        mvp = QtGui.QMatrix4x4()
        aspect_ratio = self.width() / self.height() if self.height() != 0 else 1.0
        mvp.perspective(45.0, aspect_ratio, 0.1, 10000.0)
        mvp.lookAt(self.get_camera_position(), QtGui.QVector3D(0, 0, 0), QtGui.QVector3D(0, 1, 0))
        mvp.rotate(self.rotation_x, 1, 0, 0)
        mvp.rotate(self.rotation_y, 0, 1, 0)
        return mvp

    def get_model_matrix(self):
        model = QtGui.QMatrix4x4()
        model.setToIdentity()
        model.translate(self.translation)
        return model

    def get_camera_position(self):
        # Position the camera based on zoom level
        base_distance = 10.0  # Base distance from the origin
        distance = base_distance / self.zoom_level  # Adjust distance based on zoom level
        return QtGui.QVector3D(distance, distance, distance)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.last_pos is None:
            self.last_pos = event.pos()
            return

        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()

        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            # Rotate
            self.rotation_x += dy * 0.5  # Sensitivity factor
            self.rotation_y += dx * 0.5

            # Add limits to rotation_angle_x to prevent flipping over
            self.rotation_x = max(min(self.rotation_x, 90), -90)

        if event.buttons() & QtCore.Qt.MouseButton.MiddleButton:
            # Translate
            self.translation.setX(self.translation.x() + dx * 0.01)  # Adjust factors as needed
            self.translation.setY(self.translation.y() - dy * 0.01)
        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        # Implement zoom functionality
        delta = event.angleDelta().y() / 120  # 120 units per scroll
        zoom_factor = 0.1
        self.zoom_level += delta * zoom_factor
        self.zoom_level = max(0.1, self.zoom_level)  # Prevent zooming too close

        # No need to update the grid based on zoom level anymore
        self.update()


vertex_shader_source = """
#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 color; // Added color attribute

uniform mat4 mvp_matrix;
uniform mat4 model_matrix;
uniform vec3 camera_position;

out vec3 frag_color;
out vec3 frag_world_position;

void main()
{
    vec4 world_position = model_matrix * vec4(position, 1.0);
    frag_world_position = world_position.xyz;
    frag_color = color;
    gl_Position = mvp_matrix * vec4(position, 1.0);
}
"""

fragment_shader_source = """
#version 330 core
in vec3 frag_color; // Received color from vertex shader
in vec3 frag_world_position;
out vec4 fragColor;

uniform vec3 camera_position;

void main()
{
    float distance_to_camera = length(frag_world_position - camera_position);

    // Apply color gradient based on distance
    float gradient_factor = distance_to_camera / 100.0;  // Adjust denominator to control gradient spread
    gradient_factor = clamp(gradient_factor, 0.0, 1.0);

    vec3 gradient_color = mix(frag_color, vec3(0.0, 0.0, 0.0), gradient_factor);  // Transition from base color to black

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

        # Add UI elements for changing render modes and toggling Axes/Grid
        self.create_ui()

    def create_ui(self):
        toolbar = QtWidgets.QToolBar("Main Toolbar")
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

        toolbar.addSeparator()

        # Add toggle for Axes
        self.axes_checkbox = QtWidgets.QCheckBox("Show Axes")
        self.axes_checkbox.setChecked(True)
        self.axes_checkbox.stateChanged.connect(self.toggle_axes)
        toolbar.addWidget(self.axes_checkbox)

    def toggle_axes(self, state):
        """
        Toggle the visibility of Axes based on checkbox state.
        """
        show = state == QtCore.Qt.Checked
        self.gl_widget.set_show_axes(show)


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
