import { test, expect } from '@playwright/test';
import { API, registerViaApi, uniqueUser } from './helpers';

const BOOTSTRAP_SECRET = process.env.ROLE_BOOTSTRAP_SECRET ?? 'dev_bootstrap_roles';

/**
 * Fase 0 — roles: player / publisher / admin
 */

test.describe('Fase 0 · roles', () => {
  test('registro crea rol player', async ({ request }) => {
    const { token, user, role } = await registerViaApi(request, uniqueUser('US'));
    expect(role).toBe('player');
    const profile = await request.get(`${API}/auth/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(profile.ok(), await profile.text()).toBeTruthy();
    const body = await profile.json();
    expect(body.role).toBe('player');
    expect(body.email).toBe(user.email.toLowerCase());
  });

  test('player no puede acceder a /admin/health', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const res = await request.get(`${API}/admin/health`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(403);
  });

  test('registrar partner asigna rol publisher y permite mutaciones', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const reg = await request.post(`${API}/partners/register`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { company_name: 'E2E Studio Roles' },
    });
    expect(reg.ok(), await reg.text()).toBeTruthy();
    const regBody = await reg.json();
    expect(regBody.role).toBe('publisher');

    const profile = await request.get(`${API}/auth/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect((await profile.json()).role).toBe('publisher');

    const add = await request.post(`${API}/partners/games`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        product_id: `e2e_role_${Date.now().toString(36)}`,
        game_name: 'Role Test Game',
      },
    });
    expect(add.ok(), await add.text()).toBeTruthy();
  });

  test('player sin partner no puede añadir juegos', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const add = await request.post(`${API}/partners/games`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { product_id: 'x', game_name: 'Nope' },
    });
    expect(add.status()).toBe(403);
  });

  test('bootstrap-admin crea admin y accede a /admin/health', async ({ request }) => {
    const u = uniqueUser('US');
    const boot = await request.post(`${API}/auth/bootstrap-admin`, {
      data: {
        email: u.email,
        password: u.password,
        display_name: 'E2E Admin',
        secret: BOOTSTRAP_SECRET,
        country_code: 'US',
      },
    });
    expect(boot.ok(), await boot.text()).toBeTruthy();
    const body = await boot.json();
    expect(body.user.role).toBe('admin');
    expect(body.token).toBeTruthy();

    const health = await request.get(`${API}/admin/health`, {
      headers: { Authorization: `Bearer ${body.token}` },
    });
    expect(health.ok(), await health.text()).toBeTruthy();
    const h = await health.json();
    expect(h.ok).toBeTruthy();
    expect(h.role).toBe('admin');
  });

  test('admin puede promover player a publisher', async ({ request }) => {
    const player = await registerViaApi(request);
    const adminUser = uniqueUser('US');
    const boot = await request.post(`${API}/auth/bootstrap-admin`, {
      data: {
        email: adminUser.email,
        password: adminUser.password,
        secret: BOOTSTRAP_SECRET,
        country_code: 'US',
      },
    });
    expect(boot.ok(), await boot.text()).toBeTruthy();
    const adminToken = (await boot.json()).token as string;

    const setRole = await request.put(`${API}/admin/users/${player.userId}/role`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: { role: 'publisher' },
    });
    expect(setRole.ok(), await setRole.text()).toBeTruthy();
    expect((await setRole.json()).role).toBe('publisher');

    const profile = await request.get(`${API}/auth/profile`, {
      headers: { Authorization: `Bearer ${player.token}` },
    });
    expect((await profile.json()).role).toBe('publisher');
  });

  test('UI admin: panel visible; player redirigido desde /admin', async ({ page, request }) => {
    const u = uniqueUser('US');
    const bootRes = await request.post(`${API}/auth/bootstrap-admin`, {
      data: {
        email: u.email,
        password: u.password,
        display_name: 'UI Admin',
        secret: BOOTSTRAP_SECRET,
        country_code: 'US',
      },
    });
    expect(bootRes.ok()).toBeTruthy();
    const boot = await bootRes.json();

    await page.goto('/store');
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem('gamemetrics_token', token);
        localStorage.setItem('gamemetrics_user', JSON.stringify(user));
      },
      { token: boot.token as string, user: boot.user },
    );
    await page.goto('/admin');
    await expect(page.getByRole('heading', { name: /Admin GameMetrics/i })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText(/Panel admin operativo/i)).toBeVisible();

    const player = await registerViaApi(request);
    await page.evaluate(
      ({ token, user, role }) => {
        localStorage.setItem('gamemetrics_token', token);
        localStorage.setItem(
          'gamemetrics_user',
          JSON.stringify({
            id: user,
            email: 'p@test',
            display_name: 'Player',
            avatar: null,
            bio: null,
            role,
          }),
        );
      },
      { token: player.token, user: player.userId, role: 'player' },
    );
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/store/, { timeout: 15_000 });
  });

  test('UI player: no ve Dashboard ETL; / redirige a tienda', async ({ page, request }) => {
    const player = await registerViaApi(request);
    await page.goto('/store');
    await page.evaluate(
      ({ token, userId, email, name, role }) => {
        localStorage.setItem('gamemetrics_token', token);
        localStorage.setItem(
          'gamemetrics_user',
          JSON.stringify({
            id: userId,
            email,
            display_name: name,
            avatar: null,
            bio: null,
            role,
          }),
        );
      },
      {
        token: player.token,
        userId: player.userId,
        email: player.user.email,
        name: player.user.displayName,
        role: 'player',
      },
    );
    await page.goto('/');
    await expect(page).toHaveURL(/\/store/, { timeout: 15_000 });
    await expect(page.getByText(/PIPELINE DE DATOS/i)).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Empresa', exact: true })).toHaveCount(0);
  });
});
