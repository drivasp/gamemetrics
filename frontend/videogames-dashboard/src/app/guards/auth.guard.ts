import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ModalService } from '../services/modal.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const modal = inject(ModalService);

  if (auth.isLoggedIn()) {
    return true;
  }

  router.navigate(['/']);
  modal.openAuthModal();
  return false;
};
