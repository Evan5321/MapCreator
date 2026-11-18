// @ts-check
/**
 * Terra Draw 集成：模式切换、撤销/重做、保存提交。
 * 骨架：仅声明契约；实现见 TASK-0009。
 *
 * 关键映射（D-015）：
 *   点工具  -> 只创建标注（ann 记录），不生成 GeoJSON 几何
 *   线/面   -> 先写几何，再可选关联标注
 */

export const TOOLS = ['select', 'point', 'linestring', 'polygon', 'rectangle', 'freehand'];

/**
 * @param {import('maplibre-gl').Map} map
 * @param {{ onChange?: (features: unknown[]) => void }} [options]
 */
export function createEditor(map, options = {}) {
  throw new Error('编辑器尚未实现（TASK-0009）');
}

/** 保存草稿（需带 revision；409 表示冲突）。 */
export async function save() {
  throw new Error('保存尚未实现（TASK-0009）');
}
