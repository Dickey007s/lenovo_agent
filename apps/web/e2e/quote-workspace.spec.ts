import { expect, test, type Page } from "@playwright/test";


type QuoteWorkspaceArtifact = {
  artifact_id: string;
  revision: number;
  kind: "quote";
  title: string;
  content: Record<string, unknown>;
  sources: Record<string, unknown>[];
  linked_action_id: string | null;
  linked_run_id: string | null;
  requires_recheck: boolean;
  change_history: Record<string, unknown>[];
  updated_at: string;
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(next => { resolve = next; });
  return { promise, resolve };
}

async function delayNextAgentArtifact(page: Page) {
  const requestStarted = deferred<void>();
  const artifactReady = deferred<QuoteWorkspaceArtifact>();
  await page.route("**/v1/threads/*/messages/stream", async route => {
    requestStarted.resolve();
    const artifact = await artifactReady.promise;
    const stamp = Date.now();
    const events = [
      {
        type: "message.created",
        message: { message_id: `test-user-${stamp}`, role: "user", content: "请更新报价", status: "completed" },
      },
      { type: "artifact.updated", artifact },
      {
        type: "message.completed",
        message: { message_id: `test-assistant-${stamp}`, role: "assistant", content: "报价已更新。", status: "completed" },
      },
    ];
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: `${events.map(event => `data: ${JSON.stringify(event)}`).join("\n\n")}\n\n`,
    });
  });
  return {
    requestStarted: requestStarted.promise,
    deliver: (artifact: QuoteWorkspaceArtifact) => artifactReady.resolve(artifact),
  };
}

async function saveExternalQuoteValidUntil(page: Page, validUntil: string) {
  return await page.evaluate(async value => {
    const headers = {
      "Content-Type": "application/json",
      "X-User-Id": "demo_user",
      "X-User-Roles": "current_user,sales_manager",
    };
    const workspace = await fetch("http://localhost:8011/v1/workspace", { headers })
      .then(response => response.json()) as QuoteWorkspaceArtifact[];
    const quote = workspace.find(item => item.kind === "quote");
    if (!quote) throw new Error("quote workspace is missing");
    const response = await fetch("http://localhost:8011/v1/workspace/quote", {
      method: "PUT",
      headers,
      body: JSON.stringify({
        title: quote.title,
        content: { ...quote.content, valid_until: value },
        expected_artifact_id: quote.artifact_id,
        expected_revision: quote.revision,
      }),
    });
    if (!response.ok) throw new Error(`external save failed: ${response.status}`);
    return await response.json() as QuoteWorkspaceArtifact;
  }, validUntil);
}


