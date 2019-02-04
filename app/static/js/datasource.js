function DataSourceResultInterpreter(result) {
    return result.detection
}

function DataSourceRowBuilder(task, url_prefix) {

    var rowElements = [];

    var $td = $('<td scope="row">');
    $td.append('<a href="' + url_prefix + '/' + task.task_code + '" title="' + task.task_code + '">' + task.name + '</a>');
    rowElements.push($td);

    var $td = $('<td scope="row">' + task.datasource.datasource_configuration.name + '</td>');
    rowElements.push($td);

    var created_at = moment(task.created_at);
    var $td = $('<td>' + created_at.format("YYYY-MM-DD HH:mm:ss") + '</td>');
    rowElements.push($td);

    var $td = $('<td>' + task.datasource.name + '</td>');
    rowElements.push($td)

    var last_status_index = task.statuses.length - 1;
    var last_status = task.statuses[last_status_index].state;
    var icon = statusIconBuilder(last_status)

    status = '<i class="fa ' + icon + '" alt="' + last_status + '"></i>';
    var $td = $('<td>' + status + '</td>');
    rowElements.push($td);

    return rowElements;
}
