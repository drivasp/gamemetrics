import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';
import { AuthModalComponent } from './components/auth/auth-modal/auth-modal.component';
import { CartAddedModalComponent } from './components/cart/cart-added-modal/cart-added-modal.component';
import { GiftSentModalComponent } from './components/gifts/gift-sent-modal/gift-sent-modal.component';
import { AchievementPopupComponent } from './components/achievements/achievement-popup.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    NavbarComponent,
    AuthModalComponent,
    CartAddedModalComponent,
    GiftSentModalComponent,
    AchievementPopupComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
