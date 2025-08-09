/** @odoo-module */

import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
// const { Component, onWillStart, useRef, onMounted, useEffect, onWillUnmount } = owl
import { Component, onWillStart, useRef, onPatched, useEffect, onWillUnmount } from "@odoo/owl"
import { useService } from "@web/core/utils/hooks"

export class ChartRenderer extends Component {
    setup() {
        this.chartRef = useRef("chart")

        onWillStart(async () => {

            await loadJS("https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js")
        })

        useEffect(() => {
            this.renderChart()
        }, () => [this.props.config])

        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy()
            }
        })
    }

    renderChart() {
        const chartConfigs = {
            bar: {
                type: 'bar',
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            },
            line: {
                type: 'line',
                options: {
                    fill: false
                }
            },
            pie: {
                type: 'pie',
                options: {
                    circumference: Math.PI,
                    rotation: -Math.PI
                }
            },
            doughnut: {
                type: 'doughnut',
                options: {
                    circumference: Math.PI / 2,
                    rotation: -Math.PI / 2
                }
            }
        };


        const old_chartjs = document.querySelector('script[src="/web/static/lib/Chart/Chart.js"]')

        if (old_chartjs) {
            return
        }

        if (this.chart) {
            this.chart.destroy()
        }

        const chartConfig = chartConfigs[this.props.type];
        if (!chartConfig) {
            console.error(`Unknown chart type: ${this.props.type}`);
            return;
        }

        
        this.chart = new Chart(this.chartRef.el, {
            type: chartConfig.type,
            data: this.props.config.data,
            options: this.props.config.options

        })


    }
}

ChartRenderer.template = "odoo_marketplace.ChartRenderer"