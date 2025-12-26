// src/auth.js
// ✅ Central authentication utility - single source of truth for all auth operations

const API_BASE = "http://127.0.0.1:8000";

// ==================== TOKEN STORAGE ====================

export function getAuthToken() {
  const token = localStorage.getItem("token");
  if (!token) return null;

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (payload.exp * 1000 < Date.now()) {
      clearAuth(); // ✅ Use centralized clear
      return null;
    }
    return token;
  } catch {
    clearAuth();
    return null;
  }
}

export function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

export function setTokens(accessToken, refreshToken) {
  localStorage.setItem("token", accessToken);
  if (refreshToken) {
    localStorage.setItem("refresh_token", refreshToken);
  }
}

export function getUser() {
  const userRaw = localStorage.getItem("user");
  if (!userRaw) return null;
  try {
    return JSON.parse(userRaw);
  } catch {
    return null;
  }
}

export function setUser(user) {
  localStorage.setItem("user", JSON.stringify(user));
}

// ✅ NEW: Single function to clear all auth data
export function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

// ==================== TOKEN REFRESH ====================

let isRefreshing = false; // ✅ Prevent duplicate refresh calls
let refreshSubscribers = [];

function onRefreshed(newToken) {
  refreshSubscribers.forEach(callback => callback(newToken));
  refreshSubscribers = [];
}

function addRefreshSubscriber(callback) {
  refreshSubscribers.push(callback);
}

// ✅ NEW: Silent token refresh
export async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  
  if (!refreshToken) {
    clearAuth();
    return null;
  }

  // Prevent multiple simultaneous refresh attempts
  if (isRefreshing) {
    return new Promise(resolve => {
      addRefreshSubscriber(token => resolve(token));
    });
  }

  isRefreshing = true;

  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      throw new Error("Refresh failed");
    }

    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    
    isRefreshing = false;
    onRefreshed(data.access_token);
    
    return data.access_token;
  } catch (error) {
    isRefreshing = false;
    clearAuth();
    window.location.href = "/login"; // ✅ Force redirect on refresh failure
    return null;
  }
}

// ==================== LOGOUT ====================

// ✅ NEW: Logout with backend invalidation
export async function logout() {
  const token = getAuthToken();
  
  if (token) {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
    } catch (error) {
      console.error("Logout error:", error);
      // Still clear local tokens even if backend call fails
    }
  }
  
  clearAuth();
  window.location.href = "/login";
}

// ==================== AUTH CHECK ====================

// ✅ NEW: Check if user is authenticated
export function isAuthenticated() {
  return !!getAuthToken();
}