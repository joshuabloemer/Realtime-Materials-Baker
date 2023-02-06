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
import _bpy
import cycles
import bmesh

bl_info = {
    "name": "Realtime Materials Baker",
    "author": "Ducky 3D, Joshua Blömer",
    "description": "A simple addon that simplifies the process of baking textures",
    "blender": (2, 83, 0),
    "version": (0, 9, 0),
    "location": "N-Panel > Realtim Materials",
    "warning": "",
    "category": "Material"
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
    xSize: bpy.props.IntProperty(
        name="Resolution X", description="Number of horizontal pixels in the baked image", default=1024)

    ySize: bpy.props.IntProperty(
        name="Resolution Y", description="Number of vertical pixels in the baked image", default=1024)

    path: bpy.props.StringProperty(
        name="File path",
        description="The directory baked images will be saved in",
        default="C:\\TEMP\\baked",
        maxlen=1024,
        subtype='DIR_PATH')

    use_uv: bpy.props.BoolProperty(
        name="Use UV",
        description="""Bake textures to the uv maps of the selected objects
If this is unchecked the textures will be baked as a square image""",
        default=True)


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

        type_box = layout.box()
        type_box.label(text="Included bake types")
        type_box.use_property_split = False

        for key in context.scene.rtmb_types.__annotations__.keys():
            type_box.prop(context.scene.rtmb_types, key)

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

        use_uv: bpy.props.BoolProperty()

        def execute(self, context):
            if not self.use_uv:
                mesh = context.scene.rtmb_plane.data
                bpy.data.objects.remove(context.scene.rtmb_plane)
                bpy.data.meshes.remove(mesh)
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
    bl_options = {'INTERNAL'}

    bake_type: bpy.props.StringProperty(default="AO")
    use_uv: bpy.props.BoolProperty(default=True)

    def execute(self, context):

        bake_obj = context.scene.rtmb_queue[0].object
        if not self.use_uv:
            obj = context.scene.rtmb_plane
            obj.data.materials.append(bake_obj.data.materials[0])

        else:
            obj = bake_obj

        context.scene.rtmb_queue.remove(0)

        context.scene.rtmb_obj = obj

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

        for selected in context.selected_objects:
            selected.select_set(False)

        obj.select_set(True)

        if self.use_uv:
            print(f"Baking {obj.name} {self.bake_type}")
        else:
            print(f"Baking {mat.name} {self.bake_type}")

        return {"FINISHED"}


class RTMB_OT_bake_post(bpy.types.Operator):
    bl_idname = "rtmb.bake_post"
    bl_label = "Bake Settings Change"
    bl_options = {'INTERNAL'}

    bake_type: bpy.props.StringProperty(default="AO")
    use_uv: bpy.props.BoolProperty(default=True)

    def execute(self, context):

        img = context.scene.rtmb_img
        obj = context.scene.rtmb_obj
        mat = obj.data.materials[0]
        if self.use_uv:
            path = f'{context.scene.rtmb_props.path}\\{obj.name}_{self.bake_type}.png'
        else:
            path = f'{context.scene.rtmb_props.path}\\{mat.name}_{self.bake_type}.png'

        img.save_render(filepath=path)

        # Clean up nodes
        for n in mat.node_tree.nodes:
            if n.name == 'Bake_node':
                mat.node_tree.nodes.remove(n)

        bpy.data.images.remove(img)

        # remove baked material from plane
        if not self.use_uv:
            context.scene.rtmb_plane.data.materials.pop()

        return {"FINISHED"}


# main baking operator
class WM_OT_bake_modal(bpy.types.Operator):
    bl_idname = "rtmb.bake"
    bl_label = "Bake"
    bl_description = "Bake the selected texture maps to file"
    bl_options = {'REGISTER'}

    is_running = False

    @classmethod
    def poll(cls, context):
        for object in context.selected_objects:
            if object.material_slots:
                break
        else:
            return False

        bake_types = context.scene.rtmb_types
        for key in bake_types.__annotations__.keys():
            if getattr(bake_types, key):
                return context.selected_objects and context.scene.render.engine == 'CYCLES' and not cls.is_running
        return False

    def modal(self, context, event):

        if self.dns.get('bake_set_finished'):
            wm = context.window_manager
            wm.event_timer_remove(self.refresh)
            self.report({'INFO'}, "Finished baking")
            del bpy.app.driver_namespace['bake_set_finished']
            cls = self.__class__
            cls.is_running = False

            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        cls = self.__class__
        cls.is_running = True

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

        # remove objects without materials from selection

        selected_backup = []

        for object in context.selected_objects:
            if not object.material_slots:
                object.select_set(False)
            else:
                selected_backup.append(object)

        if not context.scene.rtmb_props.use_uv:
            bpy.ops.mesh.primitive_plane_add()
            obj = context.active_object
            obj.name = "RTMB_TEX_BAKE_OBJ"
            context.scene.rtmb_plane = obj

        for object in context.selected_objects:
            object.select_set(False)

        for object in selected_backup:
            object.select_set(True)

        # for some reason an object with materials needs to be active
        context.view_layer.objects.active = context.selected_objects[0]

        for object in context.selected_objects:
            bake_obj = object

            for bake_type in includedTypes:

                # sub-operators can be stored on the macro itself
                setattr(macro, f"bake_pre_{bake_obj.name}_{bake_type}",
                        define(macro, "RTMB_OT_bake_pre"))

                setattr(macro, f"bake_{bake_obj.name}_{bake_type}", define(
                    macro, sub_op))

                setattr(macro, f"bake_post_{bake_obj.name}_{bake_type}",
                        define(macro, "RTMB_OT_bake_post"))

                pre = getattr(macro, f"bake_pre_{bake_obj.name}_{bake_type}")
                pre.properties.bake_type = bake_type
                pre.properties.use_uv = context.scene.rtmb_props.use_uv

                item = context.scene.rtmb_queue.add()
                item.object = bake_obj

                bake = getattr(macro, f"bake_{bake_obj.name}_{bake_type}")
                bake.properties.type = bake_type

                post = getattr(
                    macro, f"bake_post_{bake_obj.name}_{bake_type}")
                post.properties.bake_type = bake_type
                post.properties.use_uv = context.scene.rtmb_props.use_uv

        # define a last sub-op that tells the modal the bakes are done
        setattr(macro, "finished", define(macro, 'WM_OT_bake_set_finished'))
        finished = getattr(macro, "finished")
        finished.properties.use_uv = context.scene.rtmb_props.use_uv

        # 'INVOKE_DEFAULT' keeps the ui responsive. this is propagated onto the sub-ops
        bpy.ops.object.bake_macro('INVOKE_DEFAULT')

        wm = context.window_manager
        # timer event needed to refresh the macro between bakes
        self.refresh = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class ObjList(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(
        name="Object",
        type=bpy.types.Object,
    )


classes = (
    MATERIAL_PT_rtmb_panel,
    RTMB_OT_bake_pre,
    RTMB_OT_bake_post,
    WM_OT_bake_modal,
    RTMB_props,
    ObjList,
    IncludedBakeTypes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.rtmb_props = bpy.props.PointerProperty(type=RTMB_props)
    bpy.types.Scene.rtmb_types = bpy.props.PointerProperty(
        type=IncludedBakeTypes)
    bpy.types.Scene.rtmb_obj = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.rtmb_plane = bpy.props.PointerProperty(
        type=bpy.types.Object)
    bpy.types.Scene.rtmb_queue = bpy.props.CollectionProperty(type=ObjList)
    bpy.types.Scene.rtmb_img = bpy.props.PointerProperty(type=bpy.types.Image)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
