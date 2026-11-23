// @ts-check
/**
 * 面板：右侧详情（多语言名称、坐标、有效缩放、attrs）。
 * 只做 DOM 渲染，不发请求；数据由 main.js 通过 /api/annotations/{id} 取回。
 * 左栏与状态栏归 shell.js。
 */

/**
 * @typedef {{
 *   lang: string,
 *   name: string,
 *   role: string,
 *   is_primary: boolean,
 * }} DetailName
 *
 * @typedef {{
 *   id: string,
 *   kind: string,
 *   lon: number,
 *   lat: number,
 *   rank: number,
 *   label_mode?: string,
 *   min_zoom: number | null,
 *   max_zoom: number | null,
 *   primary_name: string | null,
 *   default_lang: string,
 *   names: DetailName[],
 *   description?: string | null,
 *   attrs?: Record<string, unknown>,
 *   geometry_id?: string | null,
 *   revision?: number,
 *   color?: string | null,
 * }} AnnotationDetail
 */

/**
 * 渲染详情面板并显示。
 * @param {AnnotationDetail} detail
 * @param {{ lang?: string | null }} [options]
 */
export function renderDetail(detail, options = {}) {
  const sidebar = document.getElementById('sidebar');
  const title = document.getElementById('detail-title');
  const body = document.getElementById('detail-body');
  if (!sidebar || !title || !body) return;

  const lang = options.lang || detail.default_lang;
  title.textContent = pickName(detail, lang) ?? detail.id;
  title.style.color = detail.color || '';

  /** @type {HTMLElement[]} */
  const sections = [];
  if (detail.names?.length) sections.push(namesSection(detail.names, lang));
  sections.push(metaSection(detail));
  if (detail.description) sections.push(paragraph('description', detail.description));
  if (detail.attrs && Object.keys(detail.attrs).length > 0) {
    sections.push(paragraph('attrs', JSON.stringify(detail.attrs, null, 2), 'pre'));
  }

  body.replaceChildren(...sections);
  sidebar.hidden = false;
}

/**
 * 详情加载失败时保留面板并给出可读错误。
 * @param {string} id
 * @param {unknown} error
 */
export function renderDetailError(id, error) {
  const sidebar = document.getElementById('sidebar');
  const title = document.getElementById('detail-title');
  const body = document.getElementById('detail-body');
  if (!sidebar || !title || !body) return;

  const err =
    /** @type {{ code?: string, detail?: { message?: string, remediation?: string } }} */ (error);
  title.textContent = '详情加载失败';
  title.style.color = '';
  const message = err?.detail?.message || String(error);
  const nodes = [paragraph('error', `${err?.code ?? 'REQUEST_FAILED'}：${message}（${id}）`)];
  if (err?.detail?.remediation) nodes.push(paragraph('hint', err.detail.remediation));
  body.replaceChildren(...nodes);
  sidebar.hidden = false;
}

export function hideDetail() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.hidden = true;
}

/**
 * 标题用名：优先所选语种的主名，其次该语种任意名，最后主名。
 * @param {AnnotationDetail} detail
 * @param {string} lang
 */
function pickName(detail, lang) {
  const names = detail.names ?? [];
  const exact = names.find((item) => item.lang === lang && item.is_primary);
  if (exact) return exact.name;
  const any = names.find((item) => item.lang === lang);
  if (any) return any.name;
  return detail.primary_name ?? names.find((item) => item.is_primary)?.name ?? names[0]?.name;
}

/**
 * 多语言名称列表：全部叠加显示，当前语种高亮。
 * @param {DetailName[]} names
 * @param {string} lang
 */
function namesSection(names, lang) {
  const list = document.createElement('div');
  list.className = 'names';
  for (const item of names) {
    const row = document.createElement('div');
    row.className = 'name-row';
    if (item.lang === lang) row.classList.add('is-active');

    const tag = document.createElement('span');
    tag.className = 'name-lang';
    tag.textContent = item.lang;
    row.appendChild(tag);

    const value = document.createElement('span');
    value.className = 'name-value';
    value.textContent = item.name;
    row.appendChild(value);

    if (item.is_primary) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = '主名';
      row.appendChild(badge);
    }
    if (item.role === 'alias') {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = '别名';
      row.appendChild(badge);
    }
    list.appendChild(row);
  }
  return list;
}

/** @param {AnnotationDetail} detail */
function metaSection(detail) {
  const dl = document.createElement('dl');
  dl.className = 'meta';
  const rows = [
    ['ID', detail.id],
    ['类型', detail.kind],
    ['坐标', `${detail.lon.toFixed(6)}, ${detail.lat.toFixed(6)}`],
    [
      '显示缩放',
      detail.min_zoom === null || detail.max_zoom === null
        ? '—'
        : `z${detail.min_zoom}–z${detail.max_zoom}`,
    ],
    ['层级', `rank ${detail.rank}`],
    ['几何', detail.geometry_id ?? '点标注（无几何）'],
  ];
  if (detail.revision !== undefined) rows.push(['修订', String(detail.revision)]);
  for (const [label, value] of rows) {
    const dt = document.createElement('dt');
    dt.textContent = label;
    const dd = document.createElement('dd');
    dd.textContent = value;
    dl.append(dt, dd);
  }
  return dl;
}

/**
 * @param {string} kindName
 * @param {string} text
 * @param {'p' | 'pre'} [tag]
 */
function paragraph(kindName, text, tag = 'p') {
  const element = document.createElement(tag);
  element.className = kindName;
  element.textContent = text;
  return element;
}
