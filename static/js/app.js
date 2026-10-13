/* DukaanDraft frontend logic (Phase 1.5).
 * Talks only to the local Flask backend. Model output is always rendered
 * with safe DOM text operations (textContent / createElement), never HTML.
 */
(function () {
  "use strict";

  var form = document.getElementById("product-form");
  var generateBtn = document.getElementById("generate-btn");
  var btnLabel = generateBtn.querySelector(".btn-label");
  var btnSpinner = generateBtn.querySelector(".btn-spinner");
  var loadingNote = document.getElementById("loading-note");
  var errorBanner = document.getElementById("error-banner");
  var resultsSection = document.getElementById("results");
  var modelTag = document.getElementById("model-tag");

  /* Rotating, honest progress messages while the local model works. */
  var PROGRESS_MESSAGES = [
    "Reading your product details…",
    "Drafting your Instagram captions…",
    "Writing the WhatsApp message…",
    "Polishing descriptions and selling points…",
    "Almost done — just a moment longer…",
  ];
  var progressTimer = null;
  var progressIndex = 0;

  /* Sample products so first-time users can see how it works. */
  var SAMPLES = {
    kurti: {
      product_name: "Cotton Kurti",
      category: "Clothing & Fashion",
      price: "599",
      features: "Breathable cotton fabric, blue colour, machine washable",
      target_audience: "College students and working women",
      language: "Hinglish",
    },
    chappal: {
      product_name: "Kolhapuri Leather Chappal",
      category: "Footwear",
      price: "749",
      features: "Handcrafted genuine leather, durable sole, traditional design",
      target_audience: "Young professionals who like ethnic style",
      language: "English",
    },
    necklace: {
      product_name: "Kundan Necklace Set",
      category: "Jewellery & Accessories",
      price: "1299",
      features: "Kundan stones, gold-plated, includes earrings and maang tikka",
      target_audience: "Women shopping for weddings and festive occasions",
      language: "Hinglish",
    },
  };

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (generateBtn.disabled) return; // prevent duplicate submissions

    clearErrors();
    hideBanner();

    var categoryCustom = form.category_custom.value.trim();
    var payload = {
      product_name: form.product_name.value.trim(),
      category: categoryCustom || form.category.value || null,
      price: form.price.value.trim() || null,
      features: form.features.value.trim() || null,
      target_audience: form.target_audience.value.trim() || null,
      language: form.language.value,
    };

    if (!payload.product_name) {
      showFieldError("product_name", "Product name is required.");
      form.product_name.focus();
      return;
    }

    setLoading(true);
    hideResults();

    fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        return response.json().catch(function () {
          throw new Error("The server returned an unreadable response.");
        }).then(function (data) {
          if (!response.ok) {
            var error = new Error(
              data && data.error
                ? data.error
                : "Request failed with status " + response.status + "."
            );
            error.fieldErrors =
              data && data.field_errors ? data.field_errors : null;
            throw error;
          }
          return data;
        });
      })
      .then(function (data) {
        renderResults(data);
      })
      .catch(function (error) {
        // Form values are intentionally preserved so the seller can retry.
        if (error.fieldErrors) {
          Object.keys(error.fieldErrors).forEach(function (field) {
            showFieldError(field, error.fieldErrors[field]);
          });
        }
        showBanner(
          error.message ||
            "Network error. Check that the DukaanDraft server is running and try again."
        );
      })
      .finally(function () {
        setLoading(false);
      });
  });

  /* ----- Sample products ----- */
  function fillSample(sample) {
    var data = SAMPLES[sample];
    if (!data) return;
    form.product_name.value = data.product_name;
    form.category.value = data.category;
    form.price.value = data.price;
    form.features.value = data.features;
    form.target_audience.value = data.target_audience;
    form.language.value = data.language;
    clearErrors();
    hideBanner();
    form.product_name.focus();
  }

  document.querySelectorAll(".sample-chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      fillSample(chip.getAttribute("data-sample"));
    });
  });

  var sampleHero = document.getElementById("sample-hero");
  if (sampleHero) {
    sampleHero.addEventListener("click", function () {
      fillSample("kurti");
      document.getElementById("workspace").scrollIntoView({ behavior: "smooth" });
    });
  }

  /* ----- Loading state ----- */
  function setLoading(isLoading) {
    generateBtn.disabled = isLoading;
    btnSpinner.hidden = !isLoading;
    btnLabel.textContent = isLoading ? "Generating…" : "Generate product content";
    if (isLoading) {
      progressIndex = 0;
      setProgressMessage(PROGRESS_MESSAGES[0]);
      loadingNote.hidden = false;
      progressTimer = setInterval(function () {
        progressIndex = (progressIndex + 1) % PROGRESS_MESSAGES.length;
        setProgressMessage(PROGRESS_MESSAGES[progressIndex]);
      }, 5000);
    } else {
      clearInterval(progressTimer);
      progressTimer = null;
      loadingNote.hidden = true;
    }
  }

  function setProgressMessage(message) {
    loadingNote.textContent = message + " (Local models can take up to a couple of minutes.)";
  }

  /* ----- Results rendering (always as text, never HTML) ----- */
  function renderResults(data) {
    setText("product_title", data.content.product_title);
    setText("marketplace_title", data.content.marketplace_title);
    setText("whatsapp_message", data.content.whatsapp_message);
    setText("product_description", data.content.product_description);
    setText("cta_suggestion", data.content.cta_suggestion);

    var captions = data.content.instagram_captions;
    if (Array.isArray(captions)) {
      for (var i = 0; i < 3; i++) {
        setText("caption_option_" + (i + 1), captions[i] || "");
      }
    }

    renderSellingPoints(data.content.selling_points);
    renderHashtags(data.content.hashtags);

    modelTag.textContent = "Generated with " + data.model + " · runs locally";
    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function setText(id, value) {
    var element = document.getElementById(id);
    if (element) element.textContent = value || "";
  }

  function renderSellingPoints(points) {
    var list = document.getElementById("selling_points");
    var card = document.getElementById("selling-points-card");
    list.textContent = ""; // safe reset of children
    if (!Array.isArray(points) || points.length === 0) {
      card.hidden = true;
      return;
    }
    card.hidden = false;
    points.forEach(function (point) {
      if (typeof point !== "string" || !point.trim()) return;
      var item = document.createElement("li");
      item.textContent = point;
      list.appendChild(item);
    });
  }

  function renderHashtags(hashtags) {
    var container = document.getElementById("hashtags");
    container.textContent = ""; // safe reset of children
    if (!Array.isArray(hashtags) || hashtags.length === 0) return;
    hashtags.forEach(function (tag) {
      if (typeof tag !== "string" || !tag.trim()) return;
      var pill = document.createElement("span");
      pill.className = "hashtag-pill";
      pill.textContent = tag;
      container.appendChild(pill);
    });
  }

  function hideResults() {
    resultsSection.hidden = true;
  }

  /* ----- Errors ----- */
  function showBanner(message) {
    errorBanner.textContent = message;
    errorBanner.hidden = false;
  }

  function hideBanner() {
    errorBanner.hidden = true;
    errorBanner.textContent = "";
  }

  function showFieldError(field, message) {
    var input = form.elements[field];
    var errorEl = document.getElementById("error-" + field);
    if (input) {
      input.classList.add("invalid");
      var fieldWrap = input.closest(".field");
      if (fieldWrap) fieldWrap.classList.add("invalid");
    }
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.hidden = false;
    }
  }

  function clearErrors() {
    form.querySelectorAll(".field-error").forEach(function (el) {
      el.textContent = "";
      el.hidden = true;
    });
    form.querySelectorAll(".invalid").forEach(function (el) {
      el.classList.remove("invalid");
    });
  }

  /* ----- Copy buttons (clipboard API + fallback) ----- */
  document.querySelectorAll(".btn-copy").forEach(function (button) {
    button.addEventListener("click", function () {
      copyText(resolveCopyText(button.getAttribute("data-copy-target")), button);
    });
  });

  var copyAllBtn = document.getElementById("copy-all");
  if (copyAllBtn) {
    copyAllBtn.addEventListener("click", function () {
      var parts = [
        "PRODUCT TITLE",
        getText("product_title"),
        "",
        "MARKETPLACE TITLE",
        getText("marketplace_title"),
        "",
        "INSTAGRAM CAPTION 1",
        getText("caption_option_1"),
        "",
        "INSTAGRAM CAPTION 2",
        getText("caption_option_2"),
        "",
        "INSTAGRAM CAPTION 3",
        getText("caption_option_3"),
        "",
        "WHATSAPP MESSAGE",
        getText("whatsapp_message"),
        "",
        "PRODUCT DESCRIPTION",
        getText("product_description"),
        "",
        "KEY SELLING POINTS",
        resolveSellingPointsText(),
        "",
        "HASHTAGS",
        resolveHashtagsText(),
        "",
        "CALL TO ACTION",
        getText("cta_suggestion"),
      ];
      copyText(parts.join("\n"), copyAllBtn, "Copy all");
    });
  }

  function getText(id) {
    var element = document.getElementById(id);
    return element ? element.textContent : "";
  }

  function resolveSellingPointsText() {
    var items = document.querySelectorAll("#selling_points li");
    return Array.prototype.map.call(items, function (li) {
      return "• " + li.textContent;
    }).join("\n");
  }

  function resolveHashtagsText() {
    var pills = document.querySelectorAll("#hashtags .hashtag-pill");
    return Array.prototype.map.call(pills, function (pill) {
      return pill.textContent;
    }).join(" ");
  }

  function resolveCopyText(target) {
    if (target === "instagram_captions") {
      return [1, 2, 3]
        .map(function (i) {
          return "OPTION " + i + "\n" + getText("caption_option_" + i);
        })
        .join("\n\n");
    }
    if (target === "selling_points") return resolveSellingPointsText();
    if (target === "hashtags") return resolveHashtagsText();
    return getText(target);
  }

  function copyText(text, button, originalLabel) {
    function markCopied() {
      var original = originalLabel || "Copy";
      button.textContent = "Copied!";
      button.classList.add("copied");
      setTimeout(function () {
        button.textContent = original;
        button.classList.remove("copied");
      }, 1600);
    }

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(markCopied, function () {
        if (fallbackCopy(text)) markCopied();
      });
    } else if (fallbackCopy(text)) {
      markCopied();
    }
  }

  function fallbackCopy(text) {
    try {
      var textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "absolute";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(textarea);
      return ok;
    } catch (err) {
      return false;
    }
  }
})();
