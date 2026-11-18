import DOMPurify from "dompurify";

const CONFIG = {
  ALLOWED_TAGS: [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr", "span", "div",
    "strong", "b", "em", "i", "u", "s",
    "ul", "ol", "li",
    "a", "blockquote", "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td",
  ],
  ALLOWED_ATTR: ["href", "target", "rel", "title", "class"],
  FORBID_TAGS: ["script", "iframe", "object", "embed", "style", "form", "input", "button", "svg", "math"],
  FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "onfocus", "onblur", "style"],
  ALLOW_DATA_ATTR: false,
};

export function sanitizeHtml(rawHtml) {
  if (!rawHtml) return "";
  
  if (typeof window === "undefined") {
    // Server-side fallback: strip dangerous tags (paired & void) and event handlers
    return rawHtml
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>|<script\b[^>]*>/gi, "")
      .replace(/<iframe\b[^>]*>[\s\S]*?<\/iframe>|<iframe\b[^>]*>/gi, "")
      .replace(/<object\b[^>]*>[\s\S]*?<\/object>|<object\b[^>]*>/gi, "")
      .replace(/<embed\b[^>]*>/gi, "")
      .replace(/<svg\b[^>]*>[\s\S]*?<\/svg>|<svg\b[^>]*>/gi, "")
      .replace(/\s*on\w+\s*=\s*(['"]).*?\1/gi, "")
      .replace(/\s*on\w+\s*=\s*[^\s>]+/gi, "")
      .replace(/href\s*=\s*(['"])\s*javascript:[^'"]*\1/gi, 'href="#"');
  }

  return DOMPurify.sanitize(rawHtml, CONFIG);
}
