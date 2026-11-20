// Unit checks of rendering functions; no browser/desktop automation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
function element() {
    return { children: [], innerHTML: '', textContent: '', appendChild(child) { this.children.push(child); }, scrollHeight: 0 };
}
const container = element();
const context = { document: { addEventListener() {}, getElementById() { return container; }, createElement: element }, console };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../frontend/js/main.js'), 'utf8'), context);
context.appendChatMessage('<img src=x onerror=alert(1)> **halo**', 'bot', [{label: '<svg onload=alert(1)>', url: '/calendar'}, {label:'external', url:'https://evil.example'}, {label:'script', url:'javascript:alert(1)'}]);
const bubble = container.children[0];
assert.ok(!bubble.innerHTML.includes('<img'));
assert.ok(bubble.innerHTML.includes('&lt;img'));
assert.ok(bubble.innerHTML.includes('<strong>halo</strong>'));
assert.equal(bubble.children[0].children.length, 1);
assert.equal(bubble.children[0].children[0].textContent, '<svg onload=alert(1)>');
assert.equal(bubble.children[0].children[0].href, '/calendar');
context.appendChatMessage('<script>alert(1)</script>', 'user');
assert.ok(!container.children[1].innerHTML.includes('<script>'));
assert.ok(container.children[1].innerHTML.includes('&lt;script&gt;'));
console.log('PASS: escaped bot/user messages, preserved formatting, safe source links.');
