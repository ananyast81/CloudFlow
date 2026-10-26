import { test, expect } from "@playwright/test";
import { pathToFileURL } from "node:url";

test("upload, durable review, training, charts, inference and artifact download", async ({
  page,
  browser,
}, testInfo) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto("/new-run");
  await expect(
    page.getByRole("heading", { name: "What will you discover?" }),
  ).toBeVisible();
  await page
    .getByLabel("What would you like to predict?")
    .fill(
      "Predict Churn and explain the most influential customer characteristics.",
    );
  await page
    .getByLabel("Upload CSV dataset")
    .setInputFiles("../data/churn.csv");
  await expect(
    page.getByText("Dataset preview", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Target column", { exact: true }).selectOption("Churn");
  await page
    .getByLabel("Problem type", { exact: true })
    .selectOption("classification");
  await page.getByText("Run preferences", { exact: true }).click();
  await page.getByLabel("Improvement rounds").selectOption("0");
  await page.getByRole("button", { name: "Launch analysis" }).click();
  await expect(page).toHaveURL(/\/pipeline\/[a-f0-9]{32}/);
  await expect(
    page.getByRole("heading", { name: "A moment for your review" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "A moment for your review" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Approve & train", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Download the full report" }),
  ).toBeVisible();
  const reportDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download the full report" }).click();
  const reportPath = testInfo.outputPath("standalone", "report.html");
  await (await reportDownload).saveAs(reportPath);
  // Only the HTML is present: no adjacent EDA folder and no network connection.
  const offline = await browser.newContext({ offline: true });
  try {
    const reportPage = await offline.newPage();
    const reportErrors = [];
    reportPage.on("pageerror", (error) => reportErrors.push(error.message));
    await reportPage.goto(pathToFileURL(reportPath).href);
    await expect(reportPage.locator("figure img")).toHaveCount(6);
    await expect
      .poll(() =>
        reportPage
          .locator("figure img")
          .evaluateAll((images) =>
            images.every((image) => image.complete && image.naturalWidth > 0),
          ),
      )
      .toBe(true);
    await expect(reportPage.locator(".js-plotly-plot")).toHaveCount(3);
    await expect(reportPage.locator("body")).not.toContainText("Â·");
    expect(reportErrors).toEqual([]);
  } finally {
    await offline.close();
  }
  await page.getByRole("tab", { name: "Results & diagnostics" }).click();
  await expect(
    page.getByRole("heading", { name: "The experiment leaderboard" }),
  ).toBeVisible();
  await expect(page.locator(".js-plotly-plot").first()).toBeVisible();
  await page.getByRole("tab", { name: "Predict", exact: true }).click();
  await page.getByLabel("Age", { exact: true }).fill("35");
  await page.getByLabel("MonthlyCharges", { exact: true }).fill("89");
  await page.getByLabel("Contract", { exact: true }).fill("Monthly");
  await page.getByRole("button", { name: "Predict Churn" }).click();
  await expect(page.locator(".prediction-result")).toBeVisible();
  await page.getByRole("tab", { name: /Artifacts/ }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download all", exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/^cloudflow-.*\.zip$/);
  await page.getByRole("link", { name: "Run history", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "churn.csv", exact: true }).first(),
  ).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("mobile page has no horizontal overflow and invalid uploads are explained", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/new-run");
  await expect(
    page.getByRole("heading", { name: "What will you discover?" }),
  ).toBeVisible();
  await page.getByLabel("Upload CSV dataset").setInputFiles({
    name: "invalid.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("a,b\n1,2"),
  });
  await expect(page.getByRole("alert")).toContainText("Choose a CSV file.");
  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflows).toBe(false);
});
