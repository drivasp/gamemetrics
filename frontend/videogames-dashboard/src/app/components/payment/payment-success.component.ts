import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { LibraryService } from '../../services/library.service';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-payment-success',
  standalone: true,
  imports: [CommonModule, RouterLink, MatIconModule],
  templateUrl: './payment-success.component.html',
  styleUrl: './payment-success.component.scss',
})
export class PaymentSuccessComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private librarySvc = inject(LibraryService);
  private cartSvc = inject(CartService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  loading = true;
  message = 'Confirmando tu pago...';
  error = '';

  ngOnInit(): void {
    const sessionId = this.route.snapshot.queryParamMap.get('session_id');
    if (!sessionId) {
      this.router.navigate(['/my-library']);
      return;
    }
    this.librarySvc.confirmPayment(sessionId).subscribe({
      next: res => {
        this.loading = false;
        this.message = res.message || 'Tus juegos ya están en tu biblioteca.';
        this.cartSvc.notifyChanged();
        this.cdr.detectChanges();
        setTimeout(() => this.router.navigate(['/my-library'], { queryParams: { paid: 1 } }), 5000);
      },
      error: err => {
        this.loading = false;
        this.error = err?.error?.detail || 'Error al confirmar el pago';
        this.cdr.detectChanges();
      },
    });
  }
}
