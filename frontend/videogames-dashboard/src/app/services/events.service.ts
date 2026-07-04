import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class EventsService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  track(eventType: string, productId?: string, metadata?: Record<string, unknown>): void {
    const token = this.auth.getToken();
    if (!token) return;
    this.http.post('/events', {
      event_type: eventType,
      product_id: productId || null,
      metadata: metadata || {},
    }, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    }).subscribe({ error: () => {} });
  }
}
