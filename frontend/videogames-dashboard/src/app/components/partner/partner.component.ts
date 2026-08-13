import { Component, OnInit, OnDestroy, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { Subject, timeout, catchError, of, debounceTime, distinctUntilChanged, switchMap, takeUntil } from 'rxjs';
import { SocialService } from '../../services/social.service';
import { CommunityService } from '../../services/community.service';
import { AuthService } from '../../services/auth.service';
import { StoreService, StoreGame } from '../../services/store.service';

@Component({
  selector: 'app-partner',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatIconModule, CurrencyPipe, DatePipe],
  templateUrl: './partner.component.html',
  styleUrl: './partner.component.scss',
})
export class PartnerComponent implements OnInit, OnDestroy {
  private social = inject(SocialService);
  private community = inject(CommunityService);
  private auth = inject(AuthService);
  private store = inject(StoreService);
  private cdr = inject(ChangeDetectorRef);
  private destroy$ = new Subject<void>();
  private search$ = new Subject<string>();

  partner: any = null;
  games: any[] = [];
  revenue: any[] = [];
  earnings: any = null;
  ledger: any[] = [];
  financialStatement: any = null;
  payouts: any[] = [];
  subscription: any = null;
  plans: any[] = [];
  branding: any = null;
  connect: any = null;
  featuredPlacements: any[] = [];
  brandName = '';
  brandColor = '#e94560';
  brandTagline = '';
  apiKeys: any[] = [];
  newApiKey = '';
  loading = true;
  company = '';
  catalogSearch = '';
  catalogResults: StoreGame[] = [];
  catalogLoading = false;
  selectedCatalog: StoreGame | null = null;
  claimBusy = false;
  message = '';
  error = '';
  uploadVersion: Record<string, string> = {};
  uploadBusy: Record<string, boolean> = {};
  buildsByProduct: Record<string, any[]> = {};

  ngOnInit(): void {
    this.search$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap((q) => {
        const term = q.trim();
        if (term.length < 2) {
          this.catalogResults = [];
          this.catalogLoading = false;
          this.cdr.detectChanges();
          return of(null);
        }
        this.catalogLoading = true;
        this.cdr.detectChanges();
        return this.store.getStoreGames({
          search: term,
          size: 12,
          page: 0,
          price_filter: 'paid',
          order_by: 'rating',
        }).pipe(catchError(() => of({ games: [], total: 0, page: 0, size: 12 })));
      }),
      takeUntil(this.destroy$),
    ).subscribe((page) => {
      if (!page) return;
      this.catalogResults = (page.games || []).filter((g) => Number(g.price) > 0);
      this.catalogLoading = false;
      this.cdr.detectChanges();
    });
    this.reload();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onCatalogSearch(term: string): void {
    this.search$.next(term || '');
  }

  selectCatalogGame(game: StoreGame): void {
    this.selectedCatalog = game;
    this.error = '';
    this.message = '';
  }

  claimSelectedGame(): void {
    if (!this.selectedCatalog || this.claimBusy) return;
    const game = this.selectedCatalog;
    this.claimBusy = true;
    this.error = '';
    this.social.addPartnerGame(game.product_id, game.name).subscribe({
      next: (res) => {
        this.claimBusy = false;
        this.message = res.message || `"${game.name}" reclamado para tu estudio`;
        this.selectedCatalog = null;
        this.catalogSearch = '';
        this.catalogResults = [];
        this.reload();
      },
      error: (err) => {
        this.claimBusy = false;
        this.error = err?.error?.detail || 'No se pudo reclamar el juego';
        this.cdr.detectChanges();
      },
    });
  }

  reload(): void {
    this.loading = true;
    this.social.getPartner().pipe(
      timeout(10000),
      catchError(() => of({ partner: null, games: [], revenue: [], earnings: null, ledger: [] })),
    ).subscribe({
      next: res => {
        this.partner = res.partner;
        this.games = res.games || [];
        this.revenue = res.revenue || [];
        this.earnings = res.earnings || null;
        this.ledger = res.ledger || [];
        this.financialStatement = res.financial_statement || null;
        this.payouts = res.payouts || [];
        this.subscription = res.subscription || null;
        this.plans = res.plans || [];
        this.branding = res.branding || null;
        this.connect = res.connect || null;
        this.featuredPlacements = res.featured_placements || [];
        if (this.branding) {
          this.brandName = this.branding.store_name || '';
          this.brandColor = this.branding.accent_color || '#e94560';
          this.brandTagline = this.branding.tagline || '';
        }
        this.loading = false;
        if (res.partner) {
          this.loadKeys();
          for (const g of this.games) {
            this.uploadVersion[g.product_id] = this.uploadVersion[g.product_id] || '1.0.1';
            this.loadBuilds(g.product_id);
          }
        }
        this.cdr.detectChanges();
      },
    });
  }

