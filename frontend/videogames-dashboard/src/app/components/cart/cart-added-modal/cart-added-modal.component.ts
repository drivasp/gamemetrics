import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { CartModalService } from '../../../services/cart-modal.service';
import { CartService } from '../../../services/cart.service';
import { GameCoverComponent } from '../../../shared/game-cover/game-cover.component';

@Component({
  selector: 'app-cart-added-modal',
  standalone: true,
  imports: [CommonModule, MatIconModule, GameCoverComponent],
  templateUrl: './cart-added-modal.component.html',
  styleUrl: './cart-added-modal.component.scss',
})
export class CartAddedModalComponent {
  private modal = inject(CartModalService);
  private cartSvc = inject(CartService);
  private router = inject(Router);

  item$ = this.modal.item$;
  cartCount$ = this.cartSvc.cartCount$;

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
