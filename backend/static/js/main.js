const menuToggle = document.querySelector(".menu-toggle");
const mainNav = document.querySelector("#main-nav");

menuToggle.addEventListener("click", () => {
  const isOpen = mainNav.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", isOpen);
});
const filterButtons = document.querySelectorAll(".filter-btn");
const cards = document.querySelectorAll(".product-card");

filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const filter = btn.dataset.filter;

    // دکمه‌ی فعال را عوض کن
    filterButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");

    // کارت‌ها را نشان بده یا مخفی کن
    cards.forEach((card) => {
      const shouldShow = filter === "all" || card.dataset.type === filter;
      card.classList.toggle("hidden", !shouldShow);
    });
  });
});

// ----- توابع کمکی برای ذخیره‌سازی -----
function loadCart() {
  try {
    return JSON.parse(localStorage.getItem("cart")) || [];
  } catch {
    return [];
  }
}

function saveCart() {
  localStorage.setItem("cart", JSON.stringify(cart));
}

function updateCartCount() {
  document.querySelector("#cart-count").textContent =
    cart.length.toLocaleString("fa-IR");
}

// ----- وضعیت سبد -----
let cart = loadCart();
updateCartCount();

// ----- افزودن به سبد -----
// ===== سبد خرید (ارتباط با سرور) =====
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const cartCountEl = document.querySelector("#cart-count");

function showCartCount(count) {
  cartCountEl.textContent = Number(count).toLocaleString("fa-IR");
}

// نمایش اولیه با ارقام فارسی
showCartCount(cartCountEl.dataset.count);

document.querySelectorAll(".add-to-cart").forEach((button) => {
  button.addEventListener("click", async () => {
    const card = button.closest("[data-id]");
    button.disabled = true;

    try {
      const response = await fetch(`/cart/add/${card.dataset.id}/`, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
      });
      const data = await response.json();

      if (response.ok) {
        showCartCount(data.count);
        button.textContent = "✓ در سبد شما";
      } else {
        button.textContent = data.error || "خطا";
      }
    } catch (error) {
      button.textContent = "خطا؛ دوباره تلاش کنید";
      button.disabled = false;
    }
  });
});