  loadBuilds(productId: string): void {
    this.social.listPartnerBuilds(productId).pipe(
      catchError(() => of({ items: [] })),
    ).subscribe({
      next: res => {
        this.buildsByProduct[productId] = res.items || [];
        this.cdr.detectChanges();
      },
    });
  }

  onBuildSelected(productId: string, event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const version = (this.uploadVersion[productId] || '1.0.1').trim() || '1.0.1';
    this.uploadBusy[productId] = true;
    this.error = '';
    this.social.uploadPartnerBuild(productId, version, file).subscribe({
      next: res => {
        this.uploadBusy[productId] = false;
        this.message = res.message || 'Build publicado';
        this.loadBuilds(productId);
        input.value = '';
        // bump suggested next version lightly
        const parts = version.split('.').map(n => parseInt(n, 10) || 0);
        while (parts.length < 3) parts.push(0);
        parts[2] += 1;
        this.uploadVersion[productId] = parts.join('.');
        this.cdr.detectChanges();
      },
      error: err => {
        this.uploadBusy[productId] = false;
        this.error = err?.error?.detail || 'No se pudo subir el build';
        this.cdr.detectChanges();
      },
    });
  }

  loadKeys(): void {
    this.community.listApiKeys().subscribe({
      next: res => { this.apiKeys = res.items || []; this.cdr.detectChanges(); },
      error: () => { this.apiKeys = []; },
    });
  }

  createKey(): void {
    this.community.createApiKey().subscribe({
      next: res => {
        this.newApiKey = res.api_key;
        this.message = res.message;
        this.loadKeys();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo crear la clave';
        this.cdr.detectChanges();
      },
    });
  }

  revokeKey(id: string): void {
    this.community.revokeApiKey(id).subscribe({
      next: () => this.loadKeys(),
    });
  }

  register(): void {
    if (!this.company.trim()) return;
    this.social.registerPartner(this.company.trim()).subscribe({
      next: res => {
        this.message = res.message;
        this.auth.getProfile().subscribe({ error: () => undefined });
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo registrar';
        this.cdr.detectChanges();
      },
    });
  }

  totalRevenue(): number {
    if (this.earnings?.gross_revenue != null) {
      return Number(this.earnings.gross_revenue) || 0;
    }
    return this.revenue.reduce((s, r) => s + (r.gross_revenue || 0), 0);
  }

  publisherNet(): number {
    return Number(this.earnings?.publisher_net ?? this.partner?.publisher_net ?? 0) || 0;
  }

  balanceAvailable(): number {
    return Number(this.earnings?.balance_available ?? this.partner?.balance_available ?? 0) || 0;
  }

  platformFee(): number {
    return Number(this.earnings?.platform_fee ?? this.partner?.platform_fee ?? 0) || 0;
  }

  balancePending(): number {
    return Number(this.earnings?.balance_pending ?? 0) || 0;
  }

  balancePaid(): number {
    return Number(this.earnings?.balance_paid_out ?? 0) || 0;
  }

  subscribe(planId: string): void {
    this.social.subscribeSaas(planId).subscribe({
      next: res => {
        if (res.checkout_url) {
          window.location.href = res.checkout_url;
          return;
        }
        this.message = `Plan ${planId} activado`;
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo activar el plan';
        this.cdr.detectChanges();
      },
    });
  }

  saveBrand(): void {
    if (!this.brandName.trim()) return;
    this.social.saveBranding({
      store_name: this.brandName.trim(),
      accent_color: this.brandColor,
      tagline: this.brandTagline,
    }).subscribe({
      next: () => {
        this.message = 'Branding white-label guardado';
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'Requiere plan Pro/Studio';
        this.cdr.detectChanges();
      },
    });
  }

  buyFeatured(g: { product_id: string; game_name: string }): void {
    this.social.buyFeatured(g.product_id, g.game_name).subscribe({
      next: res => {
        if (res.checkout_url) {
          window.location.href = res.checkout_url;
          return;
        }
        this.message = `Featured activo (${res.price_usd} USD)`;
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo comprar featured';
        this.cdr.detectChanges();
      },
    });
  }

  startConnect(): void {
    this.social.connectOnboard().subscribe({
      next: res => {
        if (res.url) window.location.href = res.url;
        else this.message = 'Connect listo';
      },
      error: err => {
        this.error = err?.error?.detail || 'Stripe Connect no configurado — usa payouts manuales';
        this.cdr.detectChanges();
      },
    });
  }
}
