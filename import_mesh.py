import bpy
import os
import bmesh
import re
from copy import deepcopy

from mathutils import (Vector, Quaternion, Matrix)


def getNameFromFile(filepath):
    return os.path.basename(filepath)

opening_bracket = re.compile(r"\t+\{+")
closing_bracket = re.compile(r"\t+\}+")


def find_skel_file(mesh_path):
    folder = os.path.dirname(os.path.abspath(mesh_path))
    for file in os.listdir(folder):
        if file.endswith(".skel"):
            return os.path.join(folder, file)

def load_skel(filepath):
    # skeleton pattern
    DataCRC_pattern = re.compile(r"\t+ DataCRC \s+ (?P<DataCRC>\d+)", re.VERBOSE)
    NumBones_pattern = re.compile(r"\t+ NumBones \s+ (?P<NumBones>\d+)", re.VERBOSE)
    Bone_header_pattern = re.compile(r"\t+ Bone \s+ (?P<bone_name>[^\s]+) \s+ (?P<bone_id>\d+)", re.VERBOSE)
    MirrorBoneId_pattern = re.compile(r"\t+ MirrorBoneId \s+ (?P<MirrorBoneId>\d+)", re.VERBOSE)
    Flags_pattern = re.compile(r"\t+ Flags (?P<flags>(\s+([^\s]+)){1,6})", re.VERBOSE)
    RotationQuaternion_pattern = re.compile(r"\t+ RotationQuaternion (?P<RotationQuaternion>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){1,6})", re.VERBOSE)
    LocalOffset_pattern = re.compile(r"\t+ LocalOffset (?P<LocalOffset>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){1,6})", re.VERBOSE)
    Scale_pattern = re.compile(r"\t+ Scale (?P<Scale>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){1,6})", re.VERBOSE)
    Children_pattern = re.compile(r"\t+ Children \s+ (?P<Children>\d+)", re.VERBOSE)


    def add_bone(lines, line_n, id, armature, parent=None):
        bone = {'id': id, 'children': {}}

        line_number = line_n
        while line_number < len(lines):

            RotQuat_match = RotationQuaternion_pattern.match(lines[line_number])
            if RotQuat_match:
                bone["RotationQuaternion"] = tuple(float(r) for r in RotQuat_match.group("RotationQuaternion").split())
                line_number += 1
                continue

            LocOff_match = LocalOffset_pattern.match(lines[line_number])
            if LocOff_match:
                bone["LocalOffset"] = Vector(float(l) for l in LocOff_match.group("LocalOffset").split())
                line_number += 1
                continue

            Scale_match = Scale_pattern.match(lines[line_number])
            if Scale_match:
                bone["Scale"] = Vector(float(s) for s in Scale_match.group("Scale").split())
                line_number += 1
                continue

            bone_match = Bone_header_pattern.match(lines[line_number])
            if bone_match:
                bone_id = bone_match.group("bone_id")
                bone_name = bone_match.group("bone_name")
                line_number += 1
                b_bone = armature.edit_bones.new(bone_name)
                b_bone.head = (0,0,0)
                b_bone.tail = (0,0.2,0)
                b_bone.use_inherit_rotation = False
                b_bone.use_local_location = False
                q = Quaternion(bone["RotationQuaternion"])
                b_bone.matrix = q.to_matrix().to_4x4()
                b_bone.translate(bone["LocalOffset"])
                if parent:
                    b_bone.parent = parent
                line_number, child = add_bone(lines, line_number, bone_id, armature, b_bone)
                bone["children"][bone_name] = child
                continue

            end_match = closing_bracket.match(lines[line_number])
            if end_match:
                line_number += 1
                return line_number, bone

            line_number += 1

    skelett = {}
    num_bones = 0
    data_crc = 0
    arma = bpy.data.armatures.new(os.path.basename(filepath))
    Obj = bpy.data.objects.new(os.path.basename(filepath), arma)
    bpy.context.scene.collection.objects.link(Obj)
    bpy.context.view_layer.objects.active = Obj
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    with open(filepath, 'r') as file:
        lines = file.readlines()
        line_number = 0
        while line_number < len(lines):
        # for line in lines:
            num_bones_match = NumBones_pattern.match(lines[line_number])
            if num_bones_match:
                num_bones = int(num_bones_match.group("NumBones"))
                line_number += 1
                continue
            dat_match = DataCRC_pattern.match(lines[line_number])
            if dat_match:
                data_crc = int(dat_match.group("DataCRC"))
                line_number += 1
                continue
            bone_match = Bone_header_pattern.match(lines[line_number])
            if bone_match:
                bone_id = bone_match.group("bone_id")
                bone_name = bone_match.group("bone_name")
                line_number += 1
                line_number, skelett[bone_name] = add_bone(lines, line_number, bone_id, arma)
                continue
            line_number += 1

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return Obj
    # print(skelett)





