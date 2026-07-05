import { APIRequestContext, Page, expect } from '@playwright/test';

export const API = process.env.E2E_API_URL ?? 'http://localhost:8080';

export function uniqueUser() {
  const id = Date.now().toString(36);
  return {
    email: `e2e.${id}@gamemetrics.test`,
    password: 'TestPass123!',
    displayName: `E2E User ${id}`,
  };
}

export async function registerViaApi(request: APIRequestContext, user = uniqueUser()) {
  const res = await request.post(`${API}/auth/register`, {
    data: {
      email: user.email,
      password: user.password,
      display_name: user.displayName,
    },
  });
  expect(res.ok(), `register failed: ${await res.text()}`).toBeTruthy();
  const body = await res.json();
  return { user, token: body.token as string };
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

export async function registerViaUi(page: Page, user = uniqueUser()) {
  await page.goto('/store');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await page.locator('.modal-tabs').getByRole('button', { name: 'Registrarse' }).click();
  const form = page.locator('form.modal-form').filter({ has: page.locator('input[name="regEmail"]') });
  await form.locator('input[name="regDisplayName"]').fill(user.displayName);
  await form.locator('input[name="regEmail"]').fill(user.email);
  await form.locator('input[name="regPassword"]').fill(user.password);
  await form.locator('input[name="regPasswordConfirm"]').fill(user.password);
  await form.locator('button[type="submit"]').click();
  await expect(page.locator('.user-name')).toBeVisible({ timeout: 20_000 });
  return user;
}

export async function getFeaturedSlug(request: APIRequestContext): Promise<string> {
  const res = await request.get(`${API}/store/featured`);
  expect(res.ok()).toBeTruthy();
  const games = await res.json();
  expect(games.length).toBeGreaterThan(0);
  return games[0].slug as string;
}
