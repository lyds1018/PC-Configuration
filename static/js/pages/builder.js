document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("save-diy-build-form");
    if (!form) return;

    const titleInput = document.getElementById("save-diy-build-title");
    const notify = (message, type) => {
        if (window.PCConfig && typeof window.PCConfig.showNotification === "function") {
            window.PCConfig.showNotification(message, type);
        }
    };

    const submitSave = async () => {
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;
        try {
            const resp = await fetch(form.action, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                },
                body: new URLSearchParams(formData).toString(),
            });
            const data = await resp.json();
            if (data && data.ok) {
                notify(data.message || "保存成功", "success");
            } else {
                notify((data && data.message) || "保存失败，请重试。", "error");
            }
        } catch (_) {
            notify("保存失败，请重试。", "error");
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    };

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        const defaultName = "DIY方案";

        if (!window.PCConfig || typeof window.PCConfig.promptDialog !== "function") {
            const fallback = window.prompt("请输入方案名称：", defaultName);
            if (fallback === null) return;
            if (titleInput) titleInput.value = (fallback || "").trim();
            await submitSave();
            return;
        }

        const result = await window.PCConfig.promptDialog("保存方案", defaultName, "给这套配置起个名字");
        if (!result.confirmed) return;
        if (titleInput) titleInput.value = (result.value || "").trim();
        await submitSave();
    });
});
