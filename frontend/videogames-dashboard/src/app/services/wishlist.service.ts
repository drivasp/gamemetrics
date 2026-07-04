import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface WishlistItem {
  id: string;
  game_slug: string;
  game_name: string;
  game_image: string | null;
  game_price: number;
  added_at: string | null;
}

@Injectable({ providedIn: 'root' })
export class WishlistService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private base = '/user';

  private _headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  getWishlist(): Observable<WishlistItem[]> {
    return this.http.get<WishlistItem[]>(`${this.base}/wishlist`, {
      headers: this._headers(),
    });
  }

  addToWishlist(game: {
    game_slug: string;
    game_name: string;
    game_image?: string | null;
    game_price: number;
  }): Observable<WishlistItem> {
    return this.http.post<WishlistItem>(`${this.base}/wishlist`, game, {
      headers: this._headers(),
    });
  }

  removeFromWishlist(slug: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/wishlist/${slug}`, {
      headers: this._headers(),
    });
  }

  checkWishlist(slug: string): Observable<{ in_wishlist: boolean }> {
    return this.http.get<{ in_wishlist: boolean }>(
      `${this.base}/wishlist/check/${slug}`,
      { headers: this._headers() }
    );
  }
}
