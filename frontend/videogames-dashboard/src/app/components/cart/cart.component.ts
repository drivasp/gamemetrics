import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { CartService, Cart } from '../../services/cart.service';
import { GameCoverComponent } from '../../shared/game-cover/game-cover.component';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [CommonModule, MatIconModule, GameCoverComponent],
  templateUrl: './cart.component.html',
  styleUrl: './cart.component.scss',
})
export class CartComponent implements OnInit {
  private cartSvc = inject(CartService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  cart: Cart | null = null;
  loading = true;
  message = '';

  ngOnInit(): void {
    this.loadCart();
  }

  loadCart(): void {
    this.loading = true;
    this.cartSvc.getCart().subscribe({
      next: (c) => { this.cart = c; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  remove(productId: string): void {
    this.cartSvc.removeItem(productId).subscribe({
      next: () => this.loadCart(),
      error: (err) => {
        this.message = err?.error?.detail || 'No se pudo quitar el artículo';
        this.cdr.detectChanges();
      },
    });
  }

  checkout(): void {
    this.router.navigate(['/payment']);
  }

  goStore(): void { this.router.navigate(['/store']); }
}
