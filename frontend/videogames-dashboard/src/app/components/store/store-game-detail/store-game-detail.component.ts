import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { StoreService, StoreGameDetail } from '../../../services/store.service';
import { StoreGameCardComponent } from '../store-game-card/store-game-card.component';
import { AuthService } from '../../../services/auth.service';
import { WishlistService } from '../../../services/wishlist.service';
import { CartService } from '../../../services/cart.service';
import { CartModalService } from '../../../services/cart-modal.service';
import { LibraryService } from '../../../services/library.service';
import { ReviewsService, Review, ReviewPage } from '../../../services/reviews.service';
import { GiftsService } from '../../../services/gifts.service';
import { GiftModalService } from '../../../services/gift-modal.service';
import { AlertsService } from '../../../services/alerts.service';
import { EventsService } from '../../../services/events.service';
import { WalletService } from '../../../services/wallet.service';
import { CommunityService } from '../../../services/community.service';
import { MatIconModule } from '@angular/material/icon';
import { ModalService } from '../../../services/modal.service';
import { GameCoverComponent } from '../../../shared/game-cover/game-cover.component';
import { coverPlaceholderUrl } from '../../../shared/utils/cover-url';

@Component({
  selector: 'app-game-detail',
  standalone: true,
  imports: [CommonModule, StoreGameCardComponent, FormsModule, MatIconModule, GameCoverComponent],
  templateUrl: './store-game-detail.component.html',
  styleUrl: './store-game-detail.component.scss',
})
export class StoreGameDetailComponent implements OnInit {
  private svc = inject(StoreService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);
  auth = inject(AuthService);
  private wishlistSvc = inject(WishlistService);
  private cartSvc = inject(CartService);
  private cartModal = inject(CartModalService);
  private librarySvc = inject(LibraryService);
  private reviewsSvc = inject(ReviewsService);
  private giftsSvc = inject(GiftsService);
  private giftModal = inject(GiftModalService);
  private alertsSvc = inject(AlertsService);
  private events = inject(EventsService);
  private walletSvc = inject(WalletService);
  private community = inject(CommunityService);
  private modal = inject(ModalService);

  forumThreads: any[] = [];
  activeThread: any = null;
  forumTitle = '';
  forumBody = '';
  replyBody = '';
  forumBusy = false;
  forumMsg = '';
  forumErr = '';

  inWishlist = false;
  inCart = false;
  owned = false;
  wishlistLoading = false;
  cartLoading = false;

  showGiftForm = false;
  giftEmail = '';
  giftMessage = '';
  giftLoading = false;
  giftMsg = '';
  giftErr = '';

  alertPrice = 0;
  alertLoading = false;
  alertMsg = '';

  game: StoreGameDetail | null = null;
  reviews: ReviewPage | null = null;
  reviewRating = 5;
  reviewComment = '';
  reviewSubmitting = false;
  reviewError = '';
  myReview: Review | null = null;

  loading = true;
  error = false;
  activeScreenshot: string | null = null;
  showTrailer = false;

  get heroStyle(): string {
    if (!this.game) return 'none';
    const url = this.game.background_image || coverPlaceholderUrl(this.game.slug, this.game.name);
    return `url('${url}')`;
  }

  get displayGenres(): string {
    return (this.game?.genres ?? '').split('||').map(g => g.trim()).filter(Boolean).join(' · ');
  }

  get displayPlatforms(): string {
    return (this.game?.platforms ?? '').split('||').slice(0, 5).map(p => p.trim()).filter(Boolean).join(', ');
  }

  get priceLabel(): string {
    if (!this.game) return '';
    return this.game.is_free ? 'GRATIS' : '$' + this.game.price.toFixed(2);
  }

  get originalPriceLabel(): string | null {
    if (!this.game?.original_price || !this.game.discount_pct) return null;
    return '$' + this.game.original_price.toFixed(2);
  }

  get shortDescription(): string {
    const d = this.game?.description ?? '';
    return d.length > 800 ? d.slice(0, 797) + '...' : d;
  }

  get ratingPct(): number { return ((this.game?.rating ?? 0) / 5) * 100; }
  get metacriticPct(): number { return this.game?.metacritic ?? 0; }

  ngOnInit(): void {
    this.route.params.subscribe(p => {
      const slug = p['slug'];
      if (!slug) { this.error = true; return; }
      this.loadGame(slug);
    });
    this.auth.currentUser$.subscribe(user => {
      if (user && this.game) this.refreshUserState(this.game);
    });
  }

