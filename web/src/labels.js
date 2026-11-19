// @ts-check
/**
 * DOM 标签层：仓库内没有 glyph/字体资产，因此不依赖 MapLibre symbol 图层，
 * 直接投影到屏幕并做贪心碰撞剔除（按 rank 优先）。
 */

/**
 * @typedef {{ properties: { name?: string, kind?: string, rank?: number } }} LabelFeature
 */

/**
 * @param {import('maplibre-gl').Map} map
 * @param {{ typography: Record<string, number[]>, kinds: Record<string, { color?: string }> }} world
 * @param {(band: string) => Promise<{ features: LabelFeature[] }>} loadBand
 */
export function createLabelLayer(map, world, loadBand) {
  const host = document.createElement('div');
  host.className = 'label-layer';
  map.getContainer().appendChild(host);

  /** @type {LabelFeature[]} */
  let features = [];
  /** @type {string | null} */
  let band = null;
  let scheduled = false;
  let visible = 0;

  /** @param {number} rank @param {number} zoom */
  const sizeFor = (rank, zoom) => {
    const pair = world.typography[String(rank)] ?? world.typography['3'] ?? [13, 15];
    return zoom >= 13 ? pair[1] : pair[0];
  };

  function place() {
    scheduled = false;
    const zoom = map.getZoom();
    const width = map.getContainer().clientWidth;
    const height = map.getContainer().clientHeight;
    /** @type {{ x: number, y: number, w: number, h: number }[]} */
    const taken = [];
    const kept = [];

    for (const feature of features) {
      const text = feature.properties.name || '';
      if (!text) continue;
      const size = sizeFor(feature.properties.rank ?? 3, zoom);
      // @ts-ignore -- Point geometry
      const point = map.project(feature.geometry.coordinates);
      const w = text.length * size * 0.95 + 8;
      const h = size + 6;
      const rect = { x: point.x - w / 2, y: point.y - h / 2, w, h };
      if (rect.x < 4 || rect.y < 4 || rect.x + w > width - 4 || rect.y + h > height - 4) continue;
      if (taken.some((other) => overlaps(rect, other))) continue;
      taken.push(rect);
      kept.push({ text, rect, size, kind: feature.properties.kind });
    }

    host.replaceChildren(
      ...kept.map(({ text, rect, size, kind }) => {
        const element = document.createElement('span');
        element.className = 'label';
        element.textContent = text;
        element.style.left = `${rect.x + rect.w / 2}px`;
        element.style.top = `${rect.y + rect.h / 2}px`;
        element.style.fontSize = `${size}px`;
        if (kind && world.kinds[kind]?.color) element.style.color = world.kinds[kind].color;
        return element;
      }),
    );
    visible = kept.length;
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    // 后台标签页里 rAF 可能被暂停，用定时器兜底，保证标签仍会渲染。
    if (document.hidden) setTimeout(place, 0);
    else requestAnimationFrame(place);
  }

  /** @param {string | null} next */
  async function setBand(next) {
    if (!next || next === band) return;
    const requested = next;
    band = requested;
    try {
      const collection = await loadBand(requested);
      if (band !== requested) return;
      features = [...collection.features].sort(
        (a, b) =>
          (a.properties.rank ?? 3) - (b.properties.rank ?? 3) ||
          String(a.properties.name ?? '').localeCompare(String(b.properties.name ?? '')),
      );
    } catch (error) {
      features = [];
      console.warn(`标签分片加载失败：${requested}`, error);
    }
    // 立即可见：不依赖下一帧（后台标签页会暂停 rAF）。
    place();
  }

  map.on('move', schedule);
  map.on('moveend', schedule);
  map.on('resize', schedule);
  // 首帧渲染完成后再排一次：容器尺寸/相机在 load 时可能尚未稳定。
  map.on('idle', place);

  return {
    setBand,
    /** @returns {number} 当前实际显示的标签数 */
    visible: () => visible,
    /** 测试钩子：立即重排一次 */
    refresh: place,
  };
}

/**
 * @param {{x:number,y:number,w:number,h:number}} a
 * @param {{x:number,y:number,w:number,h:number}} b
 */
function overlaps(a, b) {
  return !(a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y || b.y + b.h < a.y);
}
