import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { GiftModalService } from '../../../services/gift-modal.service';

@Component({
  selector: 'app-gift-sent-modal',
  standalone: true,
  imports: [CommonModule],
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
