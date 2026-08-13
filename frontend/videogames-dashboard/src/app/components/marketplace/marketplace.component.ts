import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-marketplace',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatIconModule, CurrencyPipe],
  template: `
    <div class="page">
      <header>
        <a routerLink="/store">← Tienda</a>
        <h1><mat-icon>storefront</mat-icon> Community Market</h1>
        <p class="sub">Listings · inventario · fees (wallet sandbox)</p>
      </header>

      <p class="err" *ngIf="error">{{ error }}</p>
      <p class="ok" *ngIf="message">{{ message }}</p>

      <section class="card">
        <h2>Crear item (demo mint)</h2>
        <div class="row">
          <input [(ngModel)]="gameId" placeholder="game_id" />
          <input [(ngModel)]="itemName" placeholder="Nombre del item" />
          <button type="button" (click)="mint()" [disabled]="busy">Mint</button>
        </div>
      </section>

      <section class="card">
        <h2>Mi inventario</h2>
        <article *ngFor="let i of inventory" class="row">
          <div>
            <strong>{{ i.item_name }}</strong>
            <small>{{ i.item_id }} · {{ i.status }}</small>
          </div>
          <div class="actions" *ngIf="i.status === 'owned'">
            <input type="number" [(ngModel)]="listPrice[i.item_id]" min="0.5" step="0.5" placeholder="Precio" />
            <button type="button" (click)="list(i.item_id)" [disabled]="busy">Listar</button>
          </div>
        </article>
        <p class="empty" *ngIf="!inventory.length">Sin items.</p>
      </section>

      <section class="card">
        <h2>Listings activos</h2>
        <p class="hint">Fee plataforma {{ fees?.platform_fee_pct }}% + juego {{ fees?.game_fee_pct }}%</p>
        <article *ngFor="let l of listings" class="row">
          <div>
            <strong>{{ l.item_name }}</strong>
            <small>{{ l.price_usd | currency:'USD' }} · seller {{ l.seller_user_id }}</small>
          </div>
          <button type="button" (click)="buy(l.listing_id)" [disabled]="busy">Comprar</button>
        </article>
        <p class="empty" *ngIf="!listings.length">No hay listings.</p>
      </section>

      <section class="card">
        <h2>Historial</h2>
        <article *ngFor="let t of history" class="row">
          <div>
            <strong>{{ t.item_name }}</strong>
            <small>{{ t.status }} · gross {{ t.gross_amount | currency:'USD' }} · seller net {{ t.seller_net | currency:'USD' }}</small>
          </div>
        </article>
      </section>
    </div>
  `,
  styles: [`
    .page { max-width: 900px; margin: 0 auto; padding: 24px; color: #c7d5e0; }
    header a { color: #66c0f4; text-decoration: none; }
    h1 { display: flex; align-items: center; gap: 8px; color: #fff; }
    .sub, .hint, small { color: #8f98a0; font-size: 0.85rem; }
    .card { background: #1b2838; border-radius: 4px; padding: 16px; margin: 16px 0; }
    .row { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid #2a475e; flex-wrap: wrap; }
    input { background: #0e1621; border: 1px solid #2a475e; color: #fff; padding: 6px 8px; border-radius: 3px; }
    button { background: #66c0f4; border: none; padding: 6px 12px; border-radius: 3px; font-weight: 700; cursor: pointer; }
    button:disabled { opacity: 0.5; }
    .err { color: #ff9b9b; } .ok { color: #a4d007; } .empty { color: #6b7785; }
  `],
})
export class MarketplaceComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);

  listings: any[] = [];
  inventory: any[] = [];
  history: any[] = [];
  fees: any = null;
  gameId = 'demo-game';
  itemName = 'Skin Azul';
  listPrice: Record<string, number> = {};
  busy = false;
  error = '';
  message = '';

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    const h = this.headers();
    this.http.get<any>('/marketplace/fees', { headers: h }).subscribe({ next: f => { this.fees = f; this.cdr.detectChanges(); } });
    this.http.get<any>('/marketplace/listings', { headers: h }).subscribe({
      next: r => { this.listings = r.items || []; this.cdr.detectChanges(); },
      error: e => { this.error = e?.error?.detail || 'Error listings'; this.cdr.detectChanges(); },
    });
    this.http.get<any>('/marketplace/inventory', { headers: h }).subscribe({
      next: r => { this.inventory = r.items || []; this.cdr.detectChanges(); },
    });
    this.http.get<any>('/marketplace/history', { headers: h }).subscribe({
      next: r => { this.history = r.items || []; this.cdr.detectChanges(); },
    });
  }

  mint(): void {
    this.busy = true; this.error = ''; this.message = '';
    this.http.post('/marketplace/items', { game_id: this.gameId, item_name: this.itemName }, { headers: this.headers() }).subscribe({
      next: () => { this.busy = false; this.message = 'Item creado'; this.reload(); },
      error: e => { this.busy = false; this.error = e?.error?.detail || 'Error mint'; this.cdr.detectChanges(); },
    });
  }

  list(itemId: string): void {
    const price = this.listPrice[itemId] || 5;
    this.busy = true;
    this.http.post('/marketplace/listings', { item_id: itemId, price_usd: price }, { headers: this.headers() }).subscribe({
      next: () => { this.busy = false; this.message = 'Listing creado'; this.reload(); },
      error: e => { this.busy = false; this.error = e?.error?.detail || 'Error list'; this.cdr.detectChanges(); },
    });
  }

  buy(listingId: string): void {
    this.busy = true;
    const key = `buy_${listingId}_${Date.now()}`;
    this.http.post('/marketplace/buy', { listing_id: listingId, idempotency_key: key }, {
      headers: this.headers().set('Idempotency-Key', key),
    }).subscribe({
      next: () => { this.busy = false; this.message = 'Compra OK'; this.reload(); },
      error: e => { this.busy = false; this.error = e?.error?.detail || 'Error compra'; this.cdr.detectChanges(); },
    });
  }
}
