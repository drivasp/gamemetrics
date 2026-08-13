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
  paymentMethod: 'wallet' | 'sandbox' | 'stripe' = 'sandbox';

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

  get currency(): string {
    return this.cart?.currency || 'USD';
  }

  get merchandise(): number {
    return this.cart?.total ?? 0;
  }

  get taxable(): number {
    return Math.max(0, Math.round((this.merchandise - this.couponApplied) * 100) / 100);
  }

  get taxRate(): number {
    return this.cart?.tax_rate_pct ?? 0;
  }

  get taxAmount(): number {
    return Math.round(this.taxable * (this.taxRate / 100) * 100) / 100;
  }

  get finalTotal(): number {
    return Math.round((this.taxable + this.taxAmount) * 100) / 100;
  }

  get walletAllowed(): boolean {
    return this.currency === 'USD';
  }

  get walletCanPay(): boolean {
    return this.walletAllowed
      && (this.finalTotal <= 0 || this.walletBalance + 0.001 >= this.finalTotal);
  }

  get walletMissing(): number {
    return Math.max(0, Math.round((this.finalTotal - this.walletBalance) * 100) / 100);
  }

  get payDisabled(): boolean {
    return this.paying || (this.paymentMethod === 'wallet' && !this.walletCanPay);
  }

  money(n: number): string {
    try {
      return new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: this.currency,
      }).format(n);
    } catch {
      return `${this.currency} ${n.toFixed(2)}`;
    }
  }

  private finishLoad(): void {
    if (!this.cartReady || !this.walletReady) return;
    this.loading = false;
    this.syncPaymentMethod();
    this.cdr.detectChanges();
  }

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
    const method = this.paymentMethod;
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
        const detail = err?.error?.detail;
        this.error = typeof detail === 'string'
          ? detail
          : (detail?.message || 'No se pudo procesar el pago');
        this.cdr.detectChanges();
      },
    });
  }

  payLabel(): string {
    if (this.paying) return 'Procesando...';
    if (this.paymentMethod === 'wallet') return 'Pagar con cartera';
    if (this.paymentMethod === 'stripe') return 'Pagar con Stripe';
    return 'Completar compra';
  }

  back(): void {
    this.router.navigate(['/my-cart']);
  }
}
