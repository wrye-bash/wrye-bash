/*eslint-disable no-console */
/*eslint-disable no-unused-vars */
/*jslint browser:true */
"use strict";


/*
* Javascript-available Initialization
*/
//* BREAK: IE<9
var wbDateYear = new Date().getFullYear();
if (!wbSupAEL) throw new Error("Woah there Dr. Hammond, let's talk about the dinosaur in the room. It's " + wbDateYear + " and your browser's looking a little outdated. Wrye Bash may have come out in 2006, but we have higher standards these days!");
//* Init: Resource vars
var wbFade;
var wbFigures;
var wbNavCls;
var wbNavMnu;
var wbNavSubLst;
var wbNavTab;
//* Ready Check 
function wbPgRdy(doTheThing) {
	if (document.readyState != "loading") return doTheThing();
	if (document.addEventListener) document.addEventListener("DOMContentLoaded", doTheThing);
}


/*
* Begin Heavy Manipulation
*/
//* DOM Has Loaded Frame
wbPgRdy(function() {
	// Set: DOM Resource vars
	wbDOMRVar();
	// Set: DOMContent Listeners
	wbDOMList();
	// Test Buttons
	wbJSSwitch();
	// Init: Slideshow
	wbFigGrab();
});
//* Set: DOM Resource vars
function wbDOMRVar() {
	wbFade = document.getElementById("fade");
	wbFigures = document.getElementsByClassName("slideshow");
	wbNavCls = document.getElementById("closebutton");
	wbNavMnu = document.getElementById("navmenu");
	wbNavSubLst = document.getElementsByClassName("list");
	wbNavTab = document.getElementById("navtab");
}
//* Set: DOMContent Listeners
function wbDOMList() {
	wbFade.addEventListener("click", wbNavClose);
	wbNavCls.addEventListener("click", wbNavClose);
	Object.keys(wbNavSubLst).forEach(function(i) {
		wbNavSubLst[i].addEventListener("click", wbNavSubAcc);
	})
	wbNavTab.addEventListener("click", wbNavOpen);
}


/*
* Navmenu Functions
*/
//* Test Buttons
function wbJSSwitch() {
	var wbJSTog = document.getElementById("jstoggle");
	wbJSTog.addEventListener("click", wbJSToggle);
}
function wbJSToggle() {
	if (wbRoot.classList.contains("JS-on")) return wbRoot.classList.remove("JS-on");
	if (!wbRoot.classList.contains("JS-on")) return wbRoot.classList.add("JS-on");
}
//* Menu
function wbNavOpen() {
	wbNavMnu.style.left = "0";
	wbFade.style.opacity = "1";
	wbFade.style.visibility = "visible";
	wbNavTab.removeEventListener("click", wbNavOpen);
	wbNavTab.addEventListener("click", wbNavClose);
}
function wbNavClose() {
	wbNavMnu.style.left = "-15.625rem";		// 250px
	wbFade.style.opacity = "0";
	wbFade.style.visibility = "hidden";
	wbNavTab.removeEventListener("click", wbNavClose);
	wbNavTab.addEventListener("click", wbNavOpen);
}
function wbNavSubAcc(sect) {
	sect.stopPropagation();
/* Single Depth Menus */
	if (!sect.currentTarget.classList.contains("active")) {
		Object.keys(wbNavSubLst).forEach(function(i) { wbNavSubLst[i].classList.remove("active"); })
		sect.currentTarget.classList.add("active");
	}
/* Original Menu Code */
/* 
	if (sect.currentTarget.classList.contains("active")) {
		sect.currentTarget.classList.remove("active");
	}
	else if (sect.currentTarget.parentElement.parentElement.classList.contains("active")) {
		sect.currentTarget.classList.add("active");
	}
	else {
		Object.keys(wbNavSubLst).forEach(function(i) { wbNavSubLst[i].classList.remove("active"); })
		sect.currentTarget.classList.add("active");
	}
*/
}


