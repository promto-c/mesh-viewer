
import sys
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore

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

from OpenGL import GL
from meshviewer.shaders.shader import PhongShader, BlinnPhongShader, LambertianShader
from meshviewer.utils.mesh_io import load_mesh_from_npz, load_mesh_from_pickle

class ObjectViewer(QtWidgets.QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.meshSet = MeshSet()  # Initialize an empty MeshSet
        self.scale = 1.0
        self.last_mouse_position = None
        self.rotation_angle_x = 0.0
        self.rotation_angle_y = 0.0
        # self.rotation_angle_z = -5.0
        self.translation_x = 0.0
        self.translation_y = 0.0
        # self.translation_z = 0.0
        self.middle_mouse_pressed = False
        self.mode = "wireframe"  # Default mode. Other values can be "wireframe" or "point"
        self.vaos = []  # List to store Vertex Array Objects for each mesh
        self.vertexBuffers = []  # List to store Vertex Buffer Objects for vertices
        self.normalBuffers = []  # List to store Normal Buffer Objects
        self.indexBuffers = []  # List to store Element Buffer Objects for faces
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

        # NOTE: WIP
        # Set initial view transformation parameters based on the bounding box
        self.init_view_transformation()

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
        self.meshSet.add_mesh(mesh)
        self.update()

    # def _addMeshData(self, mesh)

    def initBuffers(self):
        # Initialize min and max points with opposite infinity values
        overall_min_point = np.array([np.inf, np.inf, np.inf])
        overall_max_point = np.array([-np.inf, -np.inf, -np.inf])

        for mesh in self.meshSet:
            vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(vao)

            # Vertices
            vertices = np.array(mesh.vertex_matrix(), dtype='float32')
            vertexBuffer = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vertexBuffer)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)
            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glEnableVertexAttribArray(0)

            # Normals
            normals = np.array(mesh.vertex_normal_matrix(), dtype='float32')
            normalBuffer = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, normalBuffer)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, normals.nbytes, normals, GL.GL_STATIC_DRAW)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glEnableVertexAttribArray(1)

            # Faces
            faces = np.array(mesh.face_matrix().flatten(), dtype='uint32')
            indexBuffer = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, indexBuffer)
            GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, faces.nbytes, faces, GL.GL_STATIC_DRAW)

            # Store VAO and buffers
            self.vaos.append(vao)
            self.vertexBuffers.append(vertexBuffer)
            self.normalBuffers.append(normalBuffer)
            self.indexBuffers.append(indexBuffer)

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

    # NOTE: WIP
    def init_view_transformation(self):
        # Calculate the center of the bounding box
        # center = tuple((self.min_point[i] + self.max_point[i]) / 2 for i in range(3))

        # Calculate the dimensions of the bounding box
        dimensions = tuple(self.max_point[i] - self.min_point[i] for i in range(3))
        max_dimension = max(dimensions)

        # Set initial scale to fit the object within the view nicely
        self.scale = 5.0 / max_dimension  # Adjust the denominator to control the initial zoom level

        # # Set initial rotation angles for a good view
        # self.rotation_angle_x = 100.0  # Slight tilt
        # self.rotation_angle_y = -180.0  # Diagonal view
        # self.rotation_angle_z = 120.0  # Diagonal view

        # Set initial translation to center the object in the view
        # self.translation_x = -center[0]
        # self.translation_y = -center[1]
        # self.translation_z = -center[2]

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glClearColor(0.2, 0.3, 0.3, 1.0)

        # Set view, projection, and model matrices via PhongShader
        view = QtGui.QMatrix4x4()
        projection = QtGui.QMatrix4x4()
        projection.perspective(45.0, self.width() / self.height(), self.near_clip, self.far_clip)
        # view.translate(0, 0, -10)  # Adjust as needed

        model = QtGui.QMatrix4x4()
        model.translate(self.translation_x, self.translation_y, -5)
        model.rotate(self.rotation_angle_x, 1, 0, 0)
        model.rotate(self.rotation_angle_y, 0, 1, 0)
        # model.rotate(self.rotation_angle_z, 0, 0, 1)
        model.scale(self.scale)

        # Activate the shader program
        self.shader.use()

        # Set matrix uniforms
        self.shader.set_uniform("model", model.data())
        self.shader.set_uniform("view", view.data())
        self.shader.set_uniform("projection", projection.data())

        # Set light and view positions
        self.shader.set_uniform("lightPos", (1.2, 1.0, 2.0))
        self.shader.set_uniform("viewPos", (0.0, 0.0, 0.0))

        # Set light and object colors
        self.shader.set_uniform("lightColor", (1.0, 1.0, 1.0))  # White light
        self.shader.set_uniform("objectColor", (1.0, 0.5, 0.31))  # Some orange color

        # self.shader.set_uniform("ambientStrength", 0.1)  # Some orange color
        # self.shader.set_uniform("specularStrength", 0.5)  # Some orange color
        # self.shader.set_uniform("shininess", 32.0)  # Some orange color

        for i, vao in enumerate(self.vaos):
            GL.glBindVertexArray(vao)
            if self.mode == "wireframe":
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
            elif self.mode == "face":
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
            elif self.mode == "point":
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_POINT)

            mesh = self.meshSet[i]
            if self.mode == "point":
                GL.glDrawArrays(GL.GL_POINTS, 0, mesh.vertex_number())
            else:
                GL.glDrawElements(GL.GL_TRIANGLES, mesh.face_number() * 3, GL.GL_UNSIGNED_INT, None)

        GL.glBindVertexArray(0)
        GL.glUseProgram(0)

    def resizeGL(self, width, height):
        GL.glViewport(0, 0, width, max(1, height))

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15  # Usually, one step is equal to a 15-degree angle.
        
        # Set the scale factor and limit the zoom in/out.
        self.scale *= (1 + steps * 0.1)  # Change the 0.1 to adjust the zoom speed.
        self.scale = max(0.001, min(1000.0, self.scale))
        
        self.update()  # Trigger a repaint.

    def mousePressEvent(self, event):
        self.last_mouse_position = event.pos()
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:  # Check if the middle button is pressed
            self.middle_mouse_pressed = True

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.middle_mouse_pressed = False

    def mouseMoveEvent(self, event):
        if self.last_mouse_position:
            dx = event.x() - self.last_mouse_position.x()
            dy = event.y() - self.last_mouse_position.y()

            if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
                self.rotation_angle_x += dy * 0.5  # Adjust the factor for rotation speed
                self.rotation_angle_y += dx * 0.5  # Adjust the factor for rotation speed
            elif self.middle_mouse_pressed:
                # Adjust translation based on mouse movement
                self.translation_x += dx * 0.01  # Adjust these factors as needed
                self.translation_y -= dy * 0.01  # Invert dy for intuitive direction

            self.update()

        self.last_mouse_position = event.pos()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, file_path: str):
        super(MainWindow, self).__init__()
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

    mainWindow = MainWindow('mesh_data.npz')
    # mainWindow = MainWindow('meshviewer\example_models\Room.obj')
    mainWindow.show()
    sys.exit(app.exec_())
