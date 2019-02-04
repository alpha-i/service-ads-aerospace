

function TrainingTaskRowBuilder(task, url_prefix) {


    var rowElements = [];

    var $td = $('<td scope="row">');
    $td.append('<a href="' + url_prefix + '/' + task.task_code + '" title="' + task.task_code +'">' + task.name + '</a>');
    rowElements.push($td);

    var $td = $('<td scope="row">' + task.datasource_configuration.name + '</td>');
    rowElements.push($td);

    var domain = task.has_fft_enabled ? 'Frequency' : 'Time';
    var $td = $('<td scope="row">' + domain + '</td>');
    rowElements.push($td);

    var $td = $('<td scope="row">' + task.datasources.length + ' flight(s)</td>');
    rowElements.push($td);

    var created_at = moment(task.created_at);
    var $td = $('<td>' + created_at.format("YYYY-MM-DD HH:mm:ss") + '</td>');
    rowElements.push($td);

    var last_status_index = task.statuses.length - 1;
    var last_status = task.statuses[last_status_index].state;
    var icon = statusIconBuilder(last_status)

    status = '<i class="fa ' + icon + '" alt="' + last_status + '"></i>';
    var $td = $('<td>' + status + '</td>');
    rowElements.push($td);

    return rowElements
};


function ParentTrainingInputController(sourceSelect, targetSelect, url) {

    var self = this;
    this.url = url;

    this.sourceSelect = $(sourceSelect);
    this.targetSelect = $(targetSelect);

    this.onFlightTypeSelect = function(){
        MainSpinner.show();
     $.get({
            url: self.url,
            data: {datasource_config_id: self.sourceSelect.val(), valid_only: true},
            success: self.onFlightTypeSuccess,
            error: self.onError
        })
    }

    this.onFlightTypeSuccess = function(result) {

        self.targetSelect.empty();
        self.targetSelect.append($('<option>', {
            value: "",
            text: "Choose Parent Training (optional)"
        }));

        if (!result.training_task_list) {
            return
        }

        var training_task_list = result.training_task_list;

        $(training_task_list).each(function(i, el){
            self.targetSelect.append($('<option>', {
            value: el.id,
            text: el.name
            }));
        });
        MainSpinner.hide();
    };

    this.onParentSelect = function(event) {

        MainSpinner.show();

        var $elementValue = $(event.target).val();
        var $domainSelector = $('#enable_fft');
        var domainHiddenId = 'hidden_enable_fft';


        var downsampleHiddenId = 'hidden_downsample_id';
        var $downsampleSelector = $('#downsample_factor');

        function createHiddenInput(domainHiddenId, val, name) {
            var $hiddenInput = $('<input type="hidden">');
            $hiddenInput.attr('id', domainHiddenId);
            $hiddenInput.val(val);
            $hiddenInput.attr('name', name);

            return $hiddenInput;
        }
        $('#' + domainHiddenId).remove();
        $('#' + downsampleHiddenId).remove();

        if ($elementValue.trim() === "") {
            $domainSelector.prop('disabled', false);
            $downsampleSelector.prop('disabled', false);
        } else {

            var $domainHiddenInput = createHiddenInput(
                domainHiddenId,
                $domainSelector.val(),
                $domainSelector.attr('name')
            );
            $domainSelector.parent().append($domainHiddenInput);
            $domainSelector.prop('disabled', true);

            var $downsampleHiddenInput = createHiddenInput(
                downsampleHiddenId,
                $downsampleSelector.val(),
                $downsampleSelector.attr('name')
            )

            $downsampleSelector.prop('disabled', true);
            $downsampleSelector.parent().append($downsampleHiddenInput);
        }

         MainSpinner.hide();
    };

    this.onError = function () {
        MainSpinner.hide();
    };

    this.sourceSelect.on('change', this.onFlightTypeSelect);
    this.targetSelect.on('change', this.onParentSelect)
}
