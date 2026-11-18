// @ts-check
/**
 * 面板与状态栏：详情面板、图层开关、缩放/中心显示。
 * 骨架：仅导出占位；实现见 TASK-0007。
 */

/** @param {unknown} annotation */
export function renderDetail(annotation) {
  throw new Error('详情面板尚未实现（TASK-0007）');
}

/** @param {string} text */
export function setStatus(text) {
  const el = document.getElementById('statusbar');
  if (el) el.textContent = text;
}
