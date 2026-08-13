import { APIRequestContext, Page, expect } from '@playwright/test';

export const API = process.env.E2E_API_URL ?? 'http://localhost:8080';

export function uniqueUser(countryCode = 'US') {
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  return {
    email: `e2e.${id}@gamemetrics.test`,
    password: 'TestPass123!',
    displayName: `E2E User ${id}`,
    countryCode,
  };
}

export async function registerViaApi(
  request: APIRequestContext,
  user = uniqueUser(),
) {
  const res = await request.post(`${API}/auth/register`, {
    data: {
      email: user.email,
      password: user.password,
      display_name: user.displayName,
      country_code: user.countryCode || 'US',
    },
  });
  expect(res.ok(), `register failed: ${await res.text()}`).toBeTruthy();
  const body = await res.json();
  return {
    user,
    token: body.token as string,
    userId: body.user?.id as string,
    role: (body.user?.role as string) || 'player',
  };
}

export async function loginViaUi(page: Page, email: string, password: string) {
  await page.goto('/store');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page.locator('.modal-overlay')).toBeVisible();
  const form = page.locator('form.modal-form').filter({ has: page.locator('input[name="loginEmail"]') });
  await form.locator('input[name="loginEmail"]').fill(email);
  await form.locator('input[name="loginPassword"]').fill(password);
  await form.locator('button[type="submit"]').click();
  await expect(page.locator('.user-name')).toBeVisible({ timeout: 20_000 });
}

export async function registerViaUi(
  page: Page,
  user = uniqueUser(),
) {
  await page.goto('/store');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await page.locator('.modal-tabs').getByRole('button', { name: 'Registrarse' }).click();
  const form = page.locator('form.modal-form').filter({ has: page.locator('input[name="regEmail"]') });
  await form.locator('input[name="regDisplayName"]').fill(user.displayName);
  await form.locator('input[name="regEmail"]').fill(user.email);
  await form.locator('input[name="regPassword"]').fill(user.password);
  await form.locator('input[name="regPasswordConfirm"]').fill(user.password);
  await form.locator('select[name="regCountry"]').selectOption(user.countryCode || 'US');
  await form.locator('button[type="submit"]').click();
  await expect(page.locator('.user-name')).toBeVisible({ timeout: 20_000 });
  return user;
}

export async function getFeaturedSlug(request: APIRequestContext): Promise<string> {
  const game = await getFirstFeaturedGame(request);
  return game.slug as string;
}

export interface FeaturedGame {
  product_id: string;
  slug: string;
  name: string;
  background_image: string | null;
  price: number;
  is_free?: boolean;
}

export async function getFeaturedGames(request: APIRequestContext, limit = 12): Promise<FeaturedGame[]> {
  const res = await request.get(`${API}/store/featured`);
  expect(res.ok()).toBeTruthy();
  const games = await res.json();
  expect(games.length).toBeGreaterThan(0);
  return games.slice(0, limit);
}

export async function getFirstUnclaimedFeaturedGame(
  request: APIRequestContext,
  publisherToken: string,
): Promise<FeaturedGame> {
  const games = await getFeaturedGames(request);
  for (const game of games) {
    const add = await request.post(`${API}/partners/games`, {
      headers: { Authorization: `Bearer ${publisherToken}` },
      data: { product_id: game.product_id, game_name: game.name },
    });
    if (add.ok()) {
      const body = await add.json();
      const claimId = body.partner_game_id as string | undefined;
      if (claimId) {
        await approvePartnerGameClaim(request, claimId);
      }
      return game;
    }
    if (add.status() !== 409) {
      expect(add.ok(), `addGame ${game.product_id}: ${await add.text()}`).toBeTruthy();
    }
  }
  throw new Error('No hay juegos featured disponibles para claim en E2E');
}

/** Admin aprueba ownership (flujo tipo Steamworks). */
export async function approvePartnerGameClaim(
  request: APIRequestContext,
  partnerGameId: string,
): Promise<void> {
  const adminUser = uniqueUser('US');
  const boot = await request.post(`${API}/auth/bootstrap-admin`, {
    data: {
      email: adminUser.email,
      password: adminUser.password,
      secret: process.env.ROLE_BOOTSTRAP_SECRET ?? 'dev_bootstrap_roles',
      country_code: 'US',
    },
  });
  expect(boot.ok(), await boot.text()).toBeTruthy();
  const adminToken = (await boot.json()).token as string;
  const appr = await request.post(`${API}/admin/game-claims/${partnerGameId}/approve`, {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  expect(appr.ok(), await appr.text()).toBeTruthy();
}

export async function getFirstFeaturedGame(request: APIRequestContext): Promise<FeaturedGame> {
  const games = await getFeaturedGames(request, 1);
  return games[0];
}

export async function waitForCartItem(
  request: APIRequestContext,
  token: string,
  productId: string,
  maxMs = 20_000,
) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const res = await request.get(`${API}/cart`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok()) {
      const cart = await res.json();
      const found = (cart.items || []).find(
        (i: { product_id: string }) => i.product_id === productId,
      );
      if (found) return found;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`Item ${productId} no apareció en carrito a tiempo (lag Pinot)`);
}

export async function addToCartViaApi(
  request: APIRequestContext,
  token: string,
  game: FeaturedGame,
) {
  const res = await request.post(`${API}/cart/items`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      product_id: game.product_id,
      game_slug: game.slug,
      game_name: game.name,
      game_image: game.background_image,
      unit_price: game.price ?? 0,
      quantity: 1,
    },
  });
  expect(res.ok(), `addToCart: ${await res.text()}`).toBeTruthy();
  await waitForCartItem(request, token, game.product_id);
}

export async function checkoutViaApi(
  request: APIRequestContext,
  token: string,
  paymentMethod: 'sandbox' | 'wallet' = 'sandbox',
  headers: Record<string, string> = {},
) {
  const res = await request.post(`${API}/checkout`, {
    headers: { Authorization: `Bearer ${token}`, ...headers },
    data: { payment_method: paymentMethod },
  });
  expect(res.ok(), `checkout: ${await res.text()}`).toBeTruthy();
  return res.json();
}

export async function purchaseGameViaApi(
  request: APIRequestContext,
  token: string,
  game: FeaturedGame,
  paymentMethod: 'sandbox' | 'wallet' = 'sandbox',
) {
  await addToCartViaApi(request, token, game);
  return checkoutViaApi(request, token, paymentMethod);
}

export async function waitForLibraryItem(
  request: APIRequestContext,
  token: string,
  productId: string,
  maxMs = 20_000,
) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const res = await request.get(`${API}/library`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok()) {
      const items = await res.json();
      const found = items.find(
        (i: { product_id: string; refunded?: boolean }) =>
          i.product_id === productId && !i.refunded,
      );
      if (found) return found;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error(`Juego ${productId} no apareció en biblioteca a tiempo`);
}

export async function topupWalletViaApi(
  request: APIRequestContext,
  token: string,
  amount = 100,
) {
  const res = await request.post(`${API}/wallet/topup`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { amount },
  });
  expect(res.ok(), `topup: ${await res.text()}`).toBeTruthy();
}

export async function dismissPopups(page: Page) {
  const btn = page.getByRole('button', { name: 'Continuar' });
  if (await btn.isVisible().catch(() => false)) {
    await btn.click();
  }
}
