import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, Subject, tap } from 'rxjs';
import { AuthService } from './auth.service';

export interface CartItem {
  id: string;
  product_id: string;
  game_slug: string;
  game_name: string;
  game_image: string | null;
  unit_price: number;
  quantity: number;
  line_total: number;
}

export interface Cart {
  items: CartItem[];
  subtotal: number;
  discount_total: number;
  total: number;
  item_count: number;
}

@Injectable({ providedIn: 'root' })
export class CartService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private base = '/cart';
  private changed = new Subject<void>();

  readonly cartChanged$ = this.changed.asObservable();

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  notifyChanged(): void {
    this.changed.next();
  }

  getCart(): Observable<Cart> {
    return this.http.get<Cart>(this.base, { headers: this.headers() });
  }

  addItem(item: {
    product_id: string;
    game_slug: string;
    game_name: string;
    game_image?: string | null;
    unit_price: number;
    quantity?: number;
  }): Observable<CartItem> {
    return this.http.post<CartItem>(`${this.base}/items`, item, { headers: this.headers() }).pipe(
      tap(() => this.notifyChanged()),
    );
  }

  removeItem(productId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/items/${productId}`, { headers: this.headers() }).pipe(
      tap(() => this.notifyChanged()),
    );
  }

  clearCart(): Observable<void> {
    return this.http.delete<void>(this.base, { headers: this.headers() }).pipe(
      tap(() => this.notifyChanged()),
    );
  }

  checkInCart(productId: string): Observable<{ in_cart: boolean }> {
    return this.http.get<{ in_cart: boolean }>(`${this.base}/check/${productId}`, {
      headers: this.headers(),
    });
  }
}
