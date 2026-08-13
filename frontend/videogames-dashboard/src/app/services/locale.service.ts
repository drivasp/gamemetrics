import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { AuthService } from './auth.service';

export interface CountryLocale {
  country_code: string;
  name: string;
  pricing_region: string;
  currency: string;
  tax_rate_pct: number;
  tax_name: string;
  flag?: string;
}

export interface UserLocale extends CountryLocale {
  country_name?: string;
  message?: string;
  locked?: boolean;
  change_policy?: string;
}

@Injectable({ providedIn: 'root' })
export class LocaleService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private base = '/locale';
  private locale$ = new BehaviorSubject<UserLocale>({
    country_code: 'US',
    name: 'Estados Unidos',
    pricing_region: 'US',
    currency: 'USD',
    tax_rate_pct: 0,
    tax_name: 'Sales tax (digital exempt)',
    flag: '🇺🇸',
    locked: true,
  });
  private countries$ = new BehaviorSubject<CountryLocale[]>([]);

  readonly myLocale$ = this.locale$.asObservable();
  readonly countriesList$ = this.countries$.asObservable();

  private headers(): HttpHeaders {
    const t = this.auth.getToken();
    return t ? new HttpHeaders({ Authorization: `Bearer ${t}` }) : new HttpHeaders();
  }

  get countryCode(): string {
    return this.locale$.value.country_code || 'US';
  }

  get currency(): string {
    return this.locale$.value.currency || 'USD';
  }

  loadCountries(): void {
    this.http.get<{ items: CountryLocale[] }>(`${this.base}/countries`).subscribe({
      next: (res) => this.countries$.next(res.items || []),
      error: () => {},
    });
  }

  /** Solo lee el país de la cuenta. No hay cambio libre (anti-evasión). */
  refresh(): void {
    if (!this.auth.getToken()) {
      this.locale$.next({
        country_code: 'US',
        name: 'Estados Unidos',
        pricing_region: 'US',
        currency: 'USD',
        tax_rate_pct: 0,
        tax_name: 'Sales tax (digital exempt)',
        flag: '🇺🇸',
        locked: true,
      });
      return;
    }
    this.http.get<UserLocale>(`${this.base}/me`, { headers: this.headers() }).subscribe({
      next: (loc) => {
        this.locale$.next({
          ...loc,
          name: loc.country_name || loc.name || loc.country_code,
          locked: true,
        });
      },
      error: () => {},
    });
  }
}
