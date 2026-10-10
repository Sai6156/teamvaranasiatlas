/* UI-only fixtures: no model calls, signup emails or database mutations. */
const fs = require("fs");
const assert = require("node:assert/strict");
const {
  chromium,
} = require("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fixtures = JSON.parse(
  fs.readFileSync(".runtime/premium-ui-fixtures.json", "utf8"),
);
const live = process.argv.includes("--live");
const origin = live
  ? "https://atlas-varanasi.vercel.app"
  : "http://127.0.0.1:3001";

async function main() {
  const browser = await chromium.launch({
    executablePath:
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    headless: true,
    args: ["--host-resolver-rules=MAP atlas-varanasi.vercel.app 216.198.79.67"],
  });
  const errors = [];
  let modelRequests = 0;
  try {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(origin, { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Travel", exact: true }).click();
    assert.match(await page.locator(".preview-answer").innerText(), /14 days/);
    await page.getByRole("button", { name: "Inspect example source" }).click();
    await page
      .getByText("Fictional starter data for this interactive preview.", {
        exact: true,
      })
      .waitFor();
    await page
      .getByRole("button", { name: "Engineering", exact: true })
      .click();
    assert.match(
      await page.locator(".preview-answer").innerText(),
      /team lead/,
    );
    await page.getByRole("button", { name: "First day", exact: true }).click();
    await page.screenshot({ path: ".runtime/premium-landing-desktop.png" });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await page.screenshot({
      path: ".runtime/premium-landing-mobile.png",
      fullPage: true,
    });
    await context.close();
    const appContext = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
    });
    const expiry = Math.floor(Date.now() / 1000) + 7200;
    const user = {
      id: "11111111-1111-4111-8111-111111111111",
      email: "design-fixture@example.test",
      aud: "authenticated",
      role: "authenticated",
      app_metadata: { provider: "email", providers: ["email"] },
      user_metadata: { full_name: "Design reviewer" },
      email_confirmed_at: "2026-10-10T00:00:00Z",
      created_at: "2026-10-10T00:00:00Z",
    };
    const token = [
      Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString(
        "base64url",
      ),
      Buffer.from(
        JSON.stringify({
          sub: user.id,
          aud: "authenticated",
          role: "authenticated",
          exp: expiry,
        }),
      ).toString("base64url"),
      "design-fixture-signature",
    ].join(".");
    await appContext.addInitScript(
      ({ session }) =>
        localStorage.setItem(
          "sb-ttepdvbmvndxkpprsoih-auth-token",
          JSON.stringify(session),
        ),
      {
        session: {
          user,
          access_token: token,
          refresh_token: "design-fixture-refresh",
          expires_at: expiry,
          expires_in: 7200,
          token_type: "bearer",
        },
      },
    );
    await appContext.route(
      "https://ttepdvbmvndxkpprsoih.supabase.co/**",
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(user),
          headers: { "Access-Control-Allow-Origin": origin },
        }),
    );
    await appContext.route(
      "https://atlas-varanasi-api.onrender.com/**",
      async (route) => {
        const r = route.request(),
          url = new URL(r.url()),
          parts = url.pathname.split("/");
        let body = [];
        if (url.pathname === "/workspaces") body = fixtures.workspaces;
        else if (url.pathname.endsWith("/documents")) {
          await new Promise((resolve) => setTimeout(resolve, 750));
          body = fixtures.documents[parts[2]] || [];
        } else if (url.pathname.endsWith("/chat")) {
          modelRequests++;
          return route.fulfill({
            status: 200,
            contentType: "text/event-stream",
            headers: { "Access-Control-Allow-Origin": origin },
            body: 'data: {"type":"conversation","id":"test-conversation"}\n\ndata: {"type":"token","text":"UI routing fixture response"}\n\ndata: {"type":"done","citations":[],"model":"test/mock"}\n\n',
          });
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          headers: {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
          },
          body: JSON.stringify(body),
        });
      },
    );
    const app = await appContext.newPage();
    app.on("pageerror", (e) => errors.push(e.message));
    await app.goto(origin + "/app", { waitUntil: "domcontentloaded" });
    await app.getByRole("heading", { name: /Ten companies/ }).waitFor();
    assert.equal(await app.locator(".demo-company-card").count(), 10);
    await app.screenshot({
      path: ".runtime/premium-company-gallery.png",
      fullPage: true,
    });
    await app
      .locator(".demo-company-card")
      .filter({
        has: app.getByRole("heading", {
          name: "Reliance Industries",
          exact: true,
        }),
      })
      .click();
    await app
      .getByRole("status")
      .filter({ hasText: "Opening your knowledge library" })
      .waitFor();
    await app
      .getByText("All documents are up to date", { exact: true })
      .waitFor();
    await app
      .locator(".app-nav")
      .getByRole("button", { name: "Ask Atlas", exact: true })
      .click();
    const picker = app.getByRole("combobox", {
      name: "Demo company files",
      exact: true,
    });
    await picker.selectOption(
      fixtures.workspaces.find((w) => w.demo_slug === "microsoft").id,
    );
    await app.locator(".demo-chat-question").first().waitFor();
    assert.equal(await app.locator(".demo-chat-question").count(), 4);
    await app.locator(".demo-chat-question").first().click();
    assert.ok(
      (
        await app
          .getByRole("textbox", { name: "Your question", exact: true })
          .inputValue()
      ).length > 20,
    );
    assert.equal(modelRequests, 0);
    await app
      .getByRole("textbox", { name: "Your question", exact: true })
      .fill("");
    await app.screenshot({ path: ".runtime/premium-chat-desktop.png" });
    await app.setViewportSize({ width: 390, height: 844 });
    await app.waitForFunction(
      () =>
        document.querySelector(".sidebar").getBoundingClientRect().right <= 0,
    );
    assert.equal(
      await app.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await app.screenshot({ path: ".runtime/premium-chat-mobile.png" });
    await app.emulateMedia({ reducedMotion: "reduce" });
    const animation = await app
      .locator(".workspace-content")
      .evaluate((el) => getComputedStyle(el).animationName);
    assert.equal(animation, "none");
    await appContext.close();
    assert.deepEqual(errors, []);
    const result = {
      interactive_preview: true,
      example_source_toggle: true,
      ten_company_gallery: true,
      loading_state: true,
      four_local_questions: true,
      desktop_and_mobile: true,
      reduced_motion: true,
      page_errors: 0,
      paid_model_requests: 0,
    };
    fs.writeFileSync(
      "demo-data/premium-ui-checks.json",
      JSON.stringify(result, null, 2),
    );
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
