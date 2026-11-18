// @ts-check
/**
 * 请求封装：统一 base URL、错误归一化、超时。
 * 约定：只传/接 ID；详情按 ID 回查（D-021）。
 */

const BASE = '';

/**
 * @param {string} path
 * @param {RequestInit} [init]
 */
export async function request(path, init) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  const isJson = (response.headers.get('content-type') || '').includes('application/json');
  const body = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    // @ts-ignore -- 附加结构化信息
    error.code = body?.code ?? 'HTTP_ERROR';
    // @ts-ignore
    error.detail = body;
    throw error;
  }
  return body;
}

/** @param {string} id */
export const getAnnotation = (id) => request(`/api/annotations/${encodeURIComponent(id)}`);

/** @param {string} query */
export const search = (query) => request(`/api/search?q=${encodeURIComponent(query)}`);
