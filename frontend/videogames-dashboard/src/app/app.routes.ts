import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { GamesListComponent } from './components/games-list/games-list.component';
import { EmpresaComponent } from './components/empresa/empresa.component';
import { DimensionesComponent } from './components/dimensiones/dimensiones.component';
import { StoreHomeComponent } from './components/store/store-home/store-home.component';
import { StoreCatalogComponent } from './components/store/store-catalog/store-catalog.component';
import { StoreGameDetailComponent } from './components/store/store-game-detail/store-game-detail.component';
import { ProfileComponent } from './components/auth/profile/profile.component';
import { CartComponent } from './components/cart/cart.component';
import { LibraryComponent } from './components/library/library.component';
import { PaymentComponent } from './components/payment/payment.component';
import { PaymentSuccessComponent } from './components/payment/payment-success.component';
import { WalletComponent } from './components/wallet/wallet.component';
import { GiftsComponent } from './components/gifts/gifts.component';
import { FriendsComponent } from './components/friends/friends.component';
import { SupportComponent } from './components/support/support.component';
import { PartnerComponent } from './components/partner/partner.component';
import { FamilyComponent } from './components/family/family.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'games', component: GamesListComponent },
  { path: 'empresa', component: EmpresaComponent },
  { path: 'dimensiones', component: DimensionesComponent },
  { path: 'store', component: StoreHomeComponent },
  { path: 'store/catalog', component: StoreCatalogComponent },
  { path: 'store/game/:slug', component: StoreGameDetailComponent },
  { path: 'my-cart', component: CartComponent, canActivate: [authGuard] },
  { path: 'my-library', component: LibraryComponent, canActivate: [authGuard] },
  { path: 'payment', component: PaymentComponent, canActivate: [authGuard] },
  { path: 'payment/success', component: PaymentSuccessComponent, canActivate: [authGuard] },
  { path: 'my-wallet', component: WalletComponent, canActivate: [authGuard] },
  { path: 'my-gifts', component: GiftsComponent, canActivate: [authGuard] },
  { path: 'my-friends', component: FriendsComponent, canActivate: [authGuard] },
  { path: 'my-support', component: SupportComponent, canActivate: [authGuard] },
  { path: 'my-partner', component: PartnerComponent, canActivate: [authGuard] },
  { path: 'my-family', component: FamilyComponent, canActivate: [authGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [authGuard] },
];
