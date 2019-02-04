function DiagnosticRefreshController(url) {
    this.url = url;
    this.timer = null;

    self = this;

    this.run = function () {
        self.timer = setInterval(self.request, 1000);
    };

    this.request = function () {
        $.get({
            url: self.url,
            success: self.onSuccess,
            error: self.onError
        });
    };

    this.onSuccess = function (result) {
        var diagnostic = result.diagnostic;
        var domain = diagnostic.is_frequency_domain ? 'frequency' : 'time';
        if (diagnostic.is_completed) {
            clearInterval(self.timer);
            if (diagnostic.diagnostic_result) {
                DiagnosticGraph.build(diagnostic.diagnostic_result, diagnostic.task_code, domain)
            } else {
                $(".diagnostic_container div").html("No diagnostics available");
            }
        }
    };

    this.onError = function (xhr, status, message) {
        clearInterval(self.timer);
        switch (xhr.status) {
            case 401:
            case 403:
                location.reload();
                break;
            default:
                $(".diagnostic_container div").html("No diagnostics available");
                break;
        }
    };

    return {
        run: this.run
    }
}


var DiagnosticGraph = {
    build: function (result, diagnostic_code, diagnostic_domain) {

        if (!result.result) return;
        result = result.result;

        var $container = $('.diagnostic_container').empty();
        if (result.length === 0) return;

        var max_graph_per_row = 3;
        var rows = [];

        for (var i = 0; i < result.length; i += max_graph_per_row) {
            rows.push(result.slice(i, i + max_graph_per_row))
        }
        ;

        rows.forEach(function (sliced_result) {
            var cellSize = 12;
            var $row = $('<div class="row">');
            $container.append($row);
            sliced_result.forEach(function (chunk_diagnostic) {
                var chunk = DiagnosticGraph.parseChunk(chunk_diagnostic, diagnostic_domain);
                var $diagnosticChart = DiagnosticGraph.createElement(chunk, diagnostic_domain);
                var $container = $('<div>').addClass('col-xs-' + cellSize).append($diagnosticChart);
                $row.append($container);
                DiagnosticGraph.createHeatMap($diagnosticChart.attr('id'), [chunk.result]);
                DiagnosticGraph.createDiagnosticDetails($container, chunk_diagnostic, diagnostic_code, diagnostic_domain);
            });
        });
        ChartController.makeResponsive()
    },
    decorateDomainLabel: function (domain) {
        switch (domain) {
            case 'time':
                decorator = function (element) {
                    var splitted_string = element.split(".");
                    if (splitted_string.length > 1) {
                        decimal_part = splitted_string[1];
                        element = splitted_string[0] + "." + decimal_part.substr(0, 4);
                    }
                    return element
                };
                break;
            case 'frequency':
                decorator = function (element) {
                    return element + " Hz"
                };
                break;
            default:
                decorator = function (a) {
                    return a
                };
                break;
        }

        return decorator
    },
    parseChunk: function (chunk_diagnostic, domain) {

        var chunk_index = chunk_diagnostic['chunk_index'];
        var chunk_timedelta = chunk_diagnostic['chunk_timedelta'];
        var diagnostic = chunk_diagnostic['diagnostic'];

        var y = Object.keys(diagnostic);
        var x = Object.keys(diagnostic[y[0]]);
        var z = [];

        y.forEach(function (column_name) {
            var sensorValues = [];
            x.forEach(function (index) {
                sensorValues.push(diagnostic[column_name][index]);
            });
            z.push(sensorValues);
        });

        x = x.map(DiagnosticGraph.decorateDomainLabel(domain));

        return {
            index: chunk_index,
            timedelta: chunk_timedelta,
            result: {
                x: x,
                y: y,
                z: z,
                type: 'heatmap',
                colorscale: [
                    [0, 'red'],
                    [0.25, 'yellow'],
                    [0.50, 'green'],
                    [0.75, 'yellow'],
                    [1, 'red']
                ],
                zmin: -1,
                zmax: 1
            }
        };
    },
    createElement: function (chunk, domain) {
        var diagnostic_chart_id = 'diagnostic_chart_id' + chunk.index;
        return $('<div>')
            .attr('id', diagnostic_chart_id)
            .data('title', 'Root cause diagnostic for data<br> starting at ' + chunk.timedelta)
            .data('yaxis', 'sensor')
            .data('domain', domain)
            .data('name', 'diagnostic_chunk_' + chunk.index)

            .addClass('responsive-plot')
            .html('<div class="text-center">loading.. <i class="fa fa-spinner fa-spin"></i></div>');
    },
    createHeatMap: function (chartContainerId, result) {

        var $chartContainer = $('#' + chartContainerId);
        $chartContainer.empty();

        var layout = {
            title: $chartContainer.data('title'),
            autosize: true
        };

        var filename = $chartContainer.data('name') || chartContainerId;

        var plotOptions = {
            toImageButtonOptions: {'filename': (filename.replace(new RegExp(" ", 'g'), '_'))}
        }

        Plotly.newPlot(
            chartContainerId,
            result,
            layout,
            ChartController.globalConfig(plotOptions)
        );
    },

    createDiagnosticDetails: function ($row, chunkDiagnostic, diagnosticCode, diagnostic_domain) {

        var chunkIndex = chunkDiagnostic.chunk_index;

        var $detailContainer = $('<div id="diagnostic_detail_' + chunkIndex + '">');
        $detailContainer.append('<h4>Select the sensor to see the original chunk of data</h4>');


        var $selectorContainer = $('<div>');
        var $sensorSelect = $('<select name="detail" class="sensor_selector form-control">');

        $selectorContainer.append($sensorSelect);

        $sensorSelect.attr('data-chunkindex', chunkIndex);
        $sensorSelect.attr('data-code', diagnosticCode);
        $sensorSelect.attr('data-domain', diagnostic_domain);
        $sensorSelect.append('<option value="">Choose Sensor</option></select>');
        $sensorSelect.on('change', DiagnosticGraph.onSensorSelect);

        $(Object.keys(chunkDiagnostic.diagnostic)).each(function (i, sensor) {
            $sensorSelect.append('<option value="' + i + '">' + sensor + '</option></select>');
        });

        $detailContainer.append($selectorContainer);
        var diagnosticSensorChartContainerId = 'diagnostic_chart_sensor_' + chunkIndex;
        var $diagnosticSensorChartContainer = $('<div>');
        $diagnosticSensorChartContainer.addClass('responsive-plot');
        $diagnosticSensorChartContainer.attr('id', diagnosticSensorChartContainerId);
        $diagnosticSensorChartContainer.attr('data-name', diagnosticSensorChartContainerId);

        $detailContainer.append($diagnosticSensorChartContainer);

        $row.append($detailContainer)
    },
    onSensorSelect: function () {

        var $element = $(this);
        var $diagnosticCode = $element.data('code');
        var $chunkIndex = $element.data('chunkindex');
        var $domain = $element.data('domain');
        var diagnosticSensorChartContainerId = 'diagnostic_chart_sensor_' + $chunkIndex;
        $("#" + diagnosticSensorChartContainerId).empty();

        if ($element.val() !== "") {
            Plotly.d3.csv(
                '/diagnostic/' + $diagnosticCode + '/details/' + $chunkIndex + /sensor/ + $element.val(),
                function (err, data) {
                    if (err) {

                    } else {
                        decoration_function = DiagnosticGraph.decorateDomainLabel('time');
                        data = data.map(function (element) {
                            element['timedelta'] = decoration_function(element['timedelta']);
                            return element
                        });
                        DiagnosticGraph.lineChart(diagnosticSensorChartContainerId, data);
                        ChartController.makeResponsive()
                    }

                })
        }
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

        var maxTrace = {
            type: 'line',
            name: 'Max',
            fill: 'tonextx',
            x: raw_data.map(function (d) {
                return d.timedelta;
            }),
            y: raw_data.map(function (d) {
                return +d['max'];
            })
        };

        var meanTrace = {
            type: 'line',
            name: 'Average',
            fill: 'tonexty',
            x: raw_data.map(function (d) {
                return d.timedelta;
            }),
            y: raw_data.map(function (d) {
                return +d['mean'];
            })
        };

        var minTrace = {
            type: 'line',
            name: 'Min',
            x: raw_data.map(function (d) {
                return d.timedelta;
            }),
            y: raw_data.map(function (d) {
                return +d['min'];
            })
        };

        var traces = [minTrace, meanTrace, maxTrace];
        Plotly.newPlot(chartContainerId,
            traces,
            layout,
            ChartController.globalConfig(plotOptions)
        );
    }
}
