export const THEME_BOOTSTRAP_SCRIPT = `(function(){
  try {
    var stored = localStorage.getItem("sitebench-theme");
    var theme = stored === "dark" ? "dark" : "light";
    var dark = theme === "dark";
    var root = document.documentElement;
    root.classList.toggle("dark", dark);
    root.style.colorScheme = dark ? "dark" : "light";
    root.dataset.theme = theme;
  } catch (e) {}
})();`;
