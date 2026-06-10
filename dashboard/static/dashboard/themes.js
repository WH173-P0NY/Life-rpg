(function () {
  const storageKey = "life-rpg-dashboard-theme";
  const statePrefix = "life-rpg-dashboard-state";
  const validThemes = new Set([
    "minimal-dark",
    "cyberpunk",
    "living-world",
    "adventurers-journal",
    "premium-hybrid",
  ]);

  function applyTheme(theme) {
    const nextTheme = validThemes.has(theme) ? theme : "premium-hybrid";
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem(storageKey, nextTheme);
    window.dispatchEvent(
      new CustomEvent("life-rpg-theme-change", { detail: { theme: nextTheme } })
    );
  }

  function stateKey(rawKey) {
    return `${statePrefix}:${rawKey}`;
  }

  function readStoredState(rawKey) {
    const value = localStorage.getItem(stateKey(rawKey));
    if (value === "true") {
      return true;
    }
    if (value === "false") {
      return false;
    }
    return null;
  }

  function writeStoredState(rawKey, value) {
    localStorage.setItem(stateKey(rawKey), value ? "true" : "false");
  }

  function setPressed(element, value) {
    element.setAttribute("aria-pressed", value ? "true" : "false");
  }

  function parseBoolean(value) {
    return value === "true";
  }

  function animateProgressBars() {
    const fills = document.querySelectorAll(".theme-progress-fill, .theme-status-fill");
    fills.forEach(function (fill) {
      const targetWidth = fill.style.width;
      if (!targetWidth) {
        return;
      }
      fill.style.width = "0%";
      window.requestAnimationFrame(function () {
        fill.style.width = targetWidth;
      });
    });

    const bars = document.querySelectorAll(".legendary-bar-fill");
    bars.forEach(function (bar) {
      const targetHeight = bar.style.height;
      if (!targetHeight) {
        return;
      }
      bar.style.height = "0%";
      window.requestAnimationFrame(function () {
        bar.style.height = targetHeight;
      });
    });
  }

  function feedbackLayer() {
    return document.querySelector("[data-feedback-layer]");
  }

  function showFloatText(anchor, text) {
    const layer = feedbackLayer();
    if (!layer || !anchor) {
      return;
    }

    const rect = anchor.getBoundingClientRect();
    const bubble = document.createElement("span");
    bubble.className = "legendary-float-text";
    bubble.textContent = text;
    bubble.style.left = `${rect.left + rect.width / 2}px`;
    bubble.style.top = `${rect.top + 8}px`;
    layer.appendChild(bubble);
    window.setTimeout(function () {
      bubble.remove();
    }, 900);
  }

  function pulse(element, className) {
    if (!element) {
      return;
    }
    element.classList.remove(className);
    void element.offsetWidth;
    element.classList.add(className);
    window.setTimeout(function () {
      element.classList.remove(className);
    }, 700);
  }

  function xpController() {
    const xpElement = document.querySelector("[data-xp-value]");
    if (!xpElement) {
      return {
        applyBonus: function () {},
      };
    }

    const baseXp = Number.parseInt(xpElement.dataset.baseXp || "0", 10);
    let bonusXp = 0;

    function render() {
      xpElement.textContent = `${baseXp + bonusXp} XP`;
    }

    return {
      applyBonus: function (delta) {
        bonusXp += delta;
        render();
        pulse(xpElement, "is-xp-pulsing");
      },
    };
  }

  function setQuestComplete(item, complete) {
    item.classList.toggle("is-complete", complete);
    setPressed(item, complete);

    const fill = item.querySelector(".theme-progress-fill");
    if (!fill) {
      return;
    }

    if (!fill.dataset.originalWidth) {
      fill.dataset.originalWidth = fill.style.width || "0%";
    }
    fill.style.width = complete ? "100%" : fill.dataset.originalWidth;
  }

  function setupQuestInteractions(xp) {
    const questItems = document.querySelectorAll("[data-quest-item]");
    questItems.forEach(function (item) {
      const rawKey = item.dataset.stateKey;
      const initialComplete = parseBoolean(item.dataset.initialComplete);
      const storedComplete = rawKey ? readStoredState(rawKey) : null;
      const currentComplete = storedComplete === null ? initialComplete : storedComplete;

      setQuestComplete(item, currentComplete);
      if (storedComplete !== null && storedComplete !== initialComplete) {
        const reward = Number.parseInt(item.dataset.rewardXp || "0", 10);
        xp.applyBonus(storedComplete ? reward : -reward);
      }

      function toggleQuest() {
        const nextComplete = item.getAttribute("aria-pressed") !== "true";
        const reward = Number.parseInt(item.dataset.rewardXp || "0", 10);
        setQuestComplete(item, nextComplete);
        if (rawKey) {
          writeStoredState(rawKey, nextComplete);
        }
        xp.applyBonus(nextComplete ? reward : -reward);
        showFloatText(item, nextComplete ? `+${reward} XP` : `-${reward} XP`);
        pulse(item, "is-quest-pulsing");
      }

      item.addEventListener("click", toggleQuest);
      item.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          toggleQuest();
        }
      });
    });
  }

  function updateHabitSummary() {
    const summary = document.querySelector("[data-habit-summary]");
    if (!summary) {
      return;
    }

    const completed = document.querySelectorAll("[data-habit-dot].is-done").length;
    const total = Number.parseInt(summary.dataset.totalHabits || "0", 10);
    summary.textContent = `${completed}/${total}`;
    pulse(summary, "is-xp-pulsing");
  }

  function setupHabitInteractions() {
    const habitDots = document.querySelectorAll("[data-habit-dot]");
    habitDots.forEach(function (dot) {
      const rawKey = dot.dataset.stateKey;
      const initialComplete = parseBoolean(dot.dataset.initialComplete);
      const storedComplete = rawKey ? readStoredState(rawKey) : null;
      const currentComplete = storedComplete === null ? initialComplete : storedComplete;

      dot.classList.toggle("is-done", currentComplete);
      setPressed(dot, currentComplete);

      dot.addEventListener("click", function () {
        const nextComplete = dot.getAttribute("aria-pressed") !== "true";
        dot.classList.toggle("is-done", nextComplete);
        setPressed(dot, nextComplete);
        if (rawKey) {
          writeStoredState(rawKey, nextComplete);
        }
        updateHabitSummary();
        showFloatText(dot, nextComplete ? "Habit done" : "Habit reset");
        pulse(dot, "is-habit-pulsing");
      });
    });
    updateHabitSummary();
  }

  function setupNavigationFeedback() {
    const navItems = document.querySelectorAll(".legendary-nav-item");
    navItems.forEach(function (item) {
      item.addEventListener("click", function (event) {
        if (item.getAttribute("href") === "#") {
          event.preventDefault();
        }
        navItems.forEach(function (otherItem) {
          otherItem.classList.remove("is-active");
        });
        item.classList.add("is-active");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const select = document.querySelector("[data-theme-select]");
    if (!select) {
      animateProgressBars();
      setupQuestInteractions(xpController());
      setupHabitInteractions();
      setupNavigationFeedback();
      return;
    }

    const currentTheme = document.documentElement.dataset.theme || "premium-hybrid";
    select.value = currentTheme;
    select.addEventListener("change", function (event) {
      applyTheme(event.target.value);
    });

    animateProgressBars();
    setupQuestInteractions(xpController());
    setupHabitInteractions();
    setupNavigationFeedback();
  });
})();
