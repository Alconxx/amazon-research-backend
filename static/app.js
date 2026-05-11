const API = "/api/analyze";

let lang = "en";

const texts = {
  en: {
    title: "Amazon Product Research",
    subtitle: "Enter a keyword to analyze Amazon product opportunities.",
    placeholder: "e.g. spa headbands",
    analyze: "Analyze",
    loading: "Analyzing…",
    noData: "No data available yet. Connect data source (Keepa)."
  },
  es: {
    title: "Investigación de Productos Amazon",
    subtitle: "Escribe una palabra clave para analizar oportunidades.",
    placeholder: "ej. bandas spa",
    analyze: "Analizar",
    loading: "Analizando…",
    noData: "Datos no disponibles aún. Conecta la fuente (Keepa)."
  }
};

function setLang(l) {
  lang = l;
  document.getElementById("title").innerText = texts[l].title;
  document.getElementById("subtitle").innerText = texts[l].subtitle;
  document.getElementById("keyword").placeholder = texts[l].placeholder;
  document.getElementById("analyzeBtn").innerText = texts[l].analyze;
}

async function analyze() {
  const keyword = document.getElementById("keyword").value.trim();
  if (!keyword) return;

  document.getElementById("loading").innerText = texts[lang].loading;
  document.getElementById("loading").classList.remove("hidden");
  document.getElementById("results").classList.add("hidden");

  const response = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword, competitors: [] })
  });

  const data = await response.json();

  document.getElementById("loading").classList.add("hidden");

  let html = `<strong>Keyword:</strong> ${data.keyword}<br/><br/>`;

  if (!data.competitors || data.competitors.length === 0) {
    html += texts[lang].noData;
  } else {
    html += `<ul>`;
    data.competitors.forEach(c => {
      html += `<li>${c.asin}</li>`;
    });
    html += `</ul>`;
  }

  document.getElementById("results").innerHTML = html;
  document.getElementById("results").classList.remove("hidden");
}

// default language
setLang("en");
