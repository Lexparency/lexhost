function toggle_image(img) {
    if (img.attr('src') === '/static/icons/minus-square-o.svg') {
        img.attr('src', '/static/icons/plus-square-o.svg');
    }
    else {
        img.attr('src', '/static/icons/minus-square-o.svg');
    }
}

// noinspection JSUnusedGlobalSymbols
function toggle_node (node) {
    toggle_image(node.find('> a > img'));
    node.find('> ul > li').toggleClass('w3-hide');
    return false;
}

function toggle_meta_body(node) {
    toggle_image(node.prev().find('> a > img'));
    node.toggleClass('w3-hide');
    return false;
}

function get_current_url() {
    return window.location.href.split('#')[0].split('&')[0]
}

function get_pilcrow(li) {
    var p = $(li).find('> a.lxp-pilcrow');
    if (p.length === 0) {
        p = document.createElement('a');
        p.innerHTML = '&para;&nbsp;&nbsp;';
        $(p).addClass('lxp-pilcrow');
        p.setAttribute('href',
            get_current_url() + '#' + $(li).attr('id'));
        p.setAttribute('title',
            document.getElementById('permalink_to_this_p').innerText)
        $(li).append(p);
        return $(p)
    }
    return p
}


function href_2_id(href) {
    return href.replaceAll('/', 'Z')
        .replace('#', 'X');
}


function get_from_preview_cache(href) {
    var cached = $('#' + href_2_id(href));
    if (cached.length !== 0) {
        return cached.html();
    }
    return null;
}


// noinspection JSUnusedGlobalSymbols
function adaptBodyHeight() {
    var viewPortHeigh = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
    var footerHeight = $('footer')[0].offsetHeight;
    var topSpaceDummyHeight = $('#topSpaceDummy')[0].offsetHeight;
    $('#mainBody').css("min-height", function () {
        return viewPortHeigh - footerHeight - topSpaceDummyHeight;
    })
}


function get_cover_path(path) {
    var dom_id = path.split('#')[0].split('/').slice(1, 3);
    return '/' + dom_id[0] + '/' + dom_id[1] + '/'
}


function readerMain(overview) {
    // Setting up the environment
    var location_path = window.location.pathname;
    var preview = $('#preview');
    var preview_head = $('#preview-head');
    var preview_body_loaded = $('#preview-body-loaded');
    var preview_body = $('#preview-body');
    var sidebar_body = $('#sidebarBody');
    var toccordion = $('#toccordion');
    var loading_img = $('#loading-img');
    var toggle_previews = (window.innerWidth > 992);
    var cache_container = $('#previewContents');

    adaptBodyHeight();
    window.addEventListener('resize', adaptBodyHeight);

    if (window.location.hash !== "") {
        $(window.location.hash).addClass('lxp-focus')
    }
    window.addEventListener("hashchange", function () {
        $('.lxp-focus').removeClass('lxp-focus');
        $(window.location.hash).addClass('lxp-focus')
    }, false);

    if (!overview) {
        var active_node = toccordion.find("a[href='" + location_path + "']").parent('li');
        if (active_node.length === 0) {
            active_node = toccordion.find("a[href='" + location_path.slice(0, -1) + "']").parent('li');
        }
        toccordion.find('li.toc-node').each(function (index, element) { toggle_node($(element)); });

        active_node.parents('li.toc-node').each(function (index, element) {toggle_node($(element))});
        active_node.addClass('w3-leftbar');

        sidebar_body.animate({
            scrollTop: active_node.offset().top - 300
        }, 1000);

        function handlerOut () {  // on exit
            if (preview.height() !== 0) {
                preview.height(0);
                preview_head.toggleClass('w3-hide');
                preview_body.toggleClass('w3-hide');
                sidebar_body.toggleClass('w3-hide');
                preview_head.html('Loading preview');
                preview_body_loaded.html('');
            }
        }
        if (toggle_previews) {
            $('#article').find('a[href^="/"], a[href^="#"]').hoverIntent(
                function () {  // on entry
                    preview_head.html($(this).attr('data-content-heading'));
                    preview.height(sidebar_body.height());
                    sidebar_body.toggleClass('w3-hide');
                    preview_head.toggleClass('w3-hide');
                    preview_body.toggleClass('w3-hide');
                    var preview_url = $(this).attr('href');
                    if (preview_url[0] === '#') {
                        preview_head.html('');
                        preview_body_loaded
                            .html($(preview_url.replace(':', '\\:')).html());
                    }
                    else {
                        var url_base = get_cover_path(preview_url);
                        var cached = get_from_preview_cache(preview_url);
                        if (cached !== null) {
                            preview_body_loaded.html(cached)
                        }
                        else {
                            loading_img.toggleClass('w3-hide');
                            if (preview_url.indexOf('#') > -1) {
                                preview_url = preview_url.replace(/#/, '?snippet=');
                            }
                            else {
                                preview_url = preview_url + '?snippet=0';
                            }
                            preview_body_loaded.load(preview_url,
                                function(response, status, _) {
                                    loading_img.toggleClass('w3-hide');
                                    if (status === 'error') {
                                        handlerOut();
                                        // noinspection JSCheckFunctionSignatures
                                        $('#article')
                                            .find('a[href^="' + url_base + '"]')
                                            .replaceWith(function() {
                                                return $('<span/>', {html: this.innerHTML})
                                            }
                                        );
                                    }
                                }
                            );
                        }
                    }
                },
                function () {
                    var cache_hash = href_2_id($(this).attr('href'));
                    if ($('#' + cache_hash).length === 0) {
                        var cache = document.createElement('div')
                        cache.setAttribute('id', cache_hash)
                        cache.innerHTML = preview_body_loaded.html();
                        cache_container.append(cache);
                    }
                    handlerOut();
                }
            );
        }
    }
    else {
        $('.nat-ref-list').each(function (index, element) { toggle_node($(element)); });
    }

    $('li.toc-node > a').on('click',function (e) {
        toggle_node($(this).parent());
        e.preventDefault()
    });

    $('div.lxp-meta-head > a').on('click',function (e) {
        toggle_meta_body($(this).parent().next('div.lxp-meta-body'));
        e.preventDefault()
    });

    $('#article li[id]').mouseenter(
        function () {
            var p = get_pilcrow(this);
            if (p.css('display') === 'none') {
                p.css('display', 'block')
            }
            $('a.lxp-pilcrow').each(function () {
                if ($(this).attr('href') !== p.attr('href')) {
                    $(this).css('display', 'none')
                }
            })
        }
    )

    // Make the document search form reappear on small devices.
    $('#search-button').on('click',function () {
        $('#search-input').toggleClass('w3-hide-small')
    });

    $('table.table').addClass('w3-table-all');

    tippy('.versionSign', {
        arrow: true,
        html: '#versionsList',
        trigger: 'click',
        placement: 'bottom',
        interactive: true
    }) ;
}


// noinspection JSUnusedGlobalSymbols
function articleJumper(){
  tippy('#leafButton', {
    onShown: function(_) {
      var numberInput = $(this).find('input[name="articleNumber"]');
      numberInput.focus();
      $('form.leafForm').keypress(function(e) {
        if (e.key === "Enter") {
          var articleNumber = numberInput.val();
          if (articleNumber === "") {
            e.preventDefault();
          }
          else {
            var basicAction = $(this).attr('data-basic-action');
            $(this).attr('action', basicAction + articleNumber + '/');
          }
        }
      });
    },
    arrow: true,
    html: '#goToLeaf',
    trigger: 'click',
    placement: 'bottom',
    interactive: true
  })
}