test("quote workspace recalculates edits and answers from the visible rows", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();

  const quote = page.getByRole("main");
  await expect(page.getByRole("heading", { name: "报价工作台" })).toBeVisible();
  await expect(quote.getByLabel("报价核算结果")).toContainText("¥272,000");
  await expect(quote.getByLabel("报价核算结果")).toContainText("¥253,400");
  await expect(quote.getByLabel("报价核算结果")).toContainText("93.16%");
  await expect(quote.getByLabel("报价核算结果")).toContainText("约 9.32 折");

  const firstRequest = page.waitForRequest(request =>
    request.method() === "POST" && request.url().includes("/messages/stream")
  );
  await page.getByRole("button", { name: "核算综合折后比例" }).click();
  const initialNetworkRequest = await firstRequest;
  const initialPayload = initialNetworkRequest.postDataJSON();
  expect(initialPayload.active_view).toBe("quote");
  expect(initialPayload.workspace_context.total).toBe(253400);

  const initialAnswer = page.locator(".assistant-message").last();
  await expect(initialAnswer).toContainText("综合折后比例：93.16%，约 9.32 折");
  await expect(initialAnswer).toContainText("标准总价：¥272,000");
  await expect(initialAnswer).toContainText("折后总价：¥253,400");
  await expect(initialAnswer).toContainText("优惠金额：¥18,600");
  await expect(initialAnswer).toContainText("优惠率：6.84%");
  await expect(initialAnswer).toContainText("没有访问真实 CRM");
  await expect(initialAnswer).not.toContainText("2,000,000");
  await expect(initialAnswer).not.toContainText("1,770,000");
  await expect(page.locator(".send-spinner")).toHaveCount(0);

  await page.getByLabel("企业办公 Agent 平台许可数量").fill("101");
  await expect(quote.getByLabel("报价核算结果")).toContainText("¥273,680");
  await expect(quote.getByLabel("报价核算结果")).toContainText("¥254,912");

  const assistantMessages = page.locator(".assistant-message");
  const assistantCountBeforeQuantityAnswer = await assistantMessages.count();
  const updatedRequest = page.waitForRequest(request =>
    request.method() === "POST" && request.url().includes("/messages/stream")
  );
  await page.getByLabel("输入办公任务").fill("再算一次");
  await page.getByRole("button", { name: "发送消息" }).click();
  const updatedPayload = (await updatedRequest).postDataJSON();
  expect(updatedPayload.workspace_context.items[0].qty).toBe(101);
  expect(updatedPayload.workspace_context.items[0].subtotal).toBe(152712);
  expect(updatedPayload.workspace_context.total).toBe(254912);

  await expect(assistantMessages).toHaveCount(assistantCountBeforeQuantityAnswer + 1);
  const updatedAnswer = assistantMessages.nth(assistantCountBeforeQuantityAnswer);
  await expect(updatedAnswer).toContainText("标准总价：¥273,680");
  await expect(updatedAnswer).toContainText("折后总价：¥254,912");
  await expect(updatedAnswer).toContainText("优惠金额：¥18,768");
  await expect(page.locator(".send-spinner")).toHaveCount(0);

  await page.getByLabel("企业办公 Agent 平台许可数量").fill("100");
  await page.getByLabel("企业办公 Agent 平台许可折后比例").fill("87");
  const quoteResult = quote.getByLabel("报价核算结果");
  await expect(quoteResult).toContainText("¥272,000");
  await expect(quoteResult).toContainText("¥248,360");
  await expect(quoteResult).toContainText("企业办公 Agent 平台许可低于 88.00%（8.80 折）底线");

  const assistantCountBeforeDiscountAnswer = await assistantMessages.count();
  const discountRequest = page.waitForRequest(request =>
    request.method() === "POST" && request.url().includes("/messages/stream")
  );
  await page.getByLabel("输入办公任务").fill("按新折后比例再算一次");
  await page.getByRole("button", { name: "发送消息" }).click();
  const discountNetworkRequest = await discountRequest;
  const discountPayload = discountNetworkRequest.postDataJSON();
  expect(discountPayload.workspace_context.items[0].qty).toBe(100);
  expect(discountPayload.workspace_context.items[0].discount).toBe(0.87);
  expect(discountPayload.workspace_context.items[0].subtotal).toBe(146160);
  expect(discountPayload.workspace_context.total).toBe(248360);

  const discountResponse = await discountNetworkRequest.response();
  expect(discountResponse).not.toBeNull();
  expect(discountResponse?.headers()["content-type"]).toContain("text/event-stream");
  const discountStream = await discountResponse?.text();
  expect(discountStream).toContain("event: assistant.delta");
  expect(discountStream).toContain("event: message.completed");

  await expect(assistantMessages).toHaveCount(assistantCountBeforeDiscountAnswer + 1);
  const discountAnswer = assistantMessages.nth(assistantCountBeforeDiscountAnswer);
  await expect(discountAnswer).toContainText("标准总价：¥272,000");
  await expect(discountAnswer).toContainText("折后总价：¥248,360");
  await expect(discountAnswer).toContainText("优惠金额：¥23,640");
  await expect(discountAnswer).toContainText("低于底线的项目：企业办公 Agent 平台许可");

  const assistantCountBeforeSourceAnswer = await assistantMessages.count();
  const sourceRequest = page.waitForRequest(request =>
    request.method() === "POST" && request.url().includes("/messages/stream")
  );
  await page.getByLabel("输入办公任务").fill("你的数据是哪里来的");
  await page.getByRole("button", { name: "发送消息" }).click();
  const sourceNetworkRequest = await sourceRequest;
  expect(sourceNetworkRequest.postDataJSON().message).toBe("你的数据是哪里来的");
  await expect(assistantMessages).toHaveCount(assistantCountBeforeSourceAnswer + 1);
  const sourceAnswer = assistantMessages.nth(assistantCountBeforeSourceAnswer);
  await expect(sourceAnswer).toContainText("当前重算结果如下");
  await expect(sourceAnswer).toContainText("当前屏幕中的报价工作台 Q-991-V3");
  await expect(sourceAnswer).toContainText("折后总价：¥248,360");
  await expect(sourceAnswer).toContainText("没有使用历史对话里的金额");
  await expect(sourceAnswer).not.toContainText("crm:quote/991:v3");
});


