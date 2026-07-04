import { Component, OnInit, OnDestroy, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { StoreService, StoreGame } from '../../../services/store.service';
import { CommunityService } from '../../../services/community.service';
import { StoreGameCardComponent } from '../store-game-card/store-game-card.component';

@Component({
  selector: 'app-catalog',
  standalone: true,
  imports: [CommonModule, FormsModule, StoreGameCardComponent],
  templateUrl: './store-catalog.component.html',
  styleUrl: './store-catalog.component.scss',
})
export class StoreCatalogComponent implements OnInit, OnDestroy {
  private svc = inject(StoreService);
  private community = inject(CommunityService);
  private cdr = inject(ChangeDetectorRef);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  games: StoreGame[] = [];
  allGenres: string[] = [];
  allPlatforms: string[] = [];
  loading = false;
  totalCount = 0;

  page = 0;
  readonly pageSize = 24;

  // Filters
  search = '';
  selectedGenre = '';
  selectedPlatform = '';
  selectedPrice = '';   // '' | 'free' | 'paid'
  orderBy = 'rating';

  readonly orderOptions = [
    { value: 'rating',     label: 'Rating' },
    { value: 'metacritic', label: 'Metacritic' },
    { value: 'price_asc',  label: 'Precio: menor a mayor' },
    { value: 'price_desc', label: 'Precio: mayor a menor' },
    { value: 'released',   label: 'Fecha de lanzamiento' },
    { value: 'name',       label: 'Nombre A-Z' },
  ];

  private searchSubject = new Subject<string>();
  private subs = new Subscription();

  get totalPages(): number { return Math.ceil(this.totalCount / this.pageSize); }

  get showingFrom(): number { return this.totalCount === 0 ? 0 : this.page * this.pageSize + 1; }
  get showingTo(): number   { return Math.min((this.page + 1) * this.pageSize, this.totalCount); }

  get pageNumbers(): number[] {
    const cur = this.page + 1;
    const pages: number[] = [];
    for (let i = Math.max(1, cur - 2); i <= Math.min(this.totalPages, cur + 2); i++) pages.push(i);
    return pages;
  }

  ngOnInit(): void {
    this.svc.getFilters().subscribe({
      next: (f) => {
        this.allGenres = f.genres.slice(0, 30);
        this.allPlatforms = f.platforms.slice(0, 30);
        this.cdr.detectChanges();
      },
    });

    this.subs.add(
      this.searchSubject.pipe(debounceTime(400), distinctUntilChanged()).subscribe(val => {
        this.search = val;
        this.page = 0;
        this.fetchGames();
      })
    );

    this.subs.add(
      this.route.queryParams.subscribe(p => {
        if (p['genre']) this.selectedGenre = p['genre'];
        if (p['price_filter']) this.selectedPrice = p['price_filter'];
        this.fetchGames();
      })
    );
  }

  ngOnDestroy(): void { this.subs.unsubscribe(); }

  onSearchInput(val: string): void { this.searchSubject.next(val); }

  selectGenre(g: string): void {
    this.selectedGenre = this.selectedGenre === g ? '' : g;
    this.page = 0;
    this.fetchGames();
  }

  selectPlatform(p: string): void {
    this.selectedPlatform = this.selectedPlatform === p ? '' : p;
    this.page = 0;
    this.fetchGames();
  }

  selectPrice(val: string): void {
    this.selectedPrice = this.selectedPrice === val ? '' : val;
    this.page = 0;
    this.fetchGames();
  }

  onOrderChange(): void { this.page = 0; this.fetchGames(); }

  clearFilters(): void {
    this.selectedGenre = '';
    this.selectedPlatform = '';
    this.selectedPrice = '';
    this.search = '';
    this.orderBy = 'rating';
    this.page = 0;
    this.router.navigate([], { queryParams: {}, replaceUrl: true });
    this.fetchGames();
  }

  fetchGames(): void {
    this.loading = true;
    this.games = [];
    this.cdr.detectChanges();

    this.svc.getStoreGames({
      page: this.page,
      size: this.pageSize,
      genre: this.selectedGenre,
      platform: this.selectedPlatform,
      search: this.search,
      order_by: this.orderBy,
      price_filter: this.selectedPrice,
    }).subscribe({
      next: (res) => {
        this.games = res.games;
        this.totalCount = res.total;
        this.loading = false;
        if (this.search.trim().length >= 2) {
          this.community.logSearch(this.search.trim(), res.total || res.games.length);
        }
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  goPage(n: number): void {
    if (n < 1 || n > this.totalPages) return;
    this.page = n - 1;
    this.fetchGames();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  get hasActiveFilters(): boolean {
    return !!(this.selectedGenre || this.selectedPlatform || this.selectedPrice || this.search);
  }
}
