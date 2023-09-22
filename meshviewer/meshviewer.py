import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QVector3D
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np


class ObjectViewer(QOpenGLWidget):
    def __init__(self, obj_file_path, parent=None):
        super(ObjectViewer, self).__init__(parent)
        self.vertices = []
        self.is_face = True
        self.scale = 1.0
        self.load_obj(obj_file_path)
        
        self.last_mouse_position = None
        self.rotation_angle_x = 0.0
        self.rotation_angle_y = 0.0

    def load_obj(self, file_path):
        self.faces = []
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if parts:
                    if parts[0] == "v":
                        self.vertices.append(list(map(float, parts[1:])))
                    elif parts[0] == "f":
                        self.faces.append([int(p.split('/')[0]) - 1 for p in parts[1:]])


    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)

        vertex_shader = """
        #version 460
        layout (location = 0) in vec3 aPos;
        uniform mat4 model;
        void main() {
            gl_Position = model * vec4(aPos, 1.0);
        }
        """

        fragment_shader = """
        #version 460
        out vec4 FragColor;
        void main() {
            FragColor = vec4(1.0, 1.0, 1.0, 1.0);
        }
        """

        self.shader = compileProgram(
            compileShader(vertex_shader, GL_VERTEX_SHADER),
            compileShader(fragment_shader, GL_FRAGMENT_SHADER)
        )

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, len(self.vertices) * 3 * 4, np.array(self.vertices, dtype='float32').flatten(), GL_STATIC_DRAW)

        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, len(self.faces) * 3 * 4, np.array(self.faces, dtype='uint32').flatten(), GL_STATIC_DRAW)


        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15  # Usually, one step is equal to a 15-degree angle.
        
        # Set the scale factor and limit the zoom in/out.
        self.scale *= (1 + steps * 0.1)  # Change the 0.1 to adjust the zoom speed.
        self.scale = max(0.001, min(1000.0, self.scale))
        
        self.update()  # Trigger a repaint.

    def mousePressEvent(self, event):
        self.last_mouse_position = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_mouse_position:
            dx = event.x() - self.last_mouse_position.x()
            dy = event.y() - self.last_mouse_position.y()
            
            self.rotation_angle_x += dy * 0.5  # Adjust the factor for rotation speed
            self.rotation_angle_y += dx * 0.5  # Adjust the factor for rotation speed
            
            self.update()

        self.last_mouse_position = event.pos()

    def paintGL(self):
        glClearColor(0.2, 0.3, 0.3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.shader)

        model_location = glGetUniformLocation(self.shader, "model")
        glUniformMatrix4fv(model_location, 1, GL_FALSE, self.get_model_matrix())

        glBindVertexArray(self.vao)
        
        if self.is_face:
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE) # draw as wireframe
            glDrawElements(GL_TRIANGLES, len(self.faces) * 3, GL_UNSIGNED_INT, None)
        else:
            glDrawArrays(GL_POINTS, 0, len(self.vertices))

    def toggle_face(self):
        self.is_face = not self.is_face

    def get_model_matrix(self):
        from PyQt5.QtGui import QMatrix4x4

        model_matrix = QMatrix4x4()
        model_matrix.scale(self.scale)
        model_matrix.rotate(self.rotation_angle_x, 1, 0, 0)
        model_matrix.rotate(self.rotation_angle_y, 0, 1, 0)

        return model_matrix.data()

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)


class MainWindow(QMainWindow):
    def __init__(self, obj_file_path):
        super(MainWindow, self).__init__()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.object_viewer = ObjectViewer(obj_file_path)
        self.layout.addWidget(self.object_viewer)

        self.setWindowTitle("Simple PyQt OBJ Viewer")
        self.resize(800, 600)

def main():
    app = QApplication(sys.argv)
    window = MainWindow("meshviewer/example_models/cow.obj")
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()