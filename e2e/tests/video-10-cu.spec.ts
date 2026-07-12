import { test, expect } from '@playwright/test';
import {
  API,
  addToCartViaApi,
  checkoutViaApi,
  dismissPopups,
  getFirstFeaturedGame,
  loginViaUi,
  purchaseGameViaApi,
  registerViaApi,
  registerViaUi,
  topupWalletViaApi,
  waitForLibraryItem,
} from './helpers';

/**
 * Los 10 casos de uso operativos del video GA07 (specs/003-operativo).
 * Requiere Docker + Semana 1 cargada en Pinot.
 */

test.beforeAll(async ({ request }) => {
  const health = await request.get(`${API}/store/featured`);
  expect(health.ok(), 'Backend/Pinot no responde en /store/featured').toBeTruthy();
  const games = await health.json();
  expect(games.length, 'Sin juegos — carga Semana 1 en Panel ETL').toBeGreaterThan(0);
});

// 1 · CU-O06 — Ver home tienda
test('CU-O06 · Ver home de la tienda', async ({ page }) => {
  await page.goto('/store');
  await expect(page.locator('.loading-full')).toBeHidden({ timeout: 60_000 });
  await expect(page.locator('.spotlight, .section-title, app-game-card').first()).toBeVisible({
    timeout: 60_000,
  });
});

// 2 · CU-O07 — Navegar catálogo
test('CU-O07 · Navegar catálogo con filtros y paginación', async ({ page }) => {
  await page.goto('/store/catalog');
  await expect(page.locator('.games-grid app-game-card').first()).toBeVisible({ timeout: 60_000 });

  await page.locator('.search-input').fill('Half');
  await page.waitForTimeout(700);
  await expect(page.locator('.games-grid')).toContainText('Half', { timeout: 30_000 });

  const page2 = page.locator('.pagination .page-btn', { hasText: '2' });
  if (await page2.isVisible()) {
    await page2.click();
    await expect(page.locator('.games-grid app-game-card').first()).toBeVisible({ timeout: 30_000 });
  }
  await expect(page.locator('.catalog-error')).toHaveCount(0);
});

// 3 · CU-O01 — Registrarse
test('CU-O01 · Registrarse', async ({ page }) => {
  const user = await registerViaUi(page);
  await expect(page.locator('.user-name')).toContainText(user.displayName);
});

// 4 · CU-O14 — Agregar wishlist
test('CU-O14 · Agregar juego a wishlist', async ({ page, request }) => {
  const { user } = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  await loginViaUi(page, user.email, user.password);
  await page.goto(`/store/game/${game.slug}`);
  await page.getByRole('button', { name: 'Agregar a Wishlist' }).click();
  await expect(page.getByRole('button', { name: 'En tu wishlist' })).toBeVisible({ timeout: 15_000 });
  await page.goto('/profile');
  await expect(page.getByRole('heading', { name: 'Mi lista de deseados' })).toBeVisible();
  await expect(page.locator('.wishlist-card').first()).toBeVisible();
});

// 5 · CU-O18·O22·O23·O24 — Compra sandbox → biblioteca
test('CU-O18/O22/O23/O24 · Comprar con sandbox y ver en biblioteca', async ({ page, request }) => {
  page.on('dialog', (d) => d.dismiss());

  const { user, token } = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  await addToCartViaApi(request, token, game);

  await loginViaUi(page, user.email, user.password);
  await page.goto('/payment');
  await expect(page.getByRole('heading', { name: 'Continuar al pago' })).toBeVisible({ timeout: 15_000 });
  await page.getByLabel('Pago inmediato (sandbox)').check();
  await page.getByRole('button', { name: 'Completar compra' }).click();
  await expect(page).toHaveURL(/\/my-library/, { timeout: 45_000 });
  await expect(page.locator('body')).toContainText(game.name, { timeout: 30_000 });
});

// 6 · CU-O11·O12 — Recargar cartera y pagar con saldo
test('CU-O11/O12 · Recargar cartera y pagar con saldo', async ({ page, request }) => {
  page.on('dialog', (d) => d.dismiss());

  const { user, token } = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  await topupWalletViaApi(request, token, 100);
  await addToCartViaApi(request, token, game);

  await loginViaUi(page, user.email, user.password);
  await page.goto('/my-wallet');
  await expect(page.locator('.amount')).toContainText('$100', { timeout: 15_000 });

  await page.goto('/payment');
  await page.getByLabel('Cartera GameMetrics').check();
  await page.getByRole('button', { name: 'Pagar con cartera' }).click();
  await expect(page).toHaveURL(/\/my-library/, { timeout: 45_000 });
  await expect(page.locator('body')).toContainText(game.name, { timeout: 30_000 });
});

