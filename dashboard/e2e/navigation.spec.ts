import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  page.on('console', msg => console.log(`BROWSER LOG: ${msg.text()}`));
  page.on('pageerror', err => console.log(`BROWSER ERROR: ${err}`));
});

test('has title', async ({ page }) => {
  await page.goto('/');
  const title = await page.title();
  console.log('Current URL:', page.url());
  console.log('Current Title:', title);
  
  if (!title) {
    console.log('PAGE CONTENT:', await page.content());
  }

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/ENEM Data Robotics – Dashboard/);
});

test('authentication flow and navigation', async ({ page }) => {
  // 1. Go to root (redirects to /login)
  await page.goto('/');
  await expect(page).toHaveURL(/.*\/login/);

  // 2. Create a new account (since DB is fresh)
  await page.getByRole('link', { name: 'Cadastre-se' }).click();
  await expect(page).toHaveURL(/.*\/signup/);

  const uniqueEmail = `test_${Date.now()}@example.com`;
  await page.getByLabel('E-mail').fill(uniqueEmail);
  // Fix: Use exact match for 'Senha' to avoid ambiguity with 'Confirmar Senha'
  await page.getByLabel('Senha', { exact: true }).fill('TestPassword123!');
  await page.getByLabel('Confirmar Senha').fill('TestPassword123!');
  await page.getByRole('button', { name: 'Cadastrar' }).click();

  // 3. Expect redirect to login and success message
  await expect(page).toHaveURL(/.*\/login/);
  // Optional: check for toast "Conta criada com sucesso!" if feasible

  // 4. Login
  await page.getByLabel('E-mail').fill(uniqueEmail);
  await page.getByLabel('Senha', { exact: true }).fill('TestPassword123!');
  await page.getByRole('button', { name: 'Entrar' }).click();

  // 5. Expect redirect to dashboard
  await expect(page).toHaveURL(/.*\/dashboard/);
  
  // 6. Check Dashboard content
  await expect(page.getByText('Estatísticas Gerais')).toBeVisible();

  // 7. Navigate to Advanced Explorer
  await page.getByText('Explorador Avançado').click();
  
  // Verify URL or content
  await expect(page.getByRole('heading', { name: 'Explorador Avançado' })).toBeVisible();
});
