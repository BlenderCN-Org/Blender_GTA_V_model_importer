import bpy
import os
import bmesh
import re
from copy import deepcopy

from mathutils import (Vector)


def getNameFromFile(filepath):
    return os.path.basename(filepath)

# index_header_pattern = re.compile(r"(.*) Indices\s*(.*?) .*", re.VERBOSE)
opening_bracket = re.compile(r"\t{3}\{+")
closing_bracket = re.compile(r"\t{3}\}+")
index_header_pattern = re.compile(r"\s+ Indices \s+ (?P<index_count>\d+)", re.VERBOSE)
index_line_pattern = re.compile(r"\t{4}(?P<indices>(?:\d+[^\.]){1,15})",re.VERBOSE)

vertex_header_pattern = re.compile(r"\s+ Vertices \s+ (?P<vertex_count>\d+)", re.VERBOSE)

number_pattern = "([\-\+]?\d+(?:\.\d+)?)"
vertex_line_pattern = re.compile(r"""
\t{4}
(?P<pos>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
(?P<weights>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
(?P<undef1>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
(?P<normal>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
(?P<undef2>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
(?P<uv>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){2}) \/\s
(?P<undef3>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4})
""", re.VERBOSE)


vertex_line_pattern2 = re.compile(r"\t+(?P<pos>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/", re.VERBOSE)

def load_Mesh(filepath):
    Meshes = []
    Mesh = []
    Indices = []
    read_indices = False
    Vertices = []
    read_vertices = False


    skinned = False
    bone_count = 0
    weights = []
    with open(filepath, 'r') as file:
        for line in file.readlines():
            if not read_indices:
                # find begining of index list
                match = index_header_pattern.match(line)
                if match:
                    print("index count: {0}".format(match.group("index_count")))
                    read_indices = True
                    Mesh = []
                    Indices = []
            elif read_indices:
                if closing_bracket.match(line):
                    read_indices = False
                # reading the indices
                match = index_line_pattern.match(line)
                if match and read_indices:
                    match_i = match.group("indices")
                    temp_list = list(int(i) for i in match_i.split())
                    Indices.extend(temp_list)
            if not read_indices and not read_vertices:
                match = re.search(vertex_header_pattern, line)
                if match:
                    print("vertex count: {0}".format(match.group("vertex_count")))
                    read_vertices = True
                    Vertices = []
            elif read_vertices:
                # read vertices
                if closing_bracket.match(line):
                    read_vertices = False
                    Mesh.append(deepcopy(Indices))
                    Mesh.append(deepcopy(Vertices))
                    Meshes.append(deepcopy(Mesh))
                match = vertex_line_pattern.match(line)
                if match and read_vertices:
                    pos = Vector(float(p) for p in match.group("pos").split())
                    weights = Vector(float(p) for p in match.group("weights").split())
                    normal = Vector(float(p) for p in match.group("normal").split())
                    uv = Vector(float(p) for p in match.group("uv").split())
                    uv[1] = 1.0 - uv[1]
                    Vertices.append((pos, weights, normal, uv))
                    # print("pos: {0}, weights: {1}, normal: {2}, uv:{3}".format(match.group("pos"), match.group("weights"),match.group("normal"),match.group("uv")))

    # create meshes
    for num, m in enumerate(Meshes):
        faces = []
        for i in range(int(len(m[0])/3)):
            f = i*3
            faces.append([m[0][f], m[0][f+1], m[0][f+2]])
        name = getNameFromFile(filepath)+str(num)
        mesh = bpy.data.meshes.new(name)
        verts = list(v[0] for v in m[1])
        mesh.from_pydata(verts, (), faces)
        mesh.validate()
         # add uvs
        mesh.uv_layers.new(name="UVMap")
        uvlayer = mesh.uv_layers.active.data
        mesh.calc_loop_triangles()

        for i, lt in enumerate(mesh.loop_triangles):
            # set the shading of all polygons to smooth
            mesh.polygons[i].use_smooth = True
            for loop_index in lt.loops:
                # set uv coordinates
                uvlayer[loop_index].uv = m[1][mesh.loops[loop_index].vertex_index][3]

        Obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(Obj)


def load(operator, context, filepath=""):
    print("importing: {0}".format(filepath))
    load_Mesh(filepath)
    return {'FINISHED'}