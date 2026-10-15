import { API_URL } from "../config";

export class ApiError extends Error {
  constructor(status, detail, code) {
    super(detail || "Ошибка запроса");
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export async function api(path, options = {}) {
  const { headers, ...rest } = options;
  // FormData сам выставляет Content-Type с boundary — руками его трогать нельзя.
  const isFormData = rest.body instanceof FormData;

  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include", // без этого cookie "pid" не полетит
    ...rest,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(headers || {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail, body.code);
  }

  if (res.status === 204) return null;
  return res.json();
}