/*
* Slideshow Functions
*/
//* Init: Slideshow
function wbFigGrab() {
	if (wbFigures != null) {
		Object.keys(wbFigures).forEach(function(i) {
			if (wbFigures[i].className == "slideshow") var wbWrapper = wbFigSlide(i);
			setTimeout(wbWrapper(i), 5000);
		});
	}
}
function wbFigSlide(i) {
	return function() { wbNxtImg(wbFigures[i].getElementsByTagName("img")); };
}
function wbNxtImg(wbImgs) { for (var i = 0; i < wbImgs.length; i++) {
		if (wbImgs[0].style.opacity == "") { wbImgs[0].style.opacity = "1"; break; }
		if (wbImgs[i].style.opacity == "1" || wbImgs[i].style.opacity == "") { 
			wbImgs[i].style.opacity = "0";
			if (i + 1 < wbImgs.length) { wbImgs[i + 1].style.opacity = "1"; break; }
		wbImgs[0].style.opacity = "1"; }
	}	 
	setTimeout(wbNxtImg, 5000, wbImgs);
}


/*
* Browser Check Functions
*/
//* Init: Support vars
// var wbIsChrome = !!window.chrome && (!!window.chrome.webstore || !!window.chrome.runtime);
// var wbIsFirefox = typeof InstallTrigger !== "undefined";
// var wbIsOpera = (!!window.opr && !!opr.addons) || !!window.opera || navigator.userAgent.indexOf(" OPR/") >= 0;
// var wbIsSafari = /constructor/i.test(window.HTMLElement) || (function (p) { return p.toString() === "[object SafariRemoteNotification]"; })(!window["safari"] || (typeof safari !== "undefined" && safari.pushNotification));
// var wbIsBlink = (wbIsChrome || wbIsOpera) && !!window.CSS;
// var wbIsIE = /*@cc_on!@*/false || !!document.documentMode;
// var wbIsEdge = !wbIsIE && !!window.StyleMedia;
// var wbSupportAtSup = Boolean((window.CSSRule.SUPPORTS_RULE) || false);
// var wbSupportCSS = Boolean((window.CSS && window.CSS.supports) || window.supportsCSS || false);
// var wbSupportCSSRule = Boolean((window.CSSRule) || false);
// var wbSupportRdyChk = Boolean((document.attachEvent) || (document.addEventListener) || false);
// console.log(document.readyState, "wbIsFirefox", wbIsFirefox, ", wbIsChrome", wbIsChrome, ", wbIsSafari", wbIsSafari);
// var brwsList = {Opera:[wbIsOpera], Firefox:[wbIsFirefox], Safari:[wbIsSafari], IE:[wbIsIE], Edge:[wbIsEdge], Chrome:[wbIsChrome], Blink:[wbIsBlink]};

// function whichOne(brws) {
// 	var brwsrtn;
// 	Object.keys(brws).some(function(i) {
//   console.log(i + ": " + brws[i]);
// 	if (brws[i] == "true") brwsrtn = i;
// 		})
//   return brwsrtn;
// }

// var output = "Detecting browsers by ducktyping:<hr>";
// output += "isFirefox: " + isFirefox + "<br>";
// output += "isChrome: " + isChrome + "<br>";
// output += "isSafari: " + isSafari + "<br>";
// output += "isOpera: " + isOpera + "<br>";
// output += "isIE: " + isIE + "<br>";
// output += "isEdge: " + isEdge + "<br>";
// output += "isBlink: " + isBlink + "<br>";
// output += "<br><br>";
// output += "Truthy Toggle, Browser is:<hr>";
// output += whichOne(brwsList) + "<br>";
// document.body.innerHTML = output;
//* Supports
// function wbHasAtSup() { return wbSupportCSS && wbSupportCSSRule && wbSupportAtSup; }
// function wbHasRuleSup(wbRule1,wbRule2) { return CSS.supports(wbRule1,wbRule2); }
//* Report Stylesheets
/*
Object.keys(document.styleSheets).forEach(function(i) {
	console.log([i],document.styleSheets[i]);
});
*/
