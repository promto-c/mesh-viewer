import sys
import enum
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from OpenGL import GL

try:
    from pymeshlab import MeshSet, Mesh
except:
    class MeshSet(list):
        ...
        def load_new_mesh(self, file_path):
            ...

        def add_mesh(self, mesh):
            self.append(mesh)

        # NOTE:
        def get_bounding_box(self):
            min_x, max_x, min_y, max_y, min_z, max_z = float('inf'), float('-inf'), float('inf'), float('-inf'), float('inf'), float('-inf')

            for mesh in self.meshes:  # Assuming the MeshSet stores a list of Mesh objects in self.meshes
                mesh_min_x, mesh_max_x, mesh_min_y, mesh_max_y, mesh_min_z, mesh_max_z = mesh.get_bounding_box()

                # Update the overall bounding box
                min_x = min(min_x, mesh_min_x)
                max_x = max(max_x, mesh_max_x)
                min_y = min(min_y, mesh_min_y)
                max_y = max(max_y, mesh_max_y)
                min_z = min(min_z, mesh_min_z)
                max_z = max(max_z, mesh_max_z)

            return (min_x, max_x, min_y, max_y, min_z, max_z)

    class Mesh:
        ...

from meshviewer.shaders.shader import PhongShader, BlinnPhongShader, LambertianShader
from meshviewer.utils.mesh_io import load_mesh_from_npz, load_mesh_from_pickle

class RenderMode(enum.Enum):
    WIREFRAME = enum.auto()
    FACE = enum.auto()
    POINT = enum.auto()

