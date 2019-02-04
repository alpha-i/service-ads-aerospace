var DetectionChart = {
    combinedResult: function(chartContainerId, datasource, detection) {
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
        }

        var datasourceTraces = ChartController.lineParse(datasource);
        var detectionTraces = ChartController.lineParse(detection, {'type': 'scatter', 'fill' :'tozeroy', 'line': {'color': 'red' }});

        Plotly.newPlot(chartContainerId,
            detectionTraces.concat(datasourceTraces),
            layout,
            ChartController.globalConfig(plotOptions));
    }
};
