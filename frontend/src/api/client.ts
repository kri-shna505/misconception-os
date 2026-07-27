const API_BASE_URL = "http://127.0.0.1:8000/api";

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json();

  if (!response.ok) {
    const message = data?.detail || "API request failed";
    throw new Error(message);
  }

  return data as T;
}