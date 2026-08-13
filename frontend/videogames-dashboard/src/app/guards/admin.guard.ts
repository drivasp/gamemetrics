import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Solo cuentas con rol admin. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.isLoggedIn()) {
    router.navigate(['/store']);
    return false;
  }
  if (!auth.isAdmin()) {
    router.navigate(['/store']);
    return false;
  }
  return true;
};
