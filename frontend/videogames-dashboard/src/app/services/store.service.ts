import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';
import { LocaleService } from './locale.service';

export interface StoreGame {
  id: string;
  product_id: string;
  slug: string;
  name: string;
  released: string;
  rating: number;
  metacritic: number;
  genres: string;
  platforms: string;
  developers: string;
  publishers: string;
  esrb_rating: string;
  price: number;
  original_price?: number | null;
  discount_pct?: number;
  is_free: boolean;
  background_image: string | null;
  trailer_url?: string | null;
  currency?: string;
  pricing_region?: string;
  country_code?: string | null;
}

export interface StoreGameDetail extends StoreGame {
  description: string | null;
  screenshots: string[];
  similar: StoreGame[];
}

export interface StorePage {
  games: StoreGame[];
  total: number;
  page: number;
  size: number;
}

export interface StoreFilters {
  genres: string[];
  platforms: string[];
}

export interface GenreCount {
  label: string;
  count: number;
}

export interface StoreQueryParams {
  page?: number;
  size?: number;
  semana?: number;
  genre?: string;
  platform?: string;
  search?: string;
  order_by?: string;
  price_filter?: string;
}

@Injectable({ providedIn: 'root' })
export class StoreService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private locale = inject(LocaleService);
  private base = '/store';

  private headers(): HttpHeaders {
    const t = this.auth.getToken();
    return t ? new HttpHeaders({ Authorization: `Bearer ${t}` }) : new HttpHeaders();
  }

  private withCountry(params?: HttpParams): HttpParams {
    let p = params || new HttpParams();
    return p.set('country', this.locale.countryCode);
  }

  getStoreGames(params: StoreQueryParams = {}): Observable<StorePage> {
    let p = new HttpParams();
    if (params.page !== undefined) p = p.set('page', params.page);
    if (params.size !== undefined) p = p.set('size', params.size);
    if (params.semana !== undefined) p = p.set('semana', params.semana);
    if (params.genre) p = p.set('genre', params.genre);
    if (params.platform) p = p.set('platform', params.platform);
    if (params.search) p = p.set('search', params.search);
    if (params.order_by) p = p.set('order_by', params.order_by);
    if (params.price_filter) p = p.set('price_filter', params.price_filter);
    return this.http.get<StorePage>(`${this.base}/games`, {
      params: this.withCountry(p),
      headers: this.headers(),
    });
  }

  getGameDetail(slug: string): Observable<StoreGameDetail> {
    return this.http.get<StoreGameDetail>(`${this.base}/games/${slug}`, {
      params: this.withCountry(),
      headers: this.headers(),
    });
  }

  getFilters(semana = 17): Observable<StoreFilters> {
    return this.http.get<StoreFilters>(`${this.base}/filters?semana=${semana}`);
  }

  getFeatured(semana = 17): Observable<StoreGame[]> {
    return this.http.get<StoreGame[]>(`${this.base}/featured`, {
      params: this.withCountry(new HttpParams().set('semana', semana)),
      headers: this.headers(),
    });
  }

  getNewReleases(semana = 17): Observable<StoreGame[]> {
    return this.http.get<StoreGame[]>(`${this.base}/new-releases`, {
      params: this.withCountry(new HttpParams().set('semana', semana)),
      headers: this.headers(),
    });
  }

  getPopular(semana = 17): Observable<StoreGame[]> {
    return this.http.get<StoreGame[]>(`${this.base}/popular`, {
      params: this.withCountry(new HttpParams().set('semana', semana)),
      headers: this.headers(),
    });
  }

  getFreeGames(semana = 17): Observable<StoreGame[]> {
    return this.http.get<StoreGame[]>(`${this.base}/free-games`, {
      params: this.withCountry(new HttpParams().set('semana', semana)),
      headers: this.headers(),
    });
  }

  getGenres(semana = 17): Observable<GenreCount[]> {
    return this.http.get<GenreCount[]>(`${this.base}/genres?semana=${semana}`);
  }
}
