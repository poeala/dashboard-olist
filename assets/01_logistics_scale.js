/* Shared by the map fill and legend: percentages use the same precision. */
(function () {
    "use strict";
    const colors = ["#fff1d6", "#fed28b", "#f99d59", "#e95b3c", "#b51f32"];
    const noData = "#dce3eb";
    const format = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });
    const valid = value => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100;
    const units = value => Math.round(value * 100);

    function rateScale(values) {
        const rates = values.filter(valid).map(units);
        if (!rates.length) return { bins: [], colorFor: () => noData };
        const minimum = Math.min(...rates);
        const maximum = Math.max(...rates);
        const step = Math.max(1, Math.ceil((maximum - minimum) / colors.length));
        const count = Math.max(1, Math.ceil((maximum - minimum) / step));
        const bins = Array.from({ length: count }, (_, index) => {
            const low = minimum + index * step;
            const high = Math.min(maximum, low + step);
            const last = index === count - 1;
            return {
                color: colors[count === 1 ? 0 : Math.round(index * (colors.length - 1) / (count - 1))],
                label: (low === high ? format.format(low / 100)
                    : format.format(low / 100) + "–" + (last ? "" : "<") + format.format(high / 100)) + " %",
            };
        });
        return {
            bins,
            colorFor(value) {
                if (!valid(value)) return noData;
                const index = Math.max(0, Math.min(count - 1, Math.floor((units(value) - minimum) / step)));
                return bins[index].color;
            },
        };
    }
    globalThis.LogisticsMapScale = { rateScale };
}());
