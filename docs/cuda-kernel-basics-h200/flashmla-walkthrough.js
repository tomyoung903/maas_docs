(() => {
  "use strict";

  const stories = document.querySelectorAll("[data-fma-story]");
  if (!stories.length) return;

  stories.forEach((story) => {
    const controls = story.querySelector("[data-fma-controls]");
    const chapters = story.querySelector("[data-fma-chapters]");
    const stepButtons = [...story.querySelectorAll("[data-fma-step]")];
    const visualScenes = [...story.querySelectorAll("[data-fma-visual]")];
    const captions = [...story.querySelectorAll("[data-fma-caption]")];
    const previousButton = story.querySelector("[data-fma-previous]");
    const playButton = story.querySelector("[data-fma-play]");
    const nextButton = story.querySelector("[data-fma-next]");
    const replayButton = story.querySelector("[data-fma-replay]");
    const countLabel = story.querySelector("[data-fma-count]");
    const progressTrack = story.querySelector("[data-fma-progress]");
    const progressFill = story.querySelector("[data-fma-progress-fill]");
    const evidenceBadge = story.querySelector("[data-fma-evidence]");
    const scaleBadge = story.querySelector("[data-fma-scale]");
    const liveRegion = story.querySelector("[data-fma-live]");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sceneDuration = 8000;

    let currentScene = 0;
    let playing = false;
    let elapsed = 0;
    let lastFrame = 0;
    let frameId = 0;
    let replayOnly = false;

    story.classList.add("fma-enhanced");
    if (controls) controls.hidden = false;
    if (chapters) chapters.hidden = false;

    const smGrid = story.querySelector("[data-fma-sm-grid]");
    if (smGrid && !smGrid.children.length) {
      for (let index = 0; index < 132; index += 1) {
        const cell = document.createElement("span");
        cell.className = "fma-sm-cell";
        if (index < 25) cell.classList.add("tail29");
        else if (index < 50) cell.classList.add("tail27");
        else if (index < 125) cell.classList.add("tail24");
        else cell.classList.add("empty");
        smGrid.appendChild(cell);
      }
    }

    const updateProgress = (fraction) => {
      const bounded = Math.max(0, Math.min(1, fraction));
      const percent = Math.round(bounded * 100);
      if (progressFill) progressFill.style.width = `${percent}%`;
      if (progressTrack) progressTrack.setAttribute("aria-valuenow", String(percent));
    };

    const updatePlayButton = () => {
      if (!playButton) return;
      if (reducedMotion.matches) {
        playButton.disabled = true;
        replayButton.disabled = true;
        playButton.setAttribute("aria-pressed", "false");
        playButton.textContent = "Motion off";
        playButton.setAttribute("aria-label", "Animation disabled by reduced-motion preference");
        return;
      }
      playButton.disabled = false;
      replayButton.disabled = false;
      playButton.setAttribute("aria-pressed", String(playing));
      playButton.textContent = playing ? "Pause" : "Play tour";
      playButton.setAttribute("aria-label", playing ? "Pause animated walkthrough" : "Play animated walkthrough");
    };

    const pause = ({ announce = false } = {}) => {
      playing = false;
      replayOnly = false;
      story.classList.remove("is-playing");
      cancelAnimationFrame(frameId);
      frameId = 0;
      lastFrame = 0;
      updatePlayButton();
      if (announce && liveRegion) liveRegion.textContent = `Paused at step ${currentScene + 1} of ${stepButtons.length}.`;
    };

    const restartSceneMotion = () => {
      story.classList.remove("is-playing");
      void story.offsetWidth;
      if (playing && !reducedMotion.matches) story.classList.add("is-playing");
    };

    const setScene = (nextIndex, { announce = true, pauseTour = true } = {}) => {
      const total = stepButtons.length;
      currentScene = Math.max(0, Math.min(total - 1, nextIndex));
      story.dataset.scene = String(currentScene);

      if (pauseTour) pause();
      elapsed = 0;
      updateProgress(0);

      visualScenes.forEach((scene, index) => {
        scene.classList.toggle("is-active", index === currentScene);
      });

      captions.forEach((caption, index) => {
        caption.hidden = index !== currentScene;
      });

      stepButtons.forEach((button, index) => {
        if (index === currentScene) button.setAttribute("aria-current", "step");
        else button.removeAttribute("aria-current");
      });

      const activeButton = stepButtons[currentScene];
      if (countLabel) countLabel.textContent = `Step ${currentScene + 1} of ${total}`;
      if (evidenceBadge) evidenceBadge.textContent = activeButton.dataset.evidence || "Evidence";
      if (scaleBadge) scaleBadge.textContent = activeButton.dataset.scale || "Kernel scale";
      previousButton.disabled = currentScene === 0;
      nextButton.disabled = currentScene === total - 1;

      restartSceneMotion();
      if (announce && liveRegion) {
        liveRegion.textContent = `Step ${currentScene + 1} of ${total}: ${activeButton.dataset.title}.`;
      }
    };

    const tick = (time) => {
      if (!playing) return;
      if (!lastFrame) lastFrame = time;
      elapsed += time - lastFrame;
      lastFrame = time;
      updateProgress(elapsed / sceneDuration);

      if (elapsed >= sceneDuration) {
        if (replayOnly) {
          updateProgress(1);
          pause();
          if (liveRegion) liveRegion.textContent = `Replay of step ${currentScene + 1} complete.`;
          return;
        }
        if (currentScene >= stepButtons.length - 1) {
          updateProgress(1);
          pause();
          if (liveRegion) liveRegion.textContent = "Animated walkthrough complete.";
          return;
        }
        setScene(currentScene + 1, { announce: true, pauseTour: false });
        elapsed = 0;
        lastFrame = time;
      }
      frameId = requestAnimationFrame(tick);
    };

    const play = () => {
      if (playing || reducedMotion.matches) return;
      replayOnly = false;
      if (currentScene === stepButtons.length - 1 && (elapsed === 0 || elapsed >= sceneDuration)) {
        setScene(0, { announce: true, pauseTour: false });
      }
      playing = true;
      lastFrame = 0;
      story.classList.toggle("is-playing", !reducedMotion.matches);
      updatePlayButton();
      frameId = requestAnimationFrame(tick);
    };

    stepButtons.forEach((button, index) => {
      button.addEventListener("click", () => setScene(index));
      button.addEventListener("keydown", (event) => {
        let target = null;
        if (event.key === "ArrowRight") target = Math.min(stepButtons.length - 1, index + 1);
        else if (event.key === "ArrowLeft") target = Math.max(0, index - 1);
        else if (event.key === "Home") target = 0;
        else if (event.key === "End") target = stepButtons.length - 1;
        if (target === null) return;
        event.preventDefault();
        stepButtons[target].focus();
        setScene(target);
      });
    });

    previousButton.addEventListener("click", () => setScene(currentScene - 1));
    nextButton.addEventListener("click", () => setScene(currentScene + 1));
    playButton.addEventListener("click", () => {
      if (playing) pause({ announce: true });
      else play();
    });
    replayButton.addEventListener("click", () => {
      if (reducedMotion.matches) return;
      elapsed = 0;
      updateProgress(0);
      pause();
      replayOnly = true;
      playing = true;
      story.classList.toggle("is-playing", !reducedMotion.matches);
      updatePlayButton();
      restartSceneMotion();
      frameId = requestAnimationFrame(tick);
      if (liveRegion) liveRegion.textContent = `Replaying step ${currentScene + 1}: ${stepButtons[currentScene].dataset.title}.`;
    });

    story.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && playing) {
        event.preventDefault();
        pause({ announce: true });
      }
    });

    document.addEventListener("visibilitychange", () => {
      if (document.hidden && playing) pause({ announce: true });
    });

    window.addEventListener("pagehide", () => pause());

    const motionChange = () => {
      if (reducedMotion.matches) pause({ announce: true });
      else updatePlayButton();
    };
    if (typeof reducedMotion.addEventListener === "function") reducedMotion.addEventListener("change", motionChange);
    else if (typeof reducedMotion.addListener === "function") reducedMotion.addListener(motionChange);

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        if (!entries[0].isIntersecting && playing) pause({ announce: true });
      }, { threshold: 0.1 });
      observer.observe(story);
    }

    setScene(0, { announce: false, pauseTour: true });
    updatePlayButton();
  });
})();
