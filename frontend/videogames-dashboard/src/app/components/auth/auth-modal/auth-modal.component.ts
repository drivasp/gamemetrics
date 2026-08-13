import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../services/auth.service';
import { LocaleService, CountryLocale } from '../../../services/locale.service';
import { MatIconModule } from '@angular/material/icon';
import { ModalService } from '../../../services/modal.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-auth-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  templateUrl: './auth-modal.component.html',
  styleUrl: './auth-modal.component.scss',
})
export class AuthModalComponent implements OnInit {
  private auth = inject(AuthService);
  private locale = inject(LocaleService);
  private modal = inject(ModalService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  isOpen = false;
  activeTab: 'login' | 'register' = 'login';
  loading = false;
  errorMsg = '';

  loginEmail = '';
  loginPassword = '';
  showLoginPassword = false;

  regDisplayName = '';
  regEmail = '';
  regPassword = '';
  regPasswordConfirm = '';
  showRegPassword = false;
  showRegPasswordConfirm = false;
  regCountry = '';
  countries: CountryLocale[] = [];

  ngOnInit(): void {
    this.locale.loadCountries();
    this.locale.countriesList$.subscribe(list => {
      this.countries = list;
      this.cdr.detectChanges();
    });
    this.modal.authModalOpen$.subscribe(open => {
      this.isOpen = open;
      if (!open) this._reset();
      this.cdr.detectChanges();
    });
  }

  setTab(tab: 'login' | 'register'): void {
    this.activeTab = tab;
    this.errorMsg = '';
  }

  close(): void {
    this.modal.closeAuthModal();
  }

  onOverlayClick(e: MouseEvent): void {
    if ((e.target as HTMLElement).classList.contains('modal-overlay')) {
      this.close();
    }
  }

  login(): void {
    if (!this.loginEmail || !this.loginPassword) {
      this.errorMsg = 'Completa todos los campos';
      return;
    }
    this.loading = true;
    this.errorMsg = '';
    this.cdr.detectChanges();
    this.auth.login(this.loginEmail.trim(), this.loginPassword).subscribe({
      next: () => {
        this.loading = false;
        this.locale.refresh();
        this.close();
        this._goHomeByRole();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = this._errDetail(err) || 'Email o contraseña incorrectos';
        this.cdr.detectChanges();
      },
    });
  }

  register(): void {
    if (!this.regDisplayName || !this.regEmail || !this.regPassword || !this.regCountry) {
      this.errorMsg = 'Completa todos los campos, incluido el país de residencia';
      return;
    }
    if (this.regPassword.length < 8) {
      this.errorMsg = 'La contraseña debe tener al menos 8 caracteres';
      return;
    }
    if (this.regPassword !== this.regPasswordConfirm) {
      this.errorMsg = 'Las contraseñas no coinciden';
      return;
    }
    this.loading = true;
    this.errorMsg = '';
    this.cdr.detectChanges();
    this.auth.register(
      this.regEmail.trim(),
      this.regPassword,
      this.regDisplayName,
      this.regCountry,
    ).subscribe({
      next: () => {
        this.loading = false;
        this.locale.refresh();
        this.close();
        this._goHomeByRole();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = this._errDetail(err) || 'Error al registrar usuario';
        this.cdr.detectChanges();
      },
    });
  }

  /** Players/publishers → tienda. Admin → panel ETL. */
  private _goHomeByRole(): void {
    if (this.auth.isAdmin()) {
      this.router.navigate(['/']);
    } else {
      this.router.navigate(['/store']);
    }
  }

  private _errDetail(err: { error?: { detail?: unknown }; status?: number }): string {
    const d = err?.error?.detail;
    if (typeof d === 'string' && d.trim()) return d;
    if (Array.isArray(d)) {
      return d.map((x: { msg?: string }) => x?.msg || JSON.stringify(x)).join(' ');
    }
    if (err?.status === 503) {
      return 'Servicio temporalmente no disponible. Intenta de nuevo.';
    }
    if (err?.status === 0) {
      return 'No se pudo conectar con el servidor. Revisa tu conexion.';
    }
    return '';
  }

  private _reset(): void {
    this.loginEmail = this.loginPassword = '';
    this.regEmail = this.regPassword = this.regPasswordConfirm = this.regDisplayName = '';
    this.regCountry = '';
    this.showLoginPassword = false;
    this.showRegPassword = false;
    this.showRegPasswordConfirm = false;
    this.errorMsg = '';
    this.loading = false;
    this.activeTab = 'login';
  }
}
