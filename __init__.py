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

import typing
import bpy
import _bpy
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
    'bl_idname': "rtmb.IncludedBakeTypes",
    '__annotations__': {
                typeName.name: bpy.props.BoolProperty(name=typeName.name)
                for typeName in cycles.properties.CyclesRenderSettings.bl_rna.properties['bake_type'].enum_items_static
    }
}

IncludedBakeTypes = type("IncludedBakeTypes", (bpy.types.PropertyGroup,), data)


class RTMB_props(bpy.types.PropertyGroup):
    xSize: bpy.props.IntProperty(name="X", default=1024)
    ySize: bpy.props.IntProperty(name="Y", default=1024)
    path: bpy.props.StringProperty(
        name="",
        description="Path to Directory",
        default="C:\\TEMP\\baked",
        maxlen=1024,
        subtype='DIR_PATH')
    use_uv: bpy.props.BoolProperty(name="Use UV", default=True)


class MATERIAL_PT_rtmb_panel(bpy.types.Panel):
    bl_idname = "MATERIAL_PT_rtmb_panel"
    bl_label = "Realtime Materials Baker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Realtime Materials"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(context.scene.rtmb_props, "path",
                    text="File Path")

        col = layout.column(align=True)
        col.prop(context.scene.rtmb_props, "xSize", text="Resolution X")
        col.prop(context.scene.rtmb_props, "ySize", text="Y")

        layout.prop(context.scene.rtmb_props, "use_uv")

        typeBox = layout.box()
        typeBox.label(text="Included bake types")
        typeBox.use_property_split = False

        for key in context.scene.rtmb_types.__annotations__.keys():
            typeBox.prop(context.scene.rtmb_types, key)

        layout.split()

        layout.operator("rtmb.bake", icon='RENDER_STILL')

# mostly undocumented api features, see here for an explanation:
# https://devtalk.blender.org/t/question-about-ui-lock-ups-when-running-a-python-script/6406/10


def init_macro():
    from bpy.types import Macro
    from bpy.utils import (
        register_class,
        unregister_class)

    class OBJECT_OT_bake_macro(Macro):
        bl_idname = "object.bake_macro"
        bl_label = "Bake Macro"

    class WM_OT_set_finished(bpy.types.Operator):
        bl_idname = "wm.bake_set_finished"
        bl_label = "Bake Set Finished"
        bl_options = {'INTERNAL'}

        def execute(self, context):
            dns = bpy.app.driver_namespace
            dns['bake_set_finished'] = True
            return {'FINISHED'}

    # need to re-register macro to support
    # changing sub-operator properties
    if hasattr(bpy.types, "OBJECT_OT_bake_macro"):
        unregister_class(bpy.types.OBJECT_OT_bake_macro)

    register_class(OBJECT_OT_bake_macro)
    if not hasattr(bpy.types, "WM_OT_set_finished"):
        register_class(WM_OT_set_finished)
    return bpy.types.OBJECT_OT_bake_macro


class RTMB_OT_bake_pre(bpy.types.Operator):
    bl_idname = "rtmb.bake_pre"
    bl_label = "Bake Settings Change"
    bl_options = {'REGISTER'}

    bake_type: bpy.props.StringProperty(default="AO")
    use_uv: bpy.props.BoolProperty(default=False)

    def execute(self, context):

        print(f"Baking {bpy.types.Scene.rtmb_obj.name} {self.bake_type}")

        obj = context.scene.rtmb_obj

        image_name = obj.name + '_' + self.bake_type + '_Baked'
        img = bpy.data.images.new(
            image_name, context.scene.rtmb_props.xSize, context.scene.rtmb_props.ySize)
        context.scene.rtmb_img = img
        mat = obj.data.materials[0]
        mat.use_nodes = True  # Here it is assumed that the materials have been created with nodes, otherwise it would not be possible to assign a node for the Bake, so this step is a bit useless
        nodes = mat.node_tree.nodes
        texture_node = nodes.new('ShaderNodeTexImage')
        texture_node.name = 'Bake_node'
        texture_node.select = True
        nodes.active = texture_node
        texture_node.image = img  # Assign the image to the node

        return {"FINISHED"}


