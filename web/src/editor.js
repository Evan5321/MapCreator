// @ts-check
/**
 * 编辑器（阶段 A）：Terra Draw 装配、工具切换、内存草稿、撤销/重做与导出。
 *
 * 关键映射（D-015）：
 *   点工具  -> 只创建标注（anno.*，带 lon/lat，不生成几何）
 *   线/面   -> 创建几何（geo.*），并挂一个 label_mode=line 的标注
 *
 * 本阶段不写任何后端接口，草稿只在浏览器内存，导出 JSON 交付。
 */

import {
  TerraDraw,
  TerraDrawLineStringMode,
  TerraDrawPointMode,
  TerraDrawPolygonMode,
  TerraDrawRectangleMode,
  TerraDrawRenderMode,
  TerraDrawSelectMode,
} from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';
import { createHistory } from './history.js';
import { createInspector } from './inspector.js';
import { section } from './panels.js';
import { bindShortcuts } from './shortcuts.js';

const ACCENT = '#4da3ff';

const TOOLS = [
  { tool: 'select', label: '选择', key: 'V' },
  { tool: 'point', label: '点', key: 'P' },
  { tool: 'linestring', label: '线', key: 'L' },
  { tool: 'polygon', label: '面', key: 'G' },
  { tool: 'rectangle', label: '矩形', key: 'R' },
];

/** 各几何类型的默认 kind 偏好，取 world.kinds 里第一个存在的。 */
const KIND_PREFERENCES = {
  Point: ['city', 'town', 'village', 'poi', 'station'],
  LineString: ['road', 'street', 'river', 'transit', 'rail'],
  Polygon: ['park', 'lake', 'region', 'island', 'reserve'],
};

/** 绘制模式与其产出要素的几何类型（用于过滤辅助点）。 */
const EXPECTED_GEOMETRY = {
  point: 'Point',
  linestring: 'LineString',
  polygon: 'Polygon',
  rectangle: 'Polygon',
};

const SELECT_FLAGS = {
  point: { feature: { draggable: true } },
  linestring: {
    feature: {
      draggable: true,
      coordinates: { draggable: true, deletable: true, midpoints: true, snappable: true },
    },
  },
  polygon: {
    feature: {
      draggable: true,
      coordinates: { draggable: true, deletable: true, midpoints: true, snappable: true },
    },
  },
  rectangle: {
    feature: {
      draggable: true,
      coordinates: { draggable: true, deletable: false, midpoints: false, snappable: true },
    },
  },
};

/**
 * @typedef {{
 *   key: string,
 *   terraId: string | number | null,
 *   annotationId: string | null,
 *   geometryId: string | null,
 *   kind: string,
 *   names: { lang: string, name: string, role?: string, is_primary: boolean }[],
 *   rank: number,
 *   min_zoom: number | null,
 *   max_zoom: number | null,
 *   description: string,
 *   attrs: Record<string, unknown>,
 *   labelMode: 'point' | 'line' | 'none',
 *   origin: 'draft' | 'existing',
 *   lon: number,
 *   lat: number,
 * }} Draft
 */

/**
 * @param {{
 *   map: import('maplibre-gl').Map,
 *   world: {
 *     world: { default_lang: string, languages: string[] },
 *     kinds: Record<string, { rank?: number, color?: string }>,
 *   },
 *   onStatus?: (text: string) => void,
 *   onSelection?: (draft: Draft | null) => void,
 *   onProbe?: (state: { enabled: boolean, tool: string, draftCount: number }) => void,
 * }} options
 */
