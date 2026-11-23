// @ts-check
/**
 * 启动入口：只做装配，不放业务逻辑（AGENTS.md §5）。
 * URL 状态：#z/lat/lon?sel=<annotation-id>&lang=<bcp47>，随地图移动与选中写回 history。
 */

import 'maplibre-gl/dist/maplibre-gl.css';

import { getAnnotation } from './api.js';
import { createEditor } from './editor.js';
import { bandForZoom, initMap } from './map.js';
import { createShell } from './shell.js';
import { bindShortcuts } from './shortcuts.js';
import { hideDetail, renderDetail, renderDetailError } from './ui.js';

/** 测试模式暴露的只读探针（E2E 断言用，见 docs/TESTING.md §4）。 */
const app = {
  ready: false,
  zoom: 0,
  center: { lon: 0, lat: 0 },
  band: null,
  visibleLabelCount: 0,
  selectedId: null,
  lang: null,
  mode: 'browse',
  tool: 'select',
  draftCount: 0,
};

/**
 * 解析 `#z/lat/lon?sel=...&lang=...`。
 * @returns {{
 *   zoom?: number,
 *   center?: { lon: number, lat: number },
 *   params: URLSearchParams,
 * } | null}
 */
function parseHash() {
  const raw = window.location.hash.replace(/^#/, '');
  if (!raw) return null;
  const [cameraRaw, query = ''] = raw.split('?');
  const params = new URLSearchParams(query);
  const match = /^([0-9.]+)\/([-\d.]+)\/([-\d.]+)$/.exec(cameraRaw);
  if (!match) return params.size > 0 ? { params } : null;
  return {
    zoom: Number(match[1]),
    center: { lat: Number(match[2]), lon: Number(match[3]) },
    params,
  };
}

/** @param {import('maplibre-gl').Map} map */
function writeHash(map) {
  const center = map.getCenter();
  const params = new URLSearchParams();
  if (app.selectedId) params.set('sel', app.selectedId);
  if (app.lang) params.set('lang', app.lang);
  const query = params.toString();
  const hash = `#${map.getZoom().toFixed(2)}/${center.lat.toFixed(5)}/${center.lng.toFixed(5)}${
    query ? `?${query}` : ''
  }`;
  window.history.replaceState(null, '', hash);
}

async function bootstrap() {
  try {
    const initial = parseHash();
    app.lang = initial?.params.get('lang') ?? null;

    const { map, world, labels, pointLayers } = await initMap(
      document.getElementById('map'),
      initial ?? {},
      {
        onSelect: (id) => select(id),
        getSelectedId: () => app.selectedId,
      },
    );
    const layers = pointLayers.filter((layer) => map.getLayer(layer) !== undefined);

    const shell = createShell({
      world,
      map,
      onSelect: (id) => select(id),
      onKindVisibility: (kind, visible) => labels.setKindVisible(kind, visible),
    });

    app.band = bandForZoom(map.getZoom(), world.bands);
    await labels.setBand(app.band);
    shell.setBand(app.band);
    shell.setAnnotations(labels.list());

    const editor = createEditor({
      map,
      world,
      onStatus: (text) => shell.setStatus(text),
      onProbe: (state) => {
        app.mode = state.enabled ? 'edit' : 'browse';
        app.tool = state.tool;
        app.draftCount = state.draftCount;
      },
      onSelection: (draft) => {
        if (!draft) {
          app.selectedId = null;
          shell.setSelected(null);
          hideDetail();
          labels.refresh();
          updateStatus();
          writeHash(map);
          return;
        }
        app.selectedId = draft.annotationId;
        shell.setSelected(app.selectedId);
        renderDraftDetail(draft);
        labels.refresh();
        updateStatus();
        writeHash(map);
      },
    });

    /**
     * 用草稿数据渲染右侧只读详情。
     * @param {any} draft
     */
    function renderDraftDetail(draft) {
      const primary = draft.names.find((/** @type {any} */ item) => item.is_primary);
      renderDetail(
        {
          id: draft.annotationId ?? `draft:${draft.key}`,
          kind: draft.kind,
          lon: draft.lon,
          lat: draft.lat,
          rank: draft.rank,
          label_mode: draft.labelMode,
          min_zoom: draft.min_zoom,
          max_zoom: draft.max_zoom,
          primary_name: primary?.name || null,
          default_lang: world.world.default_lang,
          names: draft.names.map((/** @type {any} */ item) => ({
            lang: item.lang,
            name: item.name,
            role: item.role ?? 'name',
            is_primary: Boolean(item.is_primary),
          })),
          description: draft.description || null,
          attrs: draft.attrs ?? {},
          geometry_id: draft.geometryId,
          color: world.kinds[draft.kind]?.color ?? null,
        },
        { lang: app.lang },
      );
    }

    /** @param {string} id */
    async function select(id) {
      app.selectedId = id;
      shell.setSelected(id);
      if (editor.isEnabled()) {
        const local = editor.selectAnnotation(id);
        if (local) {
          renderDraftDetail(local);
          labels.refresh();
          updateStatus();
          writeHash(map);
          return;
        }
        try {
          const detail = await getAnnotation(id);
          renderDetail(detail, { lang: app.lang });
          editor.addExisting(detail);
        } catch (error) {
          renderDetailError(id, error);
        }
        labels.refresh();
        updateStatus();
        writeHash(map);
        return;
      }
      try {
        const detail = await getAnnotation(id);
        renderDetail(detail, { lang: app.lang });
      } catch (error) {
        renderDetailError(id, error);
      }
      labels.refresh();
      updateStatus();
      writeHash(map);
    }

    function clearSelection() {
      app.selectedId = null;
      shell.setSelected(null);
      hideDetail();
      if (editor.isEnabled()) editor.clearSelection();
      labels.refresh();
      updateStatus();
      writeHash(map);
    }

    const updateStatus = () => {
      const center = map.getCenter();
      app.zoom = map.getZoom();
      app.center = { lon: center.lng, lat: center.lat };
      app.visibleLabelCount = labels.visible();
      const mode = app.mode === 'edit' ? `编辑 · ${app.tool}` : '浏览';
      const selection = app.selectedId ? ` · 选中 ${app.selectedId}` : '';
      shell.setStatus(
        `${mode} · ${app.band} · z${app.zoom.toFixed(2)} · ${world.world.name} · 标签 ${app.visibleLabelCount}${selection}`,
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
        labels.setBand(band).then(() => {
          shell.setBand(band);
          shell.setAnnotations(labels.list());
          sync();
        });
      } else {
        labels.refresh();
        sync();
      }
    });

    map.on('click', (event) => {
      if (app.mode === 'edit') return;
      const hits = layers.length > 0 ? map.queryRenderedFeatures(event.point, { layers }) : [];
      const hit = hits[0];
      if (hit) {
        const id = hit.id ?? hit.properties?.id;
        if (id !== undefined && id !== null) select(String(id));
      } else if (app.selectedId) {
        clearSelection();
      }
    });

    map.on('mousemove', (event) => {
      if (app.mode === 'edit') return;
      const hits = layers.length > 0 ? map.queryRenderedFeatures(event.point, { layers }) : [];
      map.getCanvas().style.cursor = hits.length > 0 ? 'pointer' : '';
    });

    const closeButton = document.getElementById('detail-close');
    closeButton?.addEventListener('click', clearSelection);

    const modeButton = document.getElementById('btn-mode');
    const exportButton = document.getElementById('btn-export');

    /**
     * @param {'browse' | 'edit'} mode
     */
    function setMode(mode) {
      if (mode === 'edit') {
        editor.enable();
        shell.setMode('edit');
        app.mode = 'edit';
        if (modeButton) modeButton.textContent = '退出编辑';
        if (exportButton) exportButton.hidden = false;
        updateStatus();
        return;
      }
      editor.disable();
      shell.setMode('browse');
      app.mode = 'browse';
      if (modeButton) modeButton.textContent = '进入编辑';
      if (exportButton) exportButton.hidden = true;
      clearSelection();
    }

    modeButton?.addEventListener('click', () => {
      setMode(editor.isEnabled() ? 'browse' : 'edit');
    });
    exportButton?.addEventListener('click', () => editor.exportDownload());

    bindShortcuts({
      Escape: () => {
        if (editor.handleEscape()) return;
        if (app.selectedId) clearSelection();
      },
    });

    app.ready = true;
    // 测试探针：编辑器状态与导出内容（E2E 断言用）。
    app.editorProbe = () => editor.probe();
    app.exportPayload = () => editor.exportPayload();
    sync();

    const initialSelection = initial?.params.get('sel');
    if (initialSelection) await select(initialSelection);

    // 浏览器只改 hash 不会重新加载页面；手动同步相机与选中状态。
    window.addEventListener('hashchange', () => {
      const next = parseHash();
      if (!next) return;
      if (next.center) {
        map.jumpTo({ center: [next.center.lon, next.center.lat], zoom: next.zoom });
      }
      const lang = next.params.get('lang');
      if (lang !== app.lang) {
        app.lang = lang;
        if (app.selectedId) select(app.selectedId);
      }
      const selection = next.params.get('sel');
      if (selection && selection !== app.selectedId) {
        select(selection);
      } else if (!selection && app.selectedId) {
        clearSelection();
      }
    });
  } catch (error) {
    const status = document.getElementById('statusbar');
    if (status) status.textContent = `启动失败：${String(error)}`;
    throw error;
  }
}

// @ts-ignore -- 测试钩子
window.__app = app;

bootstrap();
