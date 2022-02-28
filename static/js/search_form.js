function searchFormMain() {
    $('#toggle-filters').click(function (e) {
        $('#search-filter').toggleClass('w3-hide');
        e.preventDefault();
    });
    $('#erase-search-words').click(function (e) {
        $('#search-words-form').val(undefined);
        e.preventDefault();
    });
    $('form').keypress(function(e){
        if(e.keyCode === 13){
            $('#search-form-submit').click();
            e.preventDefault();
        }
    });
    tippy('.lexttip', {
        arrow: true
    });
}

function toggleFixedYear() {
    var dateTo = document.getElementById('lex-filter-date-to');
    if (dateTo.hasAttribute('disabled')) {
        dateTo.removeAttribute('disabled');
        dateTo.value = document.date_to || "";
    }
    else {
        document.date_to = dateTo.value;
        dateTo.setAttribute('disabled', '1');
        dateTo.value = "";
    }
}

function toggleStatusFilter () {
    $('[name="in_force"]').each(function () {
        if (this.hasAttribute('disabled')) {
            this.removeAttribute('disabled')
        }
        else {
            this.setAttribute('disabled', '')
        }
    })
}

function searchFormSubmit() {
    var date_from = document.getElementById('lex-filter-date-from');
    var date_to = document.getElementById('lex-filter-date-to');
    var search_words = document.getElementById('search-words-form');
    if (date_to.value === "") {
        date_to.setAttribute('disabled', '');
    }
    if (date_from.value === "") {
        date_from.setAttribute('disabled', '');
    }
    if (search_words.value === "") {
        search_words.setAttribute('disabled', '');
    }
    var serial_number = document.getElementById('lex-filter-serial-number');
    if (serial_number.value === "") {
        serial_number.setAttribute('disabled', '');
    }
}