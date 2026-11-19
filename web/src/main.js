// @ts-check
/**
 * 启动入口：只做装配，不放业务逻辑（AGENTS.md §5）。
 * URL 状态：#z/lat/lon，随地图移动写回 history。
 */

import 'maplibre-gl/dist/maplibre-gl.css';

import { bandForZoom, initMap } from './map.js';
import { setStatus } from './ui.js';

/** 测试模式暴露的只读探针（E2E 断言用，见 docs/TESTING.md §4）。 */
const app = {
  ready: false,
  zoom: 0,
  center: { lon: 0, lat: 0 },
  band: null,
  visibleLabelCount: 0,
  selectedId: null,
};

/** @returns {{ zoom: number, center: { lon: number, lat: number } } | null} */
function parseHash() {
  const match = /^#([0-9.]+)\/([-\d.]+)\/([-\d.]+)$/.exec(window.location.hash);
  if (!match) return null;
  return {
    zoom: Number(match[1]),
    center: { lat: Number(match[2]), lon: Number(match[3]) },
  };
}

/** @param {import('maplibre-gl').Map} map */
function writeHash(map) {
  const center = map.getCenter();
  const hash = `#${map.getZoom().toFixed(2)}/${center.lat.toFixed(5)}/${center.lng.toFixed(5)}`;
  window.history.replaceState(null, '', hash);
}

async function bootstrap() {
  try {
    const view = parseHash();
    const { map, world, labels } = await initMap(document.getElementById('map'), view ?? {});

    app.band = bandForZoom(map.getZoom(), world.bands);
    await labels.setBand(app.band);

    const updateStatus = () => {
      const center = map.getCenter();
      app.zoom = map.getZoom();
      app.center = { lon: center.lng, lat: center.lat };
      app.visibleLabelCount = labels.visible();
      setStatus(
        `${app.band} · z${app.zoom.toFixed(2)} · ${world.world.name} · 标签 ${app.visibleLabelCount}`,
      );
    };

    const sync = () => {
      updateStatus();
      writeHash(map);
    };

    map.on('move', () => {
      app.visibleLabelCount = labels.visible();
    });
    map.on('idle', updateStatus);
    map.on('moveend', () => {
      const band = bandForZoom(map.getZoom(), world.bands);
      if (band !== app.band) {
        app.band = band;
        labels.setBand(band).then(sync);
      } else {
        labels.refresh();
        sync();
      }
    });

    app.ready = true;
    sync();

    // 浏览器只改 hash 不会重新加载页面；手动同步相机，保证 #z/lat/lon 始终生效。
    window.addEventListener('hashchange', () => {
      const next = parseHash();
      if (next) map.jumpTo({ center: [next.center.lon, next.center.lat], zoom: next.zoom });
    });
  } catch (error) {
    setStatus(`启动失败：${String(error)}`);
    throw error;
  }
}

// @ts-ignore -- 测试钩子
window.__app = app;

bootstrap();
