import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { StoreGame } from '../../../services/store.service';

@Component({
  selector: 'app-game-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './store-game-card.component.html',
  styleUrl: './store-game-card.component.scss',
})
export class StoreGameCardComponent {
  @Input() game!: StoreGame;

  private router = inject(Router);
  hovering = false;

  navigate(): void {
    this.router.navigate(['/store/game', this.game.slug]);
  }

  get displayGenres(): string {
    return this.game.genres
      .split('||')
      .slice(0, 2)
      .map(g => g.trim())
      .filter(Boolean)
      .join(' · ');
  }

  get priceLabel(): string {
    if (this.game.is_free) return 'GRATIS';
    return '$' + this.game.price.toFixed(2);
  }

  get originalPriceLabel(): string | null {
    if (!this.game.original_price || !this.game.discount_pct) return null;
    return '$' + this.game.original_price.toFixed(2);
  }
}
