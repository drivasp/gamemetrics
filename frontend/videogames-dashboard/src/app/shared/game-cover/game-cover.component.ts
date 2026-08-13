import { Component, Input, OnChanges } from '@angular/core';
import { coverPlaceholderUrl } from '../utils/cover-url';

@Component({
  selector: 'app-game-cover',
  standalone: true,
  templateUrl: './game-cover.component.html',
  styleUrl: './game-cover.component.scss',
})
export class GameCoverComponent implements OnChanges {
  @Input() src: string | null | undefined;
  @Input() alt = 'Juego';
  @Input() slug = '';
  @Input() title = '';
  @Input() showTitle = false;
  @Input() imgClass = '';
  @Input() size: 'card' | 'thumb' | 'cover' | 'inline' = 'card';

  displaySrc = '';
  useInlineFallback = false;
  private triedBackendPlaceholder = false;

  ngOnChanges(): void {
    this.useInlineFallback = false;
    this.triedBackendPlaceholder = false;
    this.resolveSrc();
  }

  onImageError(): void {
    const label = this.title || this.alt;
    if (!this.triedBackendPlaceholder && label) {
      this.triedBackendPlaceholder = true;
      const ph = coverPlaceholderUrl(this.slug, label);
      if (ph !== this.displaySrc) {
        this.displaySrc = ph;
        return;
      }
    }
    // Último recurso: data-URI (sin red) para nunca mostrar icono roto del navegador.
    this.displaySrc = this.inlineDataUri(label || 'Juego');
    this.useInlineFallback = false;
  }

  private resolveSrc(): void {
    const label = this.title || this.alt;
    if (this.src) {
      this.displaySrc = this.src;
      return;
    }
    if (label) {
      this.displaySrc = coverPlaceholderUrl(this.slug, label);
      return;
    }
    this.displaySrc = this.inlineDataUri('Juego');
  }

  private inlineDataUri(title: string): string {
    const safe = title
      .slice(0, 36)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">` +
      `<rect width="600" height="400" fill="#1b2838"/>` +
      `<text x="300" y="200" fill="#ffffff" font-family="Segoe UI,Arial,sans-serif" font-size="26" font-weight="700" text-anchor="middle">${safe}</text>` +
      `<text x="300" y="240" fill="#8f98a0" font-family="Segoe UI,Arial,sans-serif" font-size="14" text-anchor="middle">Portada no disponible</text>` +
      `</svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  }
}
