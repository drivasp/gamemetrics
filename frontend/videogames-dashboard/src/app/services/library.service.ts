import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface LibraryItem {
  purchase_id: string;
  product_id: string;
  game_slug: string;
  game_name: string;
  game_image: string | null;
  amount: number;
  purchased_at: string;
  refunded: boolean;
}

export interface CheckoutResult {
  order_id: string;
  payment_id: string;
  status: string;
  total: number;
  currency: string;
  message: string;
  purchases_count: number;
  checkout_url?: string | null;
  coupon_code?: string | null;
  coupon_discount?: number;
  payment_method?: string | null;
  wallet_balance?: number | null;
}

export interface CheckoutRequest {
  coupon_code?: string | null;
  payment_method?: 'auto' | 'wallet' | 'stripe' | 'sandbox';
}

@Injectable({ providedIn: 'root' })
export class LibraryService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  getLibrary(): Observable<LibraryItem[]> {
    return this.http.get<LibraryItem[]>('/library', { headers: this.headers() });
  }

  checkOwned(slug: string): Observable<{ owned: boolean }> {
    return this.http.get<{ owned: boolean }>(`/library/check/${slug}`, {
      headers: this.headers(),
    });
  }

  checkout(body: CheckoutRequest = {}): Observable<CheckoutResult> {
    return this.http.post<CheckoutResult>('/checkout', body, { headers: this.headers() });
  }

  validateCoupon(code: string, subtotal: number): Observable<{
    code: string;
    discount_type: string;
    discount_value: number;
    discount_applied: number;
    message: string;
  }> {
    return this.http.post<{
      code: string;
      discount_type: string;
      discount_value: number;
      discount_applied: number;
      message: string;
    }>('/coupons/validate', { code, subtotal }, { headers: this.headers() });
  }

  confirmPayment(sessionId: string): Observable<CheckoutResult> {
    return this.http.get<CheckoutResult>(`/checkout/confirm?session_id=${encodeURIComponent(sessionId)}`, {
      headers: this.headers(),
    });
  }

  requestRefund(purchaseId: string, reason?: string): Observable<{
    refund_id: string;
    status: string;
    amount: number;
    message: string;
  }> {
    return this.http.post<{
      refund_id: string;
      status: string;
      amount: number;
      message: string;
    }>(
      '/refunds',
      { purchase_id: purchaseId, reason: reason || 'Política de reembolso 14 días' },
      { headers: this.headers() }
    );
  }
}
