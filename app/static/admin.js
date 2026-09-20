/* 航迹云后台统一导航与视觉外壳。 */
(function () {
  const NAV = [
    { href: "/admin", label: "运营总览" },
    { href: "/logistics-dashboard", label: "运单态势" },
    { href: "/kb", label: "知识库" },
    { href: "/agent-eval", label: "Agent 评测" },
    { href: "/rag-eval", label: "RAG 评测" },
    { href: "/observability", label: "链路观测" },
    { href: "/review", label: "失败复盘" },
    { href: "/topics", label: "问题主题" },
  ];

  function injectCss() {
    if (document.getElementById("mh-admin-shell")) return;
    const link = document.createElement("link");
    link.id = "mh-admin-shell";
    link.rel = "stylesheet";
    link.href = "/static/admin-shell.css";
    document.head.appendChild(link);
  }

  function navLink(href, label, on, cls) {
    const a = document.createElement("a");
    a.href = href;
    a.className = (on ? "on " : "") + (cls || "");
    a.textContent = label;
    return a;
  }

  function moduleOf(active) {
    return NAV.find((item) => item.href === active)
      || NAV.find((item) => item.href !== "/" && active.startsWith(item.href + "/"));
  }

  function renderAdminNav(active) {
    injectCss();
    const wrap = document.createElement("div");
    wrap.className = "mh-nav";
    const row = document.createElement("div");
    row.className = "row";
    const brand = document.createElement("span");
    brand.className = "brand";
    brand.textContent = "航迹云控制台";
    row.appendChild(brand);
    const activeModule = moduleOf(active);
    for (const item of NAV) row.appendChild(navLink(item.href, item.label, item === activeModule));
    const grow = document.createElement("span");
    grow.className = "grow";
    row.appendChild(grow);
    row.appendChild(navLink("/", "返回聊天", false, "chat-link"));
    wrap.appendChild(row);
    return wrap;
  }

  function mountAdminNav(active) {
    const nav = renderAdminNav(active);
    const bar = document.querySelector(".topbar");
    if (bar && bar.parentNode) bar.parentNode.insertBefore(nav, bar.nextSibling);
    else {
      const root = document.querySelector(".wrap") || document.body;
      root.insertBefore(nav, root.firstChild);
    }
    return nav;
  }

  window.renderAdminNav = renderAdminNav;
  window.mountAdminNav = mountAdminNav;
})();
