// @ts-check
/**
 * 面板零件：可折叠分节、开关行、统计表、列表行、空态。
 * 只生成 DOM，不发请求、不读写 map；样式见 style.css。
 */

/**
 * 可折叠分节。
 * @param {{ title: string, subtitle?: string, open?: boolean }} options
 * @returns {{ root: HTMLElement, body: HTMLElement, setSubtitle: (text: string) => void }}
 */
export function section({ title, subtitle = '', open = true }) {
  const root = document.createElement('section');
  root.className = 'panel';

  const head = document.createElement('div');
  head.className = 'panel-head';

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'panel-toggle';
  toggle.setAttribute('aria-expanded', String(open));

  const label = document.createElement('span');
  label.className = 'panel-title';
  label.textContent = title;

  const chevron = document.createElement('span');
  chevron.className = 'chevron';
  chevron.setAttribute('aria-hidden', 'true');

  toggle.append(label, chevron);

  const meta = document.createElement('span');
  meta.className = 'panel-meta';
  meta.textContent = subtitle;

  head.append(toggle, meta);

  const body = document.createElement('div');
  body.className = 'panel-body';
  body.hidden = !open;
  root.classList.toggle('is-collapsed', !open);

  toggle.addEventListener('click', () => {
    const next = body.hidden;
    body.hidden = !next;
    root.classList.toggle('is-collapsed', !next);
    toggle.setAttribute('aria-expanded', String(next));
  });

  root.append(head, body);

  return {
    root,
    body,
    setSubtitle: (text) => {
      meta.textContent = text;
    },
  };
}

/**
 * 开关行：左侧开关、可选颜色点、标题。
 * @param {{ title: string, color?: string, checked?: boolean, onChange?: (checked: boolean) => void }} options
 * @returns {HTMLElement}
 */
export function switchRow({ title, color = '', checked = true, onChange }) {
  const row = document.createElement('label');
  row.className = 'switch-row';

  const input = document.createElement('input');
  input.type = 'checkbox';
  input.checked = checked;
  input.addEventListener('change', () => onChange?.(input.checked));

  const track = document.createElement('span');
  track.className = 'switch-track';
  track.setAttribute('aria-hidden', 'true');

  row.append(input, track);

  if (color) {
    const dot = document.createElement('span');
    dot.className = 'swatch';
    dot.style.background = color;
    row.appendChild(dot);
  }

  const text = document.createElement('span');
  text.className = 'switch-label';
  text.textContent = title;
  row.appendChild(text);

  return row;
}

/**
 * 小标题（组内分隔）。
 * @param {{ title: string, color?: string, count?: number }} options
 * @returns {HTMLElement}
 */
export function groupHeader({ title, color = '', count }) {
  const head = document.createElement('div');
  head.className = 'group-head';

  if (color) {
    const dot = document.createElement('span');
    dot.className = 'swatch';
    dot.style.background = color;
    head.appendChild(dot);
  }

  const text = document.createElement('span');
  text.className = 'group-title';
  text.textContent = title;
  head.appendChild(text);

  if (count !== undefined) {
    const badge = document.createElement('span');
    badge.className = 'count';
    badge.textContent = String(count);
    head.appendChild(badge);
  }

  return head;
}

/**
 * 可点击列表行。
 * @param {{ id: string, title: string, meta?: string, active?: boolean, onClick: (id: string) => void }} options
 * @returns {HTMLButtonElement}
 */
export function listRow({ id, title, meta = '', active = false, onClick }) {
  const row = document.createElement('button');
  row.type = 'button';
  row.className = 'list-row';
  row.dataset.id = id;
  row.classList.toggle('is-active', active);

  const text = document.createElement('span');
  text.className = 'list-title';
  text.textContent = title;
  row.appendChild(text);

  if (meta) {
    const suffix = document.createElement('span');
    suffix.className = 'list-meta';
    suffix.textContent = meta;
    row.appendChild(suffix);
  }

  row.addEventListener('click', () => onClick(id));
  return row;
}

/**
 * 键值统计表。
 * @param {[string, string][]} entries
 * @returns {HTMLElement}
 */
export function statGrid(entries) {
  const grid = document.createElement('dl');
  grid.className = 'stats';
  for (const [key, value] of entries) {
    const dt = document.createElement('dt');
    dt.textContent = key;
    const dd = document.createElement('dd');
    dd.textContent = value;
    grid.append(dt, dd);
  }
  return grid;
}

/**
 * 空态提示。
 * @param {string} text
 * @returns {HTMLElement}
 */
export function emptyState(text) {
  const element = document.createElement('p');
  element.className = 'empty-state';
  element.textContent = text;
  return element;
}
