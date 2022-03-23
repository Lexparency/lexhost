
// Get the Sidebar
var mySidebar = document.getElementById("mySidebar");
var ToCScrolled = false;

// Get the DIV with overlay effect
var overlayBg = document.getElementById("myOverlay");

function adaptSideBarHeight() {
    var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
    var sidebarHeadHeight = document.getElementById('sidebarHead').offsetHeight;
    $('#sidebarBody').height(viewPortHeight - sidebarHeadHeight);
}

function sidebarMain() {
    adaptSideBarHeight();
    window.addEventListener('resize', adaptSideBarHeight);

    $('.lxp-sidebarswitch').on('click', function (){
        $('.lxp-sidebarswitch').toggleClass('w3-hide');
        $('.lxp-sidebar-head-body').toggleClass('w3-hide');
        adaptSideBarHeight();
        $('.lxp-sidebar-body').toggleClass('w3-hide');
    });
}

function scrollToActiveElement() {
    if (!ToCScrolled) {
        var toccordion = $('#toccordion');
        var sidebar_body = $('#sidebarBody');
        var active_node = toccordion.find("a[href='" + location.pathname + "']").parent('li');
        if (active_node.length === 0) {
            active_node = toccordion.find("a[href='" + location.pathname.slice(0, -1) + "']").parent('li');
        }
        if (active_node.length === 1) {
            sidebar_body.animate({
                scrollTop: active_node.offset().top - 300
            }, 1000);
        }
        ToCScrolled = true;
    }
}

// Toggle between showing and hiding the sidebar, and add overlay effect
function w3_open() {
    if (mySidebar.style.display === 'block') {
        mySidebar.style.display = 'none';
        overlayBg.style.display = "none";
    } else {
        mySidebar.style.display = 'block';
        overlayBg.style.display = "block";
        adaptSideBarHeight();
        scrollToActiveElement();
    }
}

// Close the sidebar with the close button
function w3_close() {
    mySidebar.style.display = "none";
    overlayBg.style.display = "none";
}