  private refreshUserState(game: StoreGameDetail): void {
    this.wishlistSvc.checkWishlist(game.slug).subscribe({
      next: (res) => { this.inWishlist = res.in_wishlist; this.cdr.detectChanges(); },
    });
    this.cartSvc.checkInCart(game.product_id).subscribe({
      next: (res) => { this.inCart = res.in_cart; this.cdr.detectChanges(); },
    });
    this.librarySvc.checkOwned(game.slug).subscribe({
      next: (res) => { this.owned = res.owned; this.cdr.detectChanges(); },
    });
  }

  private loadReviews(slug: string): void {
    this.reviewsSvc.getReviews(slug).subscribe({
      next: (r) => {
        this.reviews = r;
        const userId = this.auth.getCurrentUser()?.id;
        this.myReview = userId
          ? (r.reviews.find(rv => rv.user_id === userId) ?? null)
          : null;
        if (this.myReview) {
          this.reviewRating = this.myReview.rating;
          this.reviewComment = this.myReview.comment;
        }
        this.cdr.detectChanges();
      },
    });
  }

  private loadGame(slug: string): void {
    this.loading = true; this.game = null; this.error = false;
    this.svc.getGameDetail(slug).subscribe({
      next: (game) => {
        this.game = game;
        this.activeScreenshot = game.screenshots[0] ?? game.background_image;
        this.showTrailer = !!game.trailer_url;
        this.alertPrice = Math.max(0.99, Math.round((game.price * 0.8) * 100) / 100);
        this.loading = false;
        this.events.track('product_view', game.product_id, { slug: game.slug });
        this.cdr.detectChanges();
        this.loadReviews(slug);
        this.loadForum(slug);
        if (this.auth.isLoggedIn()) {
          this.refreshUserState(game);
        }
      },
      error: () => { this.loading = false; this.error = true; this.cdr.detectChanges(); },
    });
  }

  private requireAuth(): boolean {
    if (!this.auth.isLoggedIn()) {
      this.modal.openAuthModal();
      return false;
    }
    return true;
  }

  toggleWishlist(): void {
    if (!this.requireAuth() || !this.game) return;
    this.wishlistLoading = true;
    if (this.inWishlist) {
      this.wishlistSvc.removeFromWishlist(this.game.slug).subscribe({
        next: () => { this.inWishlist = false; this.wishlistLoading = false; this.cdr.detectChanges(); },
        error: () => { this.wishlistLoading = false; this.cdr.detectChanges(); },
      });
    } else {
      this.wishlistSvc.addToWishlist({
        game_slug: this.game.slug,
        game_name: this.game.name,
        game_image: this.game.background_image,
        game_price: this.game.price,
      }).subscribe({
        next: () => { this.inWishlist = true; this.wishlistLoading = false; this.cdr.detectChanges(); },
        error: () => { this.wishlistLoading = false; this.cdr.detectChanges(); },
      });
    }
  }