test("invalid quote input suppresses aggregate totals and the agent fails closed", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();

  const quote = page.getByRole("main");
  const quoteResult = quote.getByLabel("报价核算结果");
  await page.getByLabel("企业办公 Agent 平台许可数量").fill("");

  await expect(quoteResult.locator("div > strong")).toHaveText([
    "待核对",
    "待核对",
    "待核对",
    "待核对",
  ]);
  await expect(quoteResult).toContainText("核算暂停：第 1 行数量缺失或不是有效数字");
  await expect(quoteResult).not.toContainText("¥253,400");

  const invalidRequest = page.waitForRequest(request =>
    request.method() === "POST" && request.url().includes("/messages/stream")
  );
  await page.getByLabel("输入办公任务").fill("再算一次");
  await page.getByRole("button", { name: "发送消息" }).click();
  const invalidPayload = (await invalidRequest).postDataJSON();
  expect(invalidPayload.workspace_context.items[0].qty).toBeUndefined();
  expect(invalidPayload.workspace_context.total).toBeNull();

  const invalidAnswer = page.locator(".assistant-message").last();
  await expect(invalidAnswer).toContainText("当前报价无法完成核算");
  await expect(invalidAnswer).toContainText("不会在字段不完整时猜测结果");
  await expect(invalidAnswer).not.toContainText("¥253,400");
});


test("saved quote edits remain visibly pending review", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();

  const quoteResult = page.getByLabel("报价核算结果");
  await page.getByLabel("企业办公 Agent 平台许可折后比例").fill("89");
  await expect(quoteResult).toContainText("当前修改尚未保存，保存后需要重新复核");

  const saveResponse = page.waitForResponse(response =>
    response.request().method() === "PUT" && response.url().includes("/workspace/quote")
  );
  await page.getByRole("button", { name: "保存", exact: true }).click();
  const savedArtifact = await (await saveResponse).json();
  expect(savedArtifact.requires_recheck).toBe(true);
  expect(savedArtifact.content.approval.status).toBe("needs_review");

  await expect(quoteResult).toContainText("当前版本已保存，正在等待重新复核");
  await expect(quoteResult).not.toContainText("当前修改尚未保存");
  await page.getByText("上下文与治理").click();
  await expect(page.getByText("演示基线版本已批准，有效期至 2026-07-31；修改后需要重新复核。" )).toBeVisible();
});


