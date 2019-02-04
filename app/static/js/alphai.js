$(document).ready(function () {
    moment.tz.setDefault('UTC');
})



var InputFieldController = {
    init: function() {
        $('.limited_input_field').keydown(InputFieldController.onKeyDown)
    },
    onKeyDown: function(e) {
        pattern = /[a-zA-Z0-9\-\_\ ]/g;
        code = e.which;
        var character = e.key;

        if (code==27) { this.blur(); return false; }
        if (!e.ctrlKey && code!=9 && code!=8 && code!=36 && code!=37 && code!=38 && (code!=39 || (code==39 && character=="'")) && code!=40) {
            return !!character.match(pattern)
        }
    }
};



function RefreshStatusTable(selector, resultInterpreter) {

    var self = this;
    this.tableElement = $(selector);
    this.url = $(selector).data('url');
    this.resultInterpreter = resultInterpreter
    this.timer = null;

    this.request = function(){
        $.get({
            url: self.url,
            success: self.onSuccess,
            error: self.onError
        })
    };

    this.onSuccess = function(result) {

        var object = self.resultInterpreter(result);

        self.tableElement.attr("data-completed", object.is_completed);
        self.tableElement.find('tbody tr').remove();

        $(object.statuses).each(function(i, status){
            $row = self.buildRow(status)
            self.tableElement.find('tbody').append($row)
        });

        if (object.is_completed) {
            clearInterval(this.timer)
            location.reload()
        }

        self.refreshElapsedTime(object);
    }

    this.buildRow = function(status){
        $row = $('<tr>');

        var created_at = moment(status.created_at);
        var cell = $('<td>').html(created_at.format("YYYY-MM-DD HH:mm:ss"));
        $row.append(cell);

        var cell = $('<td>').html(status.state);
        $row.append(cell);

        var message = status.message || "None";
        var cell = $('<td>').html(message);
        $row.append(cell);

        return $row;
    };

    this.refreshElapsedTime = function(object) {
        $duration = moment.duration(moment() - moment(object.created_at));
        $duration_string = $duration.format('hh:mm:ss');
        $elapsed_time = $(".elapsed-detection-time").html($duration_string);
    };

    this.onError = function(xhr, status, message) {
        clearInterval(self.timer)
    };

    this.run = function() {
        var completed = self.tableElement.data('completed').toLowerCase() === 'true';
        if (!completed) {
            self.timer = setInterval(self.request, 2000);
        }
    };

    return {
        run: this.run
    }
}


function statusIconBuilder(status) {
    var status_icon = '';

    switch (status) {
        case 'SUCCESSFUL' : {
            status_icon = 'fa-check-circle text-green'
        }
            break;
        case 'FAILED': {
            status_icon = 'fa-warning text-yellow'
        }
            break;
        case 'QUEUED': {
            status_icon = 'fa-hourglass text-blue'
        }
            break;
        default: {
            status_icon = 'fa-gear fa-spin text-light-blue'
        }
    }

    return status_icon
};


function RefreshTaskList(selector, resultInterpreter, rowBuilder) {
    self = this;

    this.tableElement = $(selector);
    this.url_prefix = this.tableElement.attr('data-urlprefix');
    this.timer = null;
    this.resultInterpreter = resultInterpreter;
    this.rowBuilder = rowBuilder;

    this.refresh = function () {
        var pending_elements = self.tableElement.find('tr.task-row').filter(self.isTaskInProgress);

        if (pending_elements.length === 0) {
            clearInterval(self.timer)
        } else {
            pending_elements.each(self.reloadTask)
        }
    };

    this.isTaskInProgress = function (index, task_row) {
        var task_status = $(task_row).attr("data-completed")
        return (task_status.toLowerCase() === "false");
    };

    this.reloadTask = function (i, element) {
        var task_code = $(element).attr('id')
        var url = self.url_prefix + "/" + task_code;
        $.ajax({
            url: url,
            success: self.onSuccess
        })
    };

    this.onSuccess = function (result) {
        var task = self.resultInterpreter(result);

        var $currentRow = self.tableElement.find('tr#' + task.task_code)
        $currentRow.attr('data-completed', task.is_completed ? 'True' : 'False')

        $currentRow.empty();

        var $rowElements = self.rowBuilder(task, self.url_prefix);
        $($rowElements).each(function (i, element) {
            $currentRow.append(element)
        });
    };

    this.run = function () {
        self.timer = setInterval(self.refresh, 1000)
    };

    return {
        run: this.run
    };
}

var MainSpinner ={
    show: function() {
        $('#main-spinner').removeClass('hide');
    },
    hide: function() {
        $('#main-spinner').addClass('hide');
    },
};
