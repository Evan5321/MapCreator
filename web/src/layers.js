// @ts-check
/**
 * 图层分组与开关：把 `build/style.json` 的图层 ID 映射成可读分组。
 * 点标注按 /api/world 的 kind 动态生成（`annotation-<kind>`），并与 DOM 标签联动。
 */

import { section, switchRow } from './panels.js';

/**
 * 固定分组：图层 ID 来自 `src/mapcreator/build/style.py`。
 * 颜色不在这里硬编码，图例色块从当前 style 的 paint 里读取。
 */
export const BASE_GROUPS = [
  {
    id: 'surface',
    title: '底图',
    items: [
      { id: 'land', title: '陆地', layers: ['land-fill', 'land-outline'], paint: ['fill-color'] },
      {
        id: 'water',
        title: '水体',
        layers: ['water-fill', 'water-outline'],
        paint: ['fill-color'],
      },
      { id: 'parks', title: '公园绿地', layers: ['parks-fill'], paint: ['fill-color'] },
      { id: 'terrain', title: '地形', layers: ['terrain-fill'], paint: ['fill-color'] },
    ],
  },
  {
    id: 'linear',
    title: '线状要素',
    items: [
      { id: 'river', title: '河流', layers: ['river'], paint: ['line-color'] },
      { id: 'road', title: '道路', layers: ['road-casing', 'road'], paint: ['line-color'] },
      { id: 'transit', title: '轨道交通', layers: ['transit'], paint: ['line-color'] },
    ],
  },
];

/**
 * @param {import('maplibre-gl').Map} map
 * @param {{ kinds: Record<string, { rank?: number, color?: string }> }} world
 * @param {{ onKindVisibility?: (kind: string, visible: boolean) => void }} [options]
 * @returns {{ element: HTMLElement, isKindVisible: (kind: string) => boolean }}
 */
export function createLayerPanel(map, world, options = {}) {
  const panel = section({ title: '图层', subtitle: '底图 · 线状 · 点标注' });
  const body = panel.body;

  for (const group of BASE_GROUPS) {
    body.appendChild(groupLabel(group.title));
    for (const item of group.items) {
      const color = paintColor(map, item.layers[0], item.paint[0]);
      body.appendChild(
        switchRow({
          title: item.title,
          color,
          checked: true,
          onChange: (checked) => setLayerVisibility(map, item.layers, checked),
        }),
      );
    }
  }

  body.appendChild(groupLabel('点标注'));

  const kinds = Object.entries(world.kinds)
    .sort(([nameA, a], [nameB, b]) => (a.rank ?? 99) - (b.rank ?? 99) || nameA.localeCompare(nameB))
    .map(([name]) => name);

  /** @type {Set<string>} */
  const hidden = new Set();
  /** @type {Map<string, HTMLElement>} */
  const rows = new Map();

  const master = switchRow({
    title: '全部点标注',
    checked: true,
    onChange: (checked) => {
      for (const kind of kinds) setKind(kind, checked);
      syncMaster();
    },
  });
  body.appendChild(master);

  const list = document.createElement('div');
  list.className = 'layer-kinds';
  body.appendChild(list);

  for (const kind of kinds) {
    const row = switchRow({
      title: kind,
      color: world.kinds[kind]?.color ?? '',
      checked: true,
      onChange: (checked) => {
        setKind(kind, checked);
        syncMaster();
      },
    });
    rows.set(kind, row);
    list.appendChild(row);
  }

  /** @param {string} kind @param {boolean} visible */
  function setKind(kind, visible) {
    if (visible) hidden.delete(kind);
    else hidden.add(kind);

    const row = rows.get(kind);
    const input = row?.querySelector('input');
    if (input && input.checked !== visible) input.checked = visible;

    setLayerVisibility(map, [`annotation-${kind}`], visible);
    options.onKindVisibility?.(kind, visible);
  }

  function syncMaster() {
    const input = master.querySelector('input');
    if (input) input.checked = hidden.size === 0;
  }

  return {
    element: panel.root,
    isKindVisible: (kind) => !hidden.has(kind),
  };
}

/**
 * 读取 style 里第一个可用图层的颜色，作为图例色块；表达式取不到时返回空串。
 * @param {import('maplibre-gl').Map} map
 * @param {string} layerId
 * @param {string} paintKey
 */
function paintColor(map, layerId, paintKey) {
  if (!map.getLayer(layerId)) return '';
  const value = map.getPaintProperty(layerId, paintKey);
  return typeof value === 'string' ? value : '';
}

/**
 * @param {import('maplibre-gl').Map} map
 * @param {string[]} layerIds
 * @param {boolean} visible
 */
function setLayerVisibility(map, layerIds, visible) {
  for (const id of layerIds) {
    if (!map.getLayer(id)) continue;
    map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
  }
}

/** @param {string} title */
function groupLabel(title) {
  const element = document.createElement('div');
  element.className = 'layer-group-title';
  element.textContent = title;
  return element;
}
