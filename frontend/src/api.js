import axios from "axios";
import { getAuthToken, refreshAccessToken, clearAuth } from "./auth";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

// ✅ REQUEST INTERCEPTOR: Auto-attach token
API.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ✅ RESPONSE INTERCEPTOR: Handle 401 errors globally
API.interceptors.response.use(
  (response) => response, // Pass through successful responses
  async (error) => {
    const originalRequest = error.config;

    // If 401 and we haven't tried refreshing yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // ✅ Prevent infinite loops

      try {
        const newToken = await refreshAccessToken();
        
        if (newToken) {
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return API(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed - logout user
        clearAuth();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    // If refresh also fails, or it's a different error
    if (error.response?.status === 401) {
      clearAuth();
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export default API;
