# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "GTA V Model importer (.otd)",
    "author" : "Lendo Keilbaum",
    "description" : "Import GTA V models (.otd)",
    "location": "File > Import",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "",
    "warning" : "",
    "category" : "Import"
}

if "bpy" in locals():
    import importlib
    if "import_mesh" in locals():
        importlib.reload(import_mesh)
else:
    from . import import_mesh



import bpy
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        axis_conversion,
        )



class ImportOTD(bpy.types.Operator, ImportHelper):
    """Import from OTD file format (.otd)"""
    bl_idname = "import_scene.otd"
    bl_label = 'Import otd'
    bl_options = {'UNDO'}

    filename_ext = ".mesh"

    def execute(self, context):
        keywords = self.as_keywords()
        return import_mesh.load(self, context, **keywords)

# Add to a menu
def menu_func_import(self, context):
    self.layout.operator(ImportOTD.bl_idname, text="GTA V Model (.mesh)")


def register():
    bpy.utils.register_class(ImportOTD)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportOTD)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()