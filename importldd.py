import bpy


def read_some_data(context, filepath, use_some_setting):
    print("running read_some_data...")
    f = open(filepath, 'r', encoding='utf-8')
    data = f.read()
    f.close()

    # would normally load the data here
    print(data)

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ImportLDDOps(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_description  = "Import LEGO Digital Designer scenes (.lxf/.lxfml)"
    bl_idname = "import_scene.importldd"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import LDD scenes"

    # ImportHelper mixin class uses this
    filename_ext = ".lxf"

    filter_glob: StringProperty(
        default="*.lxf;*.lxfml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        return read_some_data(context, self.filepath, self.use_setting)


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
