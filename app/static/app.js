"use strict";

// ---------------------------------------------------------------------------
// Localization dictionaries (EN/ES/FR) for UI labels and messages
// ---------------------------------------------------------------------------
const I18N = {
  en: {
    language: "Language",
    highVisibility: "High-visibility / screen-reader mode",
    yourContext: "Your context",
    whereNow: "Where are you now?",
    whereGo: "Where do you want to go?",
    accessNeeds: "Accessibility needs",
    needWheelchair: "Wheelchair / step-free",
    needVisual: "Low vision / screen reader",
    needHearing: "Deaf / hard of hearing",
    ticketSection: "Ticket section (optional)",
    minutesToKickoff: "Minutes to kick-off",
    question: "Ask a question (optional)",
    questionHint: "Free text is treated as data only and never as instructions.",
    getHelp: "Get help",
    assistance: "Assistance",
    placeholder: "Fill in your context and select “Get help”. Your answer appears here.",
    grounding:
      "Answers are grounded in verified arena layout data — the assistant never invents facilities.",
  },
  es: {
    language: "Idioma",
    highVisibility: "Modo alto contraste / lector de pantalla",
    yourContext: "Su contexto",
    whereNow: "¿Dónde se encuentra ahora?",
    whereGo: "¿A dónde quiere ir?",
    accessNeeds: "Necesidades de accesibilidad",
    needWheelchair: "Silla de ruedas / sin escalones",
    needVisual: "Baja visión / lector de pantalla",
    needHearing: "Sordo / con dificultad auditiva",
    ticketSection: "Sección del billete (opcional)",
    minutesToKickoff: "Minutos para el inicio",
    question: "Haga una pregunta (opcional)",
    questionHint: "El texto libre se trata solo como datos, nunca como instrucciones.",
    getHelp: "Obtener ayuda",
    assistance: "Asistencia",
    placeholder: "Complete su contexto y seleccione «Obtener ayuda». Su respuesta aparecerá aquí.",
    grounding:
      "Las respuestas se basan en datos verificados de la arena: el asistente nunca inventa instalaciones.",
  },
  fr: {
    language: "Langue",
    highVisibility: "Mode haute visibilité / lecteur d'écran",
    yourContext: "Votre contexte",
    whereNow: "Où êtes-vous actuellement ?",
    whereGo: "Où souhaitez-vous aller ?",
    accessNeeds: "Besoins d'accessibilité",
    needWheelchair: "Fauteuil roulant / sans marches",
    needVisual: "Basse vision / lecteur d'écran",
    needHearing: "Sourd / malentendant",
    ticketSection: "Section du billet (facultatif)",
    minutesToKickoff: "Minutes avant le coup d'envoi",
    question: "Posez une question (facultatif)",
    questionHint: "Le texte libre est traité comme des données, jamais comme des instructions.",
    getHelp: "Obtenir de l'aide",
    assistance: "Assistance",
    placeholder:
      "Renseignez votre contexte et choisissez « Obtenir de l'aide ». Votre réponse apparaîtra ici.",
    grounding:
      "Les réponses s'appuient sur des données de l'arène vérifiées — l'assistant n'invente aucune installation.",
  },
};

const INTENT_LABELS = {
  en: {
    restroom: "Restroom", gate: "Entry gate", seat: "My seat", exit: "Exit",
    first_aid: "First aid", concession: "Food & drink", guest_services: "Guest services",
    water: "Water refill", sensory_room: "Sensory room",
  },
  es: {
    restroom: "Aseos", gate: "Puerta de entrada", seat: "Mi asiento", exit: "Salida",
    first_aid: "Primeros auxilios", concession: "Comida y bebida", guest_services: "Atención al aficionado",
    water: "Fuente de agua", sensory_room: "Sala sensorial",
  },
  fr: {
    restroom: "Toilettes", gate: "Porte d'entrée", seat: "Ma place", exit: "Sortie",
    first_aid: "Premiers secours", concession: "Restauration", guest_services: "Accueil",
    water: "Point d'eau", sensory_room: "Salle sensorielle",
  },
};

