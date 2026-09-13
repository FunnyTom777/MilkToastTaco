/* Milk Toast Taco — tiny zero-dependency Markdown renderer.
 * Supports: headings, paragraphs, bold/italic/strike, inline code,
 * fenced code blocks, links, images, blockquotes, hr, tables,
 * bullet/numbered/task lists. Fully local, no CDN. */
(function () {
  "use strict";

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function safeUrl(url) {
    var u = (url || "").trim();
    if (/^(https?:\/\/|mailto:|#|\/)/i.test(u)) return u;
    if (/^[a-zA-Z0-9._\-\/?#=&%+:~@]+$/.test(u)) return u;
    // Relative paths like ../docs/INSTALL_GUIDE.md, ../FEATURE_IDEAS.md
    if (/^(\.\.?\/)+[a-zA-Z0-9._\-\/?#=&%+:~@]*$/.test(u)) return u;
    return "#";
  }

  function inlineFmt(src) {
    // src is already HTML-escaped. Extract `code` spans first.
    var codes = [];
    var text = src.replace(/`([^`\n]+)`/g, function (_, inner) {
      codes.push(inner);
      return "\u0000CODE" + (codes.length - 1) + "\u0000";
    });

    // Images: ![alt](url)
    text = text.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;)?\)/g, function (_, alt, url) {
      return '<img src="' + safeUrl(url) + '" alt="' + alt + '" loading="lazy" />';
    });
    // Links: [label](url)
    text = text.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;)?\)/g, function (_, label, url) {
      var href = safeUrl(url);
      var external = /^https?:\/\//i.test(href);
      return '<a href="' + href + '"' + (external ? ' target="_blank" rel="noopener"' : "") + ">" + label + "</a>";
    });
    // Bold, italic, strike
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    text = text.replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    text = text.replace(/(^|[\s(])_([^_\n]+)_/g, "$1<em>$2</em>");
    text = text.replace(/~~([^~]+)~~/g, "<del>$1</del>");

    // Restore code spans
    text = text.replace(/\u0000CODE(\d+)\u0000/g, function (_, i) {
      return "<code>" + codes[Number(i)] + "</code>";
    });
    return text;
  }

  function isTableSep(line) {
    return /^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$/.test(line);
  }

  function splitRow(line) {
    var t = line.trim().replace(/^\||\|$/g, "");
    return t.split("|").map(function (c) { return c.trim(); });
  }

  function render(md) {
    var lines = (md || "").replace(/\r\n?/g, "\n").split("\n");
    var html = [];
    var i = 0;

    function flushList(stack) {
      while (stack.length) {
        var kind = stack.pop();
        html.push(kind === "ul" ? "</ul>" : "</ol>");
      }
    }

    var listStack = [];

    while (i < lines.length) {
      var line = lines[i];

      // Fenced code block
      var fence = line.match(/^```(\w*)\s*$/);
      if (fence) {
        flushList(listStack);
        var lang = fence[1] || "text";
        var buf = [];
        i++;
        while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) {
          buf.push(lines[i]);
          i++;
        }
        i++; // skip closing fence
        html.push(
          '<pre><code class="lang-' + escapeHtml(lang) + '">' +
            escapeHtml(buf.join("\n")) +
            "</code></pre>"
        );
        continue;
      }

      // Headings
      var h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) {
        flushList(listStack);
        var level = h[1].length;
        html.push("<h" + level + ">" + inlineFmt(escapeHtml(h[2].trim())) + "</h" + level + ">");
        i++;
        continue;
      }

      // Horizontal rule
      if (/^\s*([-*_]\s*){3,}\s*$/.test(line)) {
        flushList(listStack);
        html.push("<hr />");
        i++;
        continue;
      }

      // Blockquote (group consecutive > lines)
      if (/^\s*&gt;/.test(escapeHtml(line)) || /^\s*>/.test(line)) {
        flushList(listStack);
        var quotes = [];
        while (i < lines.length && /^\s*>/.test(lines[i])) {
          quotes.push(lines[i].replace(/^\s*>\s?/, ""));
          i++;
        }
        html.push("<blockquote>" + renderInlineBlock(quotes.join("\n")) + "</blockquote>");
        continue;
      }

      // Table: header row + sep row + body rows
      if (line.indexOf("|") !== -1 && i + 1 < lines.length && isTableSep(lines[i + 1])) {
        flushList(listStack);
        var heads = splitRow(line);
        i += 2;
        var rows = [];
        while (i < lines.length && lines[i].indexOf("|") !== -1 && lines[i].trim() !== "") {
          rows.push(splitRow(lines[i]));
          i++;
        }
        var t = "<table><thead><tr>" +
          heads.map(function (c) { return "<th>" + inlineFmt(escapeHtml(c)) + "</th>"; }).join("") +
          "</tr></thead><tbody>" +
          rows.map(function (r) {
            return "<tr>" + r.map(function (c) { return "<td>" + inlineFmt(escapeHtml(c)) + "</td>"; }).join("") + "</tr>";
          }).join("") +
          "</tbody></table>";
        html.push('<div class="table-wrap">' + t + "</div>");
        continue;
      }

      // Lists: -, *, +, 1., task - [ ] / - [x]
      var m = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
      if (m) {
        var ordered = /^\d/.test(m[2].trim());
        var kind = ordered ? "ol" : "ul";
        if (!listStack.length || listStack[listStack.length - 1] !== kind) {
          flushList(listStack);
          html.push(ordered ? "<ol>" : "<ul>");
          listStack.push(kind);
        }
        var item = m[3];
        var task = item.match(/^\[([ xX])\]\s+(.*)$/);
        if (task) {
          var checked = task[1].toLowerCase() === "x";
          html.push(
            '<li class="task"><input type="checkbox" disabled' + (checked ? " checked" : "") + "> " +
              inlineFmt(escapeHtml(task[2])) + "</li>"
          );
        } else {
          html.push("<li>" + inlineFmt(escapeHtml(item)) + "</li>");
        }
        i++;
        // Close list when next line is not a list item / blank handling
        var next = lines[i];
        if (i >= lines.length || (next.trim() === "" || !/^(\s*)([-*+]|\d+[.)])\s+/.test(next))) {
          // keep list open across a single blank line only if another item follows later — simpler: close now
          flushList(listStack);
          if (i < lines.length && next.trim() === "") i++;
        }
        continue;
      }

      // Blank line
      if (line.trim() === "") {
        flushList(listStack);
        i++;
        continue;
      }

      // Paragraph: gather consecutive plain lines
      flushList(listStack);
      var para = [];
      while (
        i < lines.length &&
        lines[i].trim() !== "" &&
        !/^(#{1,6}\s|```|\s*>|\s*([-*_]\s*){3,}\s*$)/.test(lines[i]) &&
        !/^(\s*)([-*+]|\d+[.)])\s+/.test(lines[i]) &&
        !(lines[i].indexOf("|") !== -1 && i + 1 < lines.length && isTableSep(lines[i + 1]))
      ) {
        para.push(lines[i].trim());
        i++;
      }
      // Hard-break: two trailing spaces
      var joined = para
        .map(function (l) { return escapeHtml(l); })
        .join("<br />\n");
      html.push("<p>" + inlineFmt(joined) + "</p>");
    }

    flushList(listStack);
    return html.join("\n");
  }

  function renderInlineBlock(text) {
    // Render small inline markdown blocks (used inside blockquotes)
    return inlineFmt(escapeHtml(text).replace(/\n/g, "<br />\n"));
  }

  window.MttMarkdown = { render: render, inline: inlineFmt };
})();