export function createEditor({ map, world, onStatus, onSelection, onProbe }) {
  const adapter = new TerraDrawMapLibreGLAdapter({ map });
  const draw = new TerraDraw({
    adapter,
    modes: [
      new TerraDrawSelectMode({
        pointerDistance: 8,
        flags: SELECT_FLAGS,
        allowManualDeselection: true,
        keyEvents: { deselect: 'Escape', delete: 'Delete', rotate: null, scale: null },
        styles: {
          selectedPointColor: '#ffffff',
          selectedPointWidth: 7,
          selectedPointOutlineColor: ACCENT,
          selectedPointOutlineWidth: 2,
          selectionPointColor: ACCENT,
          selectionPointWidth: 6,
          selectionPointOutlineColor: '#0b1020',
          selectionPointOutlineWidth: 1,
          midPointColor: '#9ccaff',
          midPointWidth: 5,
          midPointOutlineColor: '#0b1020',
          midPointOutlineWidth: 1,
          selectedLineStringColor: '#9ccaff',
          selectedLineStringWidth: 3,
          selectedPolygonColor: ACCENT,
          selectedPolygonFillOpacity: 0.22,
          selectedPolygonOutlineColor: '#9ccaff',
          selectedPolygonOutlineWidth: 2,
        },
      }),
      new TerraDrawPointMode({
        pointerDistance: 8,
        styles: {
          pointColor: ACCENT,
          pointWidth: 7,
          pointOutlineColor: '#0b1020',
          pointOutlineWidth: 1.5,
        },
      }),
      new TerraDrawLineStringMode({
        pointerDistance: 8,
        styles: { lineStringColor: ACCENT, lineStringWidth: 2 },
      }),
      new TerraDrawPolygonMode({
        pointerDistance: 8,
        styles: {
          polygonFillColor: ACCENT,
          polygonFillOpacity: 0.2,
          polygonOutlineColor: '#9ccaff',
          polygonOutlineWidth: 2,
        },
      }),
      new TerraDrawRectangleMode({
        pointerDistance: 8,
        styles: {
          polygonFillColor: ACCENT,
          polygonFillOpacity: 0.2,
          polygonOutlineColor: '#9ccaff',
          polygonOutlineWidth: 2,
        },
      }),
      new TerraDrawRenderMode({
        modeName: 'render',
        styles: {
          pointColor: ACCENT,
          pointWidth: 7,
          pointOutlineColor: '#0b1020',
          pointOutlineWidth: 1.5,
          lineStringColor: ACCENT,
          lineStringWidth: 2,
          polygonFillColor: ACCENT,
          polygonFillOpacity: 0.18,
          polygonOutlineColor: '#9ccaff',
          polygonOutlineWidth: 1.5,
        },
      }),
    ],
  });

  const history = createHistory({ limit: 100 });

  // 测试钩子：E2E 断言 Terra Draw 事件与要素。
  // @ts-ignore -- 仅测试使用
  window.__terra = draw;

  /** @type {Map<string, Draft>} */
  let drafts = new Map();
  /** @type {string | null} */
  let selectedKey = null;
  let tool = 'select';
  let enabled = false;
  let started = false;
  let suppress = false;
  let commitTimer = 0;
  let fallbackCounter = 0;
  /** @type {(() => void) | null} */
  let unbindShortcuts = null;
  const toolButtons = new Map();

  // ---------- 左栏分节 ----------

  const toolbarPanel = section({ title: '工具', subtitle: '草稿仅存内存' });
  toolbarPanel.root.id = 'editor-toolbar';
  const toolGrid = document.createElement('div');
  toolGrid.className = 'tool-grid';
  toolGrid.id = 'tool-grid';

  for (const item of TOOLS) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'tool-button';
    button.dataset.tool = item.tool;
    button.id = `tool-${item.tool}`;
    button.innerHTML = `<span>${item.label}</span><kbd>${item.key}</kbd>`;
    button.addEventListener('click', () => setTool(item.tool));
    toolButtons.set(item.tool, button);
    toolGrid.appendChild(button);
  }

  const deleteButton = document.createElement('button');
  deleteButton.type = 'button';
  deleteButton.className = 'tool-button danger';
  deleteButton.id = 'tool-delete';
  deleteButton.innerHTML = '<span>删除</span><kbd>Del</kbd>';
  deleteButton.addEventListener('click', () => deleteSelected());
  toolGrid.appendChild(deleteButton);

  const historyRow = document.createElement('div');
  historyRow.className = 'tool-history';
  const undoButton = document.createElement('button');
  undoButton.type = 'button';
  undoButton.className = 'ghost-button';
  undoButton.id = 'btn-undo';
  undoButton.textContent = '撤销';
  undoButton.addEventListener('click', () => undo());
  const redoButton = document.createElement('button');
  redoButton.type = 'button';
  redoButton.className = 'ghost-button';
  redoButton.id = 'btn-redo';
  redoButton.textContent = '重做';
  redoButton.addEventListener('click', () => redo());
  historyRow.append(undoButton, redoButton);

  const hint = document.createElement('p');
  hint.className = 'editor-hint';
  hint.textContent = '双击结束线/面；Esc 取消；顶点可拖动、双击线段加顶点。';

  toolbarPanel.body.append(toolGrid, historyRow, hint);

  const propsPanel = section({ title: '属性', subtitle: '选中或绘制后编辑' });
  propsPanel.root.id = 'editor-props';

  const inspector = createInspector({
    world,
    onSave: (draft) => {
      const stored = drafts.get(draft.key);
      if (!stored) return;
      Object.assign(stored, draft);
      finalizeIds(stored);
      drafts.set(stored.key, stored);
      inspector.open(stored);
      selectedKey = stored.key;
      onSelection?.(clone(stored));
      commitNow();
      onStatus?.(`已保存草稿 ${stored.annotationId ?? '（未命名）'}`);
      notifyProbe();
    },
    onCancel: (draft, meta) => {
      const stored = drafts.get(draft.key);
      if (!stored) return;
      if (meta.isNew) {
        removeDraft(stored);
        commitNow();
      } else {
        inspector.open(stored);
      }
    },
    onDelete: (draft) => deleteDraft(draft),
  });
  propsPanel.body.appendChild(inspector.element);

  // ---------- Terra Draw 事件 ----------

  draw.on('finish', (id) => {
    if (!enabled || suppress) return;
    // 只处理当前绘制模式真正完成的要素；画线/面时的辅助点不属于草稿。
    const mode = draw.getMode();
    if (EXPECTED_GEOMETRY[mode] === undefined) return;
    if (findByTerraId(id)) return;
    const feature = draw.getSnapshotFeature(id);
    if (!feature || feature.geometry.type !== EXPECTED_GEOMETRY[mode]) return;
    const draft = createDraft(id, feature);
    drafts.set(draft.key, draft);
    // 延后切模式，避免在 Terra Draw 的模式回调里重入。
    setTimeout(() => {
      if (!findByTerraId(id)) return;
      setTool('select');
      if (draw.hasFeature(id)) draw.selectFeature(id);
      openDraft(draft);
      commitNow();
    }, 0);
  });

  draw.on('change', (ids, type) => {
    if (!enabled || suppress) return;
    if (type === 'create') {
      // 画线/面会产生辅助 Point 要素，只有点工具创建的 Point 才是标注草稿。
      if (draw.getMode() === 'point') {
        for (const id of ids) {
          const feature = draw.getSnapshotFeature(id);
          if (!feature || feature.geometry.type !== 'Point') continue;
          if (findByTerraId(id)) continue;
          const draft = createDraft(id, feature);
          drafts.set(draft.key, draft);
          setTimeout(() => {
            if (!findByTerraId(id)) return;
            setTool('select');
            if (draw.hasFeature(id)) draw.selectFeature(id);
            openDraft(draft);
            commitNow();
          }, 0);
        }
      }
    } else if (type === 'delete') {
      removeDraftsFor(ids);
    }
    if (type !== 'styling') scheduleCommit();
  });

  draw.on('select', (id) => {
    if (!enabled || suppress) return;
    const draft = findByTerraId(id);
    if (!draft) return;
    selectedKey = draft.key;
    inspector.open(draft);
    onSelection?.(clone(draft));
    updateHistoryButtons();
  });

  draw.on('deselect', (id) => {
    if (!enabled || suppress) return;
    const draft = findByTerraId(id);
    if (draft && selectedKey === draft.key) {
      selectedKey = null;
      inspector.close();
      onSelection?.(null);
    }
  });

  // ---------- 对外接口 ----------

  function enable() {
    if (enabled) return;
    enabled = true;
    const body = document.getElementById('leftbar-body');
    if (body) {
      body.prepend(propsPanel.root);
      body.prepend(toolbarPanel.root);
    }
    if (!started) {
      draw.start();
      started = true;
      history.reset(snapshot());
    }
    setTool('select');
    unbindShortcuts = bindShortcuts({
      KeyV: () => setTool('select'),
      KeyP: () => setTool('point'),
      KeyL: () => setTool('linestring'),
      KeyG: () => setTool('polygon'),
      KeyR: () => setTool('rectangle'),
      Delete: () => deleteSelected(),
      Backspace: () => deleteSelected(),
      'Ctrl+KeyZ': () => undo(),
      'Ctrl+Shift+KeyZ': () => redo(),
    });
    onStatus?.('编辑模式 · 草稿仅存内存');
    notifyProbe();
  }

  function disable() {
    if (!enabled) return;
    enabled = false;
    unbindShortcuts?.();
    unbindShortcuts = null;
    if (started) draw.setMode('render');
    inspector.close();
    selectedKey = null;
    toolbarPanel.root.remove();
    propsPanel.root.remove();
    onSelection?.(null);
    onStatus?.('浏览模式 · 只读');
    notifyProbe();
  }

  /** @param {string} next */
  function setTool(next) {
    if (!enabled) return;
    if (!TOOLS.some((item) => item.tool === next)) return;
    tool = next;
    draw.setMode(next);
    for (const [name, button] of toolButtons) {
      button.classList.toggle('is-active', name === next);
      button.setAttribute('aria-pressed', String(name === next));
    }
    onStatus?.(`工具：${labelOf(next)} · 草稿 ${drafts.size} 条`);
    notifyProbe();
  }

  /**
   * 处理 Escape：先取消草稿/关闭属性，其次回到选择工具。
   * @returns {boolean} 是否消费了按键
   */
  function handleEscape() {
    if (!enabled) return false;
    if (inspector.isOpen()) {
      const draft = selectedKey ? drafts.get(selectedKey) : null;
      if (draft) {
        const isNew = !draft.annotationId;
        if (isNew) {
          removeDraft(draft);
          commitNow();
        } else {
          inspector.open(draft);
        }
      } else {
        inspector.close();
      }
      return true;
    }
    if (tool !== 'select') {
      setTool('select');
      return true;
    }
    return false;
  }

  /** @param {string} id */
  function selectAnnotation(id) {
    const draft = pickLocal(id);
    if (!draft) return null;
    openDraft(draft);
    if (draft.terraId !== null && draw.hasFeature(draft.terraId)) {
      if (draw.getMode() !== 'select') setTool('select');
      draw.selectFeature(draft.terraId);
    }
    return clone(draft);
  }

  /**
   * 把服务端详情接入为可编辑草稿副本。
   * @param {any} detail
   * @returns {Draft}
   */
  function addExisting(detail) {
    const existing = pickLocal(detail.id);
    if (existing) {
      openDraft(existing);
      return clone(existing);
    }
    /** @type {Draft} */
    const draft = {
      key: `existing:${detail.id}`,
      terraId: null,
      annotationId: detail.id,
      geometryId: detail.geometry_id ?? null,
      kind: detail.kind,
      names: (detail.names ?? []).map((item) => ({
        lang: item.lang,
        name: item.name,
        role: item.role ?? 'name',
        is_primary: Boolean(item.is_primary),
      })),
      rank: detail.rank ?? 3,
      min_zoom: detail.min_zoom ?? null,
      max_zoom: detail.max_zoom ?? null,
      description: detail.description ?? '',
      attrs: detail.attrs ?? {},
      labelMode: detail.label_mode ?? 'point',
      origin: 'existing',
      lon: detail.lon,
      lat: detail.lat,
    };
    drafts.set(draft.key, draft);
    openDraft(draft);
    notifyProbe();
    return clone(draft);
  }

  /**
   * 导出内存草稿。
   * @returns {{
   *   annotations: { annotations: Record<string, unknown>[] },
   *   geometry: { type: string, features: Record<string, unknown>[] },
   *   warnings: string[],
   *   counts: { annotations: number, geometries: number },
   * }}
   */
  function exportPayload() {
    /** @type {Record<string, unknown>[]} */
    const annotations = [];
    /** @type {Record<string, unknown>[]} */
    const features = [];
    /** @type {string[]} */
    const warnings = [];

    for (const draft of drafts.values()) {
      const problem = exportProblem(draft);
      if (problem) {
        warnings.push(`${draft.annotationId ?? draft.key}：${problem}`);
        continue;
      }
      syncAnchor(draft);
      finalizeIds(draft);

      /** @type {Record<string, unknown>} */
      const item = {
        id: draft.annotationId,
        kind: draft.kind,
        lon: round6(draft.lon),
        lat: round6(draft.lat),
        rank: draft.rank,
        label_mode: draft.labelMode,
        names: draft.names
          .filter((name) => name.name)
          .map((name) => ({
            lang: name.lang,
            name: name.name,
            role: name.role ?? 'name',
            is_primary: Boolean(name.is_primary),
          })),
      };
      if (draft.min_zoom !== null) item.min_zoom = draft.min_zoom;
      if (draft.max_zoom !== null) item.max_zoom = draft.max_zoom;
      if (draft.description) item.description = draft.description;
      if (draft.attrs && Object.keys(draft.attrs).length > 0) item.attrs = draft.attrs;
      if (draft.labelMode !== 'point' && draft.geometryId) item.geometry_id = draft.geometryId;
      annotations.push(item);

      if (draft.terraId !== null && draft.labelMode !== 'point') {
        const feature = draw.getSnapshotFeature(draft.terraId);
        if (feature && draft.geometryId) {
          features.push({
            type: 'Feature',
            id: draft.geometryId,
            geometry: roundGeometry(feature.geometry),
            properties: { kind: draft.kind },
          });
        }
      }
    }

    return {
      annotations: { annotations },
      geometry: { type: 'FeatureCollection', features },
      warnings,
      counts: { annotations: annotations.length, geometries: features.length },
    };
  }

  /** 导出并触发下载（两个文件）。 */
  function exportDownload() {
    const payload = exportPayload();
    download('annotations.json', payload.annotations);
    setTimeout(() => download('geometry.geojson', payload.geometry), 400);
    const skipped =
      payload.warnings.length > 0 ? `，跳过 ${payload.warnings.length} 条未完成草稿` : '';
    onStatus?.(
      `已导出 ${payload.counts.annotations} 条标注 / ${payload.counts.geometries} 个几何${skipped}`,
    );
    return payload;
  }

  function undo() {
    if (!enabled) return;
    const snap = history.undo();
    if (!snap) {
      onStatus?.('没有可撤销的操作');
      return;
    }
    restore(snap);
    onStatus?.('已撤销');
  }

  function redo() {
    if (!enabled) return;
    const snap = history.redo();
    if (!snap) {
      onStatus?.('没有可重做的操作');
      return;
    }
    restore(snap);
    onStatus?.('已重做');
  }

  /** 清空选中与属性表单，但不删除草稿。 */
  function clearSelection() {
    selectedKey = null;
    inspector.close();
    if (started && enabled) draw.setMode(tool);
    onSelection?.(null);
    updateHistoryButtons();
  }

  // ---------- 内部实现 ----------

  /**
   * @param {string | number} terraId
   * @param {any} feature
   * @returns {Draft}
   */
  function createDraft(terraId, feature) {
    const geometryType = String(feature.geometry?.type ?? 'Point');
    const anchor = anchorOf(feature.geometry);
    return {
      key: `terra:${terraId}`,
      terraId,
      annotationId: null,
      geometryId: null,
      kind: pickKind(geometryType),
      names: [{ lang: world.world.default_lang, name: '', role: 'name', is_primary: true }],
      rank: 3,
      min_zoom: null,
      max_zoom: null,
      description: '',
      attrs: {},
      labelMode: geometryType === 'Point' ? 'point' : 'line',
      origin: 'draft',
      lon: anchor[0],
      lat: anchor[1],
    };
  }

  /** @param {string | number} terraId */
  function findByTerraId(terraId) {
    for (const draft of drafts.values()) {
      if (draft.terraId !== null && String(draft.terraId) === String(terraId)) return draft;
    }
    return null;
  }

  /** @param {string} annotationId */
  function pickLocal(annotationId) {
    for (const draft of drafts.values()) {
      if (draft.annotationId === annotationId || draft.key === annotationId) return draft;
    }
    return null;
  }

  /** @param {Draft} draft */
  function openDraft(draft) {
    selectedKey = draft.key;
    inspector.open(draft);
    onSelection?.(clone(draft));
    updateHistoryButtons();
  }

  function deleteSelected() {
    if (!enabled) return;
    const draft = selectedKey ? drafts.get(selectedKey) : null;
    if (!draft) {
      onStatus?.('没有选中的草稿可删除');
      return;
    }
    deleteDraft(draft);
  }

  /** @param {Draft} draft */
  function deleteDraft(draft) {
    const stored = drafts.get(draft.key) ?? draft;
    const label = primaryName(stored) || stored.annotationId || '未命名草稿';
    if (!window.confirm(`删除「${label}」？`)) return;
    removeDraft(stored);
    commitNow();
  }

  /** @param {Draft} draft */
  function removeDraft(draft) {
    if (draft.terraId !== null && draw.hasFeature(draft.terraId)) {
      suppress = true;
      try {
        draw.removeFeatures([draft.terraId]);
      } finally {
        suppress = false;
      }
    }
    drafts.delete(draft.key);
    if (selectedKey === draft.key) {
      selectedKey = null;
      inspector.close();
      onSelection?.(null);
    }
    notifyProbe();
  }

  /** @param {(string | number)[]} ids */
  function removeDraftsFor(ids) {
    for (const [key, draft] of [...drafts]) {
      if (draft.terraId === null) continue;
      if (!ids.some((id) => String(id) === String(draft.terraId))) continue;
      drafts.delete(key);
      if (selectedKey === key) {
        selectedKey = null;
        inspector.close();
        onSelection?.(null);
      }
    }
    notifyProbe();
  }

  function snapshot() {
    return {
      drafts: [...drafts.values()].map((draft) => clone(draft)),
      features: draw.getSnapshot().map((feature) => clone(feature)),
    };
  }

  /** @param {any} snap */
  function restore(snap) {
    suppress = true;
    try {
      drafts = new Map(
        (snap.drafts ?? []).map((/** @type {Draft} */ draft) => [draft.key, clone(draft)]),
      );
      draw.clear();
      if (Array.isArray(snap.features) && snap.features.length > 0) {
        draw.addFeatures(snap.features.map((/** @type {any} */ feature) => clone(feature)));
      }
    } finally {
      suppress = false;
    }
    selectedKey = null;
    inspector.close();
    onSelection?.(null);
    updateHistoryButtons();
    notifyProbe();
  }

  function scheduleCommit() {
    if (suppress) return;
    if (commitTimer) window.clearTimeout(commitTimer);
    commitTimer = window.setTimeout(() => {
      commitTimer = 0;
      commitNow();
    }, 250);
  }

  function commitNow() {
    if (commitTimer) {
      window.clearTimeout(commitTimer);
      commitTimer = 0;
    }
    if (!started) return;
    history.push(snapshot());
    updateHistoryButtons();
  }

  function updateHistoryButtons() {
    undoButton.disabled = !history.canUndo();
    redoButton.disabled = !history.canRedo();
    undoButton.title = history.canUndo() ? `撤销（${history.depth()} 步）` : '没有可撤销的操作';
  }

  function notifyProbe() {
    onProbe?.({ enabled, tool, draftCount: drafts.size });
    updateHistoryButtons();
  }

  /** @param {string} geometryType */
  function pickKind(geometryType) {
    const preferred = KIND_PREFERENCES[geometryType] ?? [];
    for (const kind of preferred) {
      if (kind in world.kinds) return kind;
    }
    const sorted = Object.keys(world.kinds).sort(
      (a, b) => (world.kinds[a]?.rank ?? 99) - (world.kinds[b]?.rank ?? 99) || a.localeCompare(b),
    );
    return sorted[0] ?? 'city';
  }

  /** @param {Draft} draft */
  function syncAnchor(draft) {
    if (draft.terraId === null) return;
    const feature = draw.getSnapshotFeature(draft.terraId);
    if (!feature) return;
    const anchor = anchorOf(feature.geometry);
    draft.lon = round6(anchor[0]);
    draft.lat = round6(anchor[1]);
  }

  /** @param {Draft} draft */
  function finalizeIds(draft) {
    if (!draft.annotationId) {
      draft.annotationId = nextId('anno', draft.kind, slugOf(primaryName(draft)));
    }
    if (draft.labelMode !== 'point' && !draft.geometryId) {
      draft.geometryId = nextId('geo', draft.kind, slugOf(primaryName(draft)));
    }
    return draft;
  }

  /**
   * @param {'anno' | 'geo'} prefix
   * @param {string} kind
   * @param {string} slug
   */
  function nextId(prefix, kind, slug) {
    const used = new Set();
    for (const draft of drafts.values()) {
      if (prefix === 'anno' && draft.annotationId) used.add(draft.annotationId);
      if (prefix === 'geo' && draft.geometryId) used.add(draft.geometryId);
    }
    const safeKind = kind.replace(/[^a-z_]/g, '_') || 'poi';
    const base = slug || `fig_${++fallbackCounter}`;
    let candidate = `${prefix}.${safeKind}.${base}`;
    let suffix = 2;
    while (used.has(candidate)) {
      candidate = `${prefix}.${safeKind}.${base}_${suffix++}`;
    }
    return candidate;
  }

  /** @param {Draft} draft @returns {string | null} */
  function exportProblem(draft) {
    if (!draft.kind) return '缺少 kind';
    const named = draft.names.filter((name) => name.name);
    if (named.length === 0) return '缺少名称';
    if (named.filter((name) => name.is_primary).length !== 1) return '必须恰好一个主名';
    if (named.some((name) => !name.lang)) return '存在缺少语种的名称';
    if (!Number.isInteger(draft.rank) || draft.rank < 1 || draft.rank > 5) return 'rank 非法';
    if (draft.min_zoom !== null && draft.max_zoom !== null && draft.min_zoom > draft.max_zoom) {
      return 'zoom 区间非法';
    }
    return null;
  }

  function destroy() {
    unbindShortcuts?.();
    unbindShortcuts = null;
    toolbarPanel.root.remove();
    propsPanel.root.remove();
    if (started) {
      draw.stop();
      started = false;
    }
    enabled = false;
  }

  return {
    enable,
    disable,
    isEnabled: () => enabled,
    setTool,
    getTool: () => tool,
    handleEscape,
    clearSelection,
    selectAnnotation,
    addExisting,
    exportPayload,
    exportDownload,
    undo,
    redo,
    canUndo: () => history.canUndo(),
    canRedo: () => history.canRedo(),
    destroy,
    probe: () => ({
      enabled,
      tool,
      mode: started ? draw.getMode() : 'stopped',
      draftCount: drafts.size,
      canUndo: history.canUndo(),
      canRedo: history.canRedo(),
      selectedKey,
    }),
  };

  /** @param {string} toolName */
  function labelOf(toolName) {
    return TOOLS.find((item) => item.tool === toolName)?.label ?? toolName;
  }
}

