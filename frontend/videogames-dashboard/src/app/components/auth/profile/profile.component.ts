import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService, User } from '../../../services/auth.service';
import { MatIconModule } from '@angular/material/icon';
import { WishlistService, WishlistItem } from '../../../services/wishlist.service';
import { GameCoverComponent } from '../../../shared/game-cover/game-cover.component';
import { LibraryService } from '../../../services/library.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, GameCoverComponent],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss',
})
export class ProfileComponent implements OnInit {
  private auth = inject(AuthService);
  private wishlist = inject(WishlistService);
  private library = inject(LibraryService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  user: User | null = null;
  wishlistItems: WishlistItem[] = [];
  purchasedCount = 0;
  loadingWishlist = true;

  editing = false;
  editDisplayName = '';
  editBio = '';
  savingProfile = false;
  profileMsg = '';

  ngOnInit(): void {
    this.user = this.auth.getCurrentUser();
    this.auth.getProfile().subscribe({
      next: (u) => { this.user = u; this.cdr.detectChanges(); },
      error: () => {},
    });
    this._loadWishlist();
    this.library.getLibrary().subscribe({
      next: (items) => {
        this.purchasedCount = items.length;
        this.cdr.detectChanges();
      },
      error: () => {},
    });
  }

  private _loadWishlist(): void {
    this.loadingWishlist = true;
    this.wishlist.getWishlist().subscribe({
      next: (items) => {
        this.wishlistItems = items;
        this.loadingWishlist = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingWishlist = false; this.cdr.detectChanges(); },
    });
  }

  startEdit(): void {
    this.editDisplayName = this.user?.display_name ?? '';
    this.editBio = this.user?.bio ?? '';
    this.editing = true;
    this.profileMsg = '';
  }

  cancelEdit(): void {
    this.editing = false;
  }

  saveProfile(): void {
    this.savingProfile = true;
    this.auth.updateProfile({
      display_name: this.editDisplayName,
      bio: this.editBio,
    }).subscribe({
      next: (u) => {
        this.user = u;
        this.editing = false;
        this.savingProfile = false;
        this.profileMsg = '¡Perfil actualizado!';
        setTimeout(() => { this.profileMsg = ''; this.cdr.detectChanges(); }, 2500);
        this.cdr.detectChanges();
      },
      error: () => {
        this.savingProfile = false;
        this.profileMsg = 'Error al guardar';
        this.cdr.detectChanges();
      },
    });
  }

  onAvatarChange(e: Event): void {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.auth.uploadAvatar(file).subscribe({
      next: (u) => { this.user = u; this.cdr.detectChanges(); },
      error: () => {},
    });
  }

  removeFromWishlist(slug: string): void {
    this.wishlist.removeFromWishlist(slug).subscribe({
      next: () => {
        this.wishlistItems = this.wishlistItems.filter(i => i.game_slug !== slug);
        this.cdr.detectChanges();
      },
      error: () => {},
    });
  }

  goToGame(slug: string): void {
    if (!slug?.trim()) {
      this.router.navigate(['/store']);
      return;
    }
    this.router.navigate(['/store/game', slug]);
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/store']);
  }

  get avatarLabel(): string {
    const name = this.user?.display_name || this.user?.email || '?';
    return name.charAt(0).toUpperCase();
  }
}
