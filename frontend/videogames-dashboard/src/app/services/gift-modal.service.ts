import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface GiftSentInfo {
  gift_id: string;
  game_name: string;
  game_image: string | null;
  recipient_email: string;
  message: string;
  amount: number;
}

@Injectable({ providedIn: 'root' })
export class GiftModalService {
  private readonly _open = new BehaviorSubject<GiftSentInfo | null>(null);
  readonly gift$ = this._open.asObservable();

  show(gift: GiftSentInfo): void {
    this._open.next(gift);
  }

  close(): void {
    this._open.next(null);
  }
}
