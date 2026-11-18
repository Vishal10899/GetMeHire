const { sanitizeHtml } = require("../src/lib/sanitize.js");
const assert = require("assert");

console.log("=== RUNNING HTML SANITIZER HOSTILE PAYLOAD TESTS ===");

// 1. Script injection
const payload1 = "<h3>Job Title</h3><script>window.__xss = true;</script><p>Description</p>";
const clean1 = sanitizeHtml(payload1);
console.log("\n[Test 1] Script Tag Injection:");
console.log("  Input: ", payload1);
console.log("  Output:", clean1);
assert(!clean1.includes("<script>"), "Script tag must be stripped");
assert(!clean1.includes("window.__xss"), "Script content must be stripped");
assert(clean1.includes("<h3>Job Title</h3>"), "Safe heading must be preserved");
assert(clean1.includes("<p>Description</p>"), "Safe paragraph must be preserved");
console.log("  => PASSED");

// 2. Event handler injection
const payload2 = "<img src='invalid-image.jpg' onerror='window.__xss = true' /><p>Valid text</p>";
const clean2 = sanitizeHtml(payload2);
console.log("\n[Test 2] Event Handler (onerror) Injection:");
console.log("  Input: ", payload2);
console.log("  Output:", clean2);
assert(!clean2.includes("onerror"), "Event handler onerror must be stripped");
assert(!clean2.includes("window.__xss"), "Script inside event handler must be stripped");
assert(clean2.includes("Valid text"), "Safe text must be preserved");
console.log("  => PASSED");

// 3. Javascript: pseudo-protocol URL scheme
const payload3 = "<a href='javascript:alert(1)'>Click here to apply</a>";
const clean3 = sanitizeHtml(payload3);
console.log("\n[Test 3] javascript: URL Scheme Injection:");
console.log("  Input: ", payload3);
console.log("  Output:", clean3);
assert(!clean3.includes("href=\"javascript:"), "javascript: link must be blocked/sanitized");
assert(!clean3.includes("href='javascript:"), "javascript: link must be blocked/sanitized");
console.log("  => PASSED");

// 4. Embedded active content (iframe, object, embed)
const payload4 = "<iframe src='http://attacker.com/malicious'></iframe><embed src='bad.swf'>";
const clean4 = sanitizeHtml(payload4);
console.log("\n[Test 4] Embedded Active Content (iframe/embed):");
console.log("  Input: ", payload4);
console.log("  Output:", clean4);
assert(!clean4.includes("<iframe"), "iframe tag must be stripped");
assert(!clean4.includes("<embed"), "embed tag must be stripped");
console.log("  => PASSED");

// 5. Preservation of safe complex employer markup
const payload5 = `
  <h3><strong>About Stripe</strong></h3>
  <p>We are looking for an <em>Engineering Lead</em>.</p>
  <ul>
    <li>5+ years of experience with <code>Python</code> or <code>Go</code></li>
    <li>Experience with distributed databases</li>
  </ul>
  <p>Learn more at <a href="https://stripe.com/about">our company site</a>.</p>
`;
const clean5 = sanitizeHtml(payload5);
console.log("\n[Test 5] Safe Complex Employer Markup Preservation:");
assert(clean5.includes("<h3><strong>About Stripe</strong></h3>"), "Headings & strong preserved");
assert(clean5.includes("<em>Engineering Lead</em>"), "Emphasis preserved");
assert(clean5.includes("<ul>"), "Unordered list preserved");
assert(clean5.includes("<li>5+ years of experience"), "List item preserved");
assert(clean5.includes("<code>Python</code>"), "Code blocks preserved");
assert(clean5.includes("href=\"https://stripe.com/about\""), "Safe HTTPS link preserved");
console.log("  => PASSED");

console.log("\n=== ALL 5 HOSTILE HTML PAYLOAD TESTS PASSED! ===");
