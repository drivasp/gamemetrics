import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface AchievementPopupData {
  title: string;
  achievements: string[];
  gameName?: string;
  kind: 'unlock' | 'info' | 'success';
}

@Injectable({ providedIn: 'root' })
export class AchievementPopupService {
  private readonly _data = new BehaviorSubject<AchievementPopupData | null>(null);
  readonly data$ = this._data.asObservable();

  showUnlock(achievements: string[], gameName?: string): void {
    if (!achievements?.length) return;
    this._data.next({
      title: achievements.length === 1 ? '¡Logro desbloqueado!' : '¡Logros desbloqueados!',
      achievements,
      gameName,
      kind: 'unlock',
    });
  }

  showSuccess(title: string, detail?: string): void {
    this._data.next({
      title,
      achievements: detail ? [detail] : [],
      kind: 'success',
    });
  }

  showInfo(title: string, detail?: string): void {
    this._data.next({
      title,
      achievements: detail ? [detail] : [],
      kind: 'info',
    });
  }

  close(): void {
    this._data.next(null);
  }
}
