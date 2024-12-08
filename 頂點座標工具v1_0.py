bl_info = {
    "name": "頂點座標工具",
    "author": "破穗",
    "version": (1, 0),
    "blender": (4, 2, 4),
    "location": "3D Viewport > Sidebar (N) > Item 標籤",
    "description": "提供複製與貼上網格/曲線/骨架座標的工具",
    "category": "3D View",
}

import bpy
import bmesh
from mathutils import Vector

# 工具函數
def get_selected_element_count(context):
    obj = context.object
    if obj.type == 'MESH' and context.mode == 'EDIT_MESH':
        bm = bmesh.from_edit_mesh(obj.data)
        return len([v for v in bm.verts if v.select])
    elif obj.type == 'CURVE' and context.mode == 'EDIT_CURVE':
        selected_points = []
        for spline in obj.data.splines:
            if spline.type == 'BEZIER':
                selected_points.extend(p for p in spline.bezier_points if p.select_control_point)
            else:
                selected_points.extend(p for p in spline.points if p.select)
        return len(selected_points)
    elif obj.type == 'ARMATURE' and context.mode in {'EDIT_ARMATURE', 'POSE'}:
        bones = context.selected_bones if context.mode == 'EDIT_ARMATURE' else context.selected_pose_bones
        return len(bones)
    return 0

def get_selected_coordinates(context, mode):
    obj = context.object
    if obj.type == 'MESH' and context.mode == 'EDIT_MESH':
        bm = bmesh.from_edit_mesh(obj.data)
        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            return None, "未選取任何頂點"
        coord = selected_verts[0].co if len(selected_verts) == 1 else \
            sum((v.co for v in selected_verts), Vector()) / len(selected_verts)
        return obj.matrix_world @ coord if mode == 'GLOBAL' else coord, None
    elif obj.type == 'CURVE' and context.mode == 'EDIT_CURVE':
        selected_points = []
        for spline in obj.data.splines:
            if spline.type == 'BEZIER':
                selected_points.extend(p for p in spline.bezier_points if p.select_control_point)
            else:
                selected_points.extend(p for p in spline.points if p.select)
        if not selected_points:
            return None, "未選取任何控制點"
        coord = selected_points[0].co.xyz if len(selected_points) == 1 else \
            sum((p.co.xyz for p in selected_points), Vector()) / len(selected_points)
        return obj.matrix_world @ coord if mode == 'GLOBAL' else coord, None
    elif obj.type == 'ARMATURE' and context.mode in {'EDIT_ARMATURE', 'POSE'}:
        bones = context.selected_bones if context.mode == 'EDIT_ARMATURE' else context.selected_pose_bones
        if not bones:
            return None, "未選取任何骨骼"
        bone = bones[-1]
        coord = bone.head if context.mode == 'EDIT_ARMATURE' else bone.head
        return obj.matrix_world @ coord if mode == 'GLOBAL' else coord, None
    return None, "目前物件類型或模式不支援"

# 運算符類
class CopyCoordinatesOperator(bpy.types.Operator):
    bl_idname = "object.copy_coordinates"
    bl_label = "複製座標"

    def execute(self, context):
        coord, error = get_selected_coordinates(context, context.scene.coordinate_mode)
        if error:
            self.report({'WARNING'}, error)
            return {'CANCELLED'}
        context.scene.copied_coordinates = coord
        self.report({'INFO'}, f"複製了座標 {tuple(coord)} ({context.scene.coordinate_mode})")
        return {'FINISHED'}

from mathutils import Vector

