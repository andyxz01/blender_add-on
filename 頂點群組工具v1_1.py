bl_info = {
    "name": "頂點權重設置工具與工具包",
    "author": "破穗",
    "version": (1, 1),
    "blender": (4, 2, 4),
    "location": "3D Viewport > Sidebar (N) > Item 標籤",
    "description": "設置頂點群組權重並刪除空白頂點群組的工具",
    "category": "Mesh",
}

import bpy
import bmesh

class SetWeightOperator(bpy.types.Operator):
    """設定選取頂點的權重並歸一化其他頂點群組權重"""
    bl_idname = "object.set_vertex_weight_extended"
    bl_label = "設定頂點權重"
    bl_options = {'REGISTER', 'UNDO'}

    weight: bpy.props.FloatProperty(
        name="Weight",
        default=1.0,
        min=0.0,
        max=1.0,
        description="要設定的權重值"
    )

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "活躍物件不是網格類型")
            return {'CANCELLED'}

        if not obj.vertex_groups.active:
            self.report({'ERROR'}, "沒有選取的頂點群組")
            return {'CANCELLED'}

        vg = obj.vertex_groups.active

        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "請進入編輯模式")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()

        # 收集選取頂點的索引
        selected_indices = [v.index for v in bm.verts if v.select]

        if not selected_indices:
            self.report({'ERROR'}, "沒有選取頂點")
            return {'CANCELLED'}

        # 切換到對象模式以修改頂點權重
        bpy.ops.object.mode_set(mode='OBJECT')

        for vert_index in selected_indices:
            vertex = obj.data.vertices[vert_index]
            all_weights = vertex.groups

            # 收集所有群組及其權重
            groups_weights = {}
            for g in all_weights:
                group = obj.vertex_groups[g.group]
                groups_weights[group.name] = g.weight

            # 設定目標群組的權重
            target_group_name = vg.name
            target_weight = self.weight
            groups_weights[target_group_name] = target_weight

            # 計算其他群組的總權重
            other_total = sum(weight for grp, weight in groups_weights.items() if grp != target_group_name)

            # 設定目標群組的權重
            vg.add([vert_index], target_weight, 'REPLACE')

            if (1.0 - target_weight) > 0 and other_total > 0:
                # 計算縮放比例
                scale = (1.0 - target_weight) / other_total
                for grp, weight in groups_weights.items():
                    if grp != target_group_name:
                        new_weight = weight * scale
                        # 確保新權重在 [0,1] 範圍內
                        new_weight = max(min(new_weight, 1.0), 0.0)
                        obj.vertex_groups[grp].add([vert_index], new_weight, 'REPLACE')
            else:
                # 無法歸一化，將其他群組權重設為0
                for grp in groups_weights:
                    if grp != target_group_name:
                        obj.vertex_groups[grp].add([vert_index], 0.0, 'REPLACE')

        # 返回編輯模式並更新 BMesh
        bpy.ops.object.mode_set(mode='EDIT')
        bmesh.update_edit_mesh(mesh)

        self.report({'INFO'}, f"設置了 {len(selected_indices)} 個頂點的權重為 {self.weight}")
        return {'FINISHED'}


class DeleteEmptyVertexGroupsOperator(bpy.types.Operator):
    """刪除所選網格物件中的空白頂點群組"""
    bl_idname = "object.delete_empty_vertex_groups"
    bl_label = "刪除空白頂點群組"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "沒有選取物件")
            return {'CANCELLED'}

        deleted_groups = []

        for obj in selected_objects:
            if obj.type != 'MESH':
                continue

            # 收集即將刪除的群組名稱
            empty_groups = []
            for vg in obj.vertex_groups:
                # 檢查是否有任何頂點分配了權重
                has_weight = False
                for vertex in obj.data.vertices:
                    for g in vertex.groups:
                        if g.group == vg.index and g.weight > 0.0:
                            has_weight = True
                            break
                    if has_weight:
                        break
                if not has_weight:
                    empty_groups.append(vg.name)

            # 刪除空白群組並記錄
            for group_name in empty_groups:
                vg = obj.vertex_groups.get(group_name)
                if vg:
                    obj.vertex_groups.remove(vg)
                    deleted_groups.append((obj.name, group_name))

        if deleted_groups:
            message = "刪除空白頂點群組:\n"
            for obj_name, group_name in deleted_groups:
                message += f"- {obj_name}: {group_name}\n"
            self.report({'INFO'}, message)
        else:
            self.report({'INFO'}, "沒有找到空白的頂點群組。")

        return {'FINISHED'}


class VertexWeightPanel(bpy.types.Panel):
    """在3D視窗的側邊欄 Item 標籤下創建一個頂點權重面板"""
    bl_label = "頂點權重工具"
    bl_idname = "VIEW3D_PT_vertex_weight_tool_extended"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
            if obj.vertex_groups.active:
                layout.label(text="頂點權重設定:")

                # 上方兩個按鈕：0 和 1
                row = layout.row(align=True)
                row.operator("object.set_vertex_weight_extended", text="0").weight = 0.0
                row.operator("object.set_vertex_weight_extended", text="1").weight = 1.0

                layout.separator()

                # 下方按鈕：0.1 到 0.9
                row = layout.row(align=True)
                for w in [0.1 * j for j in range(1, 10)]:
                    row.operator("object.set_vertex_weight_extended", text=f"{w:.1f}").weight = w

            else:
                layout.label(text="請選擇一個頂點群組")
        else:
            layout.label(text="請在編輯模式下選擇一個網格物件並選取頂點")


class ToolkitPanel(bpy.types.Panel):
    """在3D視窗的側邊欄 Item 標籤下創建一個工具包面板"""
    bl_label = "工具包"
    bl_idname = "VIEW3D_PT_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"

    def draw(self, context):
        layout = self.layout

        layout.label(text="選取單個或多個網格物件")
        layout.operator("object.delete_empty_vertex_groups", text="刪除空白頂點群組")


def register():
    bpy.utils.register_class(SetWeightOperator)
    bpy.utils.register_class(DeleteEmptyVertexGroupsOperator)
    bpy.utils.register_class(VertexWeightPanel)
    bpy.utils.register_class(ToolkitPanel)


def unregister():
    bpy.utils.unregister_class(SetWeightOperator)
    bpy.utils.unregister_class(DeleteEmptyVertexGroupsOperator)
    bpy.utils.unregister_class(VertexWeightPanel)
    bpy.utils.unregister_class(ToolkitPanel)


if __name__ == "__main__":
    register()