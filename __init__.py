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

import bpy
import cycles

bl_info = {
    "name": "Realtime Materials Baker",
    "author": "Joshua Blömer",
    "description": "",
    "blender": (2, 83, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic"
}
data = {
    'bl_label': "RtmbBakeSettings",
    'bl_idname': "rtmb.BakeSettings",
    '__annotations__': {
                typeName.name: bpy.props.BoolProperty(name=typeName.name)
                for typeName in cycles.properties.CyclesRenderSettings.bl_rna.properties['bake_type'].enum_items_static
    }
}


class RTMB_props(bpy.types.PropertyGroup):
    xSize: bpy.props.IntProperty(name="Resolution x")
    ySize: bpy.props.IntProperty(name="y")
    path: bpy.props.StringProperty(
        name="",
        description="Path to Directory",
        default="C:\\TEMP\\baked",
        maxlen=1024,
        subtype='DIR_PATH')


class MATERIAL_PT_rtmb_panel(bpy.types.Panel):
    bl_idname = "MATERIAL_PT_rtmb_panel"
    bl_label = "Realtime Materials Baker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Realtime Materials"

    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene.rtmb_props, "path",
                    text="File Path")
        excluded_keys = ["use_object_uv"]

        for key in context.scene.rtmb_props.__annotations__.keys():
            if key not in excluded_keys:
                layout.prop(context.scene.rtmb_props, key)
        layout.split()
        # layout.prop(context.scene.rtmb_props, "use_object_uv")
        layout.operator("object.bake", icon='RENDER_STILL')


classes = (
    MATERIAL_PT_rtmb_panel,
    BakeSettings,
)


def register():
    # bpy.utils.register_class(my_new_type)
    for cls in classes:
        bpy.utils.register_class(cls)
    print(
        cycles.properties.CyclesRenderSettings.bl_rna.properties['bake_type'].enum_items_static[0].name)
    bpy.types.Scene.rtmb_props = bpy.props.PointerProperty(type=BakeSettings)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    # bpy.utils.unregister_class(my_new_type)
