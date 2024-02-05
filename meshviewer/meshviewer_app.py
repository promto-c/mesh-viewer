
import sys
import numpy as np
import pickle
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

    class Mesh:
        ...

from OpenGL import GL
from meshviewer.shaders.phong_shader import PhongShader, BlinnPhongShader


class MeshData:
    def __init__(self, vertices, faces, normals):
        self.vertices = vertices
        self.faces = faces
        self.normals = normals

    def vertex_matrix(self):
        return self.vertices

    def vertex_normal_matrix(self):
        return self.normals
    
    def face_matrix(self):
        return self.faces
    
    def face_number(self):
        return len(self.faces)
    
    def vertex_number(self):
        return len(self.vertices)

def load_mesh_from_pickle(filename):
    with open(filename, 'rb') as infile:
        vertices, faces, normals = pickle.load(infile)
    return MeshData(vertices, faces, normals)

class ObjectViewer(QtWidgets.QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.meshSet = MeshSet()  # Initialize an empty MeshSet
        self.scale = 1.0
        self.last_mouse_position = None
        self.rotation_angle_x = 0.0
        self.rotation_angle_y = 0.0
        self.translation_x = 0.0
        self.translation_y = 0.0
        self.middle_mouse_pressed = False
        self.mode = "wireframe"  # Default mode. Other values can be "wireframe" or "point"
        self.vaos = []  # List to store Vertex Array Objects for each mesh
        self.vertexBuffers = []  # List to store Vertex Buffer Objects for vertices
        self.normalBuffers = []  # List to store Normal Buffer Objects
        self.indexBuffers = []  # List to store Element Buffer Objects for faces
        self.phongShader = None  # Placeholder for the PhongShader instance

    def initializeGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        self.phongShader = BlinnPhongShader()  # Initialize PhongShader
        self.phongShader.create_shader_program()  # Compile and link shaders
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
        self.meshSet.add_mesh(mesh)
        self.update()

    # def _addMeshData(self, mesh)

    def initBuffers(self):
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

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glClearColor(0.2, 0.3, 0.3, 1.0)

        # Set view, projection, and model matrices via PhongShader
        view = QtGui.QMatrix4x4()
        projection = QtGui.QMatrix4x4()
        projection.perspective(45.0, self.width() / self.height(), 0.1, 100.0)
        view.translate(0, 0, -10)  # Adjust as needed

        model = QtGui.QMatrix4x4()
        model.translate(self.translation_x, self.translation_y, -5)
        model.rotate(self.rotation_angle_x, 1, 0, 0)
        model.rotate(self.rotation_angle_y, 0, 1, 0)
        model.scale(self.scale)

        # Activate the shader program
        self.phongShader.use()

        # Set matrix uniforms
        self.phongShader.set_uniform("model", model.data(), "4fv")
        self.phongShader.set_uniform("view", view.data(), "4fv")
        self.phongShader.set_uniform("projection", projection.data(), "4fv")

        # Set light and view positions
        self.phongShader.set_uniform("lightPos", (1.2, 1.0, 2.0), "3f")
        self.phongShader.set_uniform("viewPos", (0.0, 0.0, 0.0), "3f")

        # Set light and object colors
        self.phongShader.set_uniform("lightColor", (1.0, 1.0, 1.0), "3f")  # White light
        self.phongShader.set_uniform("objectColor", (1.0, 0.5, 0.31), "3f")  # Some orange color

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
    def __init__(self, file_path):
        super(MainWindow, self).__init__()
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.object_viewer = ObjectViewer()

        if file_path.endswith('pkl'):
            mesh_data = load_mesh_from_pickle(file_path)
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

    mainWindow = MainWindow('mesh_data.pkl')
    # mainWindow = MainWindow('meshviewer\example_models\Room.obj')
    mainWindow.show()
    sys.exit(app.exec_())
