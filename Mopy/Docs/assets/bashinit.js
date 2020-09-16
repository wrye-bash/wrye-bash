/*eslint-disable no-console */
/*eslint-disable no-unused-vars */
/*jslint browser:true */
"use strict";

//* Init: Shared vars
var wbDAEL = document.addEventListener;
var wbRoot = document.documentElement;
var wbSupAEL = false; //! Halts bashfunc.js if false
//* Init: Resource vars
var wbIsChromium = !!window.chrome && (!!window.chrome.webstore || !!window.chrome.runtime);
var wbIsFirefox = typeof InstallTrigger !== "undefined";
var wbIsSafari = /constructor/i.test(window.HTMLElement) || (function (p) { return p.toString() === "[object SafariRemoteNotification]"; })(!window["safari"] || (typeof safari !== "undefined" && safari.pushNotification));

//* BREAK IE<10, else apply JS class
var head = document.getElementsByTagName('head')[0];
var footer = "#footer { text-align: center; }"
function halt(){
	if ((!wbDAEL) || (!wbRoot.classList)) {
		console.log("wbDAEL:",wbDAEL," , wbRoot.classList:",wbRoot.classList)
		fixOldIE(footer);
		throw "Poor support!"; //! Halts both scripts
	}
	wbSupAEL = true; //! Allows bashfunc.js engage
	wbRoot.classList.add("JS-on"); //! Enables JS-specific styles
}
//* Function to fix footers for IE<10
function fixOldIE(style) {
	var node = document.createElement("style");
	if(!wbDAEL) {
		node.type = "text/css";
		node.text = style;
		console.log("Style:", style);
		console.log("Node:", node);
		return head.appendChild(node);
	}
	node.innerHTML = style;
	return head.appendChild(node);
}
//* Check scrollbar style support and apply
function wbScrlApply() {
	if (wbIsFirefox && CSS.supports("scrollbar-color", "#000 #000")) return wbRoot.classList.add("scrlbarFF");
	if ((wbIsChromium)) return wbRoot.classList.add("scrlbarWK");
}

//* Engage
halt();
wbScrlApply();