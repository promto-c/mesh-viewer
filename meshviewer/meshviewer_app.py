import sys
import enum
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from OpenGL import GL
import trimesh

try:
    from pymeshlab import MeshSet, Mesh
except ImportError:
    # Placeholder implementations if pymeshlab is not available
    class MeshSet(list):
        ...
        def load_new_mesh(self, file_path):
            ...

        def add_mesh(self, mesh):
            self.append(mesh)

        # NOTE:
        def get_bounding_box(self):
            min_x, max_x = float('inf'), float('-inf')
            min_y, max_y = float('inf'), float('-inf')
            min_z, max_z = float('inf'), float('-inf')

            for mesh in self.meshes:
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

from meshviewer.shaders.shader import PhongShader, BlinnPhongShader, LambertianShader, DisparityShader
from meshviewer.utils.mesh_io import load_mesh_from_npz, load_mesh_from_pickle

class RenderMode(enum.Enum):
    WIREFRAME = enum.auto()
    FACE = enum.auto()
    POINT = enum.auto()

def load_mesh_from_glb(file_path):
    """Loads a GLB file using trimesh and converts it to a simple mesh object.
    """
    tmesh = trimesh.load(file_path, force='mesh')
    # Define a simple mesh wrapper with the required interface.
    class SimpleMesh:
        def __init__(self, vertices, faces, normals):
            self._vertices = vertices
            self._faces = faces
            self._normals = normals

        def vertex_matrix(self):
            return self._vertices

        def vertex_normal_matrix(self):
            return self._normals

        def face_matrix(self):
            return self._faces

        def vertex_number(self):
            return len(self._vertices)

        def face_number(self):
            return len(self._faces)

    vertices = np.array(tmesh.vertices, dtype='float32')
    faces = np.array(tmesh.faces, dtype='uint32')
    # If trimesh did not compute normals, use zeros as a fallback.
    if tmesh.vertex_normals is None or len(tmesh.vertex_normals) == 0:
        normals = np.zeros_like(vertices, dtype='float32')
    else:
        normals = np.array(tmesh.vertex_normals, dtype='float32')

    return SimpleMesh(vertices, faces, normals)

