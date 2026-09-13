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

// wb-checkbox sprite injection
(function() {
  function injectWbSprite() {
    try {
      if (document.getElementById('wb-svg-sprite')) return;
      var wrap = document.createElement('div');
      wrap.id = 'wb-svg-sprite';
      wrap.style.display = 'none';
      wrap.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" style="display:none">\n  <symbol id="wb-box" viewBox="0 0 16 16">\n    <rect width="14" height="14" x="1" y="1" stroke-width="1" stroke="black"\n          fill="var(--primary_color)" />\n  </symbol>\n  <symbol id="wb-diamond" viewBox="0 0 16 16">\n    <rect width="14" height="14" x="-7" y="-7" stroke-width="1" stroke="black"\n          fill="var(--primary_color)"\n          transform="translate(8 8) scale(0.707) rotate(45)" />\n  </symbol>\n  <symbol id="wb-check" viewBox="0 0 16 16">\n    <polyline points="3,9 6,12 13,4" fill="none"\n              stroke="var(--secondary_color)" stroke-width="2"\n              stroke-linecap="butt" stroke-linejoin="miter" />\n  </symbol>\n  <symbol id="wb-plus" viewBox="0 0 16 16">\n    <polygon points="4,7 7,7 7,4 9,4 9,7 12,7 12,9 9,9 9,12 7,12 7,9 4,9"\n             fill="var(--secondary_color)" />\n  </symbol>\n  <symbol id="wb-dot" viewBox="0 0 16 16">\n    <ellipse rx="2" ry="2" cx="8" cy="8" fill="var(--secondary_color)" />\n  </symbol>\n\n  <symbol id="wb-checkbox-off" viewBox="0 0 16 16">\n    <use href="#wb-box" />\n  </symbol>\n  <symbol id="wb-checkbox-on" viewBox="0 0 16 16">\n    <use href="#wb-box" />\n    <use href="#wb-check" />\n  </symbol>\n  <symbol id="wb-checkbox-inc" viewBox="0 0 16 16">\n    <use href="#wb-box" />\n    <use href="#wb-plus" />\n  </symbol>\n  <symbol id="wb-checkbox-imp" viewBox="0 0 16 16">\n    <use href="#wb-box" />\n    <use href="#wb-dot" />\n  </symbol>\n\n  <symbol id="wb-diamond-off" viewBox="0 0 16 16">\n    <use href="#wb-diamond" />\n  </symbol>\n  <symbol id="wb-diamond-on" viewBox="0 0 16 16">\n    <use href="#wb-diamond" />\n    <use href="#wb-plus" />\n  </symbol>\n</svg>';
      // Insert at top of body so <use href="#..."> works everywhere.
      (document.body || document.documentElement).insertBefore(
        wrap, (document.body || document.documentElement).firstChild
      );
    } catch (e) {
      // ignore
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectWbSprite);
  } else {
    injectWbSprite();
  }
})();

// wb-ico upgrader
// wb-ico upgrader: allow <svg class="wb-ico ..." data-wb-use="#wb-checkbox-on"></svg>
(function() {
  function upgradeWbIcons() {
    try {
      var nodes = document.querySelectorAll('svg.wb-ico[data-wb-use]');
      for (var i = 0; i < nodes.length; i++) {
        var svg = nodes[i];
        // Ensure xmlns/viewBox for consistent rendering
        if (!svg.getAttribute('xmlns')) svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        if (!svg.getAttribute('viewBox')) svg.setAttribute('viewBox', '0 0 16 16');
        // Accessibility defaults
        if (!svg.getAttribute('role')) svg.setAttribute('role', 'img');
        // Populate <use> once
        if (svg.querySelector('use')) continue;
        var href = svg.getAttribute('data-wb-use');
        if (!href) continue;
        var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
        // Set both for broader compatibility (SVG2 + older)
        use.setAttribute('href', href);
        use.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', href);
        svg.appendChild(use);
      }
    } catch (e) {
      // ignore
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', upgradeWbIcons);
  } else {
    upgradeWbIcons();
  }
})();
