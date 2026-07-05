import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { CartService, Cart } from '../../services/cart.service';
import { GameCoverComponent } from '../../shared/game-cover/game-cover.component';
import { LibraryService, CheckoutResult } from '../../services/library.service';
import { WalletService } from '../../services/wallet.service';
import { EventsService } from '../../services/events.service';

@Component({
  selector: 'app-payment',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatIconModule, GameCoverComponent],
  templateUrl: './payment.component.html',
  styleUrl: './payment.component.scss',
})
export class PaymentComponent implements OnInit {
  private cartSvc = inject(CartService);
  private librarySvc = inject(LibraryService);
  private walletSvc = inject(WalletService);
  private events = inject(EventsService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  cart: Cart | null = null;
  walletBalance = 0;
  loading = true;
  paying = false;
  message = '';
  error = '';

  couponCode = '';
  couponApplied = 0;
  couponMessage = '';
  couponError = '';
  paymentMethod: 'wallet' | 'sandbox' = 'sandbox';

  private cartReady = false;
  private walletReady = false;

  ngOnInit(): void {
    this.events.track('checkout_view');
    this.walletSvc.getWallet().subscribe({
      next: w => {
        this.walletBalance = w.balance;
        this.walletReady = true;
        this.finishLoad();
      },
      error: () => {
        this.walletBalance = 0;
        this.walletReady = true;
        this.finishLoad();
      },
    });
    this.cartSvc.getCart().subscribe({
      next: c => {
        this.cart = c;
        this.cartReady = true;
        if (!c.items.length) {
          this.router.navigate(['/my-cart']);
          return;
        }
        this.finishLoad();
      },
      error: () => {
        this.loading = false;
        this.router.navigate(['/my-cart']);
      },
    });
  }

  get subtotal(): number {
    return this.cart?.total ?? 0;
  }

  get finalTotal(): number {
    return Math.max(0, Math.round((this.subtotal - this.couponApplied) * 100) / 100);
  }

  get walletCanPay(): boolean {
    return this.finalTotal <= 0 || this.walletBalance + 0.001 >= this.finalTotal;
  }

  get walletMissing(): number {
    return Math.max(0, Math.round((this.finalTotal - this.walletBalance) * 100) / 100);
  }

  get payDisabled(): boolean {
    return this.paying || (this.paymentMethod === 'wallet' && !this.walletCanPay);
  }

  private finishLoad(): void {
    if (!this.cartReady || !this.walletReady) return;
    this.loading = false;
    this.syncPaymentMethod();
    this.cdr.detectChanges();
  }

  /** Elige método válido según saldo y total (con cupón). */
  syncPaymentMethod(): void {
    if (this.walletCanPay) {
      this.paymentMethod = 'wallet';
    } else {
      this.paymentMethod = 'sandbox';
    }
  }

  applyCoupon(): void {
    if (!this.cart || !this.couponCode.trim()) return;
    this.couponError = '';
    this.couponMessage = '';
    this.librarySvc.validateCoupon(this.couponCode.trim(), this.cart.total).subscribe({
      next: res => {
        this.couponApplied = res.discount_applied;
        this.couponCode = res.code;
        this.couponMessage = res.message;
        this.syncPaymentMethod();
        this.cdr.detectChanges();
      },
      error: err => {
        this.couponApplied = 0;
        this.couponError = err?.error?.detail || 'Cupón no válido';
        this.syncPaymentMethod();
        this.cdr.detectChanges();
      },
    });
  }

  clearCoupon(): void {
    this.couponCode = '';
    this.couponApplied = 0;
    this.couponMessage = '';
    this.couponError = '';
    this.syncPaymentMethod();
  }

  pay(): void {
    if (!this.cart || this.payDisabled) return;
    this.paying = true;
    this.error = '';
    const method = this.paymentMethod === 'wallet' ? 'wallet' : 'sandbox';
    this.events.track('checkout_pay', undefined, { method, total: this.finalTotal });

    this.librarySvc.checkout({
      coupon_code: this.couponApplied > 0 ? this.couponCode : null,
      payment_method: method,
    }).subscribe({
      next: (res: CheckoutResult) => {
        if (res.checkout_url) {
          window.location.href = res.checkout_url;
          return;
        }
        this.message = res.message;
        this.paying = false;
        if (res.wallet_balance != null) this.walletBalance = res.wallet_balance;
        this.walletSvc.refresh();
        this.cartSvc.resetCount();
        this.cartSvc.notifyChanged();
        setTimeout(() => this.router.navigate(['/my-library'], { queryParams: { paid: 1 } }), 1200);
        this.cdr.detectChanges();
      },
      error: err => {
        this.paying = false;
        this.error = err?.error?.detail || 'No se pudo procesar el pago';
        this.cdr.detectChanges();
      },
    });
  }

  back(): void {
    this.router.navigate(['/my-cart']);
  }
}
