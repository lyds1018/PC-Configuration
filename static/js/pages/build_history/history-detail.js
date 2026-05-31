document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("delete-history-form");
    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        if (!window.PCConfig || typeof window.PCConfig.confirmDialog !== "function") {
            if (window.confirm("确认删除这条历史方案吗？")) form.submit();
            return;
        }
        const result = await window.PCConfig.confirmDialog("删除方案", "确认删除这条历史方案吗？");
        if (result.confirmed) form.submit();
    });
});
