
var ChartController = {

    globalConfig: function(options={}) {

        var def = {
            modeBarButtonsToRemove: ['sendDataToCloud'],
            displaylogo: false,
            toImageButtonOptions: {'width': 1024}
        }

        return Object.assign({}, def, options)

    },
    lineChart: function (chartContainerId, raw_data) {

        var $chartContainer = $('#' + chartContainerId);
        $chartContainer.empty();

        var layout = {
            title: $chartContainer.data('title'),
            yaxis: {
                title: $chartContainer.data('yaxis')
            }
        };

        var plotOptions = {
            toImageButtonOptions: {'filename': ($chartContainer.data('name').replace(new RegExp(" ", 'g'), '_'))}
        };

        Plotly.newPlot(chartContainerId, ChartController.lineParse(raw_data, {'type': 'line'}),
            layout,
            ChartController.globalConfig(plotOptions)
        );

    },
    lineParse: function (raw_data, options={}) {
        columns = Object.keys(raw_data[0]).slice(1);
        return columns.map(function (column) {

            return Object.assign(
                {},
                {
                    type: 'line',
                    name: column,
                    x: raw_data.map(function (d) {
                        return d.timedelta;
                    }),
                    y: raw_data.map(function (d) {
                        return +d[column];
                    })
                }, options
            );
        })
    },
    makeResponsive: function () {

        var gd3 = Plotly.d3.selectAll(".responsive-plot");
        var nodes_to_resize = gd3[0];
        window.onresize = function () {
            for (var i = 0; i < nodes_to_resize.length; i++) {
                Plotly.Plots.resize(nodes_to_resize[i]);
            }
        };
    },

};
