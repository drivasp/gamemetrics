import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ModalService {
  private _open$ = new BehaviorSubject<boolean>(false);
  readonly authModalOpen$ = this._open$.asObservable();

  openAuthModal(): void {
    this._open$.next(true);
  }

  closeAuthModal(): void {
    this._open$.next(false);
  }
}
