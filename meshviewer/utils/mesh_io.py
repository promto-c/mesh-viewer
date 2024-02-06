try:
    import pymeshlab
except:
    pass

from typing import Tuple
import pickle
from pathlib import Path
import io
import numpy as np

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
    meshes = [mesh_set.mesh(i) for i in range(mesh_set.mesh_number())]

    # Combine arrays
    combined_vertices = np.concatenate([mesh.vertex_matrix() for mesh in meshes])
    combined_faces = np.concatenate([mesh.face_matrix() + sum([v.vertex_matrix().shape[0] for v in meshes[:i]]) for i, mesh in enumerate(meshes)])
    combined_normals = np.concatenate([mesh.vertex_normal_matrix() for mesh in meshes])

    return combined_vertices, combined_faces, combined_normals

def save_mesh_data_pickle(file_path, mesh_data):
    # Use a context manager to safely write the mesh data to a file
    with open(file_path, 'wb') as outfile:
        pickle.dump(mesh_data, outfile)

def save_mesh_data_npz(file_path, mesh_data):
    # Convert the file_path string to a Path object
    path = Path(file_path)
    
    # Combine the mesh data into a single byte stream
    # We'll use numpy's savez_compressed for efficient storage
    combined_vertices, combined_faces, combined_normals = mesh_data
    
    # Create a temporary buffer to store the serialized data
    with io.BytesIO() as buffer:
        # Use numpy's savez_compressed to write arrays to the buffer
        np.savez_compressed(buffer, vertices=combined_vertices, faces=combined_faces, normals=combined_normals)
        
        # Seek to the beginning of the buffer
        buffer.seek(0)
        
        # Read the contents of the buffer and write them to the file using write_bytes
        path.write_bytes(buffer.read())

def load_mesh_from_pickle(filename):
    with open(filename, 'rb') as infile:
        vertices, faces, normals = pickle.load(infile)
    return MeshData(vertices, faces, normals)

def load_mesh_from_npz(filename):
    # Load the .npz file
    with np.load(filename) as data:
        # Extract the vertices, faces, and normals arrays
        vertices = data['vertices']
        faces = data['faces']
        normals = data['normals']

    # Return an instance of MeshData containing the loaded mesh data
    return MeshData(vertices, faces, normals)

if __name__ == "__main__":
    # Specify the path to the mesh file
    mesh_file_path = 'OBJ/Room.obj'
    mesh_data = load_mesh(mesh_file_path)

    # Specify the output file path for the combined mesh data
    output_file_path = 'mesh_data.pkl'
    save_mesh_data_pickle(output_file_path, mesh_data)
    output_file_path = 'mesh_data.npz'
    save_mesh_data_npz(output_file_path, mesh_data)
