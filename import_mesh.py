import bpy
import os
import bmesh
import re
from copy import deepcopy

from mathutils import (Vector)


def getNameFromFile(filepath):
    return os.path.basename(filepath)

# .mesh file pattern
opening_bracket = re.compile(r"\t{3}\{+")
closing_bracket = re.compile(r"\t{3}\}+")
index_header_pattern = re.compile(r"\s+ Indices \s+ (?P<index_count>\d+)", re.VERBOSE)
index_line_pattern = re.compile(r"\t{4}(?P<indices>(?:\d+[^\.]){1,15})",re.VERBOSE)
vertex_header_pattern = re.compile(r"\s+ Vertices \s+ (?P<vertex_count>\d+)", re.VERBOSE)
vertex_line_pattern = re.compile(r"""
\t{4}
(?P<pos>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
(?P<weights>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
(?P<bone_indices>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
(?P<normal>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
(?P<undef2>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
(?P<uv>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){2}) (?:\/\s
(?P<undef3>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}))?
""", re.VERBOSE)
skinned_pattern = re.compile(r"\t+ Skinned \s+ (?P<skinned>True|False)", re.VERBOSE)
bone_count_pattern = re.compile(r"\t+ BoneCount \s+ (?P<bonecount>\d+)", re.VERBOSE)


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
    index_counter = 0
    vertex_counter = 0
    with open(filepath, 'r') as file:
        for line in file.readlines():
            if not read_indices and not read_vertices:
                # find begining of index list
                index_header_match = index_header_pattern.match(line)
                if index_header_match:
                    print("index count: {0}".format(index_header_match.group("index_count")))
                    read_indices = True
                    index_counter = 0
                    Mesh = []
                    Indices = []
                    continue

                # find beginning of vertex list
                verte_header_match = re.search(vertex_header_pattern, line)
                if verte_header_match:
                    print("vertex count: {0}".format(verte_header_match.group("vertex_count")))
                    read_vertices = True
                    vertex_counter = 0
                    Vertices = []
                    continue

                # get skinned
                skin_match = skinned_pattern.match(line)
                if skin_match:
                    skinned = skin_match.group("skinned") == "True"
                    print("skinned = {0}".format(str(skinned)))
                    continue

                # get bone count
                bone_match = bone_count_pattern.match(line)
                if bone_match:
                    bone_count = int(bone_match.group("bonecount"))
                    print("bone count = {0}".format(str(bone_count)))
                    continue

            elif read_indices:
                # reading the indices
                index_match = index_line_pattern.match(line)
                if index_match and read_indices:
                    match_i = index_match.group("indices")
                    temp_list = list(int(i) for i in match_i.split())
                    Indices.extend(temp_list)
                    continue

                if closing_bracket.match(line):
                    print("end read indices")
                    read_indices = False
                    continue

            elif read_vertices:
                # read vertices
                vertex_match = vertex_line_pattern.match(line)
                if vertex_match and read_vertices:
                    pos = Vector(float(p) for p in vertex_match.group("pos").split())
                    weights = Vector(float(p) for p in vertex_match.group("weights").split())
                    normal = Vector(float(p) for p in vertex_match.group("normal").split())
                    uv = Vector(float(p) for p in vertex_match.group("uv").split())
                    bone_indices = (int(p) for p in vertex_match.group("bone_indices").split())
                    uv[1] = 1.0 - uv[1]
                    Vertices.append((pos, weights, normal, uv, bone_indices))
                    vertex_counter += 1
                    # print("pos: {0}, weights: {1}, normal: {2}, uv:{3}".format(match.group("pos"), match.group("weights"),match.group("normal"),match.group("uv")))
                    continue

                if closing_bracket.match(line):
                    read_vertices = False
                    print("end read vertices. counted: {0}".format(vertex_counter))
                    Mesh.append(Indices)
                    Mesh.append(Vertices)
                    Meshes.append(Mesh)

    # create meshes
    base_name = getNameFromFile(filepath)
    for num, m in enumerate(Meshes):
        if m[1] and m[0]:
            name = base_name + str(num)
            print("create mesh: {0}".format(name))
            # populate faces
            faces = [[m[0][i*3], m[0][i*3+1], m[0][i*3+2]] for i in range(int(len(m[0])/3))]

            mesh = bpy.data.meshes.new(name)
            verts = list(v[0] for v in m[1])
            mesh.from_pydata(verts, (), faces)
            print("mesh creation done")

            if not mesh.validate():
                Obj = bpy.data.objects.new(name, mesh)
                # add uvs
                print("create uvs")
                mesh.uv_layers.new(name="UVMap")
                uvlayer = mesh.uv_layers.active.data
                mesh.calc_loop_triangles()
                normals = []
                for i, lt in enumerate(mesh.loop_triangles):
                    for loop_index in lt.loops:
                        # set uv coordinates
                        uvlayer[loop_index].uv = m[1][mesh.loops[loop_index].vertex_index][3]
                        normals.append(m[1][mesh.loops[loop_index].vertex_index][2])
                        # add bone weights
                        if skinned:
                            for i, vg in enumerate(m[1][mesh.loops[loop_index].vertex_index][4]):
                                if not str(vg) in Obj.vertex_groups:
                                    group = Obj.vertex_groups.new(name=str(vg))
                                else:
                                    group = Obj.vertex_groups[str(vg)]
                                weight = m[1][mesh.loops[loop_index].vertex_index][1][i]
                                if weight > 0.0:
                                    group.add([mesh.loops[loop_index].vertex_index], weight, 'REPLACE' )


                # normal custom verts on each axis
                mesh.use_auto_smooth = True
                mesh.normals_split_custom_set(normals)

                mat = bpy.data.materials.new(name=name)
                mesh.materials.append(mat)
                bpy.context.scene.collection.objects.link(Obj)
                Obj.select_set(True)
                bpy.context.view_layer.objects.active = Obj
            else:
                print("mesh validation failed")
        else:
            print("missing vertex data")
    print("joint meshes")
    bpy.ops.object.join()
    bpy.context.view_layer.objects.active.name = base_name


def load(operator, context, filepath=""):
    print("importing: {0}".format(filepath))
    if bpy.context.object:
        bpy.context.object.select_set(False)
    load_Mesh(filepath)
    return {'FINISHED'}