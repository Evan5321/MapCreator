// @ts-check
/**
 * MapLibre 实例、样式来源、缩放带切换。
 * 样式与分片由 `mapcreator build` 生成：/map/style.json、/map/data/labels.<band>.geojson。
 */

import maplibregl from 'maplibre-gl';
import { getBand, getStyle, getWorld } from './api.js';
import { createLabelLayer } from './labels.js';

/** 与 config/zoom_bands.toml 对应的 6 个带（D-018）；实际边界以 /api/world 为准。 */
export const BANDS = ['z0-3', 'z4-6', 'z7-9', 'z10-12', 'z13-15', 'z16-17'];

/**
 * 建立地图并返回实例、世界元数据、标签层与选中高亮。
 * @param {HTMLElement | null} container
 * @param {{ zoom?: number, center?: { lon: number, lat: number } }} [view]
 * @param {{ onSelect?: (id: string) => void, getSelectedId?: () => string | null }} [options]
 */
export async function initMap(container, view = {}, options = {}) {
  if (!container) throw new Error('缺少 #map 容器');

  const world = await getWorld();
  const style = await getStyle();
  resolveSources(style);
  // 注意：不能显式传 `zoom: undefined`。MapLibre 的 jumpTo 用 `'zoom' in options` 判断，
  // 显式 undefined 会被转成 NaN，初始化时矩阵求逆失败（failed to invert matrix）。
  const camera = view.center
    ? { center: [view.center.lon, view.center.lat], zoom: view.zoom ?? 4 }
    : { bounds: world.bounds ?? undefined };

  const map = new maplibregl.Map({
    container,
    style,
    ...camera,
    minZoom: 0,
    maxZoom: 17,
    attributionControl: false,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');

  await new Promise((resolve, reject) => {
    map.once('load', () => resolve(undefined));
    map.once('error', (event) => {
      reject(event.error ?? new Error('地图加载失败'));
    });
  });

  const labels = createLabelLayer(map, world, getBand, options);
  /** 点标注的样式图层 ID（点击查询用）。 */
  const pointLayers = Object.keys(world.kinds).map((kind) => `annotation-${kind}`);
  return { map, world, labels, pointLayers };
}

/**
 * 构建产物里的 source 使用相对文件名（如 `unified.geojson`），
 * 而 MapLibre 按页面地址而非 style.json 地址解析相对 URL；这里统一改写到 `/map/` 下。
 * @param {any} style
 */
function resolveSources(style) {
  for (const source of Object.values(style.sources ?? {})) {
    if (source && typeof source.data === 'string' && !/^(?:[a-z]+:|\/)/i.test(source.data)) {
      source.data = `/map/${source.data}`;
    }
  }
}

/**
 * 当前缩放所属的带名。
 * @param {number} zoom
 * @param {{ name: string, min_zoom: number, max_zoom: number }[]} [bands]
 */
export function bandForZoom(zoom, bands) {
  if (!bands || bands.length === 0) {
    const index = zoom < 4 ? 0 : zoom < 7 ? 1 : zoom < 10 ? 2 : zoom < 13 ? 3 : zoom < 16 ? 4 : 5;
    return BANDS[index];
  }
  // 缩放级别可以是小数，相邻带的整数区间之间存在缝隙（如 z6.5）；取最后一个 min_zoom <= zoom 的带。
  let match = bands[0];
  for (const band of bands) {
    if (zoom >= band.min_zoom) match = band;
  }
  return match.name;
}
