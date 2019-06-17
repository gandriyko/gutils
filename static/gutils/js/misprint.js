var loc = window.location;
var text;

function getSelected (){
    var t = '';
    if (window.getSelection) {
        t = window.getSelection();
    }
    else if(document.getSelection) {
        t = document.getSelection();
    } else if(document.selection){
        t = document.selection.createRange().text;
    }
    return t;
}

function getText(e) {
	if (!e) {
        e = window.event;
    }
    if ((e.ctrlKey) && ((e.keyCode==10) || (e.keyCode==13))) {
        var text = getSelected();
        if (!text) text = '';
        document.location.href = encodeURI('/misprint/?t=' + text + '&p=' + document.location.href);
    }
}

document.onkeypress = getText;