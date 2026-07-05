import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { GiftModalService } from '../../../services/gift-modal.service';
import { GameCoverComponent } from '../../../shared/game-cover/game-cover.component';

@Component({
  selector: 'app-gift-sent-modal',
  standalone: true,
  imports: [CommonModule, MatIconModule, GameCoverComponent],
  templateUrl: './gift-sent-modal.component.html',
  styleUrl: './gift-sent-modal.component.scss',
})
export class GiftSentModalComponent {
  private modal = inject(GiftModalService);
  private router = inject(Router);

  gift$ = this.modal.gift$;

  close(): void {
    this.modal.close();
  }

  continueShopping(): void {
    this.modal.close();
  }

  viewSent(): void {
    this.modal.close();
    this.router.navigate(['/my-gifts']);
  }
}
