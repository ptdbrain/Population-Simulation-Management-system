(function (global) {
  const API_BASE_URL = global.__PSMS_API_BASE_URL__ || window.location.origin || "http://localhost:8000";
  const STORAGE_KEYS = {
    accessToken: "psms_access_token",
    refreshToken: "psms_refresh_token",
    profile: "psms_profile",
  };

  const jsonHeaders = { "Content-Type": "application/json" };

  const decodeJwt = (token) => {
    try {
      const payload = token.split(".")[1];
      const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
      return JSON.parse(decodeURIComponent(escape(decoded)));
    } catch (err) {
      console.warn("Cannot decode token", err);
      return null;
    }
  };

  const persistTokens = ({ access_token, refresh_token }) => {
    if (access_token) {
      localStorage.setItem(STORAGE_KEYS.accessToken, access_token);
    }
    if (refresh_token) {
      localStorage.setItem(STORAGE_KEYS.refreshToken, refresh_token);
    }
  };

  const clearSession = () => {
    Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
    localStorage.removeItem("userRole"); // legacy key
  };

  const getAccessToken = () => localStorage.getItem(STORAGE_KEYS.accessToken);
  const getRefreshToken = () => localStorage.getItem(STORAGE_KEYS.refreshToken);

  const getSessionPayload = () => {
    const token = getAccessToken();
    if (!token) return null;
    return decodeJwt(token);
  };

  const determineRoleKey = () => {
    const payload = getSessionPayload();
    const roles = (payload?.roles || []).map((r) => (r || "").toLowerCase());
    if (roles.includes("admin")) return "admin";
    if (roles.includes("leader") || roles.includes("manager")) return "leader";
    if (roles.includes("citizen")) return "citizen";
    return roles[0] || "citizen";
  };

  const attachAuthHeader = (headers = new Headers()) => {
    const token = getAccessToken();
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return headers;
  };

  const parseResponse = async (response) => {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json();
    }
    return response.text();
  };

  const apiFetch = async (path, options = {}, retry = true) => {
    const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
    const headers = attachAuthHeader(new Headers(options.headers || {}));

    const fetchOptions = {
      method: options.method || "GET",
      headers,
      body: options.body,
    };

    if (!(fetchOptions.body instanceof FormData) && fetchOptions.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(url, fetchOptions);

    if (response.status === 401 && retry && getRefreshToken()) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        return apiFetch(path, options, false);
      }
    }

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const data = await response.json();
        detail = data.detail || JSON.stringify(data);
      } catch (err) {
        // ignore JSON parse errors
      }
      throw new Error(detail || `Request failed (${response.status})`);
    }

    return parseResponse(response);
  };

  const refreshAccessToken = async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearSession();
      return false;
    }

    const data = await response.json();
    persistTokens(data);
    return true;
  };

  const fetchCurrentUser = async (force = false) => {
    if (!force) {
      const cached = localStorage.getItem(STORAGE_KEYS.profile);
      if (cached) {
        try {
          return JSON.parse(cached);
        } catch {
          // ignore malformed cache
        }
      }
    }
    const profile = await apiFetch("/api/users/me");
    localStorage.setItem(STORAGE_KEYS.profile, JSON.stringify(profile));
    return profile;
  };

  const login = async (username, password) => {
    const body = new URLSearchParams();
    body.append("username", username);
    body.append("password", password);

    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Đăng nhập thất bại");
    }

    const data = await response.json();
    persistTokens(data);
    const payload = getSessionPayload();
    const profile = await fetchCurrentUser(true);
    const roleKey = determineRoleKey();
    localStorage.setItem("userRole", roleKey); // giữ cho logic cũ hoạt động nếu cần
    return { tokens: data, payload, profile };
  };

  const logout = async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) {
        await apiFetch(
          "/api/auth/logout",
          {
            method: "POST",
            headers: jsonHeaders,
            body: JSON.stringify({ refresh_token: refreshToken }),
          },
          false
        );
      }
    } catch (err) {
      console.warn("Cannot logout remotely", err);
    } finally {
      clearSession();
    }
  };

  const fetchHouseholds = async ({ skip = 0, limit = 50 } = {}) => {
    const query = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    return apiFetch(`/api/households?${query.toString()}`);
  };

  const register = async ({ username, password, full_name, email, phone, role = "citizen", role_secret = null }) => {
    const body = {
      username,
      password,
      full_name: full_name || null,
      email: email || null,
      phone: phone || null,
      role,
      role_secret,
    };
    const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Đăng ký thất bại");
    }
    return res.json();
  };

  global.PSMSApi = {
    API_BASE_URL,
    login,
    logout,
    apiFetch,
    refreshAccessToken,
    fetchCurrentUser,
    fetchHouseholds,
    register,
    getSessionPayload,
    getProfileCache: () => {
      const cached = localStorage.getItem(STORAGE_KEYS.profile);
      if (!cached) return null;
      try {
        return JSON.parse(cached);
      } catch {
        return null;
      }
    },
    clearSession,
    determineRole: determineRoleKey,
  };
})(window);

