const TECHSTORE_API = "http://127.0.0.1:8000";

function getAuthToken() {
  return localStorage.getItem("techstore_token") || "";
}

function getAuthUser() {
  try {
    return JSON.parse(localStorage.getItem("techstore_user") || "null");
  } catch {
    return null;
  }
}

function authHeaders(extra = {}) {
  const token = getAuthToken();
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function setAuthSession(data) {
  localStorage.setItem("techstore_token", data.token);
  localStorage.setItem("techstore_user", JSON.stringify(data.user));
}

function clearAuthSession() {
  localStorage.removeItem("techstore_token");
  localStorage.removeItem("techstore_user");
}

function formatMoney(value) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(Number(value || 0));
}

function updateCommerceNav() {
  const cartLink = document.querySelector('nav a[href="cart.html"]');
  if (!cartLink || document.getElementById("auth-nav-tools")) return;

  const parent = cartLink.parentElement;
  const user = getAuthUser();
  const wrapper = document.createElement("div");
  wrapper.id = "auth-nav-tools";
  wrapper.className =
    "hidden items-center gap-3 text-xs font-bold uppercase tracking-wider sm:flex";

  if (user) {
    wrapper.innerHTML = `
      ${
        user.role === "admin"
          ? '<a href="admin.html" class="inline-flex items-center gap-1 rounded-full bg-red-600 px-3 py-1.5 text-white hover:bg-red-700"><i class="fa-solid fa-chart-line"></i>Admin</a>'
          : ""
      }
      <a href="account.html" class="inline-flex max-w-[150px] items-center gap-2 truncate rounded-full bg-white/10 px-3 py-1.5 hover:bg-white/15">
        <i class="fa-solid fa-user"></i><span class="truncate">${user.name}</span>
      </a>
      <button type="button" class="hover:text-red-400" onclick="logoutTechStore()">Thoát</button>
    `;
  } else {
    wrapper.innerHTML =
      '<a href="login.html" class="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-black hover:bg-red-600 hover:text-white"><i class="fa-solid fa-user"></i>Đăng nhập</a>';
  }
  parent.insertBefore(wrapper, cartLink);
}

async function logoutTechStore() {
  try {
    await fetch(`${TECHSTORE_API}/api/auth/logout`, {
      method: "POST",
      headers: authHeaders(),
    });
  } catch {
    // Local logout still works if backend is offline.
  }
  clearAuthSession();
  window.location.href = "login.html";
}

function syncCartBadge() {
  const badge = document.getElementById("cart-count");
  if (!badge) return;
  const cart = JSON.parse(localStorage.getItem("techstore_cart") || "[]");
  badge.innerText = cart.reduce((sum, item) => sum + Number(item.quantity || 1), 0);
}

function productMediaHtml(product, classes = "h-full w-full object-contain") {
  const icon = product.icon || "fa-box";
  if (icon.includes(".") || icon.includes("/") || icon.startsWith("http")) {
    return `<img src="${icon}" alt="${product.name}" class="${classes}">`;
  }
  return `<i class="fa-solid ${icon} text-4xl text-black"></i>`;
}

function addProductToCart(product, quantity = 1) {
  const cart = JSON.parse(localStorage.getItem("techstore_cart") || "[]");
  const existing = cart.find((item) => String(item.id) === String(product.id));
  if (existing) {
    existing.quantity = Number(existing.quantity || 1) + Number(quantity || 1);
  } else {
    cart.push({ ...product, quantity: Number(quantity || 1) });
  }
  localStorage.setItem("techstore_cart", JSON.stringify(cart));
  syncCartBadge();
}

function toast(message) {
  const oldToast = document.getElementById("techstore-toast");
  if (oldToast) oldToast.remove();
  const box = document.createElement("div");
  box.id = "techstore-toast";
  box.className =
    "fixed bottom-5 right-5 z-[999] rounded-lg border-l-4 border-red-600 bg-black px-4 py-3 text-sm font-bold text-white shadow-2xl";
  box.textContent = message;
  document.body.appendChild(box);
  setTimeout(() => box.remove(), 2400);
}

document.addEventListener("DOMContentLoaded", () => {
  updateCommerceNav();
  syncCartBadge();
});