test("stale quote saves preserve the draft and offer an explicit reapply path", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();
  const validUntil = page.getByLabel("报价有效期");
  await validUntil.fill("2026-09-30");

  const externalRevision = await page.evaluate(async () => {
    const headers = {
      "Content-Type": "application/json",
      "X-User-Id": "demo_user",
      "X-User-Roles": "current_user,sales_manager",
    };
    const workspace = await fetch("http://localhost:8011/v1/workspace", { headers }).then(response => response.json());
    const quote = workspace.find((item: { kind: string }) => item.kind === "quote");
    const response = await fetch("http://localhost:8011/v1/workspace/quote", {
      method: "PUT",
      headers,
      body: JSON.stringify({
        title: quote.title,
        content: {
          ...quote.content,
          items: quote.content.items.map((item: Record<string, unknown>, index: number) =>
            index === 0 ? { ...item, qty: 102 } : item
          ),
        },
        expected_artifact_id: quote.artifact_id,
        expected_revision: quote.revision,
      }),
    });
    if (!response.ok) throw new Error(`external save failed: ${response.status}`);
    return (await response.json()).revision as number;
  });

  const conflictResponse = page.waitForResponse(response =>
    response.status() === 409 && response.url().includes("/workspace/quote")
  );
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await conflictResponse;
  const conflict = page.getByRole("alert").filter({ hasText: "工作区已有更新" });
  await expect(conflict).toContainText("系统只会重新应用你实际修改的字段");
  await expect(validUntil).toHaveValue("2026-09-30");

  await conflict.getByRole("button", { name: "重新应用我的修改" }).click();
  await expect(validUntil).toHaveValue("2026-09-30");
  await expect(page.getByLabel("企业办公 Agent 平台许可数量")).toHaveValue("102");
  await expect(page.getByText("已把仅在当前草稿中修改的字段重新应用到最新版本，请复核后保存")).toBeVisible();

  const saveResponse = page.waitForResponse(response =>
    response.status() === 200 && response.url().includes("/workspace/quote")
  );
  await page.getByRole("button", { name: "保存", exact: true }).click();
  const saved = await (await saveResponse).json();
  expect(saved.revision).toBe(externalRevision + 1);
  expect(saved.content.valid_until).toBe("2026-09-30");
  expect(saved.content.items[0].qty).toBe(102);
  await expect(conflict).toHaveCount(0);
});


test("same-field quote conflicts are shown instead of silently overwriting either version", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();
  const validUntil = page.getByLabel("报价有效期");
  await validUntil.fill("2026-10-30");

  await page.evaluate(async () => {
    const headers = {
      "Content-Type": "application/json",
      "X-User-Id": "demo_user",
      "X-User-Roles": "current_user,sales_manager",
    };
    const workspace = await fetch("http://localhost:8011/v1/workspace", { headers }).then(response => response.json());
    const quote = workspace.find((item: { kind: string }) => item.kind === "quote");
    const response = await fetch("http://localhost:8011/v1/workspace/quote", {
      method: "PUT",
      headers,
      body: JSON.stringify({
        title: quote.title,
        content: { ...quote.content, valid_until: "2026-10-01" },
        expected_artifact_id: quote.artifact_id,
        expected_revision: quote.revision,
      }),
    });
    if (!response.ok) throw new Error(`external save failed: ${response.status}`);
  });

  await page.getByRole("button", { name: "保存", exact: true }).click();
  const conflict = page.getByRole("alert").filter({ hasText: "工作区已有更新" });
  await expect(conflict).toBeVisible();
  await conflict.getByRole("button", { name: "重新应用我的修改" }).click();
  await expect(conflict).toContainText("有效期在两个版本中都被修改");
  await expect(validUntil).toHaveValue("2026-10-30");

  await conflict.getByRole("button", { name: "查看最新版本" }).click();
  await expect(validUntil).toHaveValue("2026-10-01");
  await expect(conflict).toHaveCount(0);
});


