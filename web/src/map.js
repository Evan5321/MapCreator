// @ts-check
/**
 * MapLibre 实例、source/layer、缩放带切换。
 * 骨架：仅建立地图与占位来源；样式与分带加载见 TASK-0006。
 */

import maplibregl from 'maplibre-gl';

/** 与 config/zoom_bands.toml 对应的 6 个带（D-018）。 */
export const BANDS = ['z0-3', 'z4-6', 'z7-9', 'z10-12', 'z13-15', 'z16-17'];

/**
 * 建立地图并返回实例。
 * @param {HTMLElement | null} container
 * @returns {Promise<import('maplibre-gl').Map>}
 */
export async function initMap(container) {
  if (!container) throw new Error('缺少 #map 容器');

  // /api/world 在 TASK-0006 实现；此处先给一个最小可用样式，保证页面能加载
  const map = new maplibregl.Map({
    container,
    style: {
      version: 8,
      sources: {},
      layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0b1020' } }],
    },
    center: [0, 0],
    zoom: 3,
    maxZoom: 17,
    minZoom: 0,
  });

  return new Promise((resolve) => {
    map.on('load', () => resolve(map));
  });
}

/**
 * 当前缩放所属的带名。
 * @param {number} zoom
 */
export function bandForZoom(zoom) {
  const index = zoom < 4 ? 0 : zoom < 7 ? 1 : zoom < 10 ? 2 : zoom < 13 ? 3 : zoom < 16 ? 4 : 5;
  return BANDS[index];
}
