import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface PriceAlert {
  alert_id: string;
  user_id: string;
  product_id: string;
  game_slug: string;
  game_name: string;
  target_price: number;
  current_price?: number | null;
  triggered: boolean;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class AlertsService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  list(): Observable<PriceAlert[]> {
    return this.http.get<PriceAlert[]>('/alerts', { headers: this.headers() });
  }

  create(body: {
    product_id: string;
    game_slug: string;
    game_name: string;
    target_price: number;
  }): Observable<PriceAlert> {
    return this.http.post<PriceAlert>('/alerts', body, { headers: this.headers() });
  }

  remove(alertId: string): Observable<void> {
    return this.http.delete<void>(`/alerts/${alertId}`, { headers: this.headers() });
  }
}
