import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class SocialService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private unread$ = new BehaviorSubject<number>(0);
  readonly unreadCount$ = this.unread$.asObservable();

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  // Friends
  getFriends(): Observable<any> {
    return this.http.get('/friends', { headers: this.headers() });
  }

  requestFriend(email: string): Observable<any> {
    return this.http.post('/friends/request', { email }, { headers: this.headers() });
  }

  acceptFriend(id: string): Observable<any> {
    return this.http.post(`/friends/${id}/accept`, {}, { headers: this.headers() });
  }

  declineFriend(id: string): Observable<any> {
    return this.http.post(`/friends/${id}/decline`, {}, { headers: this.headers() });
  }

  activity(): Observable<any> {
    return this.http.get('/friends/activity', { headers: this.headers() });
  }

  // Notifications
  getNotifications(): Observable<{ items: any[]; unread: number }> {
    return this.http.get<{ items: any[]; unread: number }>('/notifications', {
      headers: this.headers(),
    }).pipe(tap(r => this.unread$.next(r.unread || 0)));
  }

  refreshUnread(): void {
    if (!this.auth.getToken()) {
      this.unread$.next(0);
      return;
    }
    this.getNotifications().subscribe({ error: () => this.unread$.next(0) });
  }

  clearUnread(): void {
    this.unread$.next(0);
  }

  markRead(id: string): Observable<any> {
    return this.http.post(`/notifications/${id}/read`, {}, { headers: this.headers() });
  }

  markAllRead(): Observable<any> {
    return this.http.post('/notifications/read-all', {}, { headers: this.headers() }).pipe(
      tap(() => this.unread$.next(0)),
    );
  }

  // Support
  getTickets(): Observable<any> {
    return this.http.get('/support/tickets', { headers: this.headers() });
  }

  createTicket(subject: string, body: string, priority = 'normal'): Observable<any> {
    return this.http.post('/support/tickets', { subject, body, priority }, { headers: this.headers() });
  }

  closeTicket(id: string): Observable<any> {
    return this.http.post(`/support/tickets/${id}/close`, {}, { headers: this.headers() });
  }

  // Partners
  getPartner(): Observable<any> {
    return this.http.get('/partners/me', { headers: this.headers() });
  }

  registerPartner(company_name: string): Observable<any> {
    return this.http.post('/partners/register', { company_name }, { headers: this.headers() });
  }

  addPartnerGame(product_id: string, game_name: string): Observable<any> {
    return this.http.post('/partners/games', { product_id, game_name }, { headers: this.headers() });
  }

  listPartnerBuilds(productId: string): Observable<{ items: any[] }> {
    return this.http.get<{ items: any[] }>(`/partners/games/${productId}/builds`, {
      headers: this.headers(),
    });
  }

  uploadPartnerBuild(productId: string, version: string, file: File): Observable<any> {
    const form = new FormData();
    form.append('version', version);
    form.append('file', file);
    return this.http.post(`/partners/games/${productId}/builds`, form, {
      headers: this.headers(),
    });
  }

  connectOnboard(): Observable<any> {
    return this.http.post('/partners/connect/onboard', {}, { headers: this.headers() });
  }

  subscribeSaas(plan_id: string): Observable<any> {
    return this.http.post('/partners/saas/subscribe', { plan_id, pay_method: 'sandbox' }, { headers: this.headers() });
  }

  saveBranding(body: { store_name: string; logo_url?: string; accent_color?: string; tagline?: string }): Observable<any> {
    return this.http.put('/partners/branding', body, { headers: this.headers() });
  }

  buyFeatured(product_id: string, game_name: string): Observable<any> {
    return this.http.post(
      '/partners/featured/buy',
      { product_id, game_name, pay_method: 'sandbox' },
      { headers: this.headers() },
    );
  }

  heartbeat(status = 'online', detail = ''): Observable<any> {
    return this.http.post('/friends/presence', { status, detail }, { headers: this.headers() });
  }
}
