import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { CartModalService } from '../../../services/cart-modal.service';
import { CartService } from '../../../services/cart.service';

@Component({
  selector: 'app-cart-added-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cart-added-modal.component.html',
  styleUrl: './cart-added-modal.component.scss',
})
export class CartAddedModalComponent {
  private modal = inject(CartModalService);
  private cartSvc = inject(CartService);
  private router = inject(Router);

  item$ = this.modal.item$;
  cartCount = 0;

  constructor() {
    this.modal.item$.subscribe(item => {
      if (item) {
        this.cartSvc.getCart().subscribe({
          next: c => { this.cartCount = c.item_count; },
        });
      }
    });
  }

  close(): void {
    this.modal.close();
  }

  continueShopping(): void {
    this.modal.close();
  }

  viewCart(): void {
    this.modal.close();
    this.router.navigate(['/my-cart']);
  }
}
