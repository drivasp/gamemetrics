import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../services/auth.service';

interface AdminPartner {
  partner_id: string;
  company_name: string;
  contact_email: string;
  status: string;
  publisher_share_pct: number;
  platform_take_rate_pct: number;
  games_count: number;
  gross_revenue: number;
  platform_fee: number;
  publisher_net: number;
  sales: number;
  units_sold: number;
  refund_count: number;
}

interface AdminDashboard {
  ok: boolean;
  gmv: number;
  platform_revenue: number;
  publisher_payouts_owed: number;
  units_sold: number;
  refund_count: number;
  partners_count: number;
  partners_active: number;
  partners: AdminPartner[];
  recent_entries: Array<{
    entry_type: string;
    game_name: string;
    partner_id: string;
    gross_amount: number;
    platform_fee_amount: number;
    publisher_net_amount: number;
    created_at: number;
  }>;
  note: string;
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatIconModule, CurrencyPipe],
  template: `
    <div class="admin-page">
      <header>
        <a routerLink="/store">← Tienda</a>
        <h1>
          <mat-icon>admin_panel_settings</mat-icon>
          Admin GameMetrics
        </h1>
        <p class="sub">Economía B2B · GMV · payouts · publishers</p>
      </header>

      <div *ngIf="loading" class="state">Cargando dashboard...</div>
      <div *ngIf="!loading && error" class="state err">{{ error }}</div>

      <ng-container *ngIf="!loading && ok && dash">
        <section class="kpi-row">
          <div class="kpi">
            <span>GMV total</span>
            <strong>{{ dash.gmv | currency:'USD':'symbol':'1.2-2' }}</strong>
          </div>
          <div class="kpi highlight">
            <span>Ingresos GameMetrics</span>
            <strong>{{ dash.platform_revenue | currency:'USD':'symbol':'1.2-2' }}</strong>
            <small>Take rate acumulado</small>
          </div>
          <div class="kpi">
            <span>Adeudado publishers</span>
            <strong>{{ dash.publisher_payouts_owed | currency:'USD':'symbol':'1.2-2' }}</strong>
          </div>
          <div class="kpi">
            <span>Partners</span>
            <strong>{{ dash.partners_active }} / {{ dash.partners_count }}</strong>
          </div>
        </section>

        <section class="card">
          <h2>Claims de juegos (revisión)</h2>
          <p class="hint">Como Steamworks: el publisher solicita ownership; GameMetrics aprueba o rechaza. Solo los aprobados generan ingresos.</p>
          <article *ngFor="let c of claims" class="row claim-row">
            <div>
              <strong>{{ c.game_name }}</strong>
              <p>{{ c.company_name }} · {{ c.contact_email }}</p>
            </div>
            <div class="claim-actions">
              <button type="button" class="linkish" (click)="decideClaim(c.partner_game_id, true)" [disabled]="claimBusy">Aprobar</button>
              <button type="button" class="reject" (click)="decideClaim(c.partner_game_id, false)" [disabled]="claimBusy">Rechazar</button>
            </div>
          </article>
          <p class="empty" *ngIf="!claims.length">No hay claims pendientes.</p>
          <p class="ok" *ngIf="claimMsg">{{ claimMsg }}</p>
          <p class="err" *ngIf="claimErr">{{ claimErr }}</p>
        </section>

        <section class="card">
          <h2>Liquidar publisher (payout)</h2>
          <p class="hint">Como Steam: pagas el saldo disponible. Manual + referencia, o Stripe Connect.</p>
          <div class="payout-form">
            <select [(ngModel)]="payoutPartnerId">
              <option value="">Selecciona partner</option>
              <option *ngFor="let p of dash.partners" [value]="p.partner_id">
                {{ p.company_name }} ({{ p.partner_id }})
              </option>
            </select>
            <input type="number" step="0.01" [(ngModel)]="payoutAmount" placeholder="Monto USD">
            <input [(ngModel)]="payoutReference" placeholder="Referencia">
            <select [(ngModel)]="payoutMethod">
              <option value="manual">Manual</option>
              <option value="stripe_connect">Stripe Connect</option>
            </select>
            <button type="button" (click)="submitPayout()" [disabled]="payoutBusy">
              {{ payoutBusy ? 'Procesando…' : 'Marcar pagado' }}
            </button>
          </div>
          <p class="ok" *ngIf="payoutMsg">{{ payoutMsg }}</p>
          <p class="err" *ngIf="payoutErr">{{ payoutErr }}</p>
          <article *ngFor="let pay of payouts" class="row">
            <div>
              <strong>{{ pay.method }} · {{ pay.partner_id }}</strong>
              <p>{{ pay.reference }}</p>
            </div>
            <span class="net">{{ pay.amount | currency:'USD':'symbol':'1.2-2' }}</span>
          </article>
        </section>

        <section class="card">
          <h2>Publishers</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Compañía</th>
                  <th>Estado</th>
                  <th>Share</th>
                  <th>Take</th>
                  <th>GMV</th>
                  <th>Neto</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let p of dash.partners">
                  <td>
                    <strong>{{ p.company_name }}</strong>
                    <small>{{ p.contact_email }}</small>
                  </td>
                  <td>
                    <span class="badge" [class.active]="p.status === 'active'">{{ p.status }}</span>
                  </td>
                  <td>{{ p.publisher_share_pct }}%</td>
                  <td>{{ p.platform_take_rate_pct }}%</td>
                  <td>{{ p.gross_revenue | currency:'USD':'symbol':'1.2-2' }}</td>
                  <td class="net">{{ p.publisher_net | currency:'USD':'symbol':'1.2-2' }}</td>
                  <td><button type="button" class="linkish" (click)="prefillPayout(p)">Pagar</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <p class="hint">{{ dash.note }}</p>
      </ng-container>
    </div>
  `,
  styles: [`
    .admin-page { max-width: 1100px; margin: 0 auto; padding: 32px 20px 60px; color: #c7d5e0; min-height: 70vh; }
    header a { color: #66c0f4; text-decoration: none; font-size: 0.85rem; }
    h1 { display: flex; align-items: center; gap: 8px; color: #fff; font-size: 1.5rem; margin: 12px 0 4px; }
    .sub { color: #8f98a0; margin: 0 0 24px; }
    .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
    .kpi { background: #1b2838; border: 1px solid #2a475e; border-radius: 4px; padding: 16px; }
    .kpi span { display: block; color: #8f98a0; font-size: 0.72rem; text-transform: uppercase; }
    .kpi strong { display: block; color: #fff; font-size: 1.35rem; margin-top: 6px; }
    .kpi.highlight { border-color: #e94560; }
    .kpi.highlight strong { color: #ff9bb0; }
    .card { background: #1b2838; border: 1px solid #2a475e; border-radius: 4px; padding: 20px; margin-bottom: 16px; }
    h2 { color: #fff; font-size: 1rem; margin: 0 0 14px; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th { text-align: left; color: #8f98a0; padding: 8px 10px; border-bottom: 1px solid #2a475e; }
    td { padding: 10px; border-bottom: 1px solid rgba(42,71,94,0.5); }
    td strong { display: block; color: #fff; }
    td small { display: block; color: #6b7785; font-size: 0.72rem; }
    .net { color: #beee11; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; background: #3d2a2a; color: #ff9b9b; }
    .badge.active { background: #1a3d1a; color: #beee11; }
    .row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #2a475e; }
    .row p { margin: 4px 0 0; color: #8f98a0; font-size: 0.78rem; }
    .hint { color: #8f98a0; font-size: 0.85rem; }
    .state { padding: 40px 0; text-align: center; color: #8f98a0; }
    .err { color: #ff6b6b; } .ok { color: #beee11; }
    .payout-form { display: grid; grid-template-columns: 2fr 1fr 1.5fr 1fr auto; gap: 8px; margin-bottom: 12px; }
    .payout-form input, .payout-form select { background: #0f1a24; border: 1px solid #2a475e; color: #fff; padding: 8px; border-radius: 3px; }
    .payout-form button, .linkish { background: linear-gradient(90deg, #75b022, #588a1b); border: none; color: #fff; font-weight: 700; padding: 8px 12px; border-radius: 3px; cursor: pointer; }
    .linkish { padding: 4px 8px; font-size: 0.75rem; }
    .reject { background: #3d2a2a !important; color: #ff9b9b !important; border: none; font-weight: 700; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 0.75rem; margin-left: 6px; }
    .claim-actions { display: flex; align-items: center; }
    .empty { color: #8f98a0; font-size: 0.85rem; }
    @media (max-width: 900px) { .payout-form { grid-template-columns: 1fr; } }
  `],
})
export class AdminComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);

  loading = true;
  ok = false;
  error = '';
  dash: AdminDashboard | null = null;
  payouts: any[] = [];
  claims: any[] = [];
  claimBusy = false;
  claimMsg = '';
  claimErr = '';
  payoutPartnerId = '';
  payoutAmount: number | null = null;
  payoutReference = '';
  payoutMethod = 'manual';
  payoutBusy = false;
  payoutMsg = '';
  payoutErr = '';

  private headers() {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    const headers = this.headers();
    this.http.get<AdminDashboard>('/admin/dashboard', { headers }).subscribe({
      next: res => {
        this.ok = !!res.ok;
        this.dash = res;
        this.loading = false;
        this.http.get<{ items: any[] }>('/admin/payouts', { headers }).subscribe({
          next: p => { this.payouts = p.items || []; this.cdr.detectChanges(); },
          error: () => this.cdr.detectChanges(),
        });
        this.http.get<{ items: any[] }>('/admin/game-claims?status=pending', { headers }).subscribe({
          next: c => { this.claims = c.items || []; this.cdr.detectChanges(); },
          error: () => { this.claims = []; this.cdr.detectChanges(); },
        });
        this.cdr.detectChanges();
      },
      error: err => {
        this.error = err?.error?.detail || 'Acceso denegado';
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  decideClaim(partnerGameId: string, approve: boolean): void {
    this.claimBusy = true;
    this.claimErr = '';
    this.claimMsg = '';
    const path = approve ? 'approve' : 'reject';
    this.http.post(`/admin/game-claims/${partnerGameId}/${path}`, {}, { headers: this.headers() }).subscribe({
      next: (res: any) => {
        this.claimBusy = false;
        this.claimMsg = res.message || (approve ? 'Aprobado' : 'Rechazado');
        this.loadAll();
      },
      error: err => {
        this.claimBusy = false;
        this.claimErr = err?.error?.detail || 'No se pudo actualizar el claim';
        this.cdr.detectChanges();
      },
    });
  }

  prefillPayout(p: AdminPartner): void {
    this.payoutPartnerId = p.partner_id;
    this.payoutAmount = Math.round((p.publisher_net || 0) * 100) / 100;
    this.payoutReference = '';
    this.payoutMsg = '';
    this.payoutErr = '';
  }

  submitPayout(): void {
    if (!this.payoutPartnerId || !this.payoutAmount || this.payoutAmount <= 0) {
      this.payoutErr = 'Elige partner y monto válido';
      return;
    }
    this.payoutBusy = true;
    this.payoutErr = '';
    this.payoutMsg = '';
    this.http.post('/admin/payouts', {
      partner_id: this.payoutPartnerId,
      amount: this.payoutAmount,
      method: this.payoutMethod,
      reference: this.payoutReference,
      notes: 'Admin liquidación',
    }, { headers: this.headers() }).subscribe({
      next: (res: any) => {
        this.payoutBusy = false;
        this.payoutMsg = res.message || 'Payout registrado';
        this.payoutAmount = null;
        this.payoutReference = '';
        this.loadAll();
      },
      error: err => {
        this.payoutBusy = false;
        this.payoutErr = err?.error?.detail || 'No se pudo pagar';
        this.cdr.detectChanges();
      },
    });
  }
}
