// @ts-check
/**
 * 会话内快照历史：撤销/重做栈。
 * 快照由调用方给出（标注草稿 + 几何集合），本模块只负责去重、裁剪与游标移动。
 */

/** 单条历史记录。 */
/**
 * @typedef {{ undo: string[], redo: string[], current: string | null, limit: number }} HistoryState
 */

/**
 * 创建快照历史。
 * @param {{ limit?: number }} [options]
 */
export function createHistory(options = {}) {
  const limit = Math.max(1, options.limit ?? 100);
  /** @type {string[]} */
  const undoStack = [];
  /** @type {string[]} */
  const redoStack = [];
  /** @type {string | null} */
  let current = null;

  /**
   * 记录新状态。与栈顶相同则忽略。
   * @param {unknown} snapshot
   * @returns {boolean} 是否真的入栈
   */
  function push(snapshot) {
    const serialized = serialize(snapshot);
    if (current === serialized) return false;
    if (current !== null) {
      undoStack.push(current);
      if (undoStack.length > limit) undoStack.shift();
    }
    current = serialized;
    redoStack.length = 0;
    return true;
  }

  /**
   * 回到上一个状态。
   * @returns {unknown | null} 反序列化后的快照；无可撤销时返回 null
   */
  function undo() {
    if (undoStack.length === 0) return null;
    if (current !== null) redoStack.push(current);
    current = /** @type {string} */ (undoStack.pop());
    return JSON.parse(current);
  }

  /**
   * 前进到下一个状态。
   * @returns {unknown | null}
   */
  function redo() {
    if (redoStack.length === 0) return null;
    if (current !== null) undoStack.push(current);
    current = /** @type {string} */ (redoStack.pop());
    return JSON.parse(current);
  }

  /** @param {unknown} snapshot 重置基线（清空两端栈）。 */
  function reset(snapshot) {
    undoStack.length = 0;
    redoStack.length = 0;
    current = serialize(snapshot);
  }

  function clear() {
    undoStack.length = 0;
    redoStack.length = 0;
    current = null;
  }

  return {
    push,
    undo,
    redo,
    reset,
    clear,
    canUndo: () => undoStack.length > 0,
    canRedo: () => redoStack.length > 0,
    /** 可撤销步数。 */
    depth: () => undoStack.length,
    /** 当前序列化状态（调试用）。 */
    current: () => current,
  };
}

/**
 * @param {unknown} value
 * @returns {string}
 */
function serialize(value) {
  return JSON.stringify(value);
}
