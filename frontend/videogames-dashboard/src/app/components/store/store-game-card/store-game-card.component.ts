import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { StoreGame } from '../../../services/store.service';
import { GameCoverComponent } from '../../../shared/game-cover/game-cover.component';

@Component({
  selector: 'app-game-card',
  standalone: true,
  imports: [CommonModule, MatIconModule, GameCoverComponent],
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
