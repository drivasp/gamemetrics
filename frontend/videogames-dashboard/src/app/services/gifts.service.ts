import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { AuthService } from './auth.service';

export interface Gift {
  gift_id: string;
  sender_id: string;
  recipient_id: string;
  recipient_email: string;
  product_id: string;
  game_slug: string;
  game_name: string;
  game_image: string | null;
  purchase_id: string;
  message: string;
  status: string;
  amount: number;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class GiftsService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private pending$ = new BehaviorSubject<number>(0);
  readonly pendingCount$ = this.pending$.asObservable();

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  send(body: {
    product_id: string;
    game_slug: string;
    game_name: string;
    game_image?: string | null;
    recipient_email: string;
    message?: string;
    payment_method?: string;
  }): Observable<Gift> {
    return this.http.post<Gift>('/gifts', body, { headers: this.headers() });
  }

  inbox(): Observable<Gift[]> {
    return this.http.get<Gift[]>('/gifts/inbox', { headers: this.headers() }).pipe(
      tap(list => this.pending$.next(list.filter(g => g.status === 'pending').length)),
    );
  }

  sent(): Observable<Gift[]> {
    return this.http.get<Gift[]>('/gifts/sent', { headers: this.headers() });
  }

  accept(giftId: string): Observable<Gift> {
    return this.http.post<Gift>(`/gifts/${giftId}/accept`, {}, { headers: this.headers() }).pipe(
      tap(() => this.refreshPending()),
    );
  }

  decline(giftId: string): Observable<Gift> {
    return this.http.post<Gift>(`/gifts/${giftId}/decline`, {}, { headers: this.headers() }).pipe(
      tap(() => this.refreshPending()),
    );
  }

  refreshPending(): void {
    if (!this.auth.getToken()) {
      this.pending$.next(0);
      return;
    }
    this.inbox().subscribe({ error: () => this.pending$.next(0) });
  }

  clearPending(): void {
    this.pending$.next(0);
  }
}