test("late Agent artifacts preserve different-field quote edits made after send", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();

  const delayedArtifact = await delayNextAgentArtifact(page);
  const quantity = page.getByLabel("企业办公 Agent 平台许可数量");
  const localQuantity = String(Number(await quantity.inputValue()) + 7);
  await page.getByLabel("输入办公任务").fill("请更新报价有效期");
  await page.getByRole("button", { name: "发送消息" }).click();
  await delayedArtifact.requestStarted;

  await quantity.fill(localQuantity);
  const remoteArtifact = await saveExternalQuoteValidUntil(page, "2027-01-15");
  delayedArtifact.deliver(remoteArtifact);

  await expect(page.locator(".send-spinner")).toHaveCount(0);
  await expect(quantity).toHaveValue(localQuantity);
  await expect(page.getByLabel("报价有效期")).toHaveValue("2027-01-15");
  await expect(page.getByRole("alert").filter({ hasText: "工作区已有更新" })).toHaveCount(0);
  await expect(page.getByText("Agent 已更新报价表，并保留了你在等待期间的修改")).toBeVisible();
  await expect(page.getByText("未保存修改", { exact: true })).toBeVisible();

  const saveResponse = page.waitForResponse(response =>
    response.status() === 200 && response.request().method() === "PUT"
      && response.url().includes("/workspace/quote")
  );
  await page.getByRole("button", { name: "保存", exact: true }).click();
  const saved = await (await saveResponse).json();
  expect(saved.content.valid_until).toBe("2027-01-15");
  expect(String(saved.content.items[0].qty)).toBe(localQuantity);
});


test("late same-field Agent artifacts enter explicit quote conflict recovery", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();

  const delayedArtifact = await delayNextAgentArtifact(page);
  const validUntil = page.getByLabel("报价有效期");
  await page.getByLabel("输入办公任务").fill("请更新报价有效期");
  await page.getByRole("button", { name: "发送消息" }).click();
  await delayedArtifact.requestStarted;

  await validUntil.fill("2027-02-20");
  const remoteArtifact = await saveExternalQuoteValidUntil(page, "2027-02-10");
  delayedArtifact.deliver(remoteArtifact);

  await expect(page.locator(".send-spinner")).toHaveCount(0);
  await expect(validUntil).toHaveValue("2027-02-20");
  const conflict = page.getByRole("alert").filter({ hasText: "工作区已有更新" });
  await expect(conflict).toBeVisible();
  await expect(conflict).toContainText("有效期在两个版本中都被修改");
  await expect(page.getByText("Agent 返回了新版本；你在等待期间的修改未被覆盖，请处理冲突")).toBeVisible();

  await conflict.getByRole("button", { name: "查看最新版本" }).click();
  await expect(validUntil).toHaveValue("2027-02-10");
  await expect(conflict).toHaveCount(0);
});


test("late Agent artifacts merge from the exact pre-dirty send snapshot", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "报价表" }).click();

  const quantity = page.getByLabel("企业办公 Agent 平台许可数量");
  const validUntil = page.getByLabel("报价有效期");
  await quantity.fill("100");
  const baselineSave = page.waitForResponse(response =>
    response.status() === 200 && response.request().method() === "PUT"
      && response.url().includes("/workspace/quote")
  );
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await baselineSave;
  const serverValidUntil = await validUntil.inputValue();

  await quantity.fill("101");
  const delayedArtifact = await delayNextAgentArtifact(page);
  const outboundRequest = page.waitForRequest(request =>
    request.method() === "POST" && request.url().includes("/messages/stream")
  );
  await page.getByLabel("输入办公任务").fill("请按当前草稿调整报价");
  await page.getByRole("button", { name: "发送消息" }).click();
  await delayedArtifact.requestStarted;
  const outboundPayload = (await outboundRequest).postDataJSON();
  expect(outboundPayload.workspace_context.items[0].qty).toBe(101);

  await validUntil.fill("2027-03-20");
  const remoteArtifact = await saveExternalQuoteValidUntil(page, serverValidUntil);
  delayedArtifact.deliver(remoteArtifact);

  await expect(page.locator(".send-spinner")).toHaveCount(0);
  await expect(quantity).toHaveValue("100");
  await expect(validUntil).toHaveValue("2027-03-20");
  await expect(page.getByRole("alert").filter({ hasText: "工作区已有更新" })).toHaveCount(0);
  await expect(page.getByText("Agent 已更新报价表，并保留了你在等待期间的修改")).toBeVisible();
  await expect(page.getByText("未保存修改", { exact: true })).toBeVisible();
});
