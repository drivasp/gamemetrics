import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { timeout, catchError, of } from 'rxjs';
import { SocialService } from '../../services/social.service';
import { CommunityService } from '../../services/community.service';

@Component({
  selector: 'app-partner',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatIconModule],
  templateUrl: './partner.component.html',
  styleUrl: './partner.component.scss',
})
export class PartnerComponent implements OnInit {
  private social = inject(SocialService);
  private community = inject(CommunityService);
  private cdr = inject(ChangeDetectorRef);

  partner: any = null;
  games: any[] = [];
  revenue: any[] = [];
  apiKeys: any[] = [];
  newApiKey = '';
  loading = true;
  company = '';
  gameName = '';
  productId = '';
  message = '';
  error = '';

  ngOnInit(): void { this.reload(); }

  reload(): void {
    this.loading = true;
    this.social.getPartner().pipe(
      timeout(10000),
      catchError(() => of({ partner: null, games: [], revenue: [] })),
    ).subscribe({
      next: res => {
        this.partner = res.partner;
        this.games = res.games || [];
        this.revenue = res.revenue || [];
        this.loading = false;
        if (res.partner) this.loadKeys();
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
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo registrar';
        this.cdr.detectChanges();
      },
    });
  }

  addGame(): void {
    if (!this.productId.trim() || !this.gameName.trim()) return;
    this.social.addPartnerGame(this.productId.trim(), this.gameName.trim()).subscribe({
      next: res => {
        this.message = res.message;
        this.productId = '';
        this.gameName = '';
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo añadir';
        this.cdr.detectChanges();
      },
    });
  }

  totalRevenue(): number {
    return this.revenue.reduce((s, r) => s + (r.gross_revenue || 0), 0);
  }
}
