import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Panel ETL / Empresa / Dimensiones = operación interna.
 * Solo admin. Players y publishers van a la tienda.
 */
export const opsGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAdmin()) {
    return true;
  }
  router.navigate(['/store']);
  return false;
};