class ObjectViewer(QtWidgets.QOpenGLWidget):
    # Signal to emit the pixel RGB value as a tuple (R, G, B)
    pixel_value_changed = QtCore.pyqtSignal(tuple)

    RENDER_MODE_TO_GL_POLYGON = {
        RenderMode.WIREFRAME: GL.GL_LINE,
        RenderMode.FACE: GL.GL_FILL,
        RenderMode.POINT: GL.GL_POINT,
    }

    DEFAULT_BACKGROUND_COLOR = (0.2, 0.3, 0.3, 1.0)

    ROTATION_FACTOR = 0.5
    TRANSLATION_FACTOR = 0.01

    def __init__(self, parent=None, mode: RenderMode = RenderMode.FACE):
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

        self.near_clip = 0.1
        self.far_clip = 1000.0

        # Stereo parameters
        self.eye_separation = 0.05  # Default separation.
        # Additional rotation for the second (right) camera.
        self.second_camera_angle = 0.0
        self.view_mode = 'stereo'
        # Enable focus to capture key events.
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def initializeGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        self.shader = PhongShader()
        self.initBuffers()

    def set_mode(self, mode='wireframe'):
        self.mode = mode
        self.update()

    def add_mesh(self, mesh_input):
        """Adds a mesh to the viewer. The mesh can be a single Mesh object or a MeshSet.
        
        Parameters:
            mesh_input (Mesh or MeshSet): The mesh or MeshSet to add.
        """
        if isinstance(mesh_input, MeshSet):
            for mesh in mesh_input:
                self._add_single_mesh(mesh)
        else:
            self._add_single_mesh(mesh_input)

    def _add_single_mesh(self, mesh):
        self.mesh_set.add_mesh(mesh)
        self.update()

    def initBuffers(self):
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
        self.shader.set_uniform("objectColor", (1.0, 1.0, 1.0))
        # Set material properties
        self.shader.set_uniform("ambientStrength", 0.1)
        self.shader.set_uniform("specularStrength", 0.5)
        self.shader.set_uniform("shininess", 32.0)

    def setup_matrices(self, eye_offset=0.0, viewport_width=None, angle_adjust=0.0):
        projection = QtGui.QMatrix4x4()
        if viewport_width is None:
            aspect = self.width() / self.height()
        else:
            aspect = viewport_width / self.height()
        projection.perspective(self.fov, aspect, self.near_clip, self.far_clip)
        view = QtGui.QMatrix4x4()
        view.translate(eye_offset, 0, -5.0)
        # Apply an additional rotation (e.g. for right eye) if needed.
        if angle_adjust:
            view.rotate(angle_adjust, 0, 1, 0)
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

        if self.view_mode == 'disparity':
            shader = DisparityShader()
        else:
            shader = self.shader

        # Activate the shader program
        shader.use()

        # Switch rendering based on the current view_mode.
        if self.view_mode == 'stereo':
            total_width = self.width()
            total_height = self.height()
            half_width = total_width // 2
            # Left eye viewport
            GL.glViewport(0, 0, half_width, total_height)
            self.setup_matrices(eye_offset=self.eye_separation / 2, viewport_width=half_width)
            self.set_fragment_shader_uniform()
            self.render_meshes()
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
            # Right eye viewport with additional angle adjustment
            GL.glViewport(half_width, 0, total_width - half_width, total_height)
            self.setup_matrices(eye_offset=-self.eye_separation / 2, viewport_width=total_width - half_width, angle_adjust=self.second_camera_angle)
            self.set_fragment_shader_uniform()
            self.render_meshes()
        elif self.view_mode == 'left':
            GL.glViewport(0, 0, self.width(), self.height())
            self.setup_matrices(eye_offset=self.eye_separation / 2, viewport_width=self.width())
            self.set_fragment_shader_uniform()
            self.render_meshes()
        elif self.view_mode == 'right':
            GL.glViewport(0, 0, self.width(), self.height())
            self.setup_matrices(eye_offset=-self.eye_separation / 2, viewport_width=self.width(), angle_adjust=self.second_camera_angle)
            self.set_fragment_shader_uniform()
            self.render_meshes()
        elif self.view_mode == 'anaglyph':
            # Render left view in red channel only.
            GL.glViewport(0, 0, self.width(), self.height())
            GL.glColorMask(True, False, False, True)
            self.setup_matrices(eye_offset=self.eye_separation / 2, viewport_width=self.width())
            self.set_fragment_shader_uniform()
            self.render_meshes()
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
            # Render right view in cyan (green+blue)
            GL.glColorMask(False, True, True, True)
            self.setup_matrices(eye_offset=-self.eye_separation / 2, viewport_width=self.width(), angle_adjust=self.second_camera_angle)
            self.set_fragment_shader_uniform()
            self.render_meshes()
            # Reset color mask
            GL.glColorMask(True, True, True, True)
        elif self.view_mode == 'disparity':
            GL.glViewport(0, 0, self.width(), self.height())
            
            # Build the projection matrix (common to both cameras)
            projection = QtGui.QMatrix4x4()
            aspect = self.width() / self.height()
            projection.perspective(self.fov, aspect, self.near_clip, self.far_clip)
            
            # Build the model matrix (object transform)
            model = QtGui.QMatrix4x4()
            model.translate(self.translation_x, self.translation_y, self.translation_z)
            model.rotate(self.rotation_angle_x, 1, 0, 0)
            model.rotate(self.rotation_angle_y, 0, 1, 0)
            model.rotate(self.rotation_angle_z, 0, 0, 1)
            model.scale(self.scale)
            
            # Left camera: simple translation by half the eye separation.
            leftView = QtGui.QMatrix4x4()
            leftView.translate(self.eye_separation / 2, 0, -5.0)
            
            # Right camera: translation in the opposite direction and apply extra rotation.
            rightView = QtGui.QMatrix4x4()
            rightView.translate(-self.eye_separation / 2, 0, -5.0)
            rightView.rotate(self.second_camera_angle, 0, 1, 0)
            
            # Activate the disparity shader.
            # We assume self.disparity_shader is an instance of a shader class that loads
            # the vertex shader "disparity_vertex_shader.glsl" and fragment shader "disparity_fragment_shader.glsl"
            # shader.use()
            
            # Set uniforms: model, left and right view matrices, projection and screen size.
            shader.set_uniform("model", model.data())
            shader.set_uniform("leftView", leftView.data())
            shader.set_uniform("rightView", rightView.data())
            shader.set_uniform("projection", projection.data())
            shader.set_uniform("screenSize", (float(self.width()), float(self.height())))

            # Render the meshes (the vertex shader will compute the disparity).
            self.render_meshes()
        else:
            # Default monoscopic view.
            GL.glViewport(0, 0, self.width(), self.height())
            self.setup_matrices(eye_offset=0.0, viewport_width=self.width())
            self.set_fragment_shader_uniform()
            self.render_meshes()

        shader.release()

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
        # Update last mouse position.
        self.last_mouse_position = event.pos()
        self.update()

        # Read the pixel value under the mouse cursor.
        x = event.x()
        # Convert Qt mouse y (from top) to OpenGL y (from bottom)
        y = self.height() - event.y()
        # Read one pixel (RGB) from the current framebuffer as floats.
        pixel = GL.glReadPixels(x, y, 1, 1, GL.GL_RGB, GL.GL_FLOAT)
        # Convert the returned data to a tuple of floats.
        rgb = tuple(np.frombuffer(pixel, dtype=np.float32))
        # Emit the signal with the pixel's float RGB value.
        self.pixel_value_changed.emit(rgb)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        if key == QtCore.Qt.Key_1:
            self.view_mode = 'left'
        elif key == QtCore.Qt.Key_2:
            self.view_mode = 'right'
        elif key == QtCore.Qt.Key_3:
            self.view_mode = 'stereo'
        elif key == QtCore.Qt.Key_4:
            self.view_mode = 'anaglyph'
        elif key == QtCore.Qt.Key_5:
            self.view_mode = 'disparity'
        self.update()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, file_path: str):
        super().__init__()
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.object_viewer = ObjectViewer()
        # Connect the viewer's pixel_value_changed signal to update the status bar.
        self.object_viewer.pixel_value_changed.connect(
            lambda rgb: self.statusBar().showMessage(f"Pixel RGB: {rgb}")
        )
        if file_path.endswith('.pkl'):
            mesh_data = load_mesh_from_pickle(file_path)
            self.object_viewer.add_mesh(mesh_data)
        elif file_path.endswith('.npz'):
            mesh_data = load_mesh_from_npz(file_path)
            self.object_viewer.add_mesh(mesh_data)
        elif file_path.endswith('.glb'):
            mesh = load_mesh_from_glb(file_path)
            self.object_viewer.add_mesh(mesh)
        else:
            mesh_set = MeshSet()
            mesh_set.load_new_mesh(file_path)
            self.object_viewer.add_mesh(mesh_set)

        self.layout.addWidget(self.object_viewer)

        # --- Add two sliders for stereo adjustments ---
        slider_widget = QtWidgets.QWidget()
        slider_widget.setMaximumHeight(46)
        slider_layout = QtWidgets.QHBoxLayout(slider_widget)

        # Slider for eye separation (offset)
        self.eye_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.eye_slider.setRange(0, 100)
        self.eye_slider.setValue(50)  # 50 corresponds to 0.05 separation
        self.eye_slider.setToolTip("Adjust Eye Separation")
        self.eye_slider.valueChanged.connect(self.update_eye_separation)
        slider_layout.addWidget(QtWidgets.QLabel("Eye Separation"))
        slider_layout.addWidget(self.eye_slider)

        # Slider for second (right) camera angle adjustment (in degrees)
        self.angle_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.angle_slider.setRange(-45, 45)
        self.angle_slider.setValue(0)
        self.angle_slider.setToolTip("Adjust Right Camera Angle")
        self.angle_slider.valueChanged.connect(self.update_second_camera_angle)
        slider_layout.addWidget(QtWidgets.QLabel("Right Camera Angle"))
        slider_layout.addWidget(self.angle_slider)

        self.layout.addWidget(slider_widget)
        # ------------------------------

        self.setWindowTitle("PyQt OBJ Viewer")
        self.resize(800, 600)
        # Add a status bar to display pixel values.
        self.setStatusBar(QtWidgets.QStatusBar(self))

    def update_eye_separation(self, value):
        # Map slider value (0-100) to eye separation (0.0 to 0.1)
        self.object_viewer.eye_separation = (value / 100) * 0.1
        self.object_viewer.update()

    def update_second_camera_angle(self, value):
        # Directly use the slider value (degrees) for the additional rotation.
        self.object_viewer.second_camera_angle = float(value)
        self.object_viewer.update()

if __name__ == '__main__':
    format = QtGui.QSurfaceFormat()
    format.setSamples(4)
    format.setDepthBufferSize(24)
    QtGui.QSurfaceFormat.setDefaultFormat(format)

    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow('example_models/racoon_m.glb')
    mainWindow.show()
    sys.exit(app.exec_())
