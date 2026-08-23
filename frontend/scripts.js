const form = document.getElementById('search-form');
const linkForm = document.getElementById('link-search-form');
const loader = document.getElementById('loader');
const submitBtn = document.getElementById('submit-btn');
const reloadBtn = document.getElementById('reload-last');
const marketplaceSelect = document.getElementById('marketplace-select');
const searchTypeSelect = document.getElementById('search_type_select');
const allMarketsCheckbox = document.getElementById('search_all_checkbox');

form.addEventListener('submit', async (e) => {
  if (allMarketsCheckbox && allMarketsCheckbox.checked) {
    e.preventDefault();
    loader.style.display = 'block';
    submitBtn.disabled = true;
    reloadBtn.disabled = true;

    const queryInput = document.querySelector('#search-form input[name="query"]');
    const scrolls = 1;
    const max_cards = 3;

    try {
      const formData = new FormData();
      formData.append("query", queryInput.value);
      formData.append("search_type", searchTypeSelect.value);
      formData.append("scrolls", scrolls);
      formData.append("max_cards", max_cards);

      const response = await fetch('/api/search-all', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        alert(data.error || 'Ошибка при поиске');
      } else {
        // ✅ Сбрасываем форму, чтобы не было повторного submit при reload
        form.reset();
        allMarketsCheckbox.checked = false;
        updateAllMarketsCheckbox();

        // ✅ После сброса формы можно делать reload без повторного запроса
        setTimeout(() => {
          location.reload();
        }, 500);
      }
    } catch (err) {
      alert('Ошибка при запросе поиска на всех МП');
      console.error(err);
    } finally {
      loader.style.display = 'none';
      submitBtn.disabled = false;
      reloadBtn.disabled = false;
    }
  } else {
    loader.style.display = 'block';
    submitBtn.disabled = true;
    reloadBtn.disabled = true;
  }
});

// ✅ Форма поиска по ссылке
if (linkForm) {
  linkForm.addEventListener('submit', () => {
    loader.style.display = 'block';
    const btn = linkForm.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    reloadBtn.disabled = true;
  });
}

// ✅ Перепарсить
reloadBtn.addEventListener('click', async () => {
  loader.style.display = 'block';
  reloadBtn.disabled = true;
  submitBtn.disabled = true;

  const selectedMarketplace = marketplaceSelect.value;

  try {
    const response = await fetch(`/last-results-parse?marketplace=${encodeURIComponent(selectedMarketplace)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Неизвестная ошибка сервера');
    }

    const result = await response.json();

    if (result.error) {
      alert(result.error);
    } else {
      location.reload();
    }
  } catch (e) {
    alert('Ошибка при перепарсинге последнего результата');
    console.error(e);
  } finally {
    loader.style.display = 'none';
    reloadBtn.disabled = false;
    submitBtn.disabled = false;
  }
});

// ✅ Тоггл характеристик
function toggleChars(id) {
  const el = document.getElementById(id);
  if (!el) return;

  if (el.style.display === "none" || el.style.display === "") {
    el.style.display = "block";
  } else {
    el.style.display = "none";
  }

  const btn = document.querySelector(`button[onclick="toggleChars('${id}')"]`);
  if (btn) {
    btn.textContent = (el.style.display === "block") ? "Скрыть характеристики" : "Показать характеристики";
  }
}

// ✅ Управление чекбоксом «искать на всех»
function updateAllMarketsCheckbox() {
  if (searchTypeSelect.value === "name") {
    allMarketsCheckbox.disabled = false;
  } else {
    allMarketsCheckbox.checked = false;
    allMarketsCheckbox.disabled = true;
  }
}

// Подключаем события
["change", "click", "keyup", "blur", "focus"].forEach(eventType => {
  searchTypeSelect.addEventListener(eventType, updateAllMarketsCheckbox);
});

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
  allMarketsCheckbox.checked = false;
  updateAllMarketsCheckbox();
});
