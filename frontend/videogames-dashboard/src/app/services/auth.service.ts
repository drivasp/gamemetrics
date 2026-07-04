import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  avatar: string | null;
  bio: string | null;
}

export interface AuthResponse {
  token: string;
  user: User;
}

const TOKEN_KEY = 'gamemetrics_token';
const USER_KEY = 'gamemetrics_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private base = '/auth';

  private _currentUser$ = new BehaviorSubject<User | null>(this._loadUser());
  readonly currentUser$ = this._currentUser$.asObservable();

  private _loadUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  private _save(res: AuthResponse): void {
    localStorage.setItem(TOKEN_KEY, res.token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    this._currentUser$.next(res.user);
  }

  register(email: string, password: string, displayName: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.base}/register`, {
      email,
      password,
      display_name: displayName,
    }).pipe(tap(res => this._save(res)));
  }

  login(email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.base}/login`, {
      email,
      password,
    }).pipe(tap(res => this._save(res)));
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    this._currentUser$.next(null);
  }

  getProfile(): Observable<User> {
    return this.http.get<User>(`${this.base}/profile`, {
      headers: this._authHeaders(),
    }).pipe(tap(user => {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      this._currentUser$.next(user);
    }));
  }

  updateProfile(data: { display_name?: string; bio?: string }): Observable<User> {
    return this.http.put<User>(`${this.base}/profile`, data, {
      headers: this._authHeaders(),
    }).pipe(tap(user => {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      this._currentUser$.next(user);
    }));
  }

  uploadAvatar(file: File): Observable<User> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<User>(`${this.base}/avatar`, form, {
      headers: new HttpHeaders({ Authorization: `Bearer ${this.getToken()}` }),
    }).pipe(tap(user => {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      this._currentUser$.next(user);
    }));
  }

  isLoggedIn(): boolean {
    return !!this.getToken() && !!this._currentUser$.value;
  }

  getCurrentUser(): User | null {
    return this._currentUser$.value;
  }

  getToken(): string {
    return localStorage.getItem(TOKEN_KEY) ?? '';
  }

  private _authHeaders(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.getToken()}` });
  }
}
