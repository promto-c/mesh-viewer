try:
    import pymeshlab
except:
    pass

from typing import Tuple
import pickle
from pathlib import Path
import io
import numpy as np


class BoundingBox:
    def __init__(self, max_tuple, min_tuple) -> None:
        self._max = max_tuple
        self._min = min_tuple

    def max(self):
        return self._max
    
    def min(self):
        return self._min
class MeshData:
    def __init__(self, vertices, faces, normals, uvs, max_tuple, min_tuple):
        self.vertices = vertices
        self.faces = faces
        self.normals = normals
        self.uvs = uvs  # Add this line to store UVs
        self._bounding_box = BoundingBox(max_tuple, min_tuple)

    # Add a method to get UV coordinates
    def vertex_texcoords_matrix(self):
        return self.uvs

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
    
    def bounding_box(self):
        return self._bounding_box

def load_mesh(file_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Loads a mesh from the given file path and returns the combined vertices, faces, and normals.
    
    Args:
        file_path: str, the path to the mesh file.
    
    Returns:
        tuple of np.ndarray: combined vertices, faces, and normals of the mesh.
    """
    # Initialize MeshSet and load the specified mesh file
    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(file_path)

    # Check if the mesh set is empty
    if mesh_set.mesh_number() == 0:
        raise ValueError("No meshes found in the file.")

    # Use list comprehension for efficiency and readability
    # meshes = [mesh_set.mesh(i) for i in range(mesh_set.mesh_number())]

    # Initialize lists for combined data
    combined_vertices = []
    combined_faces = []
    combined_normals = []
    combined_uvs = []
    face_offset = 0

    for i in range(mesh_set.mesh_number()):
        mesh = mesh_set.mesh(i)

        # Append vertices, faces, and normals
        combined_vertices.append(mesh.vertex_matrix())
        combined_faces.append(mesh.face_matrix() + face_offset)  # Update face indices based on current offset
        combined_normals.append(mesh.vertex_normal_matrix())
        
        # Update face offset for next mesh
        face_offset += mesh.vertex_matrix().shape[0]

        # Check if the mesh has UV coordinates and append them
        if mesh.has_vertex_tex_coord():
            uvs = mesh.vertex_texcoords_matrix()
            combined_uvs.append(uvs)
        else:
            print('no_uv')
            # Handle the case where the mesh does not have UVs
            # This could be by appending an array of zeros or handling it some other way
            combined_uvs.append(np.zeros((mesh.vertex_matrix().shape[0], 2)))  # Assuming 2D UVs

    # Concatenate all the arrays
    combined_vertices = np.concatenate(combined_vertices)
    combined_faces = np.concatenate(combined_faces)
    combined_normals = np.concatenate(combined_normals)
    combined_uvs = np.concatenate(combined_uvs)

    geometric = mesh_set.get_geometric_measures()
    bbox = geometric.get('bbox')

    max_tuple, min_tuple = bbox.max(), bbox.min()

    return combined_vertices, combined_faces, combined_normals, combined_uvs, max_tuple, min_tuple

def save_mesh_data_pickle(file_path, mesh_data):
    # Use a context manager to safely write the mesh data to a file
    with open(file_path, 'wb') as outfile:
        pickle.dump(mesh_data, outfile)

def save_mesh_data_npz(file_path, mesh_data):
    # Convert the file_path string to a Path object
    path = Path(file_path)
    
    # Combine the mesh data into a single byte stream
    # We'll use numpy's savez_compressed for efficient storage
    vertices, faces, normals, uvs, max_tuple, min_tuple = mesh_data

    # Create a temporary buffer to store the serialized data
    with io.BytesIO() as buffer:
        # Use numpy's savez_compressed to write arrays to the buffer
        np.savez_compressed(buffer, vertices=vertices, faces=faces, normals=normals, 
                            uvs=uvs, max_tuple=max_tuple, min_tuple=min_tuple)

        # Seek to the beginning of the buffer
        buffer.seek(0)

        # Read the contents of the buffer and write them to the file using write_bytes
        path.write_bytes(buffer.read())

def load_mesh_from_pickle(filename):
    with open(filename, 'rb') as infile:
        vertices, faces, normals, uvs, max_tuple, min_tuple = pickle.load(infile)
    # Return MeshData instance
    return MeshData(vertices, faces, normals, uvs, max_tuple, min_tuple)

def load_mesh_from_npz(filename):
    # Load the .npz file
    with np.load(filename) as data:
        # Extract the vertices, faces, and normals arrays
        vertices = data['vertices']
        faces = data['faces']
        normals = data['normals']
        uvs = data['uvs']  # Load UVs
        max_tuple = data['max_tuple']
        min_tuple = data['min_tuple']

    # Return an instance of MeshData containing the loaded mesh data
    return MeshData(vertices, faces, normals, uvs, max_tuple, min_tuple)

if __name__ == "__main__":
    # Specify the path to the mesh file
    mesh_file_path = 'OBJ/Room.obj'
    mesh_data = load_mesh(mesh_file_path)

    # Specify the output file path for the combined mesh data
    output_file_path = 'mesh_data.pkl'
    save_mesh_data_pickle(output_file_path, mesh_data)
    output_file_path = 'mesh_data.npz'
    save_mesh_data_npz(output_file_path, mesh_data)