  addToCart(): void {
    if (!this.requireAuth() || !this.game || this.owned) return;
    this.cartLoading = true;
    this.cartSvc.addItem({
      product_id: this.game.product_id,
      game_slug: this.game.slug,
      game_name: this.game.name,
      game_image: this.game.background_image,
      unit_price: this.game.price,
    }).subscribe({
      next: () => {
        this.inCart = true;
        this.cartLoading = false;
        if (this.game) {
          this.cartModal.show({
            product_id: this.game.product_id,
            game_slug: this.game.slug,
            game_name: this.game.name,
            game_image: this.game.background_image,
            unit_price: this.game.price,
            original_price: this.game.original_price,
            discount_pct: this.game.discount_pct,
          });
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.cartLoading = false;
        alert(err?.error?.detail || 'No se pudo agregar al carrito');
        this.cdr.detectChanges();
      },
    });
  }

  goCart(): void { this.router.navigate(['/my-cart']); }
  goLibrary(): void { this.router.navigate(['/my-library']); }

  submitReview(): void {
    if (!this.requireAuth() || !this.game || !this.owned) return;
    this.reviewSubmitting = true;
    this.reviewError = '';
    const payload = {
      product_id: this.game.product_id,
      rating: Number(this.reviewRating),
      comment: this.reviewComment,
    };
    const onSuccess = () => {
      this.reviewSubmitting = false;
      if (this.game) this.loadReviews(this.game.slug);
    };
    const onError = (err: { error?: { detail?: string } }) => {
      this.reviewSubmitting = false;
      this.reviewError = err?.error?.detail || 'Error al publicar reseña';
      this.cdr.detectChanges();
    };

    if (this.myReview) {
      this.reviewsSvc.updateReview(this.game.slug, {
        rating: payload.rating,
        comment: payload.comment,
      }).subscribe({ next: onSuccess, error: onError });
      return;
    }

    this.reviewsSvc.createReview(this.game.slug, payload).subscribe({
      next: onSuccess,
      error: (err) => {
        if (err?.status === 409) {
          this.reviewsSvc.updateReview(this.game!.slug, {
            rating: payload.rating,
            comment: payload.comment,
          }).subscribe({ next: onSuccess, error: onError });
          return;
        }
        onError(err);
      },
    });
  }

  setScreenshot(url: string): void {
    this.showTrailer = false;
    this.activeScreenshot = url;
  }

  sendGift(): void {
    if (!this.requireAuth() || !this.game) return;
    this.giftLoading = true;
    this.giftErr = '';
    this.giftMsg = '';
    this.giftsSvc.send({
      product_id: this.game.product_id,
      game_slug: this.game.slug,
      game_name: this.game.name,
      game_image: this.game.background_image,
      recipient_email: this.giftEmail.trim(),
      message: this.giftMessage,
      payment_method: 'wallet',
    }).subscribe({
      next: gift => {
        this.giftLoading = false;
        this.giftMsg = '';
        this.showGiftForm = false;
        this.giftEmail = '';
        this.giftMessage = '';
        this.events.track('gift_sent', this.game!.product_id);
        this.walletSvc.refresh();
        this.giftModal.show({
          gift_id: gift.gift_id,
          game_name: gift.game_name,
          game_image: gift.game_image,
          recipient_email: gift.recipient_email,
          message: gift.message,
          amount: gift.amount,
        });
        this.cdr.detectChanges();
      },
      error: err => {
        this.giftLoading = false;
        this.giftErr = err?.error?.detail || 'No se pudo enviar el regalo';
        this.cdr.detectChanges();
      },
    });
  }

  setPriceAlert(): void {
    if (!this.requireAuth() || !this.game) return;
    this.alertLoading = true;
    this.alertMsg = '';
    this.alertsSvc.create({
      product_id: this.game.product_id,
      game_slug: this.game.slug,
      game_name: this.game.name,
      target_price: this.alertPrice,
    }).subscribe({
      next: a => {
        this.alertLoading = false;
        this.alertMsg = a.triggered
          ? '¡El precio ya está en o por debajo de tu objetivo!'
          : `Te avisaremos cuando baje de $${this.alertPrice.toFixed(2)}.`;
        this.cdr.detectChanges();
      },
      error: err => {
        this.alertLoading = false;
        this.alertMsg = err?.error?.detail || 'No se pudo crear la alerta';
        this.cdr.detectChanges();
      },
    });
  }

  voteReview(r: Review, helpful: boolean): void {
    if (!this.requireAuth()) return;
    this.reviewsSvc.vote(r.review_id, helpful).subscribe({
      next: res => {
        r.helpful_count = res.helpful_count;
        r.not_helpful_count = res.not_helpful_count;
        r.my_vote = res.my_vote;
        this.cdr.detectChanges();
      },
      error: err => alert(err?.error?.detail || 'No se pudo votar'),
    });
  }

  loadForum(slug: string): void {
    this.community.listThreads(slug).subscribe({
      next: res => { this.forumThreads = res.items || []; this.cdr.detectChanges(); },
      error: () => { this.forumThreads = []; },
    });
  }

  createThread(): void {
    if (!this.requireAuth() || !this.game || !this.forumTitle.trim() || !this.forumBody.trim()) return;
    this.forumBusy = true;
    this.forumErr = '';
    this.community.createThread({
      product_id: this.game.product_id,
      game_slug: this.game.slug,
      title: this.forumTitle.trim(),
      body: this.forumBody.trim(),
    }).subscribe({
      next: () => {
        this.forumBusy = false;
        this.forumMsg = 'Discusión publicada';
        this.forumTitle = '';
        this.forumBody = '';
        this.loadForum(this.game!.slug);
      },
      error: err => {
        this.forumBusy = false;
        this.forumErr = err?.error?.detail || 'No se pudo publicar';
        this.cdr.detectChanges();
      },
    });
  }

  openThread(t: any): void {
    this.community.getThread(t.thread_id).subscribe({
      next: res => { this.activeThread = res; this.cdr.detectChanges(); },
    });
  }

  replyThread(): void {
    if (!this.requireAuth() || !this.activeThread || !this.replyBody.trim()) return;
    this.forumBusy = true;
    const tid = this.activeThread.thread.thread_id;
    this.community.addPost(tid, this.replyBody.trim()).subscribe({
      next: () => {
        this.forumBusy = false;
        this.replyBody = '';
        this.openThread({ thread_id: tid });
      },
      error: err => {
        this.forumBusy = false;
        this.forumErr = err?.error?.detail || 'No se pudo responder';
        this.cdr.detectChanges();
      },
    });
  }

  goBack(): void { this.router.navigate(['/store/catalog']); }
  goToStore(): void { this.router.navigate(['/store']); }
}
