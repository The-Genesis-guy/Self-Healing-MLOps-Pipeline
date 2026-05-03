import { expect, test } from '@playwright/test';

test.describe('Dashboard UI smoke tests', () => {
  test('loads the operations dashboard and key controls', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'Operations Dashboard' })).toBeVisible();
    await expect(page.getByText('Live pipeline health, drift, registry status, and control actions.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Start Pipeline' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Logs' })).toBeVisible();
    await expect(page.getByText('Pipeline is stopped')).toBeVisible();
  });

  test('navigates to the logs section', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('button', { name: 'Logs' }).click();

    await expect(page.getByRole('heading', { name: 'Recent Activity', level: 2 })).toBeVisible();
    await expect(page.getByText('Timeline of pipeline actions and the latest state changes.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Runtime Context', level: 2 })).toBeVisible();
  });
});
