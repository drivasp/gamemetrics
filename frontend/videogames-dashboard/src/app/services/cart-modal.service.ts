import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface CartAddedItem {
  product_id: string;
  game_slug: string;
  game_name: string;
  game_image: string | null;
  unit_price: number;
  original_price?: number | null;
  discount_pct?: number;
}

@Injectable({ providedIn: 'root' })
export class CartModalService {
  private readonly _open = new BehaviorSubject<CartAddedItem | null>(null);
  readonly item$ = this._open.asObservable();

  show(item: CartAddedItem): void {
    this._open.next(item);
  }

  close(): void {
    this._open.next(null);
  }
}
