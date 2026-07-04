import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { WalletService, WalletTx } from '../../services/wallet.service';

@Component({
  selector: 'app-wallet',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './wallet.component.html',
  styleUrl: './wallet.component.scss',
})
export class WalletComponent implements OnInit {
  private walletSvc = inject(WalletService);
  private cdr = inject(ChangeDetectorRef);

  balance = 0;
  txs: WalletTx[] = [];
  loading = true;
  amount = 20;
  topping = false;
  message = '';
  error = '';

  presets = [5, 10, 20, 50, 100];

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.walletSvc.getWallet().subscribe({
      next: w => {
        this.balance = w.balance;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
    this.loadHistory();
  }

  loadHistory(): void {
    this.walletSvc.getTransactions().subscribe({
      next: t => { this.txs = t; this.cdr.detectChanges(); },
      error: () => { this.txs = []; this.cdr.detectChanges(); },
    });
  }

  topUp(): void {
    if (this.amount < 1) return;
    this.topping = true;
    this.error = '';
    this.message = '';
    this.walletSvc.topUp(this.amount).subscribe({
      next: res => {
        // Usar el saldo que devolvió el backend (no releer Pinot al instante:
        // Kafka→Pinot puede tardar unos segundos y sobrescribiría con $0).
        this.balance = res.balance;
        this.message = res.message;
        this.topping = false;
        this.cdr.detectChanges();
        // Historial con reintentos suaves
        this.pollHistory(0);
      },
      error: err => {
        this.topping = false;
        this.error = err?.error?.detail || 'No se pudo recargar';
        this.cdr.detectChanges();
      },
    });
  }

  private pollHistory(attempt: number): void {
    this.walletSvc.getTransactions().subscribe({
      next: t => {
        this.txs = t;
        this.cdr.detectChanges();
        if (t.length === 0 && attempt < 5) {
          setTimeout(() => this.pollHistory(attempt + 1), 1500);
        }
      },
    });
    // También reintentar saldo desde Pinot sin bajar el valor mostrado
    this.walletSvc.getWallet().subscribe({
      next: w => {
        if (w.balance > this.balance) {
          this.balance = w.balance;
          this.cdr.detectChanges();
        } else if (w.balance === this.balance) {
          // ok, Pinot ya alcanzó
        }
        // si Pinot aún tiene menos, mantener el saldo optimista de la recarga
      },
    });
  }

  txLabel(t: WalletTx): string {
    const map: Record<string, string> = {
      topup: 'Recarga',
      purchase: 'Compra',
      refund: 'Reembolso',
      credit: 'Crédito',
      debit: 'Débito',
    };
    return map[t.tx_type] || t.tx_type;
  }

  isCredit(t: WalletTx): boolean {
    return ['topup', 'refund', 'credit'].includes(t.tx_type);
  }
}
