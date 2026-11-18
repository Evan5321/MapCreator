// @ts-check
/**
 * 启动入口：只做装配，不放业务逻辑（AGENTS.md §5）。
 * 当前为骨架：地图初始化见 map.js（TASK-0006）。
 */

import { bandForZoom, initMap } from './map.js';

/** 测试模式暴露的只读探针（E2E 断言用，见 docs/TESTING.md §4）。 */
const app = {
  ready: false,
  zoom: 0,
  center: { lon: 0, lat: 0 },
  band: null,
  visibleLabelCount: 0,
  selectedId: null,
};

async function bootstrap() {
  try {
    const map = await initMap(document.getElementById('map'));
    const center = map.getCenter();
    app.zoom = map.getZoom();
    app.center = { lon: center.lng, lat: center.lat };
    app.band = bandForZoom(app.zoom);
    app.ready = true;
  } catch (error) {
    const status = document.getElementById('statusbar');
    if (status) status.textContent = `启动失败：${String(error)}`;
    throw error;
  }
}

// @ts-ignore -- 测试钩子
window.__app = app;

bootstrap();