// 7 · CU-O26 — Reseña verificada
test('CU-O26 · Crear reseña verificada', async ({ page, request }) => {
  const { user, token } = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  await purchaseGameViaApi(request, token, game);
  await waitForLibraryItem(request, token, game.product_id);

  await loginViaUi(page, user.email, user.password);
  await page.goto(`/store/game/${game.slug}`);
  await expect(page.getByRole('heading', { name: 'Escribe tu reseña' })).toBeVisible({ timeout: 20_000 });

  await page.locator('.review-form textarea').fill('Excelente juego para la demo del video.');
  await page.getByRole('button', { name: 'Publicar reseña' }).click();
  await expect(page.locator('.review-card').first()).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.reviews-section')).toContainText('Excelente juego');
});

// 8 · CU-O14·O14b — Instalar y jugar (launcher)
test('CU-O14/O14b · Instalar y jugar desde biblioteca', async ({ page, request }) => {
  const { user, token } = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  await purchaseGameViaApi(request, token, game);
  await waitForLibraryItem(request, token, game.product_id);

  await loginViaUi(page, user.email, user.password);
  await page.goto('/my-library');
  await expect(page.locator('body')).toContainText(game.name, { timeout: 20_000 });

  const card = page.locator('.lib-card').filter({ hasText: game.name });
  await card.getByRole('button', { name: 'Instalar' }).click();
  await expect(card.getByRole('button', { name: 'Jugar' })).toBeVisible({ timeout: 30_000 });
  await dismissPopups(page);

  await card.getByRole('button', { name: 'Jugar' }).click();
  await expect(page.locator('.play-overlay')).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Finalizar sesión' }).click();
  await expect(page.locator('.play-overlay')).toBeHidden({ timeout: 10_000 });
});

// 9 · CU-O15·O15b — Regalar juego y aceptar regalo
test('CU-O15/O15b · Regalar juego y aceptar regalo', async ({ page, request }) => {
  const sender = await registerViaApi(request);
  const recipient = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  await topupWalletViaApi(request, sender.token, 100);

  await loginViaUi(page, sender.user.email, sender.user.password);
  await page.goto(`/store/game/${game.slug}`);
  await page.getByRole('button', { name: 'Comprar como regalo' }).click();
  await page.locator('.gift-panel input[type="email"]').fill(recipient.user.email);
  await page.locator('.gift-panel textarea').fill('¡Disfrútalo!');
  await page.getByRole('button', { name: 'Pagar con cartera y enviar' }).click();
  await expect(page.getByText('¡Regalo enviado!')).toBeVisible({ timeout: 20_000 });

  await page.goto('/profile');
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await loginViaUi(page, recipient.user.email, recipient.user.password);
  await page.goto('/my-gifts');
  await expect(page.locator('.gift-card').first()).toBeVisible({ timeout: 20_000 });
  await page.getByRole('button', { name: 'Aceptar y añadir a biblioteca' }).first().click();

  await page.goto('/my-library');
  await expect(page.locator('body')).toContainText(game.name, { timeout: 30_000 });
});

// 10 · CU-O17 — Reembolso
test('CU-O17 · Solicitar reembolso', async ({ page, request }) => {
  const { user, token } = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  await purchaseGameViaApi(request, token, game);
  await waitForLibraryItem(request, token, game.product_id);

  await loginViaUi(page, user.email, user.password);
  await page.goto('/my-library');
  await expect(page.locator('body')).toContainText(game.name, { timeout: 20_000 });

  const card = page.locator('.lib-card').filter({ hasText: game.name });
  const modal = page.locator('.refund-modal');
  await card.getByRole('button', { name: 'Reembolso' }).click();
  await expect(modal.getByRole('heading', { name: 'Solicitud de reembolso' })).toBeVisible();
  await modal.locator('.rm-footer').getByRole('button', { name: 'Continuar' }).click();
  await modal.locator('input[type="radio"]').first().check();
  await modal.locator('.rm-footer').getByRole('button', { name: 'Continuar' }).click();
  await modal.locator('input[type="checkbox"]').check();
  await modal.getByRole('button', { name: 'Confirmar reembolso' }).click();
  await expect(modal.getByText('Reembolso aprobado')).toBeVisible({ timeout: 30_000 });
});
