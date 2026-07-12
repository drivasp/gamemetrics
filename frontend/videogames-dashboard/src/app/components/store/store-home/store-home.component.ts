import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { forkJoin, timeout, catchError, of } from 'rxjs';
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
    forkJoin({
      featured: this.svc.getFeatured().pipe(catchError(() => of([]))),
      newReleases: this.svc.getNewReleases().pipe(catchError(() => of([]))),
      popular: this.svc.getPopular().pipe(catchError(() => of([]))),
      freeGames: this.svc.getFreeGames().pipe(catchError(() => of([]))),
    }).pipe(timeout(60000)).subscribe({
      next: ({ featured, newReleases, popular, freeGames }) => {
        this.featured = featured;
        this.newReleases = newReleases;
        this.popular = popular;
        this.freeGames = freeGames;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
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