/**
 * 取几何锚点：点取自身；线取首点；面取外环包围盒中心。
 * @param {any} geometry
 * @returns {[number, number]}
 */
function anchorOf(geometry) {
  if (!geometry) return [0, 0];
  if (geometry.type === 'Point') return /** @type {[number, number]} */ (geometry.coordinates);
  if (geometry.type === 'LineString') return geometry.coordinates[0];
  if (geometry.type === 'MultiLineString') return geometry.coordinates[0][0];
  if (geometry.type === 'Polygon') return ringCenter(geometry.coordinates[0]);
  if (geometry.type === 'MultiPolygon') return ringCenter(geometry.coordinates[0][0]);
  return [0, 0];
}

/**
 * @param {number[][]} ring
 * @returns {[number, number]}
 */
function ringCenter(ring) {
  let minLon = Number.POSITIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLon = Number.NEGATIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;
  for (const [lon, lat] of ring) {
    minLon = Math.min(minLon, lon);
    minLat = Math.min(minLat, lat);
    maxLon = Math.max(maxLon, lon);
    maxLat = Math.max(maxLat, lat);
  }
  return [round6((minLon + maxLon) / 2), round6((minLat + maxLat) / 2)];
}

/**
 * @param {number} value
 * @returns {number}
 */
function round6(value) {
  const rounded = Math.round(value * 1e6) / 1e6;
  return Object.is(rounded, -0) ? 0 : rounded;
}

