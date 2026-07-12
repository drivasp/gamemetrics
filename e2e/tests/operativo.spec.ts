import { test, expect } from '@playwright/test';
import {
  API,
  getFeaturedSlug,
  loginViaUi,
  registerViaApi,
  registerViaUi,
  uniqueUser,
} from './helpers';

/**
 * Casos de uso operativos (OpenSpec 003) como historias de usuario reales.
 * Requiere stack Docker: frontend :4000, backend :8080, Pinot con semana 1+ cargada.
 */

test.beforeAll(async ({ request }) => {
  const health = await request.get(`${API}/store/featured`);
  expect(health.ok(), 'Backend/Pinot no responde en /store/featured').toBeTruthy();
  const games = await health.json();
  expect(games.length, 'Sin juegos en Pinot — ejecuta ETL semana 1').toBeGreaterThan(0);
});

test.describe('CU-O01 · US-AUTH-001 — Registro de visitante', () => {
  test('Como visitante quiero crear una cuenta para acceder a wishlist y carrito', async ({ page }) => {
    const user = await registerViaUi(page);
    await expect(page.locator('.user-name')).toContainText(user.displayName);
  });
});

test.describe('CU-O02 · US-AUTH-002 — Inicio de sesión', () => {
  test('Como visitante registrado quiero iniciar sesión con email y contraseña', async ({ page, request }) => {
    const { user } = await registerViaApi(request);
    await loginViaUi(page, user.email, user.password);
  });
});

test.describe('CU-O06 · Home de tienda (destacados)', () => {
  test('Como visitante quiero ver juegos destacados en la home de la tienda', async ({ page }) => {
    await page.goto('/store');
    await expect(page.locator('.loading-full')).toBeHidden({ timeout: 60_000 });
    await expect(
      page.locator('.spotlight, .section-title, app-game-card, app-game-cover').first(),
    ).toBeVisible({ timeout: 60_000 });
  });
});

test.describe('CU-O07 · Catálogo con paginación', () => {
  test('Como visitante quiero navegar el catálogo y pasar a la página 2 sin errores', async ({ page }) => {
    await page.goto('/store/catalog');
    await expect(page.locator('.games-grid app-game-card').first()).toBeVisible({ timeout: 30_000 });
    const page2 = page.locator('.pagination .page-btn', { hasText: '2' });
    if (await page2.isVisible()) {
      await page2.click();
      await expect(page.locator('.games-grid app-game-card').first()).toBeVisible({ timeout: 30_000 });
      await expect(page.locator('.catalog-error')).toHaveCount(0);
    }
  });
});

test.describe('CU-O08 · Detalle de juego', () => {
  test('Como visitante quiero ver la ficha de un juego desde el catálogo', async ({ page, request }) => {
    const slug = await getFeaturedSlug(request);
    const detail = await request.get(`${API}/store/games/${slug}`);
    expect(detail.ok()).toBeTruthy();
    const game = await detail.json();

    await page.goto(`/store/game/${slug}`);
    await expect(page.getByRole('heading', { name: game.name })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: /Añadir al carro|Ver carrito/ })).toBeVisible();
  });
});

