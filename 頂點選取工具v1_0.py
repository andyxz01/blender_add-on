bl_info = {
    "name": "頂點選取工具",
    "author": "破穗",
    "version": (1, 0),
    "blender": (4, 2, 4),
    "location": "3D Viewport > 工具列 > 選取 > 依軸向選取",
    "description": "依照設定的軸向(XYZ)選取頂點/控制點/骨骼,座標>=0或<=0的頂點",
    "category": "Mesh",
}

import bpy
from bpy.props import BoolProperty, EnumProperty


class OBJECT_OT_SelectVerticesByAxis(bpy.types.Operator):
    bl_idname = "object.select_vertices_by_axis"
    bl_label = "依軸向選取"
    bl_description = "依軸向選取頂點（支援網格、曲線與骨骼）"
    bl_options = {"REGISTER", "UNDO"}

    # 使用者設定屬性
    x_axis: BoolProperty(
        name="X軸",
        description="是否根據 X 軸選取",
        default=True
    )
    y_axis: BoolProperty(
        name="Y軸",
        description="是否根據 Y 軸選取",
        default=False
    )
    z_axis: BoolProperty(
        name="Z軸",
        description="是否根據 Z 軸選取",
        default=False
    )
    direction: EnumProperty(
        name="方向選擇",
        description="選取大於等於0或小於等於0的頂點",
        items=[
            ('POSITIVE', "大於等於0", "選取大於等於0的頂點"),
            ('NEGATIVE', "小於等於0", "選取小於等於0的頂點"),
        ],
        default='POSITIVE'
    )
    coord_mode: EnumProperty(
        name="座標模式",
        description="選擇座標系統模式",
        items=[
            ('LOCAL', "區域座標", "使用區域座標"),
            ('GLOBAL', "全域座標", "使用全域座標"),
        ],
        default='LOCAL'
    )

    def execute(self, context):
        # 檢查模式是否為編輯模式
        if context.mode not in {'EDIT_MESH', 'EDIT_CURVE', 'EDIT_ARMATURE'}:
            self.report({"WARNING"}, "此操作僅適用於編輯模式")
            return {'CANCELLED'}

        selected_objects = context.objects_in_mode
        if not selected_objects:
            self.report({"WARNING"}, "沒有選取任何物件")
            return {'CANCELLED'}

        axis_flags = (self.x_axis, self.y_axis, self.z_axis)
        if not any(axis_flags):
            self.report({"WARNING"}, "至少選擇一個軸向")
            return {'CANCELLED'}

        for obj in selected_objects:
            if obj.type == 'MESH':
                self.process_mesh(obj)
            elif obj.type == 'CURVE':
                self.process_curve(obj)
            elif obj.type == 'ARMATURE':
                self.process_armature(obj)
            else:
                self.report({"INFO"}, f"目前不支援物件類型: {obj.type}")

        self.report({"INFO"}, "軸向選取完成")
        return {'FINISHED'}

    def process_mesh(self, obj):
        """處理網格物件"""
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = obj.data

        axis_indices = [i for i, flag in enumerate((self.x_axis, self.y_axis, self.z_axis)) if flag]
        is_positive = self.direction == 'POSITIVE'

        for vertex in mesh.vertices:
            coord = vertex.co if self.coord_mode == 'LOCAL' else obj.matrix_world @ vertex.co
            select = all((coord[i] >= 0 if is_positive else coord[i] <= 0) for i in axis_indices)
            vertex.select = select

        bpy.ops.object.mode_set(mode='EDIT')

    def process_curve(self, obj):
        """處理曲線物件"""
        bpy.ops.object.mode_set(mode='OBJECT')
        curve = obj.data

        axis_indices = [i for i, flag in enumerate((self.x_axis, self.y_axis, self.z_axis)) if flag]
        is_positive = self.direction == 'POSITIVE'

        for spline in curve.splines:
            for point in spline.points:  # NURBS
                coord = point.co if self.coord_mode == 'LOCAL' else obj.matrix_world @ point.co
                select = all((coord[i] >= 0 if is_positive else coord[i] <= 0) for i in axis_indices)
                point.select = select
            for point in spline.bezier_points:  # Bezier
                coord = point.co if self.coord_mode == 'LOCAL' else obj.matrix_world @ point.co
                select = all((coord[i] >= 0 if is_positive else coord[i] <= 0) for i in axis_indices)
                point.select_control_point = select

        bpy.ops.object.mode_set(mode='EDIT')
  
    def process_armature(self, obj):
        """處理骨架物件"""
        armature = obj.data

        axis_indices = [i for i, flag in enumerate((self.x_axis, self.y_axis, self.z_axis)) if flag]
        is_positive = self.direction == 'POSITIVE'

        for bone in armature.edit_bones:
            # 判斷骨骼的 head 和 tail 是否符合條件
            coord_head = bone.head if self.coord_mode == 'LOCAL' else obj.matrix_world @ bone.head
            coord_tail = bone.tail if self.coord_mode == 'LOCAL' else obj.matrix_world @ bone.tail

            head_condition = all((coord_head[i] >= 0 if is_positive else coord_head[i] <= 0) for i in axis_indices)
            tail_condition = all((coord_tail[i] >= 0 if is_positive else coord_tail[i] <= 0) for i in axis_indices)

            # 根據條件選取骨骼
            bone.select = head_condition or tail_condition
            bone.select_head = head_condition
            bone.select_tail = tail_condition

# 定義功能加入選單
def menu_func(self, context):
    self.layout.operator(OBJECT_OT_SelectVerticesByAxis.bl_idname, text="依軸向選取")

# 註冊類別清單
classes = [
    OBJECT_OT_SelectVerticesByAxis,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(menu_func)  # 加入網格選單
    bpy.types.VIEW3D_MT_select_edit_curve.append(menu_func)  # 加入曲線選單
    bpy.types.VIEW3D_MT_select_edit_armature.append(menu_func)  # 加入骨架選單

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(menu_func)
    bpy.types.VIEW3D_MT_select_edit_curve.remove(menu_func)
    bpy.types.VIEW3D_MT_select_edit_armature.remove(menu_func)

if __name__ == "__main__":
    register()
