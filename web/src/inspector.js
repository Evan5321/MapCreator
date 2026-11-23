// @ts-check
/**
 * 左栏「属性」分节：草稿标注的表单。
 * 只收集与校验输入，不直接改编辑器状态；保存/取消/删除通过回调交给 editor.js。
 */

const LANG_PATTERN = /^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$/;

/**
 * @typedef {{
 *   key: string,
 *   terraId: string | number | null,
 *   annotationId: string | null,
 *   geometryId: string | null,
 *   kind: string,
 *   names: { lang: string, name: string, role?: string, is_primary: boolean }[],
 *   rank: number,
 *   min_zoom: number | null,
 *   max_zoom: number | null,
 *   description: string,
 *   attrs: Record<string, unknown>,
 *   labelMode: 'point' | 'line' | 'none',
 *   origin: 'draft' | 'existing',
 *   lon: number,
 *   lat: number,
 * }} Draft
 */

/**
 * @param {{
 *   world: { world: { default_lang: string, languages: string[] }, kinds: Record<string, { rank?: number }> },
 *   onSave: (draft: Draft) => void,
 *   onCancel: (draft: Draft, meta: { isNew: boolean }) => void,
 *   onDelete: (draft: Draft) => void,
 * }} options
 */
export function createInspector({ world, onSave, onCancel, onDelete }) {
  const element = document.createElement('div');
  element.className = 'inspector';
  element.id = 'inspector';

  const empty = document.createElement('p');
  empty.className = 'empty-state';
  empty.textContent = '未选中标注或草稿';

  const form = document.createElement('form');
  form.className = 'inspector-form';
  form.noValidate = true;
  form.hidden = true;

  const kindSelect = document.createElement('select');
  kindSelect.className = 'form-control';
  const kinds = Object.entries(world.kinds)
    .sort(([nameA, a], [nameB, b]) => (a.rank ?? 99) - (b.rank ?? 99) || nameA.localeCompare(nameB))
    .map(([name]) => name);
  for (const kind of kinds) {
    const option = document.createElement('option');
    option.value = kind;
    option.textContent = kind;
    kindSelect.appendChild(option);
  }
  const kindField = field('kind', kindSelect, 'kind');

  const namesField = document.createElement('div');
  namesField.className = 'form-field';
  const namesHead = document.createElement('div');
  namesHead.className = 'form-label-line';
  const namesLabel = document.createElement('span');
  namesLabel.className = 'form-label';
  namesLabel.textContent = '名称';
  const addNameButton = document.createElement('button');
  addNameButton.type = 'button';
  addNameButton.className = 'mini-button';
  addNameButton.textContent = '添加语种';
  namesHead.append(namesLabel, addNameButton);
  const nameRows = document.createElement('div');
  nameRows.className = 'name-rows';
  const namesError = errorNode('names');
  namesField.append(namesHead, nameRows, namesError);
  addNameButton.addEventListener('click', () => addNameRow({}));

  const rankSelect = document.createElement('select');
  rankSelect.className = 'form-control';
  for (const value of ['1', '2', '3', '4', '5']) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    rankSelect.appendChild(option);
  }
  const rankField = field('rank', rankSelect, 'rank');

  const zoomRow = document.createElement('div');
  zoomRow.className = 'zoom-row';
  const minZoom = numberInput('min_zoom', '最小 zoom（留空继承）');
  const maxZoom = numberInput('max_zoom', '最大 zoom（留空继承）');
  zoomRow.append(minZoom, maxZoom);
  const zoomField = field('zoom 范围', zoomRow, 'zoom');
  zoomField.wrap.querySelector('.form-label')?.classList.add('is-block');

  const description = document.createElement('textarea');
  description.className = 'form-control';
  description.rows = 3;
  description.placeholder = '可选描述';
  const descriptionField = field('描述', description, 'description');

  const attrs = document.createElement('textarea');
  attrs.className = 'form-control code';
  attrs.rows = 4;
  attrs.placeholder = '{"population": 12000}';
  const attrsField = field('attrs（JSON 对象）', attrs, 'attrs');

  const actions = document.createElement('div');
  actions.className = 'form-actions';
  const saveButton = document.createElement('button');
  saveButton.type = 'submit';
  saveButton.className = 'primary-button';
  saveButton.textContent = '保存';
  const cancelButton = document.createElement('button');
  cancelButton.type = 'button';
  cancelButton.className = 'ghost-button';
  cancelButton.textContent = '取消';
  const deleteButton = document.createElement('button');
  deleteButton.type = 'button';
  deleteButton.className = 'ghost-button danger';
  deleteButton.textContent = '删除';
  actions.append(saveButton, cancelButton, deleteButton);

  form.append(
    kindField.wrap,
    namesField,
    rankField.wrap,
    zoomField.wrap,
    descriptionField.wrap,
    attrsField.wrap,
    actions,
  );
  element.append(empty, form);

  /** @type {{ draft: Draft, isNew: boolean } | null} */
  let state = null;

  cancelButton.addEventListener('click', () => {
    if (!state) return;
    onCancel(clone(state.draft), { isNew: state.isNew });
  });
  deleteButton.addEventListener('click', () => {
    if (!state) return;
    onDelete(clone(state.draft));
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    save();
  });

  function save() {
    if (!state) return;
    clearErrors();

    const next = /** @type {Draft} */ (clone(state.draft));
    const minRaw = minZoom.value.trim();
    const maxRaw = maxZoom.value.trim();
    next.kind = kindSelect.value;
    next.names = readNames();
    next.rank = Number(rankSelect.value);
    next.min_zoom = minRaw ? Number(minRaw) : null;
    next.max_zoom = maxRaw ? Number(maxRaw) : null;
    next.description = description.value.trim();
    next.attrs = readAttrs(attrs);

    let failed = false;
    if (!next.kind) {
      setError('kind', '请选择 kind');
      failed = true;
    }
    const named = next.names.filter((item) => item.name);
    if (named.length === 0) {
      setError('names', '至少填写一个名称');
      failed = true;
    }
    const primaries = named.filter((item) => item.is_primary);
    if (named.length > 0 && primaries.length !== 1) {
      setError('names', '必须恰好一个主名');
      failed = true;
    }
    const badLang = named.find((item) => !LANG_PATTERN.test(item.lang));
    if (badLang) {
      setError('names', `语种代码不合法：${badLang.lang || '(空)'}`);
      failed = true;
    }
    if (!Number.isInteger(next.rank) || next.rank < 1 || next.rank > 5) {
      setError('rank', 'rank 必须是 1–5 的整数');
      failed = true;
    }
    if (
      (next.min_zoom !== null && !Number.isFinite(next.min_zoom)) ||
      (next.max_zoom !== null && !Number.isFinite(next.max_zoom))
    ) {
      setError('zoom', 'zoom 必须是数字或留空');
      failed = true;
    } else if (next.min_zoom !== null && next.max_zoom !== null && next.min_zoom > next.max_zoom) {
      setError('zoom', 'min_zoom 不能大于 max_zoom');
      failed = true;
    }
    if (next.attrs === null) {
      setError('attrs', 'attrs 必须是 JSON 对象');
      failed = true;
    }
    if (failed) return;

    next.names = named.map((item) => ({ ...item, name: item.name.trim() }));
    onSave(next);
  }

  /** @returns {{ lang: string, name: string, role: string, is_primary: boolean }[]} */
  function readNames() {
    /** @type {{ lang: string, name: string, role: string, is_primary: boolean }[]} */
    const items = [];
    for (const row of nameRows.querySelectorAll('.name-row-edit')) {
      if (!(row instanceof HTMLElement)) continue;
      const lang = /** @type {HTMLInputElement} */ (row.querySelector('.name-lang')).value.trim();
      const name = /** @type {HTMLInputElement} */ (row.querySelector('.name-name')).value.trim();
      const isPrimary = /** @type {HTMLInputElement} */ (row.querySelector('input[type="radio"]'))
        .checked;
      if (!lang && !name) continue;
      items.push({ lang, name, role: 'name', is_primary: isPrimary });
    }
    return items;
  }

  /**
   * @param {{ lang?: string, name?: string, role?: string, is_primary?: boolean }} entry
   */
  function addNameRow(entry) {
    const row = document.createElement('div');
    row.className = 'name-row-edit';

    const lang = document.createElement('input');
    lang.className = 'name-lang form-control';
    lang.placeholder = 'zh';
    lang.value = entry.lang ?? world.world.default_lang;
    lang.setAttribute('aria-label', '语种');

    const name = document.createElement('input');
    name.className = 'name-name form-control';
    name.placeholder = '名称';
    name.value = entry.name ?? '';
    name.setAttribute('aria-label', '名称');

    const primaryLabel = document.createElement('label');
    primaryLabel.className = 'primary-toggle';
    const primary = document.createElement('input');
    primary.type = 'radio';
    primary.name = 'anno-primary';
    primary.checked = Boolean(entry.is_primary);
    primaryLabel.append(primary, document.createTextNode('主名'));

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'mini-button';
    remove.textContent = '×';
    remove.title = '删除该名称';
    remove.addEventListener('click', () => {
      row.remove();
      if (nameRows.children.length === 0) addNameRow({ is_primary: true });
    });

    row.append(lang, name, primaryLabel, remove);
    nameRows.appendChild(row);
  }

  /** @param {Draft} draft */
  function open(draft) {
    state = { draft: clone(draft), isNew: !draft.annotationId };
    kindSelect.value = draft.kind;
    nameRows.replaceChildren();
    const names =
      draft.names.length > 0
        ? draft.names
        : [{ lang: world.world.default_lang, name: '', is_primary: true }];
    for (const item of names) addNameRow(item);
    rankSelect.value = String(draft.rank);
    minZoom.value = draft.min_zoom === null ? '' : String(draft.min_zoom);
    maxZoom.value = draft.max_zoom === null ? '' : String(draft.max_zoom);
    description.value = draft.description ?? '';
    attrs.value =
      draft.attrs && Object.keys(draft.attrs).length > 0
        ? JSON.stringify(draft.attrs, null, 2)
        : '';
    clearErrors();
    form.hidden = false;
    empty.hidden = true;
  }

  function close() {
    state = null;
    form.hidden = true;
    empty.hidden = false;
  }

  /** @param {boolean} disabled */
  function setDisabled(disabled) {
    for (const control of form.querySelectorAll('input, select, textarea, button')) {
      if (control instanceof HTMLButtonElement || control instanceof HTMLInputElement) {
        control.disabled = disabled;
      } else if (control instanceof HTMLSelectElement || control instanceof HTMLTextAreaElement) {
        control.disabled = disabled;
      }
    }
  }

  /** @param {string} key */
  function errorNode(key) {
    const node = document.createElement('p');
    node.className = 'form-error';
    node.dataset.error = key;
    node.hidden = true;
    return node;
  }

  /** @param {string} key @param {string} message */
  function setError(key, message) {
    const node = form.querySelector(`[data-error="${key}"]`);
    if (!(node instanceof HTMLElement)) return;
    node.textContent = message;
    node.hidden = false;
  }

  function clearErrors() {
    for (const node of form.querySelectorAll('.form-error')) {
      if (node instanceof HTMLElement) {
        node.textContent = '';
        node.hidden = true;
      }
    }
  }

  return {
    element,
    open,
    close,
    setDisabled,
    isOpen: () => state !== null,
  };

  /**
   * @param {string} label
   * @param {HTMLElement} control
   * @param {string} key
   */
  function field(label, control, key) {
    const wrap = document.createElement('div');
    wrap.className = 'form-field';
    const row = document.createElement('label');
    row.className = 'form-row';
    const text = document.createElement('span');
    text.className = 'form-label';
    text.textContent = label;
    row.append(text, control);
    wrap.append(row, errorNode(key));
    return { wrap };
  }
}

/**
 * @param {string} name
 * @param {string} placeholder
 */
function numberInput(name, placeholder) {
  const input = document.createElement('input');
  input.className = 'form-control';
  input.type = 'number';
  input.step = 'any';
  input.name = name;
  input.placeholder = placeholder;
  return input;
}

/**
 * @param {HTMLTextAreaElement} textarea
 * @returns {Record<string, unknown> | null}
 */
function readAttrs(textarea) {
  const raw = textarea.value.trim();
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

/**
 * @template T
 * @param {T} value
 * @returns {T}
 */
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