const STR = {
  en: {
    crowd: "Occupancy", accessible: "Step-free / accessible", route: "Route", mode: "Mode",
    low: "low", medium: "moderate", high: "high",
    standard: "Standard", screen_reader: "Screen-reader optimized", captioned: "Visual signage",
    reqFailed: "Sorry, something went wrong. Please try again.",
    invalid: "Please check your inputs and try again.",
    rateLimited: "Too many requests — please wait a moment and try again.",
  },
  es: {
    crowd: "Ocupación", accessible: "Sin escalones / accesible", route: "Ruta", mode: "Modo",
    low: "baja", medium: "moderada", high: "alta",
    standard: "Estándar", screen_reader: "Optimizado para lector de pantalla", captioned: "Señalización visual",
    reqFailed: "Lo sentimos, algo salió mal. Inténtelo de nuevo.",
    invalid: "Compruebe sus datos e inténtelo de nuevo.",
    rateLimited: "Demasiadas solicitudes: espere un momento e inténtelo de nuevo.",
  },
  fr: {
    crowd: "Occupation", accessible: "Sans marches / accessible", route: "Itinéraire", mode: "Mode",
    low: "faible", medium: "modérée", high: "élevée",
    standard: "Standard", screen_reader: "Optimisé lecteur d'écran", captioned: "Signalétique visuelle",
    reqFailed: "Désolé, une erreur est survenue. Réessayez.",
    invalid: "Veuillez vérifier vos saisies et réessayer.",
    rateLimited: "Trop de requêtes — patientez un instant puis réessayez.",
  },
};

const DOTS = { low: "●○○", medium: "●●○", high: "●●●" };

// ---------------------------------------------------------------------------
// Global state & utility selectors
// ---------------------------------------------------------------------------
let currentLang = "en";
const $ = (id) => document.getElementById(id);

function t(dict) {
  return dict[currentLang] || dict.en;
}

// ---------------------------------------------------------------------------
// App bootstrapping & Event bindings
// ---------------------------------------------------------------------------
async function init() {
  applyLanguage("en");
  bindEvents();
  await loadArena();
}

function bindEvents() {
  $("language").addEventListener("change", (e) => applyLanguage(e.target.value));
  $("contrast-toggle").addEventListener("click", toggleContrast);
  $("assist-form").addEventListener("submit", onSubmit);
}

async function loadArena() {
  try {
    const res = await fetch("/api/arena");
    if (!res.ok) throw new Error("arena metadata unavailable");
    const data = await res.json();
    window.__arena = data; // store metadata for language hot-swapping
    window.__intents = data.intents;
    renderLocationOptions();
    refreshIntentOptions(data.intents);
    const a = data.arena;
    $("arena-meta").textContent = `${a.name} · ${a.fifa_name} · ${a.city}`;
  } catch (err) {
    $("arena-meta").textContent = "";
    renderError(t(STR).reqFailed);
  }
}

function populateSelect(select, optionsList) {
  select.innerHTML = "";
  for (const [val, text] of optionsList) {
    const opt = document.createElement("option");
    opt.value = val;
    opt.textContent = text;
    select.appendChild(opt);
  }
}

function refreshIntentOptions(intents) {
  const labels = INTENT_LABELS[currentLang] || INTENT_LABELS.en;
  const select = $("destination_intent");
  const previous = select.value;
  populateSelect(select, intents.map((i) => [i, labels[i] || i]));
  if (previous) select.value = previous;
}

function renderLocationOptions() {
  const data = window.__arena;
  if (!data) return;
  const select = $("current_location");
  const previous = select.value;
  populateSelect(
    select,
    data.zones.map((z) => [z.id, (z.name && (z.name[currentLang] || z.name.en)) || z.id])
  );
  if (previous) select.value = previous;
}

// ---------------------------------------------------------------------------
// Translation & display adjustments
// ---------------------------------------------------------------------------
function applyLanguage(lang) {
  currentLang = lang in I18N ? lang : "en";
  document.documentElement.lang = currentLang; // standard screen reader lang update
  $("language").value = currentLang;
  const dict = I18N[currentLang];
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) el.textContent = dict[key];
  });
  if (window.__intents) refreshIntentOptions(window.__intents);
  renderLocationOptions();
}