class PasteCoordinatesOperator(bpy.types.Operator):
    """貼上座標"""
    bl_idname = "object.paste_coordinates"
    bl_label = "貼上座標"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        coord = context.scene.copied_coordinates
        if coord is None:
            self.report({'WARNING'}, "沒有複製的座標")
            return {'CANCELLED'}

        # 確保 coord 是 Vector 類型，便於矩陣乘法
        coord = Vector(coord)

        obj = context.object

        # 處理 MESH 物件
        if obj.type == 'MESH' and context.mode == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(obj.data)
            selected_verts = [v for v in bm.verts if v.select]
            if not selected_verts:
                self.report({'WARNING'}, "未選取任何頂點")
                return {'CANCELLED'}
            for v in selected_verts:
                v.co = (obj.matrix_world.inverted() @ coord
                        if context.scene.coordinate_mode == 'GLOBAL' else coord)
            bmesh.update_edit_mesh(obj.data)
            count = len(selected_verts)
            coord_str = f"({coord[0]:.2f}, {coord[1]:.2f}, {coord[2]:.2f})"
            self.report({'INFO'}, f"貼上給 {count} 個頂點座標 {coord_str} ({'全域' if context.scene.coordinate_mode == 'GLOBAL' else '區域'})")
            return {'FINISHED'}

        # 處理 CURVE 物件
        elif obj.type == 'CURVE' and context.mode == 'EDIT_CURVE':
            splines = obj.data.splines
            selected_points = []
            for spline in splines:
                if spline.type == 'BEZIER':
                    selected_points.extend(p for p in spline.bezier_points if p.select_control_point)
                else:
                    selected_points.extend(p for p in spline.points if p.select)
            if not selected_points:
                self.report({'WARNING'}, "未選取任何控制點")
                return {'CANCELLED'}
            for point in selected_points:
                point.co.xyz = (obj.matrix_world.inverted() @ coord
                                if context.scene.coordinate_mode == 'GLOBAL' else coord)
            count = len(selected_points)
            coord_str = f"({coord[0]:.2f}, {coord[1]:.2f}, {coord[2]:.2f})"
            self.report({'INFO'}, f"貼上給 {count} 個控制點座標 {coord_str} ({'全域' if context.scene.coordinate_mode == 'GLOBAL' else '區域'})")
            return {'FINISHED'}

        # 處理 ARMATURE 物件
        elif obj.type == 'ARMATURE' and context.mode in {'EDIT_ARMATURE', 'POSE'}:
            bones = context.selected_bones if context.mode == 'EDIT_ARMATURE' else context.selected_pose_bones
            if not bones:
                self.report({'WARNING'}, "未選取任何骨骼")
                return {'CANCELLED'}
            for bone in bones:
                if context.mode == 'EDIT_ARMATURE':
                    bone.head = (obj.matrix_world.inverted() @ coord
                                 if context.scene.coordinate_mode == 'GLOBAL' else coord)
                elif context.mode == 'POSE':
                    bone.location = (obj.matrix_world.inverted() @ coord
                                     if context.scene.coordinate_mode == 'GLOBAL' else coord)
            count = len(bones)
            coord_str = f"({coord[0]:.2f}, {coord[1]:.2f}, {coord[2]:.2f})"
            self.report({'INFO'}, f"貼上給 {count} 個骨骼頭部座標 {coord_str} ({'全域' if context.scene.coordinate_mode == 'GLOBAL' else '區域'})")
            return {'FINISHED'}

        self.report({'WARNING'}, "目前物件類型或模式不支援貼上功能")
        return {'CANCELLED'}

class SwitchCoordinateModeOperator(bpy.types.Operator):
    """切換座標模式"""
    bl_idname = "object.switch_coordinate_mode"
    bl_label = "切換座標模式"

    target_mode: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.coordinate_mode = self.target_mode
        self.report({'INFO'}, f"切換到 {'全域' if self.target_mode == 'GLOBAL' else '區域'}座標模式")
        return {'FINISHED'}

# UI 面板
class CopyPasteCoordinatesPanel(bpy.types.Panel):
    bl_label = "複製與貼上座標"
    bl_idname = "VIEW3D_PT_copy_paste_coordinates"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    def draw(self, context):
        layout = self.layout
        
        element_count = get_selected_element_count(context)
        if element_count == 0:
            layout.label(text="請選取一個或多個頂點/控制點/骨骼")
            return
        
        row = layout.row(align=True)
        row.operator(SwitchCoordinateModeOperator.bl_idname, text="全域座標", depress=(context.scene.coordinate_mode == 'GLOBAL')).target_mode = 'GLOBAL'
        row.operator(SwitchCoordinateModeOperator.bl_idname, text="區域座標", depress=(context.scene.coordinate_mode == 'LOCAL')).target_mode = 'LOCAL'
        layout.separator()
        layout.operator(CopyCoordinatesOperator.bl_idname)
        layout.operator(PasteCoordinatesOperator.bl_idname)

# 註冊與反註冊
classes = (
    CopyCoordinatesOperator,
    PasteCoordinatesOperator,
    SwitchCoordinateModeOperator,
    CopyPasteCoordinatesPanel,
)

def register():
    bpy.types.Scene.copied_coordinates = bpy.props.FloatVectorProperty(size=3, name="複製座標")
    bpy.types.Scene.coordinate_mode = bpy.props.EnumProperty(
        items=[('LOCAL', "區域座標", ""), ('GLOBAL', "全域座標", "")],
        name="座標模式",
        default='LOCAL'
    )
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.copied_coordinates
    del bpy.types.Scene.coordinate_mode

if __name__ == "__main__":
    register()
