document.addEventListener("DOMContentLoaded", function () {
    const esc = (s) =>
        String(s ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");

    const shell = document.getElementById("recommend-result-shell");
    if (!shell) return;

    const resultDataUrlBase = shell.dataset.resultDataUrl || "";
    const saveUrlPattern = shell.dataset.saveUrlPattern || "";
    const backUrl = shell.dataset.backUrl || "/recommender/";

    const resultStage = document.getElementById("agent-result-stage");
    const thinkingCard = document.getElementById("agent-thinking-card");
    const subtitleEl = document.getElementById("result-subtitle");
    const stepHeaderEl = document.getElementById("agent-step-header");
    const logItems = Array.from(document.querySelectorAll("#agent-log .agent-log-item"));
    const progressFill = document.getElementById("agent-progress-fill");
    const total = logItems.length || 1;
    const query = window.location.search || "";
    const dataUrl = resultDataUrlBase + query;
    const workloadLabelMap = { game: "游戏", office: "办公", productivity: "生产力" };
    let payload = null;
    let requestStarted = false;

    const getCookie = (name) => {
        const cookie = document.cookie
            .split(";")
            .map((v) => v.trim())
            .find((v) => v.startsWith(name + "="));
        return cookie ? decodeURIComponent(cookie.split("=", 2)[1]) : "";
    };

    const startTypewriter = (summary) => {
        const summaryTextEl = document.getElementById("agent-summary-text");
        const cursorEl = document.getElementById("agent-summary-cursor");
        if (!summaryTextEl) return;
        const fullText = summary || "";
        if (!fullText) {
            if (cursorEl) cursorEl.style.display = "none";
            return;
        }
        summaryTextEl.textContent = "";
        let idx = 0;
        const tick = () => {
            summaryTextEl.textContent = fullText.slice(0, idx);
            idx += 1;
            if (idx <= fullText.length) {
                window.setTimeout(tick, 16);
            } else if (cursorEl) {
                window.setTimeout(() => {
                    cursorEl.style.display = "none";
                }, 300);
            }
        };
        tick();
    };

    const renderResult = () => {
        if (!resultStage || !payload) return;
        const meta = payload.meta || {};
        const rows = payload.rows || [];
        const agentEnabled = !!payload.agent_enabled;
        const summary = payload.agent_summary || "";
        const agentReason = payload.agent_reason || "当前未启用智能体推荐。";
        const metaReason = meta.reason || "";

        const rowsHtml = rows
            .map(
                (row, idx) => `
        <tr>
          <td class="col-plan">
            <div class="plan-line"><strong>CPU：</strong>${esc(row.cpu)}</div>
            <div class="plan-line"><strong>主板：</strong>${esc(row.mb)}</div>
            <div class="plan-line"><strong>内存：</strong>${esc(row.ram)}</div>
            <div class="plan-line"><strong>硬盘：</strong>${esc(row.storage)}</div>
            <div class="plan-line"><strong>显卡：</strong>${esc(row.gpu)}</div>
            <div class="plan-line"><strong>机箱：</strong>${esc(row.case)}</div>
            <div class="plan-line"><strong>电源：</strong>${esc(row.psu)}</div>
            <div class="plan-line"><strong>散热：</strong>${esc(row.cooler)}</div>
          </td>
          <td>￥${Number(row.total_price || 0).toFixed(2)}</td>
          <td>${Number(row.total_score_100 || 0).toFixed(1)}/100</td>
          <td>${Number(row.combo_value_100 || 0).toFixed(1)}/100</td>
          <td class="col-review">${esc(row.reason || "—")}</td>
          <td><button type="button" class="btn btn-sm btn-primary js-save-combo" data-save-index="${idx + 1}">保存方案</button></td>
        </tr>
      `
            )
            .join("");

        const workloadLabel = workloadLabelMap[meta.workload] || meta.workload || "";

        resultStage.innerHTML = `
        <div class="card">
          <div class="flex-between inline-flex-wrap-gap-1">
            <div class="text-muted">场景：${esc(workloadLabel)} / 预算区间：${esc(meta.budget_min || "")} - ${esc(meta.budget_max || "")} / 候选池：${esc(meta.candidate_count || 0)}</div>
            <a href="${esc(backUrl)}" class="btn btn-outline">返回修改条件</a>
          </div>
        </div>
        ${metaReason ? `<div class="alert alert-warning">${esc(metaReason)}</div>` : ""}
        ${
            rows.length
                ? `
          <div class="card">
            <div class="card-header">智能体建议</div>
            ${
                agentEnabled
                    ? `<div class="typewriter-wrap"><span id="agent-summary-text"></span><span class="typewriter-cursor" id="agent-summary-cursor">|</span></div>`
                    : `<div class="text-muted">${esc(agentReason)}</div>`
            }
          </div>
          <div class="card">
            <div class="card-header">推荐结果（${rows.length} 套）</div>
            <div class="table-responsive">
              <table class="table recommend-table">
                <thead>
                  <tr>
                    <th class="col-plan">方案</th>
                    <th>总价</th>
                    <th>总分</th>
                    <th>性价比</th>
                    <th class="col-review">智能体评价</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>${rowsHtml}</tbody>
              </table>
            </div>
          </div>
        `
                : ""
        }
      `;
        resultStage.classList.add("ready");
        if (agentEnabled) startTypewriter(summary);

        const csrfToken = getCookie("csrftoken");
        resultStage.querySelectorAll(".js-save-combo").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const idx = btn.dataset.saveIndex;
                if (!idx) return;
                const defaultName = `智能推荐 方案 #${idx}`;
                let title = "";
                if (window.PCConfig && typeof window.PCConfig.promptDialog === "function") {
                    const result = await window.PCConfig.promptDialog("保存方案", defaultName, "给这套推荐方案起个名字");
                    if (!result.confirmed) return;
                    title = (result.value || "").trim();
                } else {
                    const inputName = window.prompt("请输入方案名称：", defaultName);
                    if (inputName === null) return;
                    title = (inputName || "").trim();
                }

                btn.disabled = true;
                const url = saveUrlPattern.replace("999999", idx);
                fetch(url, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    },
                    body: new URLSearchParams({ title }).toString(),
                })
                    .then((r) => r.json())
                    .then((data) => {
                        if (data && data.ok) {
                            btn.textContent = "已保存";
                            btn.classList.remove("btn-primary");
                            btn.classList.add("btn-outline");
                        } else {
                            btn.disabled = false;
                            alert((data && data.message) || "保存失败，请重试。");
                        }
                    })
                    .catch(() => {
                        btn.disabled = false;
                        alert("保存失败，请重试。");
                    });
            });
        });
    };

    const startRequest = () => {
        if (requestStarted) return;
        requestStarted = true;
        if (!query || query === "?") {
            payload = {
                meta: { reason: "未检测到推荐条件，请返回上一页重新提交。" },
                rows: [],
                agent_enabled: false,
                agent_reason: "",
            };
            return;
        }
        fetch(dataUrl, { credentials: "same-origin" })
            .then((r) => r.json())
            .then((data) => {
                payload = data;
            })
            .catch(() => {
                payload = {
                    meta: { reason: "推荐数据加载失败，请返回重试。" },
                    rows: [],
                    agent_enabled: false,
                    agent_reason: "推荐数据加载失败，请返回重试。",
                };
            });
    };

    const activeClass = (idx, done) => {
        logItems.forEach((el, i) => {
            el.classList.toggle("active", i === idx && !done);
            if (done && i <= idx) el.classList.add("done");
        });
        if (stepHeaderEl && logItems[idx]) {
            stepHeaderEl.textContent = (logItems[idx].textContent || "智能体思考中").replace(/\.\.\.$/, "");
        }
    };

    const setProgress = (percent) => {
        if (progressFill) progressFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    };

    const callStepIdx = Math.max(0, total - 1);
    for (let idx = 0; idx < callStepIdx; idx += 1) {
        window.setTimeout(() => {
            activeClass(idx, false);
            const preRatio = (idx + 1) / Math.max(1, callStepIdx);
            setProgress(preRatio * 88);
            window.setTimeout(() => activeClass(idx, true), 220);
        }, idx * 300);
    }

    const startWaitAt = callStepIdx * 300 + 120;
    let creep = 88;
    const creepTimer = window.setInterval(() => {
        if (payload) return;
        creep = Math.min(96, creep + 0.35);
        setProgress(creep);
    }, 120);

    window.setTimeout(() => {
        activeClass(callStepIdx, false);
        startRequest();
    }, startWaitAt);

    const waitForPayload = () => {
        if (!payload) {
            window.setTimeout(waitForPayload, 120);
            return;
        }
        window.clearInterval(creepTimer);
        activeClass(callStepIdx, true);
        setProgress(100);
        window.setTimeout(() => {
            if (thinkingCard) thinkingCard.style.display = "none";
            renderResult();
            if (subtitleEl) subtitleEl.textContent = "分析完成";
        }, 220);
    };
    waitForPayload();
});