test.describe('CU-O14 · Wishlist — agregar juego', () => {
  test('Como usuario registrado quiero guardar un juego en mi lista de deseos', async ({ page, request }) => {
    const { user } = await registerViaApi(request);
    const slug = await getFeaturedSlug(request);
    await loginViaUi(page, user.email, user.password);
    await page.goto(`/store/game/${slug}`);
    await page.getByRole('button', { name: 'Agregar a Wishlist' }).click();
    await expect(page.getByRole('button', { name: 'En tu wishlist' })).toBeVisible({ timeout: 15_000 });
    await page.goto('/profile');
    await expect(page.getByRole('heading', { name: 'Mi lista de deseados' })).toBeVisible();
    await expect(page.locator('.wishlist-card').first()).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('CU-O18 · Carrito — agregar juego (precio coherente)', () => {
  test('Como usuario registrado quiero añadir un juego al carrito sin error de precio desactualizado', async ({ page, request }) => {
    page.on('dialog', (d) => {
      throw new Error(`Diálogo inesperado: ${d.message()}`);
    });

    const { user } = await registerViaApi(request);
    const slug = await getFeaturedSlug(request);
    await loginViaUi(page, user.email, user.password);
    await page.goto(`/store/game/${slug}`);

    const addBtn = page.getByRole('button', { name: 'Añadir al carro' });
    await expect(addBtn).toBeVisible({ timeout: 15_000 });
    await addBtn.click();

    await expect(page.getByRole('button', { name: 'Ver carrito' })).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('CU-O19 · Carrito — ver contenido', () => {
  test('Como usuario registrado quiero ver los juegos que agregué al carrito', async ({ page, request }) => {
    const { user, token } = await registerViaApi(request);
    const featured = await request.get(`${API}/store/featured`);
    const game = (await featured.json())[0];

    await request.post(`${API}/cart/items`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        product_id: game.product_id,
        game_slug: game.slug,
        game_name: game.name,
        game_image: game.background_image,
        unit_price: 0,
        quantity: 1,
      },
    });

    await loginViaUi(page, user.email, user.password);
    await page.goto('/my-cart');
    await expect(page.locator('body')).toContainText(game.name, { timeout: 15_000 });
  });
});

test.describe('Navegación · Dashboard ↔ Tienda', () => {
  test('Como administrador ETL quiero volver al dashboard desde la tienda', async ({ page }) => {
    await page.goto('/store/catalog');
    await page.getByRole('link', { name: /Volver al Dashboard/i }).click();
    await expect(page).toHaveURL(/\/(\?.*)?$/);
    await expect(page.getByText('Dataset Principal')).toBeVisible({ timeout: 10_000 });
  });

  test('La ruta raíz carga el dashboard aunque haya visitado la tienda antes', async ({ page }) => {
    await page.goto('/store');
    await page.goto('/');
    await expect(page.getByText('Panel ETL')).toBeVisible({ timeout: 10_000 });
  });
});

test.describe('CU-O03-a · Perfil propio', () => {
  test('Como usuario registrado quiero ver mi perfil tras iniciar sesión', async ({ page, request }) => {
    const { user } = await registerViaApi(request);
    await loginViaUi(page, user.email, user.password);
    await page.goto('/profile');
    await expect(page.locator('body')).toContainText(user.email);
  });
});

test.describe('CU-O11 · Buscar juego por nombre', () => {
  test('Como visitante quiero buscar un título concreto en el catálogo para encontrarlo rápido', async ({ page, request }) => {
    const featured = await request.get(`${API}/store/featured`);
    const game = (await featured.json())[0];

    await page.goto('/store/catalog');
    await page.locator('.search-input').fill(game.name.slice(0, 12));
    await page.waitForTimeout(600);
    await expect(page.locator('.games-grid app-game-card').first()).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('.games-grid')).toContainText(game.name.slice(0, 8));
  });
});

test.describe('CU-O12 · Filtrar juegos gratis', () => {
  test('Como visitante quiero ver solo juegos gratuitos para probar sin pagar', async ({ page }) => {
    await page.goto('/store/catalog');
    await page.getByRole('button', { name: 'Gratis' }).click();
    await expect(page.locator('.games-grid app-game-card').first()).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('.games-grid')).toContainText('GRATIS');
  });
});

test.describe('CU-O17 · Wishlist — quitar juego', () => {
  test('Como usuario registrado quiero quitar un juego de mi lista cuando ya no me interesa', async ({ page, request }) => {
    const { user, token } = await registerViaApi(request);
    const slug = await getFeaturedSlug(request);
    const detail = await request.get(`${API}/store/games/${slug}`);
    const game = await detail.json();

    await request.post(`${API}/user/wishlist`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        game_slug: slug,
        game_name: game.name,
        game_image: game.background_image,
        game_price: game.price,
      },
    });

    await loginViaUi(page, user.email, user.password);
    await page.goto('/profile');
    await expect(page.locator('.wishlist-card').first()).toBeVisible({ timeout: 15_000 });
    await page.locator('.btn-remove').first().click();
    await expect(page.getByText('Tu wishlist está vacía.')).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('Historia · De la wishlist al carrito', () => {
  test('Como comprador registrado quiero guardar un juego y luego añadirlo al carrito cuando decido comprarlo', async ({ page, request }) => {
    page.on('dialog', (d) => {
      throw new Error(`Diálogo inesperado: ${d.message()}`);
    });

    const { user } = await registerViaApi(request);
    const slug = await getFeaturedSlug(request);
    await loginViaUi(page, user.email, user.password);

    await page.goto(`/store/game/${slug}`);
    await page.getByRole('button', { name: 'Agregar a Wishlist' }).click();
    await expect(page.getByRole('button', { name: 'En tu wishlist' })).toBeVisible({ timeout: 15_000 });

    await page.getByRole('button', { name: 'Añadir al carro' }).click();
    await expect(page.getByRole('button', { name: 'Ver carrito' })).toBeVisible({ timeout: 15_000 });

    await page.goto('/my-cart');
    const detail = await request.get(`${API}/store/games/${slug}`);
    const game = await detail.json();
    await expect(page.locator('body')).toContainText(game.name, { timeout: 15_000 });
  });
});

test.describe('CU-O02 · Cerrar sesión', () => {
  test('Como usuario registrado quiero cerrar sesión para proteger mi cuenta en un equipo compartido', async ({ page, request }) => {
    const { user } = await registerViaApi(request);
    await loginViaUi(page, user.email, user.password);
    await page.goto('/profile');
    await page.getByRole('button', { name: 'Cerrar sesión' }).click();
    await expect(page).toHaveURL(/\/store/);
    await expect(page.getByRole('button', { name: 'Iniciar sesión', exact: true })).toBeVisible();
  });
});

test.describe('Carrito · contador en popup', () => {
  test('Al añadir un juego el popup muestra de inmediato la cantidad correcta en el carrito', async ({ page, request }) => {
    page.on('dialog', (d) => d.dismiss());

    const { user } = await registerViaApi(request);
    const slug = await getFeaturedSlug(request);
    await loginViaUi(page, user.email, user.password);
    await page.goto(`/store/game/${slug}`);

    await page.getByRole('button', { name: 'Añadir al carro' }).click();
    await expect(page.getByRole('button', { name: /Ver mi carro \(1\)/ })).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('CU-O22/O23 · Compra sandbox → biblioteca', () => {
  test('Como comprador quiero pagar con sandbox y ver el juego en mi biblioteca', async ({ page, request }) => {
    page.on('dialog', (d) => d.dismiss());

    const { user, token } = await registerViaApi(request);
    const featured = await request.get(`${API}/store/featured`);
    const game = (await featured.json())[0];

    await request.post(`${API}/cart/items`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        product_id: game.product_id,
        game_slug: game.slug,
        game_name: game.name,
        game_image: game.background_image,
        unit_price: 0,
        quantity: 1,
      },
    });

    await loginViaUi(page, user.email, user.password);
    await page.goto('/payment');
    await expect(page.getByRole('heading', { name: 'Continuar al pago' })).toBeVisible({ timeout: 15_000 });
    await page.getByLabel('Pago inmediato (sandbox)').check();
    await page.getByRole('button', { name: 'Completar compra' }).click();
    await expect(page).toHaveURL(/\/my-library/, { timeout: 30_000 });
    await expect(page.locator('body')).toContainText(game.name, { timeout: 30_000 });
  });
});

test.describe('Cartera · recarga sandbox y pago', () => {
  test('Como comprador quiero recargar la cartera y pagar con saldo', async ({ page, request }) => {
    page.on('dialog', (d) => d.dismiss());

    const { user, token } = await registerViaApi(request);
    const featured = await request.get(`${API}/store/featured`);
    const game = (await featured.json())[0];

    const topup = await request.post(`${API}/wallet/topup`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { amount: 100 },
    });
    expect(topup.ok(), `topup failed: ${await topup.text()}`).toBeTruthy();

    await request.post(`${API}/cart/items`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        product_id: game.product_id,
        game_slug: game.slug,
        game_name: game.name,
        game_image: game.background_image,
        unit_price: 0,
        quantity: 1,
      },
    });

    await loginViaUi(page, user.email, user.password);
    await page.goto('/my-wallet');
    await expect(page.locator('.amount')).toContainText('$100', { timeout: 15_000 });

    await page.goto('/payment');
    await page.getByLabel('Cartera GameMetrics').check();
    await page.getByRole('button', { name: 'Pagar con cartera' }).click();
    await expect(page).toHaveURL(/\/my-library/, { timeout: 30_000 });
    await expect(page.locator('body')).toContainText(game.name, { timeout: 30_000 });
  });
});

test.describe('HU-O-COMPRA-003 · Reembolso sandbox', () => {
  test('Como comprador quiero reembolsar un juego reciente sin error Not Found', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const featured = await request.get(`${API}/store/featured`);
    const game = (await featured.json())[0];

    await request.post(`${API}/cart/items`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        product_id: game.product_id,
        game_slug: game.slug,
        game_name: game.name,
        game_image: game.background_image,
        unit_price: 0,
        quantity: 1,
      },
    });

    const checkout = await request.post(`${API}/checkout`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { payment_method: 'sandbox' },
    });
    expect(checkout.ok(), `checkout: ${await checkout.text()}`).toBeTruthy();

    await new Promise((r) => setTimeout(r, 2000));
    const library = await request.get(`${API}/library`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const purchase = (await library.json()).find(
      (i: { product_id: string }) => i.product_id === game.product_id,
    );
    expect(purchase).toBeTruthy();

    const refund = await request.post(`${API}/refunds`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { purchase_id: purchase.purchase_id, reason: 'No funciona en mi equipo' },
    });
    expect(refund.ok(), `refund: ${await refund.text()}`).toBeTruthy();
    const body = await refund.json();
    expect(body.status).toBe('approved');
  });
});
