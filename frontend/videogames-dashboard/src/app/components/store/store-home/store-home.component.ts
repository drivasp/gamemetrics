import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { timeout, catchError, of } from 'rxjs';
import { StoreService, StoreGame } from '../../../services/store.service';
import { MatIconModule } from '@angular/material/icon';
import { StoreGameCardComponent } from '../store-game-card/store-game-card.component';
import { GameCoverComponent } from '../../../shared/game-cover/game-cover.component';

@Component({
  selector: 'app-store-home',
  standalone: true,
  imports: [CommonModule, StoreGameCardComponent, MatIconModule, GameCoverComponent],
  templateUrl: './store-home.component.html',
  styleUrl: './store-home.component.scss',
})
export class StoreHomeComponent implements OnInit {
  private svc = inject(StoreService);
  private cdr = inject(ChangeDetectorRef);
  private router = inject(Router);

  loading = true;
  featured: StoreGame[] = [];
  newReleases: StoreGame[] = [];
  popular: StoreGame[] = [];
  freeGames: StoreGame[] = [];
  spotIndex = 0;
  spotHoverSlug: string | null = null;

  get visibleFeatured(): StoreGame[] {
    if (this.featured.length <= 3) return this.featured;
    const n = this.featured.length;
    const prev = (this.spotIndex - 1 + n) % n;
    const next = (this.spotIndex + 1) % n;
    return [this.featured[prev], this.featured[this.spotIndex], this.featured[next]];
  }

  ngOnInit(): void {
    // Carga por sección: un endpoint lento no bloquea toda la tienda.
    const load = <T>(obs: ReturnType<StoreService['getFeatured']>, assign: (v: StoreGame[]) => void) => {
      obs.pipe(
        timeout(8000),
        catchError(() => of([] as StoreGame[])),
      ).subscribe({
        next: (games) => {
          assign(games);
          this.loading = false;
          this.cdr.detectChanges();
        },
      });
    };

    load(this.svc.getFeatured(), (g) => { this.featured = g; });
    load(this.svc.getNewReleases(), (g) => { this.newReleases = g; });
    load(this.svc.getPopular(), (g) => { this.popular = g; });
    load(this.svc.getFreeGames(), (g) => { this.freeGames = g; });
  }

  setSpot(i: number): void {
    this.spotIndex = i;
    this.cdr.detectChanges();
  }

  nextSpot(): void {
    if (!this.featured.length) return;
    this.spotIndex = (this.spotIndex + 1) % this.featured.length;
    this.cdr.detectChanges();
  }

  prevSpot(): void {
    if (!this.featured.length) return;
    this.spotIndex = (this.spotIndex - 1 + this.featured.length) % this.featured.length;
    this.cdr.detectChanges();
  }

  setSpotHover(slug: string): void {
    this.spotHoverSlug = slug;
    this.cdr.detectChanges();
  }

  clearSpotHover(): void {
    this.spotHoverSlug = null;
    this.cdr.detectChanges();
  }

  goToDetail(slug: string): void {
    this.router.navigate(['/store/game', slug]);
  }

  goToCatalog(filter?: string): void {
    if (filter === 'free') {
      this.router.navigate(['/store/catalog'], { queryParams: { price_filter: 'free' } });
    } else {
      this.router.navigate(['/store/catalog']);
    }
  }
}
