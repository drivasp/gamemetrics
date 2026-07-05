import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { timeout, catchError, of } from 'rxjs';
import { GiftsService, Gift } from '../../services/gifts.service';

import { GameCoverComponent } from '../../shared/game-cover/game-cover.component';

@Component({
  selector: 'app-gifts',
  standalone: true,
  imports: [CommonModule, RouterLink, MatIconModule, GameCoverComponent],
  templateUrl: './gifts.component.html',
  styleUrl: './gifts.component.scss',
})
export class GiftsComponent implements OnInit {
  private giftsSvc = inject(GiftsService);
  private cdr = inject(ChangeDetectorRef);

  tab: 'inbox' | 'sent' = 'inbox';
  inbox: Gift[] = [];
  sent: Gift[] = [];
  loading = true;
  message = '';
  error = '';
  pendingCount = 0;

  ngOnInit(): void {
    this.giftsSvc.pendingCount$.subscribe(n => {
      this.pendingCount = n;
      this.cdr.detectChanges();
    });
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.message = '';
    this.error = '';
    this.giftsSvc.inbox().pipe(
      timeout(10000),
      catchError(() => of([] as Gift[])),
    ).subscribe({
      next: g => {
        this.inbox = g;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
    this.giftsSvc.sent().pipe(
      timeout(10000),
      catchError(() => of([] as Gift[])),
    ).subscribe({
      next: g => { this.sent = g; this.cdr.detectChanges(); },
    });
  }

  accept(g: Gift): void {
    this.giftsSvc.accept(g.gift_id).subscribe({
      next: () => {
        this.message = `"${g.game_name}" se añadió a tu biblioteca.`;
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo aceptar';
        this.cdr.detectChanges();
      },
    });
  }

  decline(g: Gift): void {
    this.giftsSvc.decline(g.gift_id).subscribe({
      next: () => {
        this.message = 'Regalo rechazado. El saldo se devolvió al remitente.';
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo rechazar';
        this.cdr.detectChanges();
      },
    });
  }

  statusLabel(s: string): string {
    const m: Record<string, string> = {
      pending: 'Pendiente',
      accepted: 'Aceptado',
      declined: 'Rechazado',
    };
    return m[s] || s;
  }
}
