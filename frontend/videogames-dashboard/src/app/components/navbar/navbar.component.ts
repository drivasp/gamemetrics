import { Component, OnInit, inject, HostListener, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService, User } from '../../services/auth.service';
import { CartService } from '../../services/cart.service';
import { WalletService } from '../../services/wallet.service';
import { GiftsService } from '../../services/gifts.service';
import { SocialService } from '../../services/social.service';
import { MatIconModule } from '@angular/material/icon';
import { ModalService } from '../../services/modal.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, MatIconModule],
  templateUrl: './navbar.component.html',
})
export class NavbarComponent implements OnInit {
  private auth = inject(AuthService);
  private cartSvc = inject(CartService);
  private walletSvc = inject(WalletService);
  private giftsSvc = inject(GiftsService);
  private social = inject(SocialService);
  private modal = inject(ModalService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  user: User | null = null;
  dropdownOpen = false;
  notifOpen = false;
  cartCount = 0;
  walletBalance = 0;
  giftPending = 0;
  notifUnread = 0;
  notifications: any[] = [];
  isStoreArea = false;

  ngOnInit(): void {
    this.updateStoreArea(this.router.url);
    this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe((e: NavigationEnd) => {
      this.updateStoreArea(e.urlAfterRedirects);
      this.notifOpen = false;
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
      } else {
        this.cartCount = 0;
        this.walletBalance = 0;
        this.giftPending = 0;
        this.notifUnread = 0;
        this.notifications = [];
        this.giftsSvc.clearPending();
        this.social.clearUnread();
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

  refreshCartCount(): void {
    this.cartSvc.getCart().subscribe({
      next: (c) => { this.cartCount = c.item_count; },
      error: () => { this.cartCount = 0; },
    });
  }

  toggleNotif(e: MouseEvent): void {
    e.stopPropagation();
    this.dropdownOpen = false;
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

  goFamily(): void {
    this.dropdownOpen = false;
    this.router.navigate(['/my-family']);
  }

  logout(): void {
    this.dropdownOpen = false;
    this.auth.logout();
    this.router.navigate(['/']);
  }

  @HostListener('document:click', ['$event'])
  onDocClick(e: MouseEvent): void {
    const t = e.target as HTMLElement;
    if (!t.closest('.user-menu')) this.dropdownOpen = false;
    if (!t.closest('.notif-menu')) this.notifOpen = false;
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
      || url.startsWith('/profile');
  }
}
