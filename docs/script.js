const config = window.SITE_CONFIG || {};
const streamlitLink = document.querySelector("#streamlit-link");
const linkStatus = document.querySelector("#link-status");
const appUrl = config.streamlitAppUrl || "";

if (appUrl && !appUrl.includes("your-app")) {
  streamlitLink.href = appUrl;
} else {
  streamlitLink.removeAttribute("target");
  streamlitLink.addEventListener("click", event => {
    event.preventDefault();
    linkStatus.textContent = "Streamlit App 地址尚未配置，请在 config.js 中填写部署地址。";
    linkStatus.classList.add("notice");
  });
}

const progressBar = document.querySelector(".progress i");
const updateProgress = () => {
  const distance = document.documentElement.scrollHeight - window.innerHeight;
  progressBar.style.width = (distance > 0 ? window.scrollY / distance * 100 : 0) + "%";
};
window.addEventListener("scroll", updateProgress, { passive: true });
updateProgress();

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const reveals = document.querySelectorAll(".reveal");
if (reducedMotion || !("IntersectionObserver" in window)) {
  reveals.forEach(element => element.classList.add("visible"));
} else {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.14, rootMargin: "0px 0px -6% 0px" });
  reveals.forEach(element => observer.observe(element));
}

const typeLine = document.querySelector(".type-line");
const phrase = typeLine.dataset.text;
if (reducedMotion) {
  typeLine.textContent = phrase;
} else {
  let index = 0;
  let deleting = false;
  const type = () => {
    typeLine.textContent = phrase.slice(0, index);
    if (!deleting && index < phrase.length) {
      index += 1;
      setTimeout(type, 115);
    } else if (!deleting) {
      deleting = true;
      setTimeout(type, 2100);
    } else if (index > 0) {
      index -= 1;
      setTimeout(type, 55);
    } else {
      deleting = false;
      setTimeout(type, 650);
    }
  };
  type();
}
