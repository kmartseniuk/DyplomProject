// static/js/jobs.js

$(document).ready(function(){
    // Function to perform job search and update the table
    function performJobSearch(){
        var params = $('#job-search-form').serializeArray();
        var currentPage = 1; // Reset to first page on search change
        params.push({ name: 'job_page', value: currentPage });
        $.get(dashboardUrl, $.param(params), function(data){
            var newJobsTable = $(data).find('#jobs-table').html();
            $('#jobs-table').fadeOut(200, function(){
                $(this).html(newJobsTable).fadeIn(200);
                $('#jobs-table tbody tr').addClass('table-row');
            });
            // Update pagination
            var newPagination = $(data).find('.job-pagination').html();
            $('.job-pagination').html(newPagination);
        });
    }

    // Event listeners for search inputs
    $('#job_name_search, #job_skill_search, #job_knowledge_search').on('input', function(){
        performJobSearch();
    });

    // Handle per_page changes
    $('#jobPerPage').on('change', function(){
        performJobSearch();
    });

    // Pagination for jobs
    $(document).on('click', '.job-pagination a', function(e){
        e.preventDefault();
        var href = $(this).attr('href');
        $.get(href, function(data){
            var newJobsTable = $(data).find('#jobs-table').html();
            $('#jobs-table').fadeOut(200, function(){
                $(this).html(newJobsTable).fadeIn(200);
                $('#jobs-table tbody tr').addClass('table-row');
            });
            // Update pagination
            var newPagination = $(data).find('.job-pagination').html();
            $('.job-pagination').html(newPagination);
        });
    });

    // Autocomplete for job skills
    $('#job_skill_search').autocomplete({
        source: function(request, response) {
            $.ajax({
                url: jobUrls.autocompleteJobSkills,
                data: { term: request.term },
                success: function(data) {
                    response(data);
                }
            });
        },
        minLength: 2,
        select: function(event, ui) {
            $('#job_skill_search').val(ui.item.value);
            performJobSearch();
        }
    });

    // Autocomplete for job knowledge
    $('#job_knowledge_search').autocomplete({
        source: function(request, response) {
            $.ajax({
                url: jobUrls.autocompleteJobKnowledge,
                data: { term: request.term },
                success: function(data) {
                    response(data);
                }
            });
        },
        minLength: 2,
        select: function(event, ui) {
            $('#job_knowledge_search').val(ui.item.value);
            performJobSearch();
        }
    });

    // Add job
    $('#addJobForm').on('submit', function(e){
        e.preventDefault();
        var formData = $(this).serialize();
        $('#addJobForm button[type="submit"]').prop('disabled', true);
        $.ajax({
            url: jobUrls.addJobUrl,
            type: 'POST',
            data: formData,
            success: function(response){
                $('#addJobForm button[type="submit"]').prop('disabled', false);
                if(response.status === 'success'){
                    $('#addJobModal').modal('hide');
                    performJobSearch();
                } else {
                    alert('Помилка при додаванні вакансії.');
                }
            }
        });
    });

    // Edit job
    $(document).on('click', '.edit-job', function(event){
        event.preventDefault();
        var jobId = $(this).data('id');

        // Get job info via AJAX
        $.get(jobUrls.getJobInfoBase + jobId, function(data){
            if (data.status !== 'error') {
                $('#jobId').val(jobId);
                $('#jobTitle').val(data.title);
                $('#jobDescription').val(data.description);

                // Clear and add skills
                $('#jobSkills').tagsinput('removeAll');
                if (data.skills) {
                    var skillsArray = data.skills.split(', ');
                    skillsArray.forEach(function(skill){
                        $('#jobSkills').tagsinput('add', skill);
                    });
                }

                // Clear and add knowledge
                $('#jobKnowledge').tagsinput('removeAll');
                if (data.knowledge) {
                    var knowledgeArray = data.knowledge.split(', ');
                    knowledgeArray.forEach(function(item){
                        $('#jobKnowledge').tagsinput('add', item);
                    });
                }

                $('#jobModal').modal('show');
            } else {
                alert('Помилка при отриманні даних вакансії.');
            }
        });
    });

    // Submit job edit form
    $('#jobEditForm').on('submit', function(e){
        e.preventDefault();
        var jobId = $('#jobId').val();
        var updateJobUrl = jobUrls.updateJobBase + jobId;
        var formData = $(this).serialize();
        $.ajax({
            url: updateJobUrl,
            type: 'POST',
            data: formData,
            success: function(response){
                if(response.status === 'success'){
                    $('#jobModal').modal('hide');
                    performJobSearch(); // Update jobs table
                } else {
                    alert('Помилка при збереженні даних вакансії.');
                }
            },
            error: function(){
                alert('Помилка при збереженні даних вакансії.');
            }
        });
    });

    // Delete job
    $(document).on('click', '.delete-job', function(event){
        event.preventDefault();
        var jobId = $(this).data('id');
        var deleteJobUrl = jobUrls.deleteJobBase + jobId;
        if(confirm('Ви впевнені, що хочете видалити цю вакансію?')){
            $.post(deleteJobUrl, function(data){
                if(data.status === 'success'){
                    performJobSearch();
                } else {
                    alert(data.message);
                }
            });
        }
    });
});
