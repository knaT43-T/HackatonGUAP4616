const API_URL = import.meta.env.VITE_API_URL;

export class ApiError extends Error {
  constructor(status, detail, code) {
    super(detail || "Ошибка запроса");
    this.status = status;
    this.code = code;
  }
}

export async function api(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail, body.code);
  }

  if (res.status === 204) return null;
  return res.json();
}