class ObjectViewer(QtWidgets.QOpenGLWidget):

    RENDER_MODE_TO_GL_POLYGON = {
        RenderMode.WIREFRAME: GL.GL_LINE,
        RenderMode.FACE: GL.GL_FILL,
        RenderMode.POINT: GL.GL_POINT,
    }

    DEFAULT_BACKGROUND_COLOR = (0.2, 0.3, 0.3, 1.0)

    ROTATION_FACTOR = 0.5
    TRANSLATION_FACTOR = 0.01

    def __init__(self, parent=None, mode: RenderMode = RenderMode.WIREFRAME):
        super().__init__(parent)
        self.mesh_set = MeshSet()  # Initialize an empty MeshSet
        self.scale = 1.0
        self.last_mouse_position = None
        self.rotation_angle_x = 0.0
        self.rotation_angle_y = 0.0
        self.rotation_angle_z = 0.0
        self.translation_x = 0.0
        self.translation_y = 0.0
        self.translation_z = 0.0

        self.fov = 45.0

        self._middle_mouse_pressed = False
        self.mode = mode  # Default mode. Other values can be "wireframe" or "point"
        self.vaos = []  # List to store Vertex Array Objects for each mesh
        self.vertex_buffers = []  # List to store Vertex Buffer Objects for vertices
        self.normal_buffers = []  # List to store Normal Buffer Objects
        self.index_buffers = []  # List to store Element Buffer Objects for faces
        self.shader = None  # Placeholder for the PhongShader instance

        # Initialize bounding box corners
        self.min_point = (float('inf'), float('inf'), float('inf'))
        self.max_point = (float('-inf'), float('-inf'), float('-inf'))

        self.near_clip = 0.1
        self.far_clip = 1000

    def initializeGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        self.shader = PhongShader()  # Initialize PhongShader
        self.shader.create_shader_program()  # Compile and link shaders
        self.initBuffers()

    def set_mode(self, mode='wireframe'):
        self.mode = mode
        self.update()

    def addMesh(self, mesh_input):
        """
        Adds a mesh to the viewer. The mesh can be a single Mesh object or a MeshSet.
        
        Parameters:
            mesh (Mesh or MeshSet): The mesh or MeshSet to add.
        """
        if isinstance(mesh_input, MeshSet):
            for mesh in mesh_input:
                self._addSingleMesh(mesh)
        else:
            self._addSingleMesh(mesh_input)

    def _addSingleMesh(self, mesh):
        self.mesh_set.add_mesh(mesh)
        self.update()

    def initBuffers(self):
        # Initialize min and max points with opposite infinity values
        overall_min_point = np.array([np.inf, np.inf, np.inf])
        overall_max_point = np.array([-np.inf, -np.inf, -np.inf])

        for mesh in self.mesh_set:
            vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(vao)

            # Vertices
            vertices = np.array(mesh.vertex_matrix(), dtype='float32')
            vertex_buffer = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vertex_buffer)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)
            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glEnableVertexAttribArray(0)

            # Normals
            normals = np.array(mesh.vertex_normal_matrix(), dtype='float32')
            normal_buffer = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, normal_buffer)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, normals.nbytes, normals, GL.GL_STATIC_DRAW)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glEnableVertexAttribArray(1)

            # Faces
            faces = np.array(mesh.face_matrix().flatten(), dtype='uint32')
            index_buffer = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, index_buffer)
            GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, faces.nbytes, faces, GL.GL_STATIC_DRAW)

            # Store VAO and buffers
            self.vaos.append(vao)
            self.vertex_buffers.append(vertex_buffer)
            self.normal_buffers.append(normal_buffer)
            self.index_buffers.append(index_buffer)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
            GL.glBindVertexArray(0)

            # NOTE: WIP
            # Get bounding box
            bbox = mesh.bounding_box()
            min_point = np.array(bbox.min())
            max_point = np.array(bbox.max())

            # Update the overall bounding box
            overall_min_point = np.minimum(overall_min_point, min_point)
            overall_max_point = np.maximum(overall_max_point, max_point)

        self.min_point = tuple(overall_min_point.tolist())
        self.max_point = tuple(overall_max_point.tolist())

    def set_vertex_shader_uniform(self, view, projection, model):
        # Set matrix uniforms
        self.shader.set_uniform("model", model.data())
        self.shader.set_uniform("view", view.data())
        self.shader.set_uniform("projection", projection.data())

    def set_fragment_shader_uniform(self):
        # Set light and view positions
        self.shader.set_uniform("lightPos", (1.2, 1.0, 2.0))
        self.shader.set_uniform("viewPos", (0.0, 0.0, 0.0))
        # Set light and object colors
        self.shader.set_uniform("lightColor", (1.0, 1.0, 1.0))
        self.shader.set_uniform("objectColor", (1.0, 0.5, 0.31))
        # Set material properties
        self.shader.set_uniform("ambientStrength", 0.1)
        self.shader.set_uniform("specularStrength", 0.5)
        self.shader.set_uniform("shininess", 32.0)

    def setup_matrices(self):
        projection = QtGui.QMatrix4x4()
        projection.perspective(self.fov, self.width() / self.height(), self.near_clip, self.far_clip)

        view = QtGui.QMatrix4x4()
        view.translate(0, 0, -5.0)

        model = QtGui.QMatrix4x4()
        model.translate(self.translation_x, self.translation_y, self.translation_z)
        model.rotate(self.rotation_angle_x, 1, 0, 0)
        model.rotate(self.rotation_angle_y, 0, 1, 0)
        model.rotate(self.rotation_angle_z, 0, 0, 1)
        model.scale(self.scale)

        self.set_vertex_shader_uniform(view, projection, model)

    def render_meshes(self):
        # Default to GL_LINE if mode not found, though all modes should be covered
        gl_mode = self.RENDER_MODE_TO_GL_POLYGON.get(self.mode, GL.GL_LINE)

        for i, vao in enumerate(self.vaos):
            GL.glBindVertexArray(vao)
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, gl_mode)

            mesh = self.mesh_set[i]
            if self.mode == RenderMode.POINT:
                GL.glDrawArrays(GL.GL_POINTS, 0, mesh.vertex_number())
            else:
                GL.glDrawElements(GL.GL_TRIANGLES, mesh.face_number() * 3, GL.GL_UNSIGNED_INT, None)

        GL.glBindVertexArray(0)

    def clear_screen(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glClearColor(*self.DEFAULT_BACKGROUND_COLOR)

    def paintGL(self):
        self.clear_screen()

        # Activate the shader program
        self.shader.use()

        # Set matrix uniforms
        self.setup_matrices()
        # Set light and material properties
        self.set_fragment_shader_uniform()

        self.render_meshes()

        self.shader.release()

    def resizeGL(self, width, height):
        GL.glViewport(0, 0, width, max(1, height))

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Handles mouse wheel events to adjust camera properties for zooming and moving in 3D space.

        Zooming is achieved by adjusting the field of view (FOV), and moving the object closer or further
        away is done by changing the object's z-axis position. The Ctrl modifier key is used to switch between
        these modes.

        - Scrolling with Ctrl pressed adjusts the FOV, providing a zoom effect. A smaller FOV zooms in, making
        objects appear larger, while a larger FOV zooms out.
        - Scrolling without the Ctrl key adjusts the object's z-axis position, moving the object in or out.

        Args:
            event (QtGui.QWheelEvent):The event triggered by scrolling the mouse wheel.

        Usage:
            Scroll while pressing Ctrl to zoom in or out. This modifies `self.fov`.
            Scroll without pressing Ctrl to move the object in or out along the z-axis. This modifies `self.camera_z`.

        Both actions trigger a repaint by calling `self.update()`.
        """
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15  # Usually, one step is equal to a 15-degree angle.

        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            # Adjust the FOV for zooming
            self.fov += steps * -1.0  # Adjust zoom speed if necessary
            self.fov = max(10, min(120, self.fov))  # Constrain the FOV to reasonable limits
        else:
            # # Adjust the Z translation based on the steps. Change the value 10 to adjust translation speed.
            # self.translation_z += steps * 10
            # self.translation_z = max(-1000, min(1000, self.translation_z))

            # Set the scale factor and limit the zoom in/out.
            self.scale *= (1 + steps * 0.1)  # Change the 0.1 to adjust the zoom speed.
            self.scale = max(0.001, min(1000.0, self.scale))

        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self.last_mouse_position = event.pos()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.last_mouse_position:
            dx = event.x() - self.last_mouse_position.x()
            dy = event.y() - self.last_mouse_position.y()

            if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
                self.rotation_angle_x += dy * self.ROTATION_FACTOR
                self.rotation_angle_y += dx * self.ROTATION_FACTOR

                # Add limits to rotation_angle_x to prevent flipping over
                self.rotation_angle_x = max(min(self.rotation_angle_x, 90), -90)

            if event.buttons() & QtCore.Qt.MouseButton.MiddleButton:
                # Adjust translation base d on mouse movement
                self.translation_x += dx * self.TRANSLATION_FACTOR
                self.translation_y -= dy * self.TRANSLATION_FACTOR

            self.update()
            self.last_mouse_position = event.pos()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, file_path: str):
        super().__init__()
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.object_viewer = ObjectViewer()

        if file_path.endswith('.pkl'):
            mesh_data = load_mesh_from_pickle(file_path)
            self.object_viewer.addMesh(mesh_data)
        elif file_path.endswith('.npz'):
            mesh_data = load_mesh_from_npz(file_path)
            self.object_viewer.addMesh(mesh_data)
        else:
            mesh_set = MeshSet()
            mesh_set.load_new_mesh(file_path)
            self.object_viewer.addMesh(mesh_set)
            
        self.layout.addWidget(self.object_viewer)
        self.setWindowTitle("Simple PyQt OBJ Viewer")
        self.resize(800, 600)

if __name__ == '__main__':
    # Set up QSurfaceFormat for antialiasing
    format = QtGui.QSurfaceFormat()
    format.setSamples(4)  # Set the number of samples for multisampling
    format.setDepthBufferSize(24)
    QtGui.QSurfaceFormat.setDefaultFormat(format)

    app = QtWidgets.QApplication(sys.argv)

    # mainWindow = MainWindow('mesh_data.npz')
    mainWindow = MainWindow('example_models/cat.glb')
    mainWindow.show()
    sys.exit(app.exec_())
