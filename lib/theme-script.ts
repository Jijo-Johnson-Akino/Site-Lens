export const THEME_BOOTSTRAP_SCRIPT = `(function(){
  try {
    var stored = localStorage.getItem("sitebench-theme");
    var theme = stored === "dark" ? "dark" : "system";
    var dark = theme === "dark" || window.matchMedia("(prefers-color-scheme: dark)").matches;
    var root = document.documentElement;
    root.classList.toggle("dark", dark);
    root.style.colorScheme = dark ? "dark" : "light";
    root.dataset.theme = theme;
  } catch (e) {}
})();`;
