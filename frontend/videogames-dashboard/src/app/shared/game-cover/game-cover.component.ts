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
      this.displaySrc = coverPlaceholderUrl(this.slug, label);
      return;
    }
    this.useInlineFallback = true;
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
    this.useInlineFallback = true;
  }
}
