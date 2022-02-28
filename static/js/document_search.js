function documentSearchMain() {
    $('input[name="search_words"]').keypress(function (e) {
        if (e.keyCode === 13) {
            if ($(this).val() === '') {
                e.preventDefault()
            }
        }
    })
}