import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { AuthService } from './auth.service';

export interface Wallet {
  balance: number;
  currency: string;
}

export interface WalletTx {
  tx_id: string;
  amount: number;
  tx_type: string;
  reference_id: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class WalletService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private balance$ = new BehaviorSubject<number | null>(null);

  readonly walletBalance$ = this.balance$.asObservable();

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  getWallet(): Observable<Wallet> {
    return this.http.get<Wallet>('/wallet', { headers: this.headers() }).pipe(
      tap(w => this.balance$.next(w.balance)),
    );
  }

  getTransactions(): Observable<WalletTx[]> {
    return this.http.get<WalletTx[]>('/wallet/transactions', { headers: this.headers() });
  }

  topUp(amount: number): Observable<{ balance: number; tx_id: string; message: string }> {
    return this.http.post<{ balance: number; tx_id: string; message: string }>(
      '/wallet/topup',
      { amount },
      { headers: this.headers() },
    ).pipe(tap(r => this.balance$.next(r.balance)));
  }

  refresh(): void {
    if (this.auth.getToken()) {
      this.getWallet().subscribe({ error: () => this.balance$.next(null) });
    } else {
      this.balance$.next(null);
    }
  }
}
