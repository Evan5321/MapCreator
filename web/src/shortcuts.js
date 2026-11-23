// @ts-check
/**
 * 快捷键：按 `KeyboardEvent.code` 识别，输入控件内不响应。
 * 组合键顺序固定为 Ctrl → Alt → Shift → code（例如 `Ctrl+Backslash`）。
 */

/**
 * 注册快捷键表，返回解绑函数。
 * @param {Record<string, (event: KeyboardEvent) => void>} table
 * @returns {() => void}
 */
export function bindShortcuts(table) {
  const handler = (event) => {
    if (isEditable(event.target)) return;
    const action = table[comboOf(event)];
    if (!action) return;
    event.preventDefault();
    action(event);
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}

/**
 * @param {KeyboardEvent} event
 * @returns {string}
 */
export function comboOf(event) {
  const parts = [];
  if (event.ctrlKey || event.metaKey) parts.push('Ctrl');
  if (event.altKey) parts.push('Alt');
  if (event.shiftKey) parts.push('Shift');
  parts.push(event.code);
  return parts.join('+');
}

/**
 * 焦点在输入框/文本域/下拉框或可编辑区域时不拦截按键。
 * @param {EventTarget | null} target
 */
export function isEditable(target) {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
}
