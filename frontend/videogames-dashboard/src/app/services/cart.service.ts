import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, Subject, tap } from 'rxjs';
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
  private count$ = new BehaviorSubject<number>(0);

  readonly cartChanged$ = this.changed.asObservable();
  readonly cartCount$ = this.count$.asObservable();

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  getCartCount(): number {
    return this.count$.value;
  }

  resetCount(): void {
    this.count$.next(0);
  }

  notifyChanged(): void {
    this.changed.next();
  }

  refreshCount(): void {
    this.getCart().subscribe({
      next: (c) => this.count$.next(c.item_count),
      error: () => {},
    });
  }

  getCart(): Observable<Cart> {
    return this.http.get<Cart>(this.base, { headers: this.headers() }).pipe(
      tap((c) => this.count$.next(c.item_count)),
    );
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
      tap(() => {
        this.count$.next(this.count$.value + 1);
        this.notifyChanged();
      }),
    );
  }

  removeItem(productId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/items/${productId}`, { headers: this.headers() }).pipe(
      tap(() => {
        this.count$.next(Math.max(0, this.count$.value - 1));
        this.notifyChanged();
      }),
    );
  }

  clearCart(): Observable<void> {
    return this.http.delete<void>(this.base, { headers: this.headers() }).pipe(
      tap(() => {
        this.count$.next(0);
        this.notifyChanged();
      }),
    );
  }

  checkInCart(productId: string): Observable<{ in_cart: boolean }> {
    return this.http.get<{ in_cart: boolean }>(`${this.base}/check/${productId}`, {
      headers: this.headers(),
    });
  }
}
