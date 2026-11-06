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
document.querySelectorAll(".add-to-cart").forEach((button) => {
  button.addEventListener("click", () => {
    const card = button.closest(".product-card");

    const product = {
      id: card.dataset.id,
      name: card.dataset.name,
      price: Number(card.dataset.price),
    };

    // محصول دیجیتال را فقط یک‌بار می‌شود خرید
    if (cart.some((item) => item.id === product.id)) {
      button.textContent = "قبلاً اضافه شده";
      return;
    }

    cart.push(product);
    saveCart();
    updateCartCount();
    button.textContent = "✓ اضافه شد";
  });
});