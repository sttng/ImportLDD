# -*- coding: utf-8 -*-

import bpy

from . import importldd

bl_info = {
    "name": "Import LDD",
    "description": "Import LDD scenes in .lxf .lxfml formats",
    "author": "gmail.com>",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "location": "File > Import",
    "warning": "",
    "wiki_url": "https://github.com/",
    "tracker_url": "https://github.com/",
    "category": "Import-Export"
    }


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportLDDOps.bl_idname, text="LEGO Digital Designer (.lxf/.lxfml)")


def register():
    bpy.utils.register_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_scene.importldd('INVOKE_DEFAULT')
