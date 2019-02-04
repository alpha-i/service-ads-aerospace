
var ProgressBar = {
    create: function () {
        var $progressBar = $("<div>");
        $progressBar.addClass("progress-bar progress-bar-green progress-bar-striped");
        $progressBar.attr("role", "progressbar");
        $progressBar.attr("aria-valuenow", "0");
        $progressBar.attr("aria-valuemin", "0");
        $progressBar.attr("aria-valuemax", "100");
        $progressBar.css("width", "0%");

        $(".progress").empty();
        $(".progress").append($progressBar);
    },
    update: function (value) {
        var $bar = $(".progress-bar");

        if (value >= 100) {
            $bar.addClass("active");
        } else {
            $bar.removeClass("active");
        }
        var percent = value + "%";
        $bar.css("width", percent);
        $(".percent").html(percent);
    },
    show: function() {
        $("#progress_container").removeClass("hide");
    },
    hide: function() {
         $("#progress_container").addClass("hide");
    }
};

var ProgressCounter = {
    update: function(bytesUploaded, totalBytes) {
        var megabytesUploaded = Utils.bytesToMegabytes(bytesUploaded);
        $(".bytes_uploaded").html(megabytesUploaded);

        var totalBytes = Utils.bytesToMegabytes(totalBytes);
        $(".bytes_total").html(totalBytes);
    },
    reset: function() {
        $(".bytes_uploaded").html();
        $(".bytes_total").html();
    }
};

var Utils = {
    bytesToMegabytes: function (bytes) {
        mb = bytes/1048576;
        return Utils.precisionRound(mb, 2)
    },
    precisionRound: function (number, precision) {
        var factor = Math.pow(10, precision);
        var converted = Math.round(number * factor) / factor;
        return parseFloat(converted).toFixed(2);
    },
};

var MessageArea = {
    addError: function(message){
        var $alert = $("<div class='alert alert-warning'>");
        $alert.html(message);

        $("#message_area").html($alert)
    },
    addInfo: function(message) {
        var $alert = $("<div class='alert alert-info'>");
        $alert.html(message);

        $("#message_area").html($alert)
    },
    clean: function() {
        $("#message_area").empty()
    }
};

var FileController = {
    init: function() {
        var $browseBtn = $('#browse_btn');
        var $filePath = $('#file_path');
        var $uploadInput = $('#upload');
        var $submitBtn = $('#submit');

        $browseBtn.click(function (e) {
            e.preventDefault();
            $uploadInput.click();
        });

        $uploadInput.change(function () {
            MessageArea.clean();
            $submitBtn.attr('disabled', true);
            var $upload = $(this);

            $filePath.val($upload.val());
            if (FileController.isValidFile($upload)) {
                $submitBtn.attr('disabled', false)
            }
        });

        $filePath.click(function () {
            $browseBtn.click();
        });
    },
    isValidFile: function($upload) {

        if ($.trim($upload.val()) == "") {
            return false;
        }
        if (window.FileReader && window.Blob) {
            var max_size = $upload.data("maxsize");
            var file_list = $upload[0].files;
            if (file_list.length !== 1) {
                return false
            } else if (file_list[0].size < max_size) {
                return true;
            } else {
                max_size_mb = Math.round(max_size/1000000);
                MessageArea.addError("Wrong file size. Max File Size " + max_size_mb + " MB");
                return false;
            }
        }
        return true;
    },
};

var UploadForm = {

    hide: function() {
        $("#upload_form").hide();
    },
    show: function() {
         $("#upload_form").show();
    },
    resetForm: function () {
        $("#upload_form").resetForm();
        $('#submit').attr('disabled', true);
    },
    init: function () {
        FileController.init();
        InputFieldController.init()
        MessageArea.clean();
        ProgressBar.hide();

        $("#upload_form").ajaxForm({
            beforeSend: UploadForm.beforeSend,
            uploadProgress: UploadForm.onProgress,
            error: UploadForm.onError,
            success: UploadForm.onSuccess,
            complete: UploadForm.onComplete
        })
    },
    onCancel: function (event) {
        event.data.abort();
        MessageArea.clean();
        UploadForm.resetForm();
        ProgressBar.hide()
    },
    beforeSend: function (xhr) {
        ProgressBar.create();
        MessageArea.clean();
        ProgressBar.show();

        var $cancelBtn = $('#upload_cancel_btn');
        $cancelBtn.removeClass('hide');
        $cancelBtn.click(xhr, UploadForm.onCancel)
    },
    onProgress: function (event, bytesUploaded, total, percent) {
        ProgressCounter.update(bytesUploaded, total);
        if (percent === 100) {
            UploadForm.onPercentComplete()
        }
        ProgressBar.update(percent);
    },
    onSuccess: function (response, status, xhr) {
        window.location.href = xhr.getResponseHeader('Location');
    },
    onError: function (xhr, status) {
        if (status !== 'abort') {
            switch (xhr.status) {
                case 0:
                case 401:
                case 403:
                    message = "Your session has expired. You will be redirected to the login page in few seconds."
                    window.setTimeout(function () {
                        window.location.reload()
                    }, 2000);
                    break;
                default:
                    var response_data = xhr.responseJSON || {};
                    var message = response_data.message || "(" + xhr.status + "): " + xhr.statusText;
                    message = message.split('|').join('<br/>')
                    break;
            }
            MessageArea.addError(message);
        }
        UploadForm.resetForm();
        ProgressBar.hide()
    },
    onComplete: function (xhr) {
        ProgressBar.update(100);
    },
    onPercentComplete : function() {
        processing_message = "Processing file..please wait. &nbsp; &nbsp;<i class='fa fa-spinner fa-spin'></i>"
        MessageArea.addInfo(processing_message);
        $("#upload_cancel_btn").addClass("hide");
    }
};