class RTMB_OT_bake_post(bpy.types.Operator):
    bl_idname = "rtmb.bake_post"
    bl_label = "Bake Settings Change"
    bl_options = {'REGISTER'}

    bake_type: bpy.props.StringProperty(default="AO")
    use_uv: bpy.props.BoolProperty(default=False)

    def execute(self, context):

        img = context.scene.rtmb_img
        obj = context.scene.rtmb_obj
        img.save_render(
            filepath=f'{context.scene.rtmb_props.path}\\{obj.name}_{self.bake_type}.png')

        # Clean up nodes
        for mat in obj.data.materials:
            for n in mat.node_tree.nodes:
                if n.name == 'Bake_node':
                    mat.node_tree.nodes.remove(n)
        # this sould throw an exception access violation
        # bpy.data.images.remove(img)
        return {"FINISHED"}


# main baking operator
class WM_OT_bake_modal(bpy.types.Operator):
    bl_idname = "rtmb.bake"
    bl_label = "Bake"
    bl_description = "Bake the selected texture maps to file"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.scene.render.engine == 'CYCLES'

    def modal(self, context, event):

        if self.dns.get('bake_set_finished'):
            wm = context.window_manager
            wm.event_timer_remove(self.refresh)
            self.report({'INFO'}, "Finished baking")
            del bpy.app.driver_namespace['bake_set_finished']
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):

        macro = init_macro()

        # store a flag in driver name space so the modal knows when to end
        dns = bpy.app.driver_namespace
        dns['bake_set_finished'] = False
        self.dns = dns

        sub_op = 'OBJECT_OT_bake'
        define = _bpy.ops.macro_define
        # map display name to internal name
        map = {
            typeName.name: typeName.identifier
            for typeName in cycles.properties.CyclesRenderSettings.bl_rna.properties['bake_type'].enum_items_static}

        bakeTypes = context.scene.rtmb_types

        includedTypes = [map[key]
                         for key in bakeTypes.__annotations__.keys()
                         if getattr(bakeTypes, key)]

        for object in context.selected_objects:

            # skip to the next object if the current object has no material slots
            if not object.material_slots:
                continue

            for bakeType in includedTypes:

                # sub-operators can be stored on the macro itself
                setattr(macro, f"bake_pre_{object.name}_{bakeType}",
                        define(macro, "RTMB_OT_bake_pre"))

                setattr(macro, f"bake_{object.name}_{bakeType}", define(
                    macro, sub_op))

                setattr(macro, f"bake_post_{object.name}_{bakeType}",
                        define(macro, "RTMB_OT_bake_post"))

                pre = getattr(macro, f"bake_pre_{object.name}_{bakeType}")
                pre.properties.bake_type = bakeType
                bpy.types.Scene.rtmb_obj = object

                bake = getattr(macro, f"bake_{object.name}_{bakeType}")
                bake.properties.type = bakeType

                post = getattr(
                    macro, f"bake_post_{object.name}_{bakeType}")
                post.properties.bake_type = bakeType

        # define a last sub-op that tells the modal the bakes are done
        define(macro, 'WM_OT_bake_set_finished')

        # 'INVOKE_DEFAULT' keeps the ui responsive. this is propagated onto the sub-ops
        bpy.ops.object.bake_macro('INVOKE_DEFAULT')

        wm = context.window_manager
        # timer event needed to refresh the macro between bakes
        self.refresh = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


classes = (
    MATERIAL_PT_rtmb_panel,
    RTMB_OT_bake_pre,
    RTMB_OT_bake_post,
    WM_OT_bake_modal,
    RTMB_props,
    IncludedBakeTypes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.rtmb_props = bpy.props.PointerProperty(type=RTMB_props)
    bpy.types.Scene.rtmb_types = bpy.props.PointerProperty(
        type=IncludedBakeTypes)
    bpy.types.Scene.rtmb_obj = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.rtmb_img = bpy.props.PointerProperty(type=bpy.types.Image)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
