import { test, expect } from "@playwright/test";

test("live signed-in Codex selects real application tools", async ({
  page,
  request,
}) => {
  test.skip(
    process.env.RUN_CODEX_LIVE !== "1",
    "Explicit opt-in required: this consumes the signed-in Codex plan allowance.",
  );
  test.setTimeout(130000);
  const health = await (
    await request.get("http://127.0.0.1:8000/api/health")
  ).json();
  expect(health.codex_configured).toBe(true);
  const rid = process.env.LASTMILE_LIVE_RUN;
  if (rid)
    await page.addInitScript(
      (id) => localStorage.setItem("lastmile-run", id),
      rid,
    );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.getByText("FalkorDB connected")).toBeVisible();
  if (!rid)
    await page.getByRole("button", { name: "Create first run" }).click();
  await page
    .getByRole("combobox", { name: "Controller mode" })
    .selectOption("codex");
  const resultPromise = page.waitForResponse(
    (r) => r.url().endsWith("/cycle") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "One decision" }).click();
  const result = await (await resultPromise).json();
  expect(result.completed).toBe(true);
  expect(result.model).toBeTruthy();
  expect(
    result.calls.some((c: any) => c.tool === "get_operational_context"),
  ).toBe(true);
  expect(result.calls.some((c: any) => c.tool === "advance_simulation")).toBe(
    true,
  );
  await expect(
    page.getByRole("button", { name: "One decision" }),
  ).toBeEnabled();
  await expect(page.locator(".timeline")).toContainText("Codex · ChatGPT plan");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../docs/screenshots/05-live-codex-desktop.png",
    fullPage: true,
  });
});