function toggleContrast() {
  const btn = $("contrast-toggle");
  const on = btn.getAttribute("aria-pressed") !== "true";
  btn.setAttribute("aria-pressed", String(on));
  document.body.classList.toggle("hi-vis", on);
  // High contrast mode auto-toggles screen reader compatibility checks
  const visual = document.querySelector('input[name="need"][value="visual"]');
  if (visual) visual.checked = on;
}

// ---------------------------------------------------------------------------
// Form submissions & payload compilation
// ---------------------------------------------------------------------------
function collectContext() {
  const needs = Array.from(document.querySelectorAll('input[name="need"]:checked')).map(
    (el) => el.value
  );
  const ticket = $("ticket_section").value.trim();
  const question = $("question").value.trim();
  const payload = {
    language: $("language").value,
    current_location: $("current_location").value,
    destination_intent: $("destination_intent").value,
    accessibility_needs: needs.length ? needs : ["none"],
    minutes_to_kickoff: parseInt($("minutes_to_kickoff").value, 10),
  };
  if (ticket) payload.ticket_section = ticket;
  if (question) payload.question = question;
  return payload;
}

async function onSubmit(event) {
  event.preventDefault();
  const result = $("result");
  result.setAttribute("aria-busy", "true");
  try {
    const res = await fetch("/api/guide", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectContext()),
    });
    if (res.status === 422) return renderError(t(STR).invalid);
    if (res.status === 429) return renderError(t(STR).rateLimited);
    if (!res.ok) return renderError(t(STR).reqFailed);
    renderResult(await res.json());
  } catch (err) {
    renderError(t(STR).reqFailed);
  } finally {
    result.setAttribute("aria-busy", "false");
  }
}

function createBadge(text, extraClass) {
  const span = document.createElement("span");
  span.className = "badge" + (extraClass ? " " + extraClass : "");
  span.textContent = text;
  return span;
}

function renderResult(data) {
  const s = STR[currentLang] || STR.en;
  const result = $("result");
  result.innerHTML = "";

  const answer = document.createElement("p");
  answer.className = "answer";
  answer.textContent = data.answer;
  result.appendChild(answer);

  // Metadata information badges
  const grid = document.createElement("div");
  grid.className = "meta-grid";

  grid.appendChild(createBadge(data.amenity.name));

  const occBadge = createBadge("", "crowd-" + data.occupancy_level);
  const dots = document.createElement("span");
  dots.className = "dots";
  dots.setAttribute("aria-hidden", "true");
  dots.textContent = DOTS[data.occupancy_level] || "";
  occBadge.appendChild(dots);
  const occText = document.createElement("span");
  occText.textContent = `${s.crowd}: ${s[data.occupancy_level]}`;
  occBadge.appendChild(occText);
  grid.appendChild(occBadge);

  if (data.amenity.accessible) grid.appendChild(createBadge("♿ " + s.accessible));
  grid.appendChild(createBadge(`${s.mode}: ${s[data.accessibility_mode] || data.accessibility_mode}`));
  result.appendChild(grid);

  if (data.urgency) result.appendChild(notice(data.urgency, true));
  if (data.alternatives_note) result.appendChild(notice(data.alternatives_note, false));

  // Render navigation route steps
  if (data.path_steps && data.path_steps.length) {
    const heading = document.createElement("h3");
    heading.textContent = s.route;
    result.appendChild(heading);
    const ol = document.createElement("ol");
    ol.className = "route-steps";
    for (const step of data.path_steps) {
      const li = document.createElement("li");
      li.textContent = step.instruction;
      const means = document.createElement("span");
      means.className = "step-means";
      means.textContent = step.means;
      li.appendChild(means);
      ol.appendChild(li);
    }
    result.appendChild(ol);
  }
}

function notice(text, urgent) {
  const div = document.createElement("div");
  div.className = "notice" + (urgent ? " urgent" : "");
  div.textContent = text;
  return div;
}

function renderError(message) {
  const result = $("result");
  result.innerHTML = "";
  const p = document.createElement("p");
  p.className = "error";
  p.setAttribute("role", "alert");
  p.textContent = message;
  result.appendChild(p);
}

document.addEventListener("DOMContentLoaded", init);
