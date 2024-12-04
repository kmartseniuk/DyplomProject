// static/js/rank_resumes.js

$(document).ready(function(){

    var rankingTable;

    // Attach event handlers
    $('#start-ranking').on('click', function(){
        startRanking();
    });

    // Function to start the ranking process
    function startRanking(){
        $('#progress-container').show();
        $('#ranking-results').hide();
        $('#progress-bar').css('width', '0%');
        $('#progress-text').text('Ранжування триває...');
        $.ajax({
            url: processRankingUrl,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ model: 'all' }),
            success: function(data){
                if(data.status === 'success'){
                    var taskId = data.task_id;
                    // Start polling for progress updates
                    checkRankingStatus(taskId);
                } else {
                    alert('Помилка при запуску ранжування.');
                    window.location.href = dashboardUrl;
                }
            },
            error: function(){
                alert('Помилка при запуску ранжування.');
                window.location.href = dashboardUrl;
            }
        });
    }

    // Function to check the ranking status periodically
    function checkRankingStatus(taskId) {
        var interval = setInterval(function() {
            $.ajax({
                url: '/ranking_status/' + taskId,
                type: 'GET',
                success: function(data){
                    if (data.status === 'complete') {
                        clearInterval(interval);
                        fetchRankingResults();
                    } else if (data.status === 'in_progress') {
                        var progress = data.progress;
                        $('#progress-text').text('Ранжування: ' + data.current + '/' + data.total);
                        $('#progress-bar').css('width', progress + '%');
                    } else {
                        clearInterval(interval);
                        alert('Помилка при ранжуванні резюме.');
                        window.location.href = dashboardUrl;
                    }
                },
                error: function(){
                    clearInterval(interval);
                    alert('Помилка при отриманні статусу ранжування.');
                    window.location.href = dashboardUrl;
                }
            });
        }, 1000); // Poll every 1 second
    }

    // Function to fetch and display the ranking results
    function fetchRankingResults(){
        $.get(rankingResultsUrl, function(data){
            // Update the ranking results div directly
            $('#ranking-results').html(data);
            $('#progress-container').hide();
            $('#ranking-results').show();

            // Initialize DataTable
            initializeRankingTable();

            // Re-attach event listeners for resume viewing and favorite toggling
            attachEventListeners();
        });
    }

    // Function to initialize DataTable
    function initializeRankingTable(){
        rankingTable = $('#rankingResultsTable').DataTable({
            "pageLength": 100,
            "lengthMenu": [ [100, 200, 500, 1000, -1], [100, 200, 500, 1000, "Всі"]],
            "order": [[3, "desc"]],  // Default ordering by "Загальна відповідність"
            "columns": [
                null,   // Кандидат
                {   // Навички (відповідність по навичкам)
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data);
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                {   // Знання (відповідність по знанням)
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data);
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                {   // Загальна відповідність
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data);
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                {   // Sentence-BERT
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data);
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                {   // TF-IDF
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data);
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                {   // GloVe
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data);
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                {   // BM25
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data);
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                null,   // Ключові слова
                {   // Оцінка
                    "type": "num",
                    "render": function(data, type, row) {
                        if (type === 'sort') {
                            var val = parseFloat(data.replace('★', ''));
                            return isNaN(val) ? 0 : val;
                        }
                        return data;
                    }
                },
                null    // Улюблене
            ],
            "destroy": true,
            "language": {
                "url": languageUrl  // Use the languageUrl variable defined in your template
            }
        });

        // Apply custom filtering
        $('#hasPhoneFilter, #hasEmailFilter, #hasRatingFilter').on('change', function(){
            rankingTable.draw();
        });

        $.fn.dataTable.ext.search.push(
            function(settings, data, dataIndex){
                var hasPhoneFilter = $('#hasPhoneFilter').is(':checked');
                var hasEmailFilter = $('#hasEmailFilter').is(':checked');
                var hasRatingFilter = $('#hasRatingFilter').is(':checked');
        
                var resumeRow = rankingTable.row(dataIndex).node();
                var $resumeRow = $(resumeRow);
        
                var hasPhone = $resumeRow.attr('data-has-phone') === 'true';
                var hasEmail = $resumeRow.attr('data-has-email') === 'true';
                var hasRating = $resumeRow.attr('data-has-rating') === 'true';
        
                if (hasPhoneFilter && !hasPhone) {
                    return false;
                }
                if (hasEmailFilter && !hasEmail) {
                    return false;
                }
                if (hasRatingFilter && !hasRating) {
                    return false;
                }
                return true;
            }
        );        
        
    }

    // Function to attach event listeners to dynamically added elements
    function attachEventListeners(){
        // View and edit resume
        $('.view-resume').on('click', function(event){
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
                    $('#resumeFeedback').val(data.feedback || '');

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
                        // Optionally refresh the ranking results if data changed
                        fetchRankingResults();
                    } else {
                        alert('Помилка при збереженні даних резюме.');
                    }
                }
            });
        });

        // Toggle favorite resume from the table
        $('.favorite-resume').on('click', function(){
            var resumeId = $(this).data('id');
            var button = $(this);
            $.post(resumeUrls.toggleFavoriteResume, {resume_id: resumeId}, function(data){
                if(data.status === 'success'){
                    if(data.is_favorite){
                        button.find('i').removeClass('far').addClass('fas').addClass('text-danger');
                    } else {
                        button.find('i').removeClass('fas').removeClass('text-danger').addClass('far');
                    }
                    // Optionally refresh the ranking results
                    fetchRankingResults();
                } else {
                    alert('Помилка при оновленні улюбленого резюме.');
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
                    // Optionally refresh the ranking results if data changed
                    fetchRankingResults();
                } else {
                    alert('Помилка при оновленні улюбленого резюме.');
                }
            });
        });
    }

    // Initialize DataTable if results are already present
    if ($('#rankingResultsTable').length > 0) {
        initializeRankingTable();
        attachEventListeners();
    }


});
