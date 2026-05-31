document.addEventListener("DOMContentLoaded", function () {
    const groups = document.querySelectorAll(".dual-range");
    groups.forEach((group) => {
        const minInput = group.querySelector(".range-input-min");
        const maxInput = group.querySelector(".range-input-max");
        const hiddenMin = group.querySelector(".range-hidden-min");
        const hiddenMax = group.querySelector(".range-hidden-max");
        const valueMin = group.parentElement.querySelector(".range-value-min");
        const valueMax = group.parentElement.querySelector(".range-value-max");
        const fill = group.querySelector(".dual-range-fill");
        const minBound = parseFloat(group.dataset.min);
        const maxBound = parseFloat(group.dataset.max);
        const step = parseFloat(group.dataset.step || "1");

        const formatValue = (v) => (step >= 1 ? String(Math.round(v)) : Number(v).toFixed(1));
        const clamp = () => {
            let minVal = parseFloat(minInput.value);
            let maxVal = parseFloat(maxInput.value);
            if (minVal > maxVal) {
                if (document.activeElement === minInput) {
                    maxVal = minVal;
                    maxInput.value = maxVal;
                } else {
                    minVal = maxVal;
                    minInput.value = minVal;
                }
            }

            const left = ((minVal - minBound) / (maxBound - minBound)) * 100;
            const right = ((maxVal - minBound) / (maxBound - minBound)) * 100;
            fill.style.left = left + "%";
            fill.style.width = (right - left) + "%";

            hiddenMin.value = minVal;
            hiddenMax.value = maxVal;
            valueMin.textContent = formatValue(minVal);
            valueMax.textContent = formatValue(maxVal);
        };

        minInput.addEventListener("input", clamp);
        maxInput.addEventListener("input", clamp);
        clamp();
    });
});
