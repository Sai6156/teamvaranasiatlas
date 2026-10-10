/* Browser routing regression. Synthetic SSE avoids model charges during UI tests. */
const fs = require("fs");
const assert = require("node:assert/strict");
const { randomUUID } = require("node:crypto");
const {
  chromium,
} = require("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

async function main() {
  const state = JSON.parse(fs.readFileSync(".runtime/demo-qa.json", "utf8"));
  const account = state.users[0];
  const companies = state.workspaces.filter((w) => w.is_demo);
  const browser = await chromium.launch({
    executablePath:
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    headless: true,
    args: [
      "--host-resolver-rules=MAP atlas-varanasi.vercel.app 216.198.79.67,MAP atlas-varanasi-api.onrender.com 216.24.57.16,MAP ttepdvbmvndxkpprsoih.supabase.co 104.18.38.10",
    ],
  });
  try {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (response.url().includes("atlas-varanasi-api.onrender.com"))
        console.log(
          JSON.stringify({
            api_status: response.status(),
            path: new URL(response.url()).pathname,
          }),
        );
    });
    if (process.argv.includes("--local")) {
      // Keep the real app origin and API CORS policy while testing the local build.
      await page.route(
        "https://atlas-varanasi.vercel.app/**",
        async (route) => {
          const url = new URL(route.request().url());
          const response = await route.fetch({
            url: "http://127.0.0.1:3001" + url.pathname + url.search,
          });
          await route.fulfill({ response });
        },
      );
    }
    const requests = [];
    const created = {};
    await page.route("**/workspaces/*/chat", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      const org = route.request().url().split("/workspaces/")[1].split("/")[0];
      const payload = route.request().postDataJSON();
      requests.push({ org, payload });
      const id = payload.conversation_id || randomUUID();
      created[org] ||= id;
      await new Promise((resolve) => setTimeout(resolve, 500));
      const events = [
        { type: "conversation", id },
        { type: "token", text: "Synthetic routing answer " + org },
        { type: "done", citations: [], model: "test/mock" },
      ];
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: {
          "Access-Control-Allow-Origin": "https://atlas-varanasi.vercel.app",
        },
        body: events
          .map((event) => "data: " + JSON.stringify(event) + "\n\n")
          .join(""),
      });
    });
    await page.goto("https://atlas-varanasi.vercel.app/login", {
      waitUntil: "domcontentloaded",
    });
    await page.getByLabel("Work email").fill(account.email);
    await page
      .locator('input[autocomplete="current-password"]')
      .fill(account.password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page.waitForURL("**/app");
    await page
      .getByRole("combobox", { name: "Select workspace" })
      .waitFor({ timeout: 30000 })
      .catch(async (error) => {
        await page.screenshot({ path: ".runtime/demo-picker-failure.png" });
        console.log((await page.locator("body").innerText()).slice(0, 1500));
        throw error;
      });
    await page
      .locator(".app-nav")
      .getByRole("button", { name: "Ask Atlas", exact: true })
      .click();
    const picker = page.getByRole("combobox", {
      name: "Demo company files",
      exact: true,
    });
    const input = page.getByRole("textbox", {
      name: "Your question",
      exact: true,
    });
    await picker.waitFor();
    assert.equal(await picker.locator("option").count(), 11);
    const a = companies.find((w) => w.demo_slug === "reliance");
    const b = companies.find((w) => w.demo_slug === "microsoft");
    await picker.selectOption(a.id);
    await page.locator(".demo-chat-question").first().waitFor();
    assert.equal(await page.locator(".demo-chat-question").count(), 4);
    const questions = await page
      .locator(".demo-chat-question")
      .allTextContents();
    assert.equal(new Set(questions).size, 4);
    await page.getByRole("button", { name: "Refresh questions" }).click();
    assert.equal(
      requests.length,
      0,
      "Company selection and suggestions must not call the model",
    );
    await page.locator(".demo-chat-question").first().click();
    assert.ok((await input.inputValue()).length > 20);
    async function send(text) {
      if (text) await input.fill(text);
      await page
        .getByRole("button", { name: "Send question", exact: true })
        .click();
      assert.ok(
        await picker.isDisabled(),
        "Company cannot change during an answer",
      );
      await page
        .getByRole("button", { name: "Send question", exact: true })
        .waitFor();
    }
    await send();
    assert.equal(requests[0].org, a.id);
    assert.equal(requests[0].payload.conversation_id, null);
    await picker.selectOption(b.id);
    assert.equal(
      await page.locator(".message").count(),
      2,
      "Switching must retain the visible conversation",
    );
    await send("What was Microsoft's fiscal 2025 revenue?");
    assert.equal(requests[1].org, b.id);
    assert.equal(
      requests[1].payload.conversation_id,
      null,
      "New company cannot inherit another company's context",
    );
    await picker.selectOption(a.id);
    await send("Compare that with the preceding financial year.");
    assert.equal(
      requests[2].payload.conversation_id,
      created[a.id],
      "Returning company keeps only its own follow-up context",
    );
    assert.equal(await page.locator(".message").count(), 6);
    for (const request of requests) {
      assert.deepEqual(Object.keys(request.payload).sort(), [
        "collection",
        "conversation_id",
        "question",
      ]);
      assert.equal(request.payload.collection, null);
    }
    for (const company of companies) {
      await picker.selectOption(company.id);
      await page
        .getByText(company.name + " · 3 indexed files", { exact: true })
        .waitFor();
      assert.equal(await page.locator(".demo-chat-question").count(), 4);
      assert.equal(await page.locator(".message").count(), 6);
    }
    assert.equal(requests.length, 3);
    await page
      .locator(".answer-actions")
      .getByRole("button", { name: "Edit & resend" })
      .first()
      .click();
    assert.equal(
      await picker.inputValue(),
      a.id,
      "Editing an old question restores its company",
    );
    await input.fill("");
    await page.screenshot({ path: ".runtime/demo-chat-picker-desktop.png" });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForFunction(
      () =>
        document.querySelector(".sidebar").getBoundingClientRect().right <= 0,
    );
    await page.screenshot({ path: ".runtime/demo-chat-picker-mobile.png" });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await page.getByRole("button", { name: "Hide company questions" }).click();
    assert.equal(await page.locator(".demo-chat-question").count(), 0);
    await page.getByRole("button", { name: "Show company questions" }).click();
    await page
      .locator(".chat-top")
      .getByRole("button", { name: "New conversation", exact: true })
      .click();
    await send("A fresh question for the selected company");
    assert.equal(requests[3].payload.conversation_id, null);
    assert.deepEqual(errors, []);
    const result = {
      companies: 10,
      suggestions_per_company: 4,
      single_visible_chat: true,
      scoped_followup_context: true,
      suggestions_make_no_model_calls: true,
      previous_company_prompts_not_sent: true,
      streaming_switch_guard: true,
      edit_restores_company: true,
      mobile_no_overflow: true,
      fresh_chat_resets_context: true,
    };
    fs.writeFileSync(
      "demo-data/chat-picker-checks.json",
      JSON.stringify(result, null, 2),
    );
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
