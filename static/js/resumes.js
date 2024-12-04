// static/js/resumes.js

$(document).ready(function(){

    // Function to check upload status
    function checkUploadStatus(taskId) {
        var interval = setInterval(function() {
            $.ajax({
                url: '/upload_status/' + taskId,
                type: 'GET',
                success: function(data){
                    if (data.status === 'complete') {
                        clearInterval(interval);
                        // Remove task_id from localStorage
                        localStorage.removeItem('upload_task_id');
                        $('#uploadResumeButton').prop('disabled', false);
                        $('#uploadProgress').hide();
                        refreshResumesTable();
                    } else if (data.status === 'in_progress') {
                        var progress = data.progress;
                        $('#uploadProgressBar').css('width', progress + '%');
                        $('#uploadProgressText').text('Завантажено: ' + data.current + '/' + data.total);
                    } else {
                        clearInterval(interval);
                        // Remove task_id from localStorage
                        localStorage.removeItem('upload_task_id');
                        $('#uploadResumeButton').prop('disabled', false);
                        $('#uploadProgress').hide();
                    }
                },
                error: function(){
                    clearInterval(interval);
                    // Remove task_id from localStorage
                    localStorage.removeItem('upload_task_id');
                    $('#uploadResumeButton').prop('disabled', false);
                    $('#uploadProgress').hide();
                }
            });
        }, 1000); // Poll every 1 second
    }

    // Function to refresh resumes table
    function refreshResumesTable() {
        $.ajax({
            url: dashboardUrl,
            type: 'GET',
            dataType: 'html',
            success: function(response) {
                // Extract the new table from the received HTML page
                var newTable = $(response).find('#resumes-table').html();
                // Update the table on the page
                $('#resumes-table').html(newTable);

                // Update pagination
                var newPagination = $(response).find('.resume-pagination').html();
                $('.resume-pagination').html(newPagination);
            }
        });
    }

    // On page load, check if there's an ongoing upload
    var ongoingTaskId = localStorage.getItem('upload_task_id');
    if (ongoingTaskId) {
        // Show progress bar
        $('#uploadProgress').show();
        $('#uploadResumeButton').prop('disabled', true);
        // Start checking upload status
        checkUploadStatus(ongoingTaskId);
    } else {
        // Hide progress bar if no ongoing upload
        $('#uploadProgress').hide();
        $('#uploadResumeButton').prop('disabled', false);
    }
    
    // Form submission for uploading resumes
    $('#uploadResumeForm').on('submit', function(e){
        e.preventDefault();
        $('#uploadProgress').show();
        $('#uploadResumeButton').prop('disabled', true);

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
                    // Store task_id in localStorage
                    localStorage.setItem('upload_task_id', taskId);
                    // Start checking upload status
                    checkUploadStatus(taskId);
                } else {
                    alert('Помилка при завантаженні резюме.');
                    $('#uploadResumeButton').prop('disabled', false);
                    $('#uploadProgress').hide();
                }
            },
            error: function(){
                alert('Помилка при завантаженні резюме.');
                $('#uploadResumeButton').prop('disabled', false);
                $('#uploadProgress').hide();
            }
        });
    });

    // View and edit resume
    $(document).on('click', '.view-resume', function(event){
        event.preventDefault();
        var resumeId = $(this).data('id');

        var getResumeInfoUrl = resumeUrls.getResumeInfoBase + resumeId;
        var resumePdfUrl = resumeUrls.resumePdfBase + resumeId;

        // Get resume info
        $.get(getResumeInfoUrl, function(data){
            if (data.status !== 'error') {
                $('#resumeId').val(resumeId);
                $('#resumeName').val(data.name);
                $('#resumeEmail').val(data.email || '');
                $('#resumePhone').val(data.phone || '');
                $('#resumeSkills').tagsinput('removeAll');
                $('#resumeKnowledge').tagsinput('removeAll');
                $('#resumeRating').val(data.rating || '');

                var skillsArray = data.skills ? data.skills.split(', ') : [];
                skillsArray.forEach(function(skill){
                    var safeSkill = skill.replace(/"/g, '');
                    $('#resumeSkills').tagsinput('add', safeSkill);
                });
        
                var knowledgeArray = data.knowledge ? data.knowledge.split(', ') : [];
                knowledgeArray.forEach(function(knowledge){
                    var safeKnowledge = knowledge.replace(/"/g, '');
                    $('#resumeKnowledge').tagsinput('add', safeKnowledge);
                });
                // Update favorite icon
                if (data.is_favorite) {
                    $('#favoriteIcon').removeClass('far').addClass('fas').addClass('text-danger');
                } else {
                    $('#favoriteIcon').removeClass('fas').removeClass('text-danger').addClass('far');
                }
                $('#resumeFrame').attr('src', resumePdfUrl);
                $('#resumeModal').modal('show');
            } else {
                alert('Помилка при отриманні даних резюме.');
            }
        });
    });

    // Submit resume edit form
    $('#resumeEditForm').on('submit', function(e){
        e.preventDefault();
        var resumeId = $('#resumeId').val();
        var updateResumeUrl = resumeUrls.updateResumeBase + resumeId;
        var formData = $(this).serialize();
        $.ajax({
            url: updateResumeUrl,
            type: 'POST',
            data: formData,
            success: function(response){
                if(response.status === 'success'){
                    $('#resumeModal').modal('hide');
                    performResumeSearch();
                } else {
                    alert('Помилка при збереженні даних резюме.');
                }
            }
        });
    });

    // Toggle favorite resume from modal
    $('#favoriteResumeButton').on('click', function(){
        var resumeId = $('#resumeId').val();
        $.post(resumeUrls.toggleFavoriteResume, {resume_id: resumeId}, function(data){
            if(data.status === 'success'){
                if(data.is_favorite){
                    $('#favoriteIcon').removeClass('far').addClass('fas').addClass('text-danger');
                } else {
                    $('#favoriteIcon').removeClass('fas').removeClass('text-danger').addClass('far');
                }
                performResumeSearch();
            } else {
                alert('Помилка при оновленні улюбленого резюме.');
            }
        });
    });

    // Delete resume
    $(document).on('click', '.delete-resume', function(event){
        event.preventDefault();
        var resumeId = $(this).data('id');
        var deleteResumeUrl = resumeUrls.deleteResumeBase + resumeId;
        if(confirm('Ви впевнені, що хочете видалити це резюме?')){
            $.post(deleteResumeUrl, function(data){
                if(data.status === 'success'){
                    performResumeSearch();
                } else {
                    alert(data.message);
                }
            });
        }
    });

    // Toggle favorite resume from table
    $(document).on('click', '.favorite-resume', function(){
        var resumeId = $(this).data('id');
        var button = $(this);
        $.post(resumeUrls.toggleFavoriteResume, {resume_id: resumeId}, function(data){
            if(data.status === 'success'){
                if(data.is_favorite){
                    button.find('i').removeClass('far').addClass('fas').addClass('text-danger');
                } else {
                    button.find('i').removeClass('fas').removeClass('text-danger').addClass('far');
                }
                performResumeSearch();
            }
        });
    });

    // Dynamic resume search
    $('#name_search, #skill_search, #knowledge_search').on('input', function(){
        performResumeSearch();
    });

    $('#has_phone, #has_email, #has_rating').on('change', function(){
        performResumeSearch();
    });

    function performResumeSearch(){
        var params = $('#resume-search-form').serializeArray();
        var currentPage = 1; // Reset to page 1 on search or filter change
        params.push({ name: 'resume_page', value: currentPage });
        $.get(dashboardUrl, $.param(params), function(data){
            var newResumesTable = $(data).find('#resumes-table').html();
            $('#resumes-table').fadeOut(200, function(){
                $(this).html(newResumesTable).fadeIn(200);
                $('#resumes-table tbody tr').addClass('table-row');
            });
            // Update pagination
            var newPagination = $(data).find('.resume-pagination').html();
            $('.resume-pagination').html(newPagination);
        });
    }

    $('#knowledge_search').autocomplete({
        source: function(request, response) {
            $.ajax({
                url: resumeUrls.autocompleteKnowledge,
                data: { term: request.term },
                success: function(data) {
                    response(data);
                }
            });
        },
        minLength: 2,
        select: function(event, ui) {
            $('#knowledge_search').val(ui.item.value);
            performResumeSearch();
        }
    });

    $('#skill_search').autocomplete({
        source: function(request, response) {
            $.ajax({
                url: resumeUrls.autocompleteSkills,
                data: { term: request.term },
                success: function(data) {
                    response(data);
                }
            });
        },
        minLength: 2,
        select: function(event, ui) {
            $('#skill_search').val(ui.item.value);
            performResumeSearch();
        }
    });    

    // Handle per_page changes
    $('#resumePerPage').on('change', function(){
        performResumeSearch();
    });

    // Pagination for resumes
    $(document).on('click', '.resume-pagination a', function(e){
        e.preventDefault();
        var href = $(this).attr('href');
        $.get(href, function(data){
            var newResumesTable = $(data).find('#resumes-table').html();
            $('#resumes-table').fadeOut(200, function(){
                $(this).html(newResumesTable).fadeIn(200);
                $('#resumes-table tbody tr').addClass('table-row');
            });
            // Update pagination
            var newPagination = $(data).find('.resume-pagination').html();
            $('.resume-pagination').html(newPagination);
        });
    });

    // Button hover effects
    $('.btn').hover(
        function(){
            $(this).css({'background-color': '#0056b3', 'color': '#fff'});
        },
        function(){
            $(this).css({'background-color': '', 'color': ''});
        }
    );

    // Removed the call to checkUploadStatus() from refreshResumesTable()

});
