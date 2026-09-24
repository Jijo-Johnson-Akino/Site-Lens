export const THEME_BOOTSTRAP_SCRIPT = `(function(){
  try {
    var stored = localStorage.getItem("sitebench-theme");
    var theme = stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
    var dark = theme === "dark" || (theme !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    var root = document.documentElement;
    root.classList.toggle("dark", dark);
    root.style.colorScheme = dark ? "dark" : "light";
    root.dataset.theme = theme;
  } catch (e) {}
})();`;
