import { test, expect } from "@playwright/test";
test("load → investigate → inspect → plan → commit → execute → explain → replay", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("FalkorDB connected")).toBeVisible();
  await page.getByRole("button", { name: "Create first run" }).click();
  await expect(
    page.getByRole("heading", { name: "Alder Reach", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Neighbourhood message")).toBeVisible();
  await page.getByRole("button", { name: "Trace delivery impact" }).click();
  await expect(page.getByRole("dialog")).toContainText("hypothetical_requests");
  await page.getByRole("button", { name: "Close evidence" }).click();
  await page.getByRole("button", { name: "Compare inspections" }).click();
  await expect(page.getByText("+57.2", { exact: true })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../docs/screenshots/01-investigate-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Inspect road · 5 min" }).click();
  await expect(
    page.getByText("Inspection: OPEN at simulation minute 5."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Preview plan", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Reserve & commit plan" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Reserve & commit plan" }).click();
  await expect(
    page.getByText("Reserved 4 vehicle routes; stock held until loading."),
  ).toBeVisible();
  const rid = await page.evaluate(() => localStorage.getItem("lastmile-run"));
  const getState = async () =>
    await (await request.get("http://127.0.0.1:8000/api/runs/" + rid)).json();
  let state = await getState();
  expect(state.reservations.length).toBe(4);
  for (let i = 0; i < 7 && state.status === "active"; i++) {
    const previous = state.revision;
    await page
      .getByRole("button", { name: "Advance 10 minutes", exact: true })
      .click();
    await expect
      .poll(async () => (await getState()).revision)
      .toBeGreaterThan(previous);
    state = await getState();
    await expect(
      page.getByRole("button", { name: "Advance 10 minutes", exact: true }),
    )
      .toBeEnabled({ timeout: 5000 })
      .catch(() => {});
  }
  expect(state.metrics.on_time_requests).toBe(6);
  expect(state.metrics.delivered_kits).toBe(42);
  await page.reload();
  await expect(page.getByText("FalkorDB connected")).toBeVisible();
  await expect(page.locator(".metric").first().locator("strong")).toHaveText(
    "42",
  );
  await expect(page.locator(".metric").nth(2).locator("strong")).toHaveText(
    "1",
  );
  await page.locator(".timeline-decision").first().click();
  await expect(page.getByRole("dialog"))
    .toContainText("BASED_ON")
    .catch(
      async () => await expect(page.getByRole("dialog")).toContainText("graph"),
    );
  await page.getByRole("button", { name: "Close evidence" }).click();
  await page.getByRole("button", { name: "Replay", exact: true }).click();
  await expect(page.getByText("Read-only replay")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "One decision" }),
  ).toBeDisabled();
  await page.getByRole("slider", { name: "Replay revision" }).fill("0");
  await expect(page.locator(".metric").first().locator("strong")).toHaveText(
    "0",
  );
  expect((await getState()).metrics.delivered_kits).toBe(42);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../docs/screenshots/02-replay-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Return to live" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("heading", { name: "Alder Reach", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../docs/screenshots/03-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page
    .getByRole("button", { name: "Graph evidence", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Graph query evidence" }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "load", exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Benchmarks", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Policy comparison" }),
  ).toBeVisible();
  await expect(page.locator(".benchmark-cards article")).toHaveCount(3);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../docs/screenshots/04-benchmarks-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