/**
 * @param {any} geometry
 * @returns {any}
 */
function roundGeometry(geometry) {
  if (!geometry) return geometry;
  if (geometry.type === 'Point') {
    return {
      type: 'Point',
      coordinates: [round6(geometry.coordinates[0]), round6(geometry.coordinates[1])],
    };
  }
  if (geometry.type === 'LineString') {
    return { type: 'LineString', coordinates: geometry.coordinates.map(roundPosition) };
  }
  if (geometry.type === 'Polygon') {
    return {
      type: 'Polygon',
      coordinates: geometry.coordinates.map((ring) => ring.map(roundPosition)),
    };
  }
  return geometry;
}

/** @param {number[]} pair */
function roundPosition(pair) {
  return [round6(pair[0]), round6(pair[1])];
}

/** @param {Draft} draft */
function primaryName(draft) {
  return draft.names.find((name) => name.is_primary && name.name)?.name ?? '';
}

/**
 * 主名转 slug：小写、非字母数字转下划线；中文等无法转换时返回空串。
 * @param {string} name
 */
function slugOf(name) {
  return name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 32);
}

/**
 * @param {string} filename
 * @param {unknown} data
 */
function download(filename, data) {
  const blob = new Blob([`${JSON.stringify(data, null, 2)}\n`], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * @template T
 * @param {T} value
 * @returns {T}
 */
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
