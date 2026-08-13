import { Component, OnInit, OnDestroy, inject, HostListener, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService, User } from '../../services/auth.service';
import { CartService } from '../../services/cart.service';
import { WalletService } from '../../services/wallet.service';
import { GiftsService } from '../../services/gifts.service';
import { SocialService } from '../../services/social.service';
import { LocaleService, CountryLocale, UserLocale } from '../../services/locale.service';
import { MatIconModule } from '@angular/material/icon';
import { ModalService } from '../../services/modal.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, MatIconModule],
  templateUrl: './navbar.component.html',
})
export class NavbarComponent implements OnInit, OnDestroy {
  private auth = inject(AuthService);
  private cartSvc = inject(CartService);
  private walletSvc = inject(WalletService);
  private giftsSvc = inject(GiftsService);
  private social = inject(SocialService);
  private localeSvc = inject(LocaleService);
  private modal = inject(ModalService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  user: User | null = null;
  dropdownOpen = false;
  notifOpen = false;
  regionOpen = false;
  cartCount = 0;
  walletBalance = 0;
  giftPending = 0;
  notifUnread = 0;
  notifications: any[] = [];
  isStoreArea = false;
  countries: CountryLocale[] = [];
  locale: UserLocale | null = null;
  selectedCountry = 'US';
  private presenceTimer: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.localeSvc.loadCountries();
    this.localeSvc.refresh();
    this.localeSvc.countriesList$.subscribe(list => {
      this.countries = list;
      this.cdr.detectChanges();
    });
    this.localeSvc.myLocale$.subscribe(loc => {
      this.locale = loc;
      this.selectedCountry = loc.country_code;
      this.cdr.detectChanges();
    });

    this.updateStoreArea(this.router.url);
    this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe((e: NavigationEnd) => {
      this.updateStoreArea(e.urlAfterRedirects);
      this.notifOpen = false;
      this.regionOpen = false;
      if (this.user && e.urlAfterRedirects.startsWith('/my-gifts')) {
        this.giftsSvc.refreshPending();
      }
    });
    this.auth.currentUser$.subscribe(u => {
      this.user = u;
      if (u) {
        this.cartSvc.refreshCount();
        this.walletSvc.refresh();
        this.giftsSvc.refreshPending();
        this.social.refreshUnread();
        this.localeSvc.refresh();
        this.startPresenceHeartbeat();
      } else {
        this.cartCount = 0;
        this.walletBalance = 0;
        this.giftPending = 0;
        this.notifUnread = 0;
        this.notifications = [];
        this.giftsSvc.clearPending();
        this.social.clearUnread();
        this.stopPresenceHeartbeat();
        this.localeSvc.refresh();
      }
      this.cdr.detectChanges();
    });
    this.cartSvc.cartCount$.subscribe(n => {
      this.cartCount = n;
      this.cdr.detectChanges();
    });
    this.cartSvc.cartChanged$.subscribe(() => {
      if (this.user) this.cartSvc.refreshCount();
    });
    this.walletSvc.walletBalance$.subscribe(b => {
      this.walletBalance = b ?? 0;
      this.cdr.detectChanges();
    });
    this.giftsSvc.pendingCount$.subscribe(n => {
      this.giftPending = n;
      this.cdr.detectChanges();
    });
    this.social.unreadCount$.subscribe(n => {
      this.notifUnread = n;
      this.cdr.detectChanges();
    });
  }

  get currentCountryName(): string {
    const fromList = this.countries.find(c => c.country_code === this.selectedCountry)?.name;
    return fromList || this.locale?.name || this.locale?.country_name || this.selectedCountry;
  }

  get currentFlag(): string {
    return this.countries.find(c => c.country_code === this.selectedCountry)?.flag
      || this.locale?.flag
      || '🌐';
  }

  toggleRegion(e: MouseEvent): void {
    e.stopPropagation();
    this.dropdownOpen = false;
    this.notifOpen = false;
    this.regionOpen = !this.regionOpen;
  }

  refreshCartCount(): void {
    this.cartSvc.getCart().subscribe({
      next: (c) => { this.cartCount = c.item_count; },
      error: () => { this.cartCount = 0; },
    });
  }

  toggleNotif(e: MouseEvent): void {
    e.stopPropagation();
    this.dropdownOpen = false;
    this.regionOpen = false;
    this.notifOpen = !this.notifOpen;
    if (this.notifOpen) {
      this.social.getNotifications().subscribe({
        next: res => { this.notifications = res.items || []; },
        error: () => { this.notifications = []; },
      });
    }
  }

  markAllRead(): void {
    this.social.markAllRead().subscribe({
      next: () => {
        this.notifications = this.notifications.map(n => ({ ...n, read: true }));
        this.notifUnread = 0;
      },
    });
  }

  readOne(n: any): void {
    if (!n.read) {
      this.social.markRead(n.notification_id).subscribe({
        next: () => {
          n.read = true;
          this.notifUnread = Math.max(0, this.notifUnread - 1);
        },
      });
    }
  }

  openLogin(): void {
    this.modal.openAuthModal();
  }

  toggleDropdown(): void {
    this.notifOpen = false;
    this.regionOpen = false;
    this.dropdownOpen = !this.dropdownOpen;
  }

  goToProfile(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/profile']);
  }

  goToLibrary(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/my-library']);
  }

  goFriends(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/my-friends']);
  }

  goSupport(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/my-support']);
  }

  goPartner(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/my-partner']);
  }

  goAdmin(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/admin']);
  }

  get isAdmin(): boolean {
    return this.user?.role === 'admin';
  }

  get brandHome(): string {
    return this.isAdmin ? '/' : '/store';
  }

  goFamily(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/my-family']);
  }

  logout(): void {
    this.dropdownOpen = false;
    this.auth.logout();
    this.router.navigate(['/store']);
  }

  @HostListener('document:click', ['$event'])
  onDocClick(e: MouseEvent): void {
    const t = e.target as HTMLElement;
    if (!t.closest('.user-menu')) this.dropdownOpen = false;
    if (!t.closest('.notif-menu')) this.notifOpen = false;
    if (!t.closest('.region-menu')) this.regionOpen = false;
  }

  get avatarLabel(): string {
    const name = this.user?.display_name || this.user?.email || '?';
    return name.charAt(0).toUpperCase();
  }

  private updateStoreArea(url: string): void {
    this.isStoreArea = url.startsWith('/store') || url.startsWith('/my-cart')
      || url.startsWith('/my-library') || url.startsWith('/payment')
      || url.startsWith('/my-wallet') || url.startsWith('/my-gifts')
      || url.startsWith('/my-friends') || url.startsWith('/my-support')
      || url.startsWith('/my-partner') || url.startsWith('/my-family')
      || url.startsWith('/profile') || url.startsWith('/admin');
  }

  private startPresenceHeartbeat(): void {
    this.stopPresenceHeartbeat();
    this.social.heartbeat('online').subscribe({ error: () => undefined });
    this.presenceTimer = setInterval(() => {
      this.social.heartbeat('online').subscribe({ error: () => undefined });
    }, 45_000);
  }

  private stopPresenceHeartbeat(): void {
    if (this.presenceTimer) {
      clearInterval(this.presenceTimer);
      this.presenceTimer = null;
    }
  }

  ngOnDestroy(): void {
    this.stopPresenceHeartbeat();
  }
}