def load_Mesh(filepath):
    # re .mesh pattern
    index_header_pattern = re.compile(r"\s+ Indices \s+ (?P<index_count>\d+)", re.VERBOSE)
    index_line_pattern = re.compile(r"\t{4}(?P<indices>(?:\d+[^\.]){1,15})",re.VERBOSE)
    vertex_header_pattern = re.compile(r"\s+ Vertices \s+ (?P<vertex_count>\d+)", re.VERBOSE)
    vertex_line_pattern_skinned = re.compile(r"""
    \t{4}
    (?P<pos>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
    (?P<weights>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
    (?P<bone_indices>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
    (?P<normal>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
    (?P<color>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
    (?P<uv>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){2}) (?:\/\s
    (?P<undef3>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}))?
    """, re.VERBOSE)
    vertex_line_pattern = re.compile(r"""
    \t{4}
    (?P<pos>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
    (?P<normal>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/\s
    (?P<color>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){4}) \/\s
    (?P<uv>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){2})
    """, re.VERBOSE)

    skinned_pattern = re.compile(r"\t+ Skinned \s+ (?P<skinned>True|False)", re.VERBOSE)
    bone_count_pattern = re.compile(r"\t+ BoneCount \s+ (?P<bonecount>\d+)", re.VERBOSE)
    vertex_line_pattern2 = re.compile(r"\t+(?P<pos>(?:(?:[\-\+]?\d*(?:\.\d*)?)\s+){3}) \/", re.VERBOSE)

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
                vertex_header_match = vertex_header_pattern.match(line)
                if vertex_header_match:
                    print("vertex count: {0}".format(vertex_header_match.group("vertex_count")))
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
                if skinned:
                    vertex_match = vertex_line_pattern_skinned.match(line)
                    if vertex_match and read_vertices:
                        pos = Vector(float(p) for p in vertex_match.group("pos").split())
                        weights = Vector(float(p) for p in vertex_match.group("weights").split())
                        normal = Vector(float(p) for p in vertex_match.group("normal").split())
                        uv = Vector(float(p) for p in vertex_match.group("uv").split())
                        bone_indices = (int(p) for p in vertex_match.group("bone_indices").split())
                        uv[1] = 1.0 - uv[1]
                        Vertices.append((pos, normal, uv, weights, bone_indices))
                        vertex_counter += 1
                        # print("pos: {0}, weights: {1}, normal: {2}, uv:{3}".format(match.group("pos"), match.group("weights"),match.group("normal"),match.group("uv")))
                        continue
                else:
                    vertex_match = vertex_line_pattern.match(line)
                    if vertex_match and read_vertices:
                        pos = Vector(float(p) for p in vertex_match.group("pos").split())
                        normal = Vector(float(p) for p in vertex_match.group("normal").split())
                        uv = Vector(float(p) for p in vertex_match.group("uv").split())
                        uv[1] = 1.0 - uv[1]
                        Vertices.append((pos, normal, uv))
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
                        # set uv coordinates (2)
                        uvlayer[loop_index].uv = m[1][mesh.loops[loop_index].vertex_index][2]
                        # set normals (1)
                        normals.append(m[1][mesh.loops[loop_index].vertex_index][1])
                        # add bone weights
                        if skinned:
                            # bone indices (4)
                            for i, vg in enumerate(m[1][mesh.loops[loop_index].vertex_index][4]):
                                if not str(vg) in Obj.vertex_groups:
                                    group = Obj.vertex_groups.new(name=str(vg))
                                else:
                                    group = Obj.vertex_groups[str(vg)]
                                # bone weights (3)
                                weight = m[1][mesh.loops[loop_index].vertex_index][3][i]
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
    return bpy.context.view_layer.objects.active


def load(operator, context, filepath=""):
    print("importing: {0}".format(filepath))
    bpy.context.view_layer.objects.active = None
    for obj in bpy.data.objects:
        obj.select_set(False)
    mesh = load_Mesh(filepath)
    skel = load_skel(find_skel_file(filepath))
    mod = mesh.modifiers.new("armature", 'ARMATURE')
    mod.object = skel
    mesh.parent = skel
    return {'FINISHED'}