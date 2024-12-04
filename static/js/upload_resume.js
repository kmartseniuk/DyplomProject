// static/js/upload_resume.js

$(document).ready(function(){

    $('#uploadForm').on('submit', function(e){
        e.preventDefault();
        $('#progress-container').show();
        $('#progress-bar').css('width', '0%');
        $('#upload-button').prop('disabled', true);

        var formData = new FormData(this);

        $.ajax({
            url: uploadResumeUrl,
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(data){
                if (data.status === 'success') {
                    var taskId = data.task_id;
                    // Start polling for progress updates
                    checkUploadStatus(taskId);
                } else {
                    alert('Помилка при завантаженні резюме.');
                    $('#upload-button').prop('disabled', false);
                    $('#progress-container').hide();
                }
            },
            error: function(){
                alert('Помилка при завантаженні резюме.');
                $('#upload-button').prop('disabled', false);
                $('#progress-container').hide();
            }
        });
    });

    function checkUploadStatus(taskId) {
        var interval = setInterval(function() {
            $.ajax({
                url: '/upload_status/' + taskId,
                type: 'GET',
                success: function(data){
                    if (data.status === 'complete') {
                        clearInterval(interval);
                        $('#uploadResumeModal').modal('hide');
                        $('#upload-button').prop('disabled', false);
                        $('#progress-container').hide();
                        // Refresh resumes table
                        loadResumes(); // Implement this function to refresh the resumes table
                    } else if (data.status === 'in_progress') {
                        var progress = data.progress;
                        $('#progress-bar').css('width', progress + '%');
                        $('#progress-text').text('Завантажено: ' + data.current + '/' + data.total);
                    } else {
                        clearInterval(interval);
                        alert('Помилка при завантаженні резюме.');
                        $('#upload-button').prop('disabled', false);
                        $('#progress-container').hide();
                    }
                },
                error: function(){
                    clearInterval(interval);
                    alert('Помилка при отриманні статусу завантаження.');
                    $('#upload-button').prop('disabled', false);
                    $('#progress-container').hide();
                }
            });
        }, 1000); // Poll every 1 second
    }

    function loadResumes() {
        // Implement this function to reload the resumes table
        // You can use AJAX to get the updated content and update the page
        refreshResumesTable(); // If this function is defined elsewhere
    }
});
