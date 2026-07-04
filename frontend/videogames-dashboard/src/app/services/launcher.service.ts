import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface LauncherLibraryItem {
  product_id: string;
  game_slug: string;
  game_name: string;
  game_image: string | null;
  amount: number;
  purchased_at: string;
  install_status: string;
  progress_pct: number;
  build_id: string;
  playtime_minutes: number;
  active_session_id: string | null;
}

export interface Achievement {
  achievement_id: string;
  product_id: string;
  name: string;
  description: string;
  icon_url: string;
  points: number;
  unlocked: boolean;
}

export interface GameLauncherDetail {
  build: {
    build_id: string;
    version: string;
    os: string;
    file_size_bytes: number;
    checksum: string;
  };
  install: {
    status: string;
    progress_pct: number;
    build_id: string;
  };
  playtime_minutes: number;
  active_session: { session_id: string } | null;
  achievements: Achievement[];
  achievements_unlocked: number;
  achievements_total: number;
}

@Injectable({ providedIn: 'root' })
export class LauncherService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  libraryStatus(): Observable<{ items: LauncherLibraryItem[] }> {
    return this.http.get<{ items: LauncherLibraryItem[] }>('/launcher/library-status', {
      headers: this.headers(),
    });
  }

  myAchievements(): Observable<{
    items: Array<{
      achievement_id: string;
      product_id: string;
      game_name: string;
      game_image: string | null;
      name: string;
      description: string;
      points: number;
      unlocked_at: string;
    }>;
    total: number;
  }> {
    return this.http.get<any>('/launcher/achievements/me', { headers: this.headers() });
  }

  gameDetail(productId: string, gameName = ''): Observable<GameLauncherDetail> {
    const q = gameName ? `?game_name=${encodeURIComponent(gameName)}` : '';
    return this.http.get<GameLauncherDetail>(`/launcher/game/${productId}${q}`, {
      headers: this.headers(),
    });
  }

  startInstall(productId: string, gameName = ''): Observable<{
    install: { status: string; progress_pct: number; build_id: string };
    build: { file_size_bytes: number; version: string };
    download_token: string;
    message: string;
  }> {
    const q = gameName ? `?game_name=${encodeURIComponent(gameName)}` : '';
    return this.http.post<any>(`/launcher/install/${productId}${q}`, {}, { headers: this.headers() });
  }

  updateProgress(productId: string, progressPct: number): Observable<{ install: { status: string; progress_pct: number } }> {
    return this.http.patch<any>(`/launcher/install/${productId}/progress`, {
      progress_pct: progressPct,
    }, { headers: this.headers() });
  }

  uninstall(productId: string): Observable<{ install: { status: string }; message: string }> {
    return this.http.post<any>(`/launcher/uninstall/${productId}`, {}, { headers: this.headers() });
  }

  playStart(productId: string, gameName = ''): Observable<{
    session: { session_id: string };
    unlocked_achievements: string[];
    message: string;
  }> {
    return this.http.post<any>('/launcher/play/start', {
      product_id: productId,
      game_name: gameName,
    }, { headers: this.headers() });
  }

  playEnd(sessionId: string, productId: string, durationSeconds: number): Observable<{
    duration_minutes: number;
    playtime_minutes: number;
    unlocked_achievements: string[];
    message: string;
  }> {
    return this.http.post<any>('/launcher/play/end', {
      session_id: sessionId,
      product_id: productId,
      duration_seconds: durationSeconds,
    }, { headers: this.headers() });
  }
}
