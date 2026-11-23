// @ts-check
/**
 * 浏览外壳：顶栏、左栏（图层 → 标注列表 → 世界信息）、状态栏。
 * 只读模式：这里不挂载任何编辑工具；编辑组件由 TASK-0009 按模式加载。
 */

import { createLayerPanel } from './layers.js';
import { emptyState, groupHeader, listRow, section, statGrid } from './panels.js';
import { bindShortcuts } from './shortcuts.js';

/**
 * @typedef {{
 *   id: string,
 *   name: string,
 *   kind: string,
 *   rank?: number,
 *   min_zoom?: number,
 *   max_zoom?: number,
 * }} LabelSummary
 *
 * @typedef {{
 *   world: {
 *     world: { id: string, name: string, default_lang: string, languages: string[] },
 *     bounds?: number[],
 *     kinds: Record<string, { rank?: number, color?: string }>,
 *     build_id?: string,
 *   },
 *   map: import('maplibre-gl').Map,
 *   onSelect: (id: string) => void,
 *   onKindVisibility?: (kind: string, visible: boolean) => void,
 * }} ShellOptions
 */

/**
 * @param {ShellOptions} options
 */
export function createShell({ world, map, onSelect, onKindVisibility }) {
  const leftbar = document.getElementById('leftbar');
  const body = document.getElementById('leftbar-body');
  const title = document.getElementById('topbar-title');
  const subtitle = document.getElementById('topbar-subtitle');
  const status = document.getElementById('statusbar');
  const toggleButton = document.getElementById('btn-toggle-left');
  const resetButton = document.getElementById('btn-reset-view');

  if (!leftbar || !body) throw new Error('缺少左栏容器 #leftbar / #leftbar-body');

  if (title) title.textContent = world.world.name;
  if (subtitle) subtitle.textContent = '浏览模式 · 只读';

  const layerPanel = createLayerPanel(map, world, { onKindVisibility });
  const listPanel = section({ title: '标注列表', subtitle: '当前带 —' });
  const worldPanel = section({ title: '世界信息', subtitle: world.world.id });
  listPanel.root.classList.add('panel-scroll');

  worldPanel.body.appendChild(
    statGrid([
      ['世界', world.world.name],
      ['ID', world.world.id],
      ['默认语种', world.world.default_lang],
      ['语种', world.world.languages.join(' / ') || '—'],
      ['范围', formatBounds(world.bounds)],
      ['构建', world.build_id ?? '—'],
      ['快捷键', 'Ctrl+\\ 收起左栏'],
    ]),
  );

  body.append(layerPanel.element, listPanel.root, worldPanel.root);

  /** @type {LabelSummary[]} */
  let annotations = [];
  let band = '';
  /** @type {string | null} */
  let selectedId = null;

  /** @param {LabelSummary[]} features */
  function setAnnotations(features) {
    annotations = [...features].sort(
      (a, b) => (a.rank ?? 99) - (b.rank ?? 99) || a.name.localeCompare(b.name),
    );
    renderList();
    updateListSubtitle();
  }

  function renderList() {
    const counts = new Map();
    for (const item of annotations) {
      counts.set(item.kind, (counts.get(item.kind) ?? 0) + 1);
    }

    const nodes = [];
    for (const kind of sortKinds([...counts.keys()])) {
      nodes.push(
        groupHeader({ title: kind, color: world.kinds[kind]?.color, count: counts.get(kind) }),
      );
      for (const item of annotations) {
        if (item.kind !== kind) continue;
        nodes.push(
          listRow({
            id: item.id,
            title: item.name,
            meta: zoomLabel(item),
            active: item.id === selectedId,
            onClick: onSelect,
          }),
        );
      }
    }

    listPanel.body.replaceChildren(
      ...(nodes.length > 0 ? nodes : [emptyState('当前缩放带没有可显示的标注')]),
    );
  }

  /** @param {string[]} kinds */
  function sortKinds(kinds) {
    return kinds.sort((a, b) => {
      const rankA = world.kinds[a]?.rank ?? 99;
      const rankB = world.kinds[b]?.rank ?? 99;
      return rankA - rankB || a.localeCompare(b);
    });
  }

  /** @param {string} name */
  function setBand(name) {
    band = name;
    updateListSubtitle();
  }

  function updateListSubtitle() {
    const parts = [];
    if (band) parts.push(`当前带 ${band}`);
    parts.push(`${annotations.length} 条`);
    listPanel.setSubtitle(parts.join(' · '));
  }

  /** @param {string | null} id */
  function setSelected(id) {
    selectedId = id;
    for (const row of listPanel.body.querySelectorAll('.list-row')) {
      row.classList.toggle('is-active', row instanceof HTMLElement && row.dataset.id === id);
    }
  }

  /** @param {string} text */
  function setStatus(text) {
    if (status) status.textContent = text;
  }

  /**
   * 切换浏览/编辑模式的外观。编辑控件由 editor.js 自行挂载。
   * @param {'browse' | 'edit'} mode
   */
  function setMode(mode) {
    const editing = mode === 'edit';
    if (subtitle) {
      subtitle.textContent = editing ? '编辑模式 · 草稿仅存内存' : '浏览模式 · 只读';
    }
    document.body.classList.toggle('is-editing', editing);
  }

  function toggleLeftbar() {
    const collapsed = leftbar?.classList.toggle('is-collapsed') ?? false;
    if (toggleButton) {
      toggleButton.textContent = collapsed ? '展开左栏' : '收起左栏';
      toggleButton.setAttribute('aria-expanded', String(!collapsed));
    }
  }

  toggleButton?.addEventListener('click', toggleLeftbar);
  resetButton?.addEventListener('click', () => {
    if (!world.bounds) return;
    const [west, south, east, north] = world.bounds;
    map.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      {
        padding: {
          top: 84,
          bottom: 64,
          left: leftbar?.classList.contains('is-collapsed') ? 48 : 344,
          right: 48,
        },
        duration: 400,
      },
    );
  });

  bindShortcuts({ 'Ctrl+Backslash': toggleLeftbar });

  updateListSubtitle();

  return { setAnnotations, setBand, setSelected, setStatus, setMode, toggleLeftbar };
}

/**
 * @param {number[] | undefined} bounds
 */
function formatBounds(bounds) {
  if (!bounds || bounds.length !== 4) return '—';
  const [west, south, east, north] = bounds;
  return `${west.toFixed(2)}, ${south.toFixed(2)} → ${east.toFixed(2)}, ${north.toFixed(2)}`;
}

/**
 * @param {LabelSummary} item
 */
function zoomLabel(item) {
  if (item.min_zoom === undefined || item.max_zoom === undefined) return '';
  return `z${item.min_zoom}–z${item.max_zoom}`;
}
