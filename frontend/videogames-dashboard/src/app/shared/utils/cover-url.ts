/** URL del placeholder SVG servido por el backend (sin RAWG). */
export function coverPlaceholderUrl(slug: string, title: string): string {
  const key = encodeURIComponent(slug || title.slice(0, 40) || 'game');
  const t = encodeURIComponent((title || 'Juego').slice(0, 40));
  return `/store/cover-placeholder/${key}?title=${t}`;
}
