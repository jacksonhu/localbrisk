/**
 * useMarkdownRenderer — Shared markdown-it renderer with custom rules.
 *
 * Extracted from AgentChatPanel to be reused by both AgentChatPanel,
 * ForemanChatWorkspace, and the shared AgentExecutionBlock component.
 *
 * Features:
 * - External links open in new tab with noopener/noreferrer
 * - Fenced code blocks rendered with language header card
 * - Custom component mapping (cb-callout, cb-file, cb-tool)
 * - Script / event handler sanitization
 */

import MarkdownIt from "markdown-it";

// ============ HTML helpers ============

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function parseAttrMap(attrText: string): Record<string, string> {
  const map: Record<string, string> = {};
  const regex = /(\w+)="([^"]*)"/g;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(attrText)) !== null) {
    map[m[1]] = m[2];
  }
  return map;
}

// ============ Custom component mapping ============

function mapCustomComponents(md: MarkdownIt, input: string): string {
  let out = input;

  // <cb-callout type="info" title="Title">Body</cb-callout>
  out = out.replace(/<cb-callout([^>]*)>([\s\S]*?)<\/cb-callout>/g, (_, attrs, body) => {
    const a = parseAttrMap(attrs || "");
    const type = (a.type || "info").toLowerCase();
    const title = a.title ? `<div class="cb-callout-title">${escapeHtml(a.title)}</div>` : "";
    return `<div class="cb-callout cb-callout-${escapeHtml(type)}">${title}<div class="cb-callout-body">${md.renderInline(body || "")}</div></div>`;
  });

  // <cb-file path="xxx" op="create"/>
  out = out.replace(/<cb-file([^>]*)\/>/g, (_, attrs) => {
    const a = parseAttrMap(attrs || "");
    const path = escapeHtml(a.path || "");
    const op = escapeHtml(a.op || "view");
    return `<div class="cb-file-card"><span class="cb-chip">File</span><span class="cb-file-path">${path}</span><span class="cb-chip cb-chip-op">${op}</span></div>`;
  });

  // <cb-tool name="xxx" status="running"/>
  out = out.replace(/<cb-tool([^>]*)\/>/g, (_, attrs) => {
    const a = parseAttrMap(attrs || "");
    const name = escapeHtml(a.name || "tool");
    const status = escapeHtml(a.status || "running");
    return `<div class="cb-tool-card"><span class="cb-chip">Tool</span><span class="cb-tool-name">${name}</span><span class="cb-chip cb-chip-status">${status}</span></div>`;
  });

  return out;
}

// ============ Sanitizer ============

function sanitizeUnsafeMarkup(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}

// ============ Composable ============

/**
 * Create a configured markdown-it instance and return a render function.
 *
 * @param options.html  Allow raw HTML in source (default: true for full features).
 */
export function useMarkdownRenderer(options?: { html?: boolean }) {
  const md = new MarkdownIt({
    html: options?.html ?? true,
    linkify: true,
    breaks: true,
  });

  // Links open in new tab.
  md.renderer.rules.link_open = (tokens, idx, opts, _env, self) => {
    const token = tokens[idx];
    token.attrSet("target", "_blank");
    token.attrSet("rel", "noopener noreferrer nofollow");
    token.attrJoin("class", "cb-link");
    return self.renderToken(tokens, idx, opts);
  };

  // Fenced code blocks with language header.
  md.renderer.rules.fence = (tokens, idx) => {
    const token = tokens[idx];
    const lang = (token.info || "").trim().split(/\s+/)[0] || "text";
    const code = md.utils.escapeHtml(token.content || "");
    return `<div class="cb-code-card"><div class="cb-code-head">${lang}</div><pre class="code-block"><code class="language-${lang}">${code}</code></pre></div>`;
  };

  /**
   * Render markdown string to safe HTML.
   * Applies custom component mapping and script sanitization.
   */
  function renderMarkdown(content: string): string {
    if (!content) return "";
    const mapped = mapCustomComponents(md, content);
    return md.render(sanitizeUnsafeMarkup(mapped));
  }

  return { renderMarkdown, md };
}

export default useMarkdownRenderer